import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useTheme } from './useTheme'

describe('useTheme', () => {
  beforeEach(() => {
    document.documentElement.classList.remove('dark')
    localStorage.removeItem('fluxdesk-theme')
  })

  afterEach(() => {
    document.documentElement.classList.remove('dark')
    localStorage.removeItem('fluxdesk-theme')
  })

  it('initializes from system preference', () => {
    const { isDark, init } = useTheme()
    init()
    // Should match current system preference (true/false)
    expect(typeof isDark.value).toBe('boolean')
  })

  it('sets dark mode explicitly', () => {
    const { isDark, setTheme } = useTheme()
    setTheme('dark')
    expect(isDark.value).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('sets light mode explicitly', () => {
    const { isDark, setTheme } = useTheme()
    setTheme('light')
    expect(isDark.value).toBe(false)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})
