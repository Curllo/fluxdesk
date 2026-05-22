use std::collections::HashMap;
use std::sync::Mutex;

static KEYCHAIN: Mutex<Option<HashMap<String, String>>> = Mutex::new(None);

fn with_chain<F, R>(f: F) -> Result<R, String>
where
    F: FnOnce(&mut HashMap<String, String>) -> R,
{
    let mut guard = KEYCHAIN.lock().map_err(|e| e.to_string())?;
    if guard.is_none() {
        *guard = Some(HashMap::new());
    }
    let map = guard.as_mut().unwrap();
    Ok(f(map))
}

pub fn set_key(service: &str, key: &str, value: &str) -> Result<(), String> {
    with_chain(|map| {
        map.insert(format!("{}:{}", service, key), value.to_string());
    })
}

pub fn get_key(service: &str, key: &str) -> Result<Option<String>, String> {
    with_chain(|map| map.get(&format!("{}:{}", service, key)).cloned())
}

pub fn delete_key(service: &str, key: &str) -> Result<(), String> {
    with_chain(|map| {
        map.remove(&format!("{}:{}", service, key));
    })
}
