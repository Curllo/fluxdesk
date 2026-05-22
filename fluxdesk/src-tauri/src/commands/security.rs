use crate::security::keychain;

#[tauri::command]
pub fn set_api_key(provider: String, key: String) -> Result<(), String> {
    keychain::set_key("fluxdesk", &format!("api_key_{}", provider), &key)
}

#[tauri::command]
pub fn get_api_key(provider: String) -> Result<Option<String>, String> {
    keychain::get_key("fluxdesk", &format!("api_key_{}", provider))
}

#[tauri::command]
pub fn delete_api_key(provider: String) -> Result<(), String> {
    keychain::delete_key("fluxdesk", &format!("api_key_{}", provider))
}
