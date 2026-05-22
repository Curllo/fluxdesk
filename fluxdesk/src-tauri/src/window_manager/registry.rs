use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tauri::{Emitter, WebviewWindow, WebviewWindowBuilder};

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct WindowMeta {
    pub id: String,
    pub window_type: String,
    pub position: (i32, i32),
    pub size: (u32, u32),
    pub display_index: u32,
    pub always_on_top: bool,
    pub opacity: f64,
    pub data: serde_json::Value,
}

#[derive(Default)]
pub struct WindowRegistry {
    windows: HashMap<String, WindowMeta>,
    z_stack: Vec<String>,
    focus_id: Option<String>,
    next_z: u32,
}

pub type SharedRegistry = Arc<Mutex<WindowRegistry>>;

impl WindowRegistry {
    pub fn new() -> Self {
        Self {
            windows: HashMap::new(),
            z_stack: Vec::new(),
            focus_id: None,
            next_z: 100,
        }
    }

    pub fn register(&mut self, meta: WindowMeta) {
        self.windows.insert(meta.id.clone(), meta.clone());
        self.z_stack.push(meta.id.clone());
    }

    pub fn unregister(&mut self, id: &str) {
        self.windows.remove(id);
        self.z_stack.retain(|x| x != id);
        if self.focus_id.as_deref() == Some(id) {
            self.focus_id = None;
        }
    }

    pub fn get(&self, id: &str) -> Option<&WindowMeta> {
        self.windows.get(id)
    }

    pub fn get_mut(&mut self, id: &str) -> Option<&mut WindowMeta> {
        self.windows.get_mut(id)
    }

    pub fn focus(&mut self, id: &str) {
        if self.windows.contains_key(id) {
            self.focus_id = Some(id.to_string());
            self.z_stack.retain(|x| x != id);
            self.z_stack.push(id.to_string());
        }
    }

    pub fn next_z_index(&mut self) -> u32 {
        let z = self.next_z;
        self.next_z += 1;
        z
    }

    pub fn all_windows(&self) -> Vec<WindowMeta> {
        self.windows.values().cloned().collect()
    }
}

pub fn snap_to_edge(position: (i32, i32), size: (u32, u32), monitors: &[tauri::Monitor]) -> (i32, i32) {
    let (mut x, mut y) = position;
    let (width, height) = size;

    for monitor in monitors {
        let pos = monitor.position();
        let sz = monitor.size();
        let mx = pos.x;
        let my = pos.y;
        let m_right = mx + sz.width as i32;
        let m_bottom = my + sz.height as i32;

        // Horizontal snap
        if (x - mx).abs() <= 20 {
            x = mx;
        } else if ((x + width as i32) - m_right).abs() <= 20 {
            x = m_right - width as i32;
        }

        // Vertical snap
        if (y - my).abs() <= 20 {
            y = my;
        } else if ((y + height as i32) - m_bottom).abs() <= 20 {
            y = m_bottom - height as i32;
        }
    }

    (x, y)
}

pub fn monitor_recovery(
    windows: &[WindowMeta],
    old_monitors: &[tauri::Monitor],
    new_monitors: &[tauri::Monitor],
) -> Vec<(String, (i32, i32))> {
    let mut updates = Vec::new();

    if new_monitors.is_empty() {
        return updates;
    }

    let primary = &new_monitors[0];
    let new_pos = primary.position();
    let new_sz = primary.size();

    for window in windows {
        let center_x = window.position.0 + (window.size.0 as i32) / 2;
        let center_y = window.position.1 + (window.size.1 as i32) / 2;

        let mut old_monitor = None;
        for monitor in old_monitors {
            let pos = monitor.position();
            let sz = monitor.size();
            if center_x >= pos.x
                && center_x < pos.x + sz.width as i32
                && center_y >= pos.y
                && center_y < pos.y + sz.height as i32
            {
                old_monitor = Some(monitor);
                break;
            }
        }

        if let Some(monitor) = old_monitor {
            let old_pos = monitor.position();
            let old_sz = monitor.size();
            let still_exists = new_monitors.iter().any(|m| {
                let p = m.position();
                let s = m.size();
                p.x == old_pos.x && p.y == old_pos.y && s.width == old_sz.width && s.height == old_sz.height
            });

            if !still_exists {
                let rel_x = if old_sz.width > 0 {
                    (window.position.0 - old_pos.x) as f64 / old_sz.width as f64
                } else {
                    0.0
                };
                let rel_y = if old_sz.height > 0 {
                    (window.position.1 - old_pos.y) as f64 / old_sz.height as f64
                } else {
                    0.0
                };
                let new_x = new_pos.x + (rel_x * new_sz.width as f64) as i32;
                let new_y = new_pos.y + (rel_y * new_sz.height as f64) as i32;
                updates.push((window.id.clone(), (new_x, new_y)));
            }
        } else {
            // Window wasn't on any known old monitor, snap to primary top-left
            updates.push((window.id.clone(), (new_pos.x, new_pos.y)));
        }
    }

    updates
}

pub fn create_floating_window(
    app: &tauri::AppHandle,
    registry: &SharedRegistry,
    id: String,
    window_type: String,
    config: serde_json::Value,
) -> Result<WebviewWindow, String> {
    let width = config.get("size").and_then(|s| s.get("width")).and_then(|v| v.as_u64()).unwrap_or(400) as u32;
    let height = config.get("size").and_then(|s| s.get("height")).and_then(|v| v.as_u64()).unwrap_or(300) as u32;
    let x = config.get("position").and_then(|p| p.get("x")).and_then(|v| v.as_i64()).unwrap_or(100) as i32;
    let y = config.get("position").and_then(|p| p.get("y")).and_then(|v| v.as_i64()).unwrap_or(100) as i32;
    let always_on_top = config.get("alwaysOnTop").and_then(|v| v.as_bool()).unwrap_or(true);
    let opacity = config.get("opacity").and_then(|v| v.as_f64()).unwrap_or(1.0);

    let label = format!("floating-{}", id);
    
    // Build URL with window type and config params
    let mut url = format!("/?type={}&id={}", window_type, id);
    
    // Helper to get value from config or config.data
    let get_val = |key: &str| -> Option<&serde_json::Value> {
        config.get(key).or_else(|| config.get("data").and_then(|d| d.get(key)))
    };
    
    if let Some(dur) = get_val("duration").and_then(|v| v.as_u64()) {
        url.push_str(&format!("&duration={}", dur));
    }
    if let Some(title) = get_val("title").and_then(|v| v.as_str()) {
        url.push_str(&format!("&title={}", urlencoding::encode(title)));
    }
    if let Some(note_id) = get_val("id").and_then(|v| v.as_str()) {
        url.push_str(&format!("&id={}", note_id));
    }
    
    let window = WebviewWindowBuilder::new(app, &label, tauri::WebviewUrl::App(url.into()))
        .title(format!("FluxDesk - {}", window_type))
        .inner_size(width as f64, height as f64)
        .position(x as f64, y as f64)
        .decorations(false)
        .transparent(true)
        .always_on_top(always_on_top)
        .skip_taskbar(true)
        .build()
        .map_err(|e| e.to_string())?;

    let meta = WindowMeta {
        id: id.clone(),
        window_type: window_type.clone(),
        position: (x, y),
        size: (width, height),
        display_index: 0,
        always_on_top,
        opacity,
        data: config.get("data").cloned().unwrap_or(serde_json::Value::Null),
    };

    let z_index = {
        let mut reg = registry.lock().unwrap();
        let z = reg.next_z_index();
        reg.register(meta);
        reg.focus(&id);
        z
    };

    app.emit("window-state-changed", serde_json::json!({
        "action": "created",
        "payload": {
            "id": id,
            "type": window_type,
            "position": {"x": x, "y": y},
            "size": {"width": width, "height": height},
            "zIndex": z_index,
            "isAlwaysOnTop": always_on_top,
            "opacity": opacity,
            "data": config.get("data").cloned().unwrap_or(serde_json::Value::Null),
        }
    })).ok();

    Ok(window)
}
