/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** FastAPI 的 API 根地址，例如 http://localhost:8080/api/v1 */
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
