
use std::net::SocketAddr;
use tauri::AppHandle;
use tokio::net::TcpListener;

use crate::api::handlers::{internal_routes, ApiState};
use crate::window_manager::registry::SharedRegistry;

/// Find a free port on 127.0.0.1 and return it.
pub fn find_free_port_sync() -> Result<u16, String> {
    let listener = std::net::TcpListener::bind("127.0.0.1:0")
        .map_err(|e| format!("Failed to find free port: {}", e))?;
    let port = listener.local_addr()
        .map_err(|e| format!("Failed to get local address: {}", e))?
        .port();
    drop(listener);
    Ok(port)
}

pub async fn start_internal_server(
    app_handle: &AppHandle,
    registry: SharedRegistry,
    internal_token: String,
) -> u16 {
    let state = ApiState {
        app_handle: app_handle.clone(),
        registry,
        internal_token,
    };

    let app = internal_routes(state);

    // Try to bind with port fallback
    let mut port = 9595;
    let listener = loop {
        let addr = SocketAddr::from(([127, 0, 0, 1], port));
        match TcpListener::bind(&addr).await {
            Ok(l) => break l,
            Err(e) => {
                if port >= 9595 + 5 {
                    eprintln!("Failed to bind internal server after 5 attempts: {}", e);
                    return 0;
                }
                port += 1;
            }
        }
    };

    if let Err(e) = axum::serve(listener, app).await {
        eprintln!("Internal server error: {}", e);
    }
    port
}
