import apiClient from './client'
import type {
  ConversationCreatePayload,
  ConversationDetailOut,
  ConversationOut,
} from '../types/conversation'

export async function listConversations(): Promise<ConversationOut[]> {
  const { data } = await apiClient.get<ConversationOut[]>('/conversations')
  return data
}

export async function createConversation(
  payload: ConversationCreatePayload = {},
): Promise<ConversationOut> {
  const { data } = await apiClient.post<ConversationOut>('/conversations', payload)
  return data
}

export async function getConversation(
  conversationId: string,
): Promise<ConversationDetailOut> {
  const { data } = await apiClient.get<ConversationDetailOut>(
    `/conversations/${conversationId}`,
  )
  return data
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await apiClient.delete(`/conversations/${conversationId}`)
}
