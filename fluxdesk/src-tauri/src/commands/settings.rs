use std::path::PathBuf;
use serde::{Deserialize, Serialize};
use tauri::Manager;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct GeneralSettings {
    pub language: String,
    pub auto_launch: bool,
    pub minimize_to_tray: bool,
    pub close_behavior: String,
    pub auto_check_update: bool,
}

fn settings_path(app: &tauri::AppHandle) -> PathBuf {
    app.path()
        .app_data_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("general_settings.json")
}

pub fn load_settings(app: &tauri::AppHandle) -> GeneralSettings {
    let path = settings_path(app);
    if let Ok(content) = std::fs::read_to_string(&path) {
        if let Ok(settings) = serde_json::from_str::<GeneralSettings>(&content) {
            return settings;
        }
    }
    GeneralSettings::default()
}

fn save_settings(app: &tauri::AppHandle, settings: &GeneralSettings) -> Result<(), String> {
    let path = settings_path(app);
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let content = serde_json::to_string_pretty(settings).map_err(|e| e.to_string())?;
    std::fs::write(path, content).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_general_settings(app: tauri::AppHandle) -> Result<GeneralSettings, String> {
    Ok(load_settings(&app))
}

#[tauri::command]
pub fn set_general_settings(
    app: tauri::AppHandle,
    settings: GeneralSettings,
) -> Result<(), String> {
    save_settings(&app, &settings)
}

#[tauri::command]
pub fn set_auto_launch(app: tauri::AppHandle, enabled: bool) -> Result<(), String> {
    use tauri_plugin_autostart::ManagerExt;
    let manager = app.autolaunch();
    if enabled {
        manager.enable().map_err(|e| e.to_string())?;
    } else {
        manager.disable().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
pub fn is_auto_launch_enabled(app: tauri::AppHandle) -> Result<bool, String> {
    use tauri_plugin_autostart::ManagerExt;
    app.autolaunch().is_enabled().map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn check_for_update(app: tauri::AppHandle) -> Result<Option<String>, String> {
    #[cfg(desktop)]
    {
        use tauri_plugin_updater::UpdaterExt;
        match app.updater() {
            Ok(updater) => match updater.check().await {
                Ok(Some(update)) => Ok(Some(update.version.to_string())),
                Ok(None) => Ok(None),
                Err(e) => Err(e.to_string()),
            },
            Err(e) => Err(e.to_string()),
        }
    }
    #[cfg(not(desktop))]
    {
        Ok(None)
    }
}

#[tauri::command]
pub async fn install_update(app: tauri::AppHandle) -> Result<(), String> {
    #[cfg(desktop)]
    {
        use tauri_plugin_updater::UpdaterExt;
        match app.updater() {
            Ok(updater) => match updater.check().await {
                Ok(Some(update)) => {
                    let _ = update
                        .download_and_install(|_chunk, _total| {}, || {})
                        .await;
                }
                _ => {}
            },
            Err(_) => {}
        }
        Ok(())
    }
    #[cfg(not(desktop))]
    {
        Ok(())
    }
}
