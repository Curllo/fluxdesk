import { config } from '@vue/test-utils'

// Global test utilities can be registered here
config.global.stubs = {
  // Stub Tauri APIs that require native context
  'tauri-api-stub': true,
}
