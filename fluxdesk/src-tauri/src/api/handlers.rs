use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;


use tauri::{AppHandle, Manager};

use crate::window_manager::registry::{create_floating_window, SharedRegistry};

#[derive(Clone)]
pub struct ApiState {
    pub app_handle: AppHandle,
    pub registry: SharedRegistry,
    #[allow(dead_code)]
    pub internal_token: String,
}

#[derive(Serialize)]
struct HealthResponse {
    status: String,
    version: String,
}

#[derive(Deserialize)]
struct CreateWindowReq {
    #[serde(rename = "type")]
    window_type: String,
    #[allow(dead_code)]
    config: Value,
}

#[derive(Deserialize)]
struct WindowIdReq {
    id: String,
}

#[derive(Deserialize)]
struct NotifyReq {
    title: String,
    body: String,
}

pub fn internal_routes(state: ApiState) -> Router {
    Router::new()
        .route("/internal/health", get(health))
        .route("/internal/window/create", post(create_window))
        .route("/internal/window/destroy", post(destroy_window))
        .route("/internal/window/focus", post(focus_window))
        .route("/internal/notify", post(notify))
        .with_state(state)
}

async fn health() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok".to_string(),
        version: "1.1.0".to_string(),
    })
}

async fn create_window(
    State(state): State<ApiState>,
    Json(req): Json<CreateWindowReq>,
) -> Result<Json<Value>, StatusCode> {
    let id = format!("win_{}", uuid::Uuid::new_v4().to_string().replace('-', ""));
    match create_floating_window(
        &state.app_handle,
        &state.registry,
        id.clone(),
        req.window_type.clone(),
        req.config,
    ) {
        Ok(_) => Ok(Json(serde_json::json!({
            "id": id,
            "type": req.window_type,
            "success": true
        }))),
        Err(e) => Ok(Json(serde_json::json!({
            "id": id,
            "type": req.window_type,
            "success": false,
            "error": e
        }))),
    }
}

async fn destroy_window(
    State(state): State<ApiState>,
    Json(req): Json<WindowIdReq>,
) -> Result<Json<Value>, StatusCode> {
    {
        let mut reg = state.registry.lock().unwrap();
        reg.unregister(&req.id);
    }
    let label = format!("floating-{}", req.id);
    if let Some(window) = state.app_handle.get_webview_window(&label) {
        let _ = window.close();
    }
    Ok(Json(serde_json::json!({
        "id": req.id,
        "success": true
    })))
}

async fn focus_window(
    State(state): State<ApiState>,
    Json(req): Json<WindowIdReq>,
) -> Result<Json<Value>, StatusCode> {
    {
        let mut reg = state.registry.lock().unwrap();
        reg.focus(&req.id);
    }
    let label = format!("floating-{}", req.id);
    if let Some(window) = state.app_handle.get_webview_window(&label) {
        let _ = window.set_focus();
    }
    Ok(Json(serde_json::json!({
        "id": req.id,
        "success": true
    })))
}

async fn notify(
    State(_state): State<ApiState>,
    Json(req): Json<NotifyReq>,
) -> Result<Json<Value>, StatusCode> {
    Ok(Json(serde_json::json!({
        "title": req.title,
        "body": req.body,
        "success": true
    })))
}
