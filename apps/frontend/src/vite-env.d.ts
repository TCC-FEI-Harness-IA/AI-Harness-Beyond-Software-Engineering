/// <reference types="vite/client" />

// Espelha as variáveis da seção 7 do README — todas chegam como string (ou ausentes).
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_WS_BASE_URL?: string
  readonly VITE_API_PREFIX?: string
  readonly VITE_REQUEST_TIMEOUT_MS?: string
  readonly VITE_WS_OPEN_TIMEOUT_MS?: string
  readonly VITE_DEFAULT_PROVIDER?: string
  readonly VITE_AVAILABLE_MODELS?: string
  readonly VITE_DEFAULT_MODEL?: string
  readonly VITE_DEFAULT_MAX_TOKENS?: string
  readonly VITE_DEFAULT_TEMPERATURE?: string
  readonly VITE_HISTORY_FETCH_CONCURRENCY?: string
  readonly VITE_HISTORY_SUMMARY_MAX_CHARS?: string
  readonly VITE_HISTORY_SIDEBAR_SUMMARY_MAX_CHARS?: string
  readonly VITE_ENABLE_DEBUG_PANEL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
