// 与后端 app/schemas/chat.py 对齐（Backend API contract is the source of truth）。

export interface ChatRequest {
  conversation_id: string
  query: string
}

export interface ChatSource {
  document_id: string
  document_name: string
  relevance: number
}

export interface ChatMetadata {
  retrieval_count: number
  duration_ms: number
}

export interface ChatResponse {
  answer: string
  sources: ChatSource[]
  metadata: ChatMetadata
}
