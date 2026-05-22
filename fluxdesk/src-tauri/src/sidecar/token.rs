use crate::security::token::generate_secure_token;
use serde::{Deserialize, Serialize};

#[derive(Clone, Serialize, Deserialize)]
pub struct SidecarTokens {
    pub api_token: String,
    pub internal_token: String,
}

impl SidecarTokens {
    pub fn generate() -> Self {
        Self {
            api_token: generate_secure_token(32),
            internal_token: generate_secure_token(32),
        }
    }

    pub fn with_internal(internal_token: &str) -> Self {
        Self {
            api_token: generate_secure_token(32),
            internal_token: internal_token.to_string(),
        }
    }
}
