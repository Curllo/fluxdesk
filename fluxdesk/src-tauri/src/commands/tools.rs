use serde_json::Value;
use tauri::State;

use crate::sidecar::manager::SharedSidecar;

/// Call Python API to manage a todo item
#[tauri::command]
pub async fn manage_todo(
    sidecar: State<'_, SharedSidecar>,
    action: String,
    content: Option<String>,
    todo_id: Option<String>,
) -> Result<Value, String> {
    let (port, token) = {
        let state = sidecar.lock().await;
        match state.as_ref() {
            Some(h) => (h.port, h.tokens.api_token.clone()),
            None => return Err("AI service not running".to_string()),
        }
    };

    let client = reqwest::Client::new();

    match action.as_str() {
        "add" => {
            let body = serde_json::json!({ "content": content.unwrap_or_default() });
            let resp = client
                .post(format!("http://127.0.0.1:{}/api/v1/todos", port))
                .header("Authorization", format!("Bearer {}", token))
                .json(&body)
                .timeout(std::time::Duration::from_secs(5))
                .send()
                .await
                .map_err(|e| e.to_string())?;
            let json: Value = resp.json().await.map_err(|e| e.to_string())?;
            Ok(json)
        }
        "complete" => {
            let id = todo_id.ok_or("todo_id required")?;
            let resp = client
                .post(format!("http://127.0.0.1:{}/api/v1/todos/{}/complete", port, id))
                .header("Authorization", format!("Bearer {}", token))
                .timeout(std::time::Duration::from_secs(5))
                .send()
                .await
                .map_err(|e| e.to_string())?;
            let json: Value = resp.json().await.map_err(|e| e.to_string())?;
            Ok(json)
        }
        "delete" => {
            let id = todo_id.ok_or("todo_id required")?;
            let resp = client
                .delete(format!("http://127.0.0.1:{}/api/v1/todos/{}", port, id))
                .header("Authorization", format!("Bearer {}", token))
                .timeout(std::time::Duration::from_secs(5))
                .send()
                .await
                .map_err(|e| e.to_string())?;
            let json: Value = resp.json().await.map_err(|e| e.to_string())?;
            Ok(json)
        }
        "list" => {
            let resp = client
                .get(format!("http://127.0.0.1:{}/api/v1/todos", port))
                .header("Authorization", format!("Bearer {}", token))
                .timeout(std::time::Duration::from_secs(5))
                .send()
                .await
                .map_err(|e| e.to_string())?;
            let json: Value = resp.json().await.map_err(|e| e.to_string())?;
            Ok(json)
        }
        _ => Err(format!("Unknown action: {}", action)),
    }
}

/// Call Python API to set a reminder
#[tauri::command]
pub async fn set_reminder(
    sidecar: State<'_, SharedSidecar>,
    title: String,
    time: String,
    repeat: String,
) -> Result<Value, String> {
    let (port, token) = {
        let state = sidecar.lock().await;
        match state.as_ref() {
            Some(h) => (h.port, h.tokens.api_token.clone()),
            None => return Err("AI service not running".to_string()),
        }
    };

    let client = reqwest::Client::new();
    let body = serde_json::json!({ "title": title, "time": time, "repeat": repeat });
    let resp = client
        .post(format!("http://127.0.0.1:{}/api/v1/reminders", port))
        .header("Authorization", format!("Bearer {}", token))
        .json(&body)
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await
        .map_err(|e| e.to_string())?;
    let json: Value = resp.json().await.map_err(|e| e.to_string())?;
    Ok(json)
}
