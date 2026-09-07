import apiClient from './client'
import type { ChatRequest, ChatResponse } from '../types/chat'

export async function sendChat(payload: ChatRequest): Promise<ChatResponse> {
  const { data } = await apiClient.post<ChatResponse>('/chat', payload, {
    // Agent 一次回答可能数十秒，chat 请求单独给 120s（spec §2/§3）
    timeout: 120_000,
  })
  return data
}
