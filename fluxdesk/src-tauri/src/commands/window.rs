// NOTE: v2.0 前端不再调用这些命令（工具通过 toolRegistry 管理）。
// 这些命令保留以保持向后兼容，新建工具由前端 toolRegistry 处理。

use serde_json::Value;
use tauri::{Emitter, Manager, State};

use crate::sidecar::manager::SharedSidecar;
use crate::window_manager::registry::{create_floating_window, snap_to_edge, SharedRegistry, WindowMeta};

#[tauri::command]
pub async fn create_window(
    app: tauri::AppHandle,
    registry: State<'_, SharedRegistry>,
    sidecar: State<'_, SharedSidecar>,
    window_type: String,
    config: Value,
) -> Result<String, String> {
    let id = format!("win_{}", uuid::Uuid::new_v4().to_string().replace('-', ""));
    create_floating_window(&app, &registry, id.clone(), window_type.clone(), config.clone())?;

    // Sync to Python database if sidecar is running
    sync_window_to_db(&sidecar, &id, &window_type, &config).await;

    Ok(id)
}

async fn sync_window_to_db(
    sidecar: &SharedSidecar,
    id: &str,
    window_type: &str,
    config: &Value,
) {
    let (port, token) = {
        let state = sidecar.lock().await;
        match state.as_ref() {
            Some(h) => (h.port, h.tokens.api_token.clone()),
            None => return,
        }
    };

    let payload = serde_json::json!({
        "type": window_type,
        "position": config.get("position").cloned().unwrap_or(serde_json::json!({"x": 100, "y": 100})),
        "size": config.get("size").cloned().unwrap_or(serde_json::json!({"width": 400, "height": 300})),
        "data": config.get("data").cloned().unwrap_or(serde_json::json!({"id": id})),
    });

    let client = reqwest::Client::new();
    let _ = client
        .post(format!("http://127.0.0.1:{}/api/v1/windows", port))
        .header("Authorization", format!("Bearer {}", token))
        .json(&payload)
        .timeout(std::time::Duration::from_secs(3))
        .send()
        .await;
}

#[tauri::command]
pub async fn destroy_window(
    app: tauri::AppHandle,
    registry: State<'_, SharedRegistry>,
    sidecar: State<'_, SharedSidecar>,
    id: String,
) -> Result<(), String> {
    let label = format!("floating-{}", id);
    if let Some(window) = app.get_webview_window(&label) {
        window.close().map_err(|e| e.to_string())?;
    }
    {
        let mut reg = registry.lock().unwrap();
        reg.unregister(&id);
    }

    // Remove from Python database
    remove_window_from_db(&sidecar, &id).await;

    app.emit(
        "window-state-changed",
        serde_json::json!({
            "action": "destroyed",
            "payload": { "id": id }
        }),
    )
    .ok();
    Ok(())
}

async fn remove_window_from_db(sidecar: &SharedSidecar, id: &str) {
    let (port, token) = {
        let state = sidecar.lock().await;
        match state.as_ref() {
            Some(h) => (h.port, h.tokens.api_token.clone()),
            None => return,
        }
    };

    let client = reqwest::Client::new();
    let _ = client
        .delete(format!("http://127.0.0.1:{}/api/v1/windows/{}", port, id))
        .header("Authorization", format!("Bearer {}", token))
        .timeout(std::time::Duration::from_secs(3))
        .send()
        .await;
}

#[tauri::command]
pub async fn update_window_position(
    app: tauri::AppHandle,
    registry: State<'_, SharedRegistry>,
    sidecar: State<'_, SharedSidecar>,
    id: String,
    x: f64,
    y: f64,
) -> Result<(), String> {
    let size = {
        let mut reg = registry.lock().unwrap();
        if let Some(win) = reg.get_mut(&id) {
            win.position = (x as i32, y as i32);
            win.size
        } else {
            return Ok(());
        }
    };

    let monitors = app.available_monitors().map_err(|e| e.to_string())?;
    let snapped = snap_to_edge((x as i32, y as i32), size, &monitors);

    let final_pos = if snapped != (x as i32, y as i32) {
        let label = format!("floating-{}", id);
        if let Some(window) = app.get_webview_window(&label) {
            let _ = window.set_position(tauri::Position::Physical(tauri::PhysicalPosition {
                x: snapped.0,
                y: snapped.1,
            }));
        }
        let mut reg = registry.lock().unwrap();
        if let Some(win) = reg.get_mut(&id) {
            win.position = snapped;
        }
        snapped
    } else {
        (x as i32, y as i32)
    };

    update_window_in_db(&sidecar, &id, serde_json::json!({
        "position": {"x": final_pos.0, "y": final_pos.1}
    }))
    .await;

    app.emit(
        "window-state-changed",
        serde_json::json!({
            "action": "moved",
            "payload": { "id": id, "position": {"x": final_pos.0, "y": final_pos.1} }
        }),
    )
    .ok();
    Ok(())
}

#[tauri::command]
pub async fn update_window_size(
    app: tauri::AppHandle,
    registry: State<'_, SharedRegistry>,
    sidecar: State<'_, SharedSidecar>,
    id: String,
    width: f64,
    height: f64,
) -> Result<(), String> {
    {
        let mut reg = registry.lock().unwrap();
        if let Some(win) = reg.get_mut(&id) {
            win.size = (width as u32, height as u32);
        }
    }

    update_window_in_db(&sidecar, &id, serde_json::json!({
        "size": {"width": width, "height": height}
    })).await;

    app.emit(
        "window-state-changed",
        serde_json::json!({
            "action": "resized",
            "payload": { "id": id, "size": {"width": width, "height": height} }
        }),
    )
    .ok();
    Ok(())
}

async fn update_window_in_db(sidecar: &SharedSidecar, id: &str, data: Value) {
    let (port, token) = {
        let state = sidecar.lock().await;
        match state.as_ref() {
            Some(h) => (h.port, h.tokens.api_token.clone()),
            None => return,
        }
    };

    let client = reqwest::Client::new();
    let _ = client
        .patch(format!("http://127.0.0.1:{}/api/v1/windows/{}", port, id))
        .header("Authorization", format!("Bearer {}", token))
        .json(&data)
        .timeout(std::time::Duration::from_secs(3))
        .send()
        .await;
}

#[tauri::command]
pub fn focus_window(
    app: tauri::AppHandle,
    registry: State<'_, SharedRegistry>,
    id: String,
) -> Result<(), String> {
    let label = format!("floating-{}", id);
    if let Some(window) = app.get_webview_window(&label) {
        window.set_focus().map_err(|e| e.to_string())?;
    }
    {
        let mut reg = registry.lock().unwrap();
        reg.focus(&id);
    }
    app.emit(
        "window-state-changed",
        serde_json::json!({
            "action": "focused",
            "payload": { "id": id }
        }),
    )
    .ok();
    Ok(())
}

#[tauri::command]
pub fn list_windows(registry: State<'_, SharedRegistry>) -> Vec<WindowMeta> {
    let reg = registry.lock().unwrap();
    reg.all_windows()
}
