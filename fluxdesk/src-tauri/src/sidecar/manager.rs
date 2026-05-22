use std::path::PathBuf;
use std::process::Stdio;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tauri::Manager;
use tokio::process::Child;
use tokio::time::{sleep, Duration};

use crate::sidecar::token::SidecarTokens;
use crate::security::keychain;
use tauri::Emitter;

pub struct SidecarHandle {
    pub child: Child,
    pub port: u16,
    pub tokens: SidecarTokens,
}

pub type SharedSidecar = Arc<tokio::sync::Mutex<Option<SidecarHandle>>>;

pub fn find_free_port() -> Result<u16, String> {
    let listener = std::net::TcpListener::bind("127.0.0.1:0")
        .map_err(|e| format!("Failed to find free port: {}", e))?;
    let port = listener.local_addr()
        .map_err(|e| format!("Failed to get local address: {}", e))?
        .port();
    // Keep listener alive until caller uses the port; dropped here.
    drop(listener);
    Ok(port)
}

fn bundled_binary_path(app: &tauri::AppHandle) -> Option<PathBuf> {
    // 1. Resource dir (Tauri bundles sidecar here for AppImage/macOS)
    if let Ok(resource) = app.path().resource_dir() {
        let sidecar = resource.join("bin").join("fluxdesk-ai");
        if sidecar.exists() {
            return Some(sidecar);
        }
        #[cfg(target_os = "windows")]
        {
            let sidecar_exe = resource.join("bin").join("fluxdesk-ai.exe");
            if sidecar_exe.exists() {
                return Some(sidecar_exe);
            }
        }
    }

    // 2. Next to the current executable (deb/RPM install to /usr/bin/)
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let sidecar = dir.join("fluxdesk-ai");
            if sidecar.exists() {
                return Some(sidecar);
            }
            #[cfg(target_os = "windows")]
            {
                let sidecar_exe = dir.join("fluxdesk-ai.exe");
                if sidecar_exe.exists() {
                    return Some(sidecar_exe);
                }
            }
        }
    }

    None
}

fn find_python() -> String {
    for cmd in &["python3", "python", "py"] {
        if std::process::Command::new(cmd)
            .arg("--version")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .is_ok()
        {
            return cmd.to_string();
        }
    }
    "py".to_string()
}

/// Kill any orphan fluxdesk-ai sidecar processes left from previous instances.
pub fn kill_orphan_sidecars() {
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        let _ = std::process::Command::new("taskkill")
            .args(&["/f", "/im", "fluxdesk-ai.exe"])
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .creation_flags(0x08000000) // CREATE_NO_WINDOW
            .output();
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = std::process::Command::new("pkill")
            .args(&["-f", "fluxdesk-ai"])
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .output();
    }
}

pub async fn start_sidecar(
    app: &tauri::AppHandle,
    sidecar_state: &SharedSidecar,
    internal_token: &str,
    rust_port: u16,
    stop_flag: Option<Arc<AtomicBool>>,
) -> Result<u16, String> {
    // 启动前检查 stop_flag
    if let Some(ref flag) = stop_flag {
        if flag.load(Ordering::Relaxed) {
            return Err("Sidecar start aborted: stop flag is set".to_string());
        }
    }
    // Kill orphan sidecars before starting a new one to prevent port conflicts
    kill_orphan_sidecars();

    let port = find_free_port()?;
    let tokens = SidecarTokens::with_internal(internal_token);

    let app_dir = app
        .path()
        .app_data_dir()
        .map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&app_dir).ok();

    let mut envs = vec![
        ("FLUXDESK_PORT".to_string(), port.to_string()),
        ("FLUXDESK_API_TOKEN".to_string(), tokens.api_token.clone()),
        ("FLUXDESK_INTERNAL_TOKEN".to_string(), tokens.internal_token.clone()),
        ("FLUXDESK_RUST_PORT".to_string(), rust_port.to_string()),
        ("FLUXDESK_APP_DIR".to_string(), app_dir.to_string_lossy().to_string()),
    ];

    // Inject API keys from keychain (set by user via Settings UI)
    let providers = &["openai", "anthropic", "deepseek", "gemini"];
    for provider in providers {
        let env_var = match *provider {
            "openai" => "OPENAI_API_KEY",
            "anthropic" => "ANTHROPIC_API_KEY",
            "deepseek" => "DEEPSEEK_API_KEY",
            "gemini" => "GEMINI_API_KEY",
            _ => continue,
        };
        if let Ok(Some(key)) = keychain::get_key("fluxdesk", &format!("api_key_{}", provider)) {
            if !key.is_empty() {
                envs.push((env_var.to_string(), key));
            }
        }
    }

    let mut child = if let Some(bin_path) = bundled_binary_path(app) {
        let mut cmd = tokio::process::Command::new(&bin_path);
        #[cfg(target_os = "windows")]
        {
            cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }
        for (k, v) in &envs {
            cmd.env(k, v);
        }
        cmd.stdout(Stdio::null())
            .stderr(Stdio::null());
        cmd.spawn().map_err(|e| format!("Failed to spawn bundled sidecar: {} (path: {})", e, bin_path.display()))?
    } else {
        let python_path = std::env::var("FLUXDESK_PYTHON_PATH").unwrap_or_else(|_| find_python());
        let server_script = app.path().resource_dir()
            .map(|r| r.join("server").join("main.py"))
            .unwrap_or_else(|_| {
                let cwd = std::env::current_dir().unwrap_or_default();
                cwd.join("server").join("main.py")
            });

        let mut cmd = tokio::process::Command::new(&python_path);
        #[cfg(target_os = "windows")]
        {
            cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }
        cmd.arg("-u")
            .arg(&server_script);
        for (k, v) in &envs {
            cmd.env(k, v);
        }
        cmd.stdout(Stdio::null())
            .stderr(Stdio::null());
        cmd.spawn().map_err(|e| format!("Failed to spawn sidecar (dev mode): {}", e))?
    };

    let mut healthy = false;
    for _ in 0..60 {
        // Check stop flag during health check
        if let Some(ref flag) = stop_flag {
            if flag.load(Ordering::Relaxed) {
                let _ = child.kill().await;
                return Err("Sidecar health check aborted: stop flag is set".to_string());
            }
        }
        sleep(Duration::from_millis(500)).await;
        if reqwest::get(format!("http://127.0.0.1:{}/api/v1/health", port))
            .await
            .is_ok()
        {
            healthy = true;
            break;
        }
    }

    if !healthy {
        let _ = child.kill().await;
        return Err(format!("Sidecar failed to become healthy on port {}", port));
    }

    let handle = SidecarHandle {
        child,
        port,
        tokens: tokens.clone(),
    };

    {
        let mut state = sidecar_state.lock().await;
        *state = Some(handle);
    }

    app.emit(
        "ai-service-ready",
        serde_json::json!({
            "port": port,
            "apiToken": tokens.api_token,
        }),
    )
    .ok();

    Ok(port)
}

pub async fn stop_sidecar(sidecar_state: &SharedSidecar) {
    let child = {
        let mut state = sidecar_state.lock().await;
        state.take().map(|h| h.child)
    };
    if let Some(mut c) = child {
        c.kill().await.ok();
    }
}
