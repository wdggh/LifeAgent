import axios, { type AxiosError } from 'axios'
import { readApiError } from './errors'

const ACCESS_TOKEN_KEY = 'lifeagent.access_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function setAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

export function clearAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}

/** 会话失效（UNAUTHENTICATED / INVALID_TOKEN）与登录失败（INVALID_CREDENTIALS）分开处理。 */
function isSessionExpiredError(error: AxiosError): boolean {
  if (error.response?.status !== 401) return false
  const code = readApiError(error)?.code
  return code === 'UNAUTHENTICATED' || code === 'INVALID_TOKEN'
}

/**
 * 统一 Axios 客户端。
 *
 * 所有业务 API（auth / documents / conversations / chat）都从这里派发请求，
 * 而不是在组件里直接调用 axios.post(...)。
 *
 * 扩展点都集中在这一层：
 * - 请求拦截器：自动附加 JWT Authorization 头（request_id 待后端 header 方案确认）
 * - 响应拦截器：401 会话失效自动回登录并携带 redirect（登录失败除外）
 * - 按请求覆盖超时（上传大文件、长回答时单独设置）
 */
const apiClient = axios.create({
  // baseURL 来自 .env 的 VITE_API_BASE_URL，构建期由 Vite 注入
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (isSessionExpiredError(error)) {
      clearAccessToken()
      const currentPath = window.location.pathname + window.location.search
      const isLoginPage = window.location.pathname.startsWith('/login')
      if (!isLoginPage) {
        const redirect = encodeURIComponent(currentPath)
        window.location.assign(`/login?redirect=${redirect}`)
      }
    }
    return Promise.reject(error)
  },
)

export default apiClient
