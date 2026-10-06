/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_FLOWLENS_MODE?: string
  readonly VITE_FLOWLENS_FIXTURE_VIEW?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
