// 与后端 app/schemas/conversation.py 对齐（Backend API contract is the source of truth）。

export type MessageRole = 'user' | 'assistant'

export interface ConversationOut {
  conversation_id: string
  title: string | null
  created_at: string | null
  updated_at: string | null
}

export interface MessageOut {
  message_id: string
  role: MessageRole
  content: string
  created_at: string | null
}

export interface ConversationDetailOut extends ConversationOut {
  messages: MessageOut[]
}

export interface ConversationCreatePayload {
  title?: string | null
}
