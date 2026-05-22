use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use tauri_plugin_global_shortcut::GlobalShortcutExt;

pub type SharedShortcut = Arc<Mutex<CurrentShortcut>>;

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct ShortcutConfig {
    pub key: String,
}

pub struct CurrentShortcut {
    pub key: String,
    config_path: PathBuf,
}

impl CurrentShortcut {
    pub fn new(app_data_dir: PathBuf) -> Self {
        fs::create_dir_all(&app_data_dir).ok();
        let config_path = app_data_dir.join("shortcut.json");

        let key = fs::read_to_string(&config_path)
            .ok()
            .and_then(|s| serde_json::from_str::<ShortcutConfig>(&s).ok())
            .map(|c| c.key)
            .unwrap_or_else(|| "Ctrl+K".to_string());

        Self { key, config_path }
    }

    fn save(&self) {
        let config = ShortcutConfig {
            key: self.key.clone(),
        };
        if let Ok(json) = serde_json::to_string_pretty(&config) {
            fs::write(&self.config_path, json).ok();
        }
    }
}

/// Get the currently configured global shortcut key.
#[tauri::command]
pub fn get_shortcut(shortcut_state: tauri::State<'_, SharedShortcut>) -> String {
    let state = shortcut_state.lock().unwrap();
    state.key.clone()
}

/// Update the global shortcut key (unregister old, register new).
#[tauri::command]
pub fn update_shortcut(
    app: tauri::AppHandle,
    shortcut_state: tauri::State<'_, SharedShortcut>,
    new_key: String,
) -> Result<String, String> {
    let old_key = {
        let mut state = shortcut_state.lock().unwrap();
        let old = state.key.clone();
        state.key = new_key.clone();
        state.save();
        old
    };

    // Unregister old shortcut
    if !old_key.is_empty() {
        if let Ok(old) = old_key.parse::<tauri_plugin_global_shortcut::Shortcut>() {
            let _ = app.global_shortcut().unregister(old);
        }
    }

    // Register new shortcut
    let shortcut = new_key
        .parse::<tauri_plugin_global_shortcut::Shortcut>()
        .map_err(|e| format!("无效的快捷键: {} ({})", new_key, e))?;

    app.global_shortcut()
        .register(shortcut)
        .map_err(|e| format!("注册快捷键失败: {}", e))?;

    Ok(new_key)
}

