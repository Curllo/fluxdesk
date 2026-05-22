use tauri::{Manager, State};

use crate::sidecar::manager::{start_sidecar, stop_sidecar, SharedSidecar};
use crate::security::token::generate_secure_token;

#[tauri::command]
pub async fn toggle_command_center(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("command-center") {
        if let Ok(true) = window.is_visible() {
            window.hide().map_err(|e| e.to_string())?;
        } else {
            window.center().map_err(|e| e.to_string())?;
            window.show().map_err(|e| e.to_string())?;
            window.set_focus().map_err(|e| e.to_string())?;
        }
    }
    Ok(())
}

#[tauri::command]
pub async fn get_ai_service_config(
    sidecar: State<'_, SharedSidecar>,
) -> Result<serde_json::Value, String> {
    let state = sidecar.lock().await;
    match state.as_ref() {
        Some(ref handle) => Ok(serde_json::json!({
            "port": handle.port,
            "apiToken": handle.tokens.api_token.clone(),
            "pid": handle.child.id().unwrap_or(0),
        })),
        None => Err("AI service starting...".to_string()),
    }
}

#[tauri::command]
pub async fn restart_ai_service(
    app: tauri::AppHandle,
    sidecar: State<'_, SharedSidecar>,
    runtime: State<'_, crate::AppRuntimeConfig>,
) -> Result<serde_json::Value, String> {
    stop_sidecar(&sidecar).await;
    let rust_port = *runtime.rust_port.lock().map_err(|_| "Lock poisoned")?;
    let internal_token = generate_secure_token(32);
    // Update persisted token
    *runtime.internal_token.lock().map_err(|_| "Lock poisoned")? = internal_token.clone();
    let port = start_sidecar(&app, &sidecar, &internal_token, rust_port, None).await?;
    {
        let state = sidecar.lock().await;
        let handle = state.as_ref().unwrap();
        Ok(serde_json::json!({
            "port": port,
            "apiToken": handle.tokens.api_token.clone(),
            "pid": handle.child.id().unwrap_or(0),
        }))
    }
}

#[tauri::command]
pub fn show_notification(
    app: tauri::AppHandle,
    title: String,
    body: String,
) -> Result<(), String> {
    use tauri_plugin_notification::NotificationExt;
    app.notification()
        .builder()
        .title(title)
        .body(body)
        .show()
        .map_err(|e| e.to_string())?;
    Ok(())
}
