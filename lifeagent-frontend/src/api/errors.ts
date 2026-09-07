// 统一错误体解析与中文文案映射（spec §6 / §15 文案表）。
// 后端错误体：{"error": {"code", "message", "request_id"}}；
// Backend API contract is the source of truth：这里只负责“读懂”错误，不重新定义 API。

import type { AxiosError } from 'axios'

export interface ApiErrorBody {
  error?: {
    code?: string
    message?: string
    request_id?: string
  }
}

export interface ApiErrorInfo {
  code?: string
  message?: string
  request_id?: string
}

/** 从错误中解出后端统一错误体；请求没到达后端或响应不含 error 时返回 undefined。 */
export function readApiError(error: unknown): ApiErrorInfo | undefined {
  if (typeof error !== 'object' || error === null) return undefined
  const envelope = (error as AxiosError<ApiErrorBody>).response?.data?.error
  if (!envelope) return undefined
  return {
    code: envelope.code,
    message: envelope.message,
    request_id: envelope.request_id,
  }
}

const CODE_MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: '用户名或密码错误',
  USERNAME_TAKEN: '用户名已被使用',
  FILE_TOO_LARGE: '文件超过 50MB 限制',
  UNSUPPORTED_FILE_TYPE: '不支持的文件类型（支持 PDF/TXT/Markdown）',
  INVALID_FILE_CONTENT: '文件内容与所选类型不匹配',
  LLM_UNAVAILABLE: 'AI 服务暂时不可用，请稍后重试',
  SERVICE_UNAVAILABLE: '服务暂时不可用，请稍后重试',
  DOCUMENT_NOT_RETRYABLE: '当前状态不可重试',
  CONVERSATION_NOT_FOUND: '内容不存在或已被删除',
  DOCUMENT_NOT_FOUND: '内容不存在或已被删除',
  DOCUMENT_DELETE_FAILED: '删除失败，请重试',
  VALIDATION_ERROR: '输入不合法，请检查后重试',
}

/** 优先按 code 显示中文文案；未知 code 回退后端 message，最后用调用方兜底。 */
export function apiErrorMessage(error: unknown, fallback: string): string {
  const info = readApiError(error)
  if (!info) return fallback
  if (info.code && CODE_MESSAGES[info.code]) return CODE_MESSAGES[info.code]
  return info.message ?? fallback
}
