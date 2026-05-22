use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tauri::{Emitter, Manager};
use tokio::sync::Mutex;
use tokio::time::{sleep, Duration};

mod api;
mod commands;
mod security;
mod sidecar;
mod window_manager;

use api::server::{find_free_port_sync, start_internal_server};
use commands::security::{delete_api_key, get_api_key, set_api_key};
use commands::settings::{check_for_update, get_general_settings, install_update, is_auto_launch_enabled, load_settings, set_auto_launch, set_general_settings};
use commands::shortcut::{get_shortcut, update_shortcut, CurrentShortcut, SharedShortcut};
use commands::system::{get_ai_service_config, restart_ai_service, show_notification, toggle_command_center};
use commands::tools::{manage_todo, set_reminder};
use commands::window::{create_window, destroy_window, focus_window, list_windows, update_window_position, update_window_size};
use sidecar::manager::{kill_orphan_sidecars, start_sidecar, stop_sidecar, SharedSidecar};
use window_manager::registry::{create_floating_window, monitor_recovery, WindowRegistry};

/// Runtime configuration shared across commands (e.g. internal server port).
#[derive(Default)]
pub struct AppRuntimeConfig {
    pub rust_port: std::sync::Mutex<u16>,
    pub internal_token: std::sync::Mutex<String>,
}

async fn restore_windows(app: &tauri::AppHandle, registry: &Arc<std::sync::Mutex<WindowRegistry>>, port: u16, api_token: &str) {
    let client = reqwest::Client::new();
    let resp = client
        .get(format!("http://127.0.0.1:{}/api/v1/windows", port))
        .header("Authorization", format!("Bearer {}", api_token))
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await;

    match resp {
        Ok(r) => {
            if let Ok(json) = r.json::<serde_json::Value>().await {
                if let Some(windows) = json.get("data").and_then(|d| d.as_array()) {
                    for win in windows {
                        let id = win.get("id").and_then(|v| v.as_str()).unwrap_or("");
                        let wtype = win.get("type").and_then(|v| v.as_str()).unwrap_or("custom");
                        if id.is_empty() { continue; }

                        let config = serde_json::json!({
                            "position": win.get("position").cloned(),
                            "size": win.get("size").cloned(),
                            "data": win.get("data").cloned(),
                        });

                        let _ = create_floating_window(app, registry, id.to_string(), wtype.to_string(), config);
                    }
                }
            }
        }
        Err(e) => {
            eprintln!("Failed to restore windows: {}", e);
        }
    }
}

fn monitor_hash(monitors: &[tauri::Monitor]) -> String {
    let mut parts: Vec<String> = monitors
        .iter()
        .map(|m| {
            let name = m.name().cloned().unwrap_or_default();
            let sz = m.size();
            let pos = m.position();
            format!("{}:{}x{}+{}+{}", name, sz.width, sz.height, pos.x, pos.y)
        })
        .collect();
    parts.sort();
    parts.join(";")
}

async fn monitor_change_watcher(
    app: tauri::AppHandle,
    registry: Arc<std::sync::Mutex<WindowRegistry>>,
) {
    let mut last_hash = String::new();
    let mut last_monitors: Vec<tauri::Monitor> = Vec::new();

    loop {
        sleep(Duration::from_secs(5)).await;

        let monitors = match app.available_monitors() {
            Ok(m) => m,
            Err(_) => continue,
        };

        let hash = monitor_hash(&monitors);
        if hash != last_hash && !last_hash.is_empty() {
            let windows = {
                let reg = registry.lock().unwrap();
                reg.all_windows()
            };

            let updates = monitor_recovery(&windows, &last_monitors, &monitors);

            for (id, (x, y)) in updates {
                let label = format!("floating-{}", id);
                if let Some(window) = app.get_webview_window(&label) {
                    let _ = window.set_position(tauri::Position::Physical(tauri::PhysicalPosition { x, y }));
                }
                {
                    let mut reg = registry.lock().unwrap();
                    if let Some(win) = reg.get_mut(&id) {
                        win.position = (x, y);
                    }
                }
                app.emit(
                    "window-state-changed",
                    serde_json::json!({
                        "action": "moved",
                        "payload": { "id": id, "position": {"x": x, "y": y} }
                    }),
                ).ok();
            }
        }

        last_hash = hash;
        last_monitors = monitors;
    }
}

fn toggle_cc(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("command-center") {
        if let Ok(true) = window.is_visible() {
            let _ = window.hide();
        } else {
            let _ = window.center();
            let _ = window.show();
            let _ = window.set_focus();
        }
    }
}

/// Watchdog that monitors the sidecar process and restarts it with exponential backoff.
async fn sidecar_watchdog(
    app: tauri::AppHandle,
    registry: Arc<std::sync::Mutex<WindowRegistry>>,
    sidecar: SharedSidecar,
    internal_token: String,
    rust_port: u16,
    stop_flag: Arc<AtomicBool>,
) {
    let mut consecutive_failures = 0u32;
    let max_backoff_secs = 30u64;

    loop {
        if stop_flag.load(Ordering::Relaxed) {
            eprintln!("[watchdog] Stop flag set, exiting watchdog");
            break;
        }
        sleep(Duration::from_secs(5)).await;

        let is_alive = {
            let mut state = sidecar.lock().await;
            if let Some(ref mut handle) = *state {
                // Check if child process has exited
                match handle.child.try_wait() {
                    Ok(None) => true,  // still running
                    Ok(Some(_)) => false, // exited
                    Err(_) => false,
                }
            } else {
                false // not even started
            }
        };

        if is_alive {
            consecutive_failures = 0;
            continue;
        }

        // Sidecar is dead or missing — attempt restart
        eprintln!("[watchdog] Sidecar not alive, attempting restart (failure #{})", consecutive_failures + 1);

        // Stop any residual state
        stop_sidecar(&sidecar).await;

        let backoff = std::cmp::min(2u64.saturating_pow(consecutive_failures), max_backoff_secs);
        if backoff > 0 {
            sleep(Duration::from_secs(backoff)).await;
        }

        match start_sidecar(&app, &sidecar, &internal_token, rust_port, Some(stop_flag.clone())).await {
            Ok(port) => {
                eprintln!("[watchdog] Sidecar restarted on port {}", port);
                consecutive_failures = 0;

                // Fetch fresh token and restore windows
                let api_token = {
                    let state = sidecar.lock().await;
                    state.as_ref().map(|h| h.tokens.api_token.clone()).unwrap_or_else(|| "dev-token".to_string())
                };

                sleep(Duration::from_secs(1)).await;
                restore_windows(&app, &registry, port, &api_token).await;

                // Notify frontend
                app.emit("ai-service-ready", serde_json::json!({
                    "port": port,
                    "apiToken": api_token,
                    "restarted": true,
                })).ok();
            }
            Err(e) => {
                eprintln!("[watchdog] Failed to restart sidecar: {}", e);
                consecutive_failures += 1;
            }
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let registry = Arc::new(std::sync::Mutex::new(WindowRegistry::new()));
    let sidecar: SharedSidecar = Arc::new(Mutex::new(None));
    let sidecar_clone = sidecar.clone();

    let registry_clone = registry.clone();

    let stop_flag = Arc::new(AtomicBool::new(false));
    let stop_flag_setup = stop_flag.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            None,
        ))
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, _shortcut, event| {
                    use tauri_plugin_global_shortcut::ShortcutState;
                    if event.state == ShortcutState::Pressed {
                        toggle_cc(app);
                    }
                })
                .build(),
        )
        .manage(registry)
        .manage(sidecar)
        .manage(stop_flag)
        .invoke_handler(tauri::generate_handler![
            toggle_command_center,
            get_ai_service_config,
            restart_ai_service,
            show_notification,
            create_window,
            destroy_window,
            focus_window,
            list_windows,
            update_window_position,
            update_window_size,
            manage_todo,
            set_reminder,
            set_api_key,
            get_api_key,
            delete_api_key,
            get_shortcut,
            update_shortcut,
            get_general_settings,
            set_general_settings,
            set_auto_launch,
            is_auto_launch_enabled,
            check_for_update,
            install_update,
        ])
        .setup(move |app| {
            // Initialize shortcut state with persistence
            let app_data_dir = app.path().app_data_dir().unwrap_or_else(|_| {
                std::path::PathBuf::from(".")
            });
            let current = CurrentShortcut::new(app_data_dir);
            let shortcut_key = current.key.clone();
            let shortcut_state: SharedShortcut = Arc::new(std::sync::Mutex::new(current));
            app.manage(shortcut_state);

            // Runtime config for restart operations
            let runtime_config = AppRuntimeConfig::default();
            app.manage(runtime_config);

            // Register the persisted shortcut
            use tauri_plugin_global_shortcut::GlobalShortcutExt;
            if let Ok(shortcut) = shortcut_key.parse::<tauri_plugin_global_shortcut::Shortcut>() {
                if let Err(e) = app.global_shortcut().register(shortcut) {
                    eprintln!("Failed to register global shortcut {}: {}", shortcut_key, e);
                }
            }

            // Generate shared internal token for Rust-Python IPC
            let internal_token = security::token::generate_secure_token(32);

            // Find a free port for the internal HTTP server
            let rust_port = find_free_port_sync().unwrap_or(9595);

            // Persist runtime config for restart command
            {
                let rt_cfg = app.state::<AppRuntimeConfig>();
                *rt_cfg.rust_port.lock().unwrap() = rust_port;
                *rt_cfg.internal_token.lock().unwrap() = internal_token.clone();
            }

            // Start internal HTTP server for Python sidecar
            let app_handle = app.app_handle().clone();
            let reg = registry_clone.clone();
            let itoken = internal_token.clone();
            let _rust_port = rust_port;
            std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async move {
                    start_internal_server(&app_handle, reg, itoken).await;
                });
            });

            // Start sidecar then restore floating windows from Python database
            let app_handle = app.app_handle().clone();
            let reg = registry_clone.clone();
            let sc = sidecar_clone.clone();
            let itoken = internal_token.clone();
            let rp = rust_port;
            std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async move {
                    // Start the Python AI sidecar with shared internal token
                    let port = match start_sidecar(&app_handle, &sc, &itoken, rp, Some(stop_flag_setup.clone())).await {
                        Ok(p) => p,
                        Err(e) => {
                            eprintln!("[setup] Failed to start sidecar: {}", e);
                            return;
                        }
                    };
                    // Extract api_token from sidecar state for restore_windows
                    let api_token = {
                        let state = sc.lock().await;
                        state.as_ref().map(|h| h.tokens.api_token.clone()).unwrap_or_else(|| "dev-token".to_string())
                    };
                    // Wait for the sidecar to be fully ready
                    sleep(Duration::from_secs(1)).await;
                    restore_windows(&app_handle, &reg, port, &api_token).await;

                    // Spawn watchdog task in the same runtime
                    let app_handle2 = app_handle.clone();
                    let reg2 = reg.clone();
                    let sc2 = sc.clone();
                    let itoken2 = itoken.clone();
                    tokio::spawn(sidecar_watchdog(app_handle2, reg2, sc2, itoken2, rp, stop_flag_setup.clone()));
                });
            });

            // Spawn monitor change watcher
            let app_handle = app.app_handle().clone();
            let reg = registry_clone.clone();
            std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(monitor_change_watcher(app_handle, reg));
            });

            // Create tray icon for minimize-to-tray
            if let Some(icon) = app.default_window_icon() {
                let _tray = tauri::tray::TrayIconBuilder::new()
                    .icon(icon.clone())
                    .on_tray_icon_event(|tray, event| {
                        if let tauri::tray::TrayIconEvent::Click {
                            button: tauri::tray::MouseButton::Left,
                            button_state: tauri::tray::MouseButtonState::Up,
                            ..
                        } = event
                        {
                            let app = tray.app_handle();
                            if let Some(window) = app.get_webview_window("command-center") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    })
                    .build(app);
                if let Err(e) = _tray {
                    eprintln!("Failed to create tray icon: {}", e);
                }
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            match event {
                tauri::RunEvent::WindowEvent {
                    label,
                    event: window_event,
                    ..
                } => {
                    if label == "command-center" {
                        if let tauri::WindowEvent::CloseRequested { api, .. } = window_event {
                            let settings = load_settings(app_handle);
                        if settings.close_behavior == "minimize" {
                            api.prevent_close();
                            if let Some(window) =
                                app_handle.get_webview_window(&label)
                            {
                                let _ = window.hide();
                            }
                        } else {
                            // Quit behavior — kill sidecars then hard exit
                            kill_orphan_sidecars();
                            std::process::exit(0);
                        }
                    }
                }
            }
                tauri::RunEvent::ExitRequested { .. } => {
                    // Signal watchdog to stop (best effort)
                    if let Some(flag) = app_handle.try_state::<Arc<AtomicBool>>() {
                        flag.store(true, Ordering::Relaxed);
                    }
                    // Force kill any sidecar processes to prevent restart race
                    kill_orphan_sidecars();
                    // Hard exit immediately — no async cleanup, no waiting
                    std::process::exit(0);
                }
                _ => {}
            }
        });
}
