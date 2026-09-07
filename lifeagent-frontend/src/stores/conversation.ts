import { defineStore } from 'pinia'
import * as conversationsApi from '../api/conversations'
import * as chatApi from '../api/chat'
import { apiErrorMessage } from '../api/errors'
import type { ConversationOut, MessageOut } from '../types/conversation'
import type { ChatMetadata, ChatSource } from '../types/chat'

export interface DisplayMessage extends MessageOut {
  sources?: ChatSource[]
  metadata?: ChatMetadata
  optimistic?: boolean
}

export interface ChatFailure {
  conversationId: string | null
  message: string
}

export type SendResult =
  | { ok: true; createdConversationId?: string; finishedAway: boolean }
  | { ok: false; message: string }

const TITLE_CHAR_LIMIT = 30

export const useConversationStore = defineStore('conversation', {
  state: () => ({
    conversations: [] as ConversationOut[],
    activeConversationId: null as string | null,
    messages: [] as DisplayMessage[],
    loadingConversations: false,
    loadingMessages: false,
    conversationListError: null as string | null,
    inFlight: false,
    failure: null as ChatFailure | null,
    /** 会话内 assistant 消息的来源/检索信息缓存（刷新历史后仍可展示；浏览器刷新后由后端历史兜底）。 */
    sourceCache: {} as Record<
      string,
      { sources: ChatSource[]; metadata: ChatMetadata }
    >,
  }),

  getters: {
    isDraft(state): boolean {
      return state.activeConversationId === null
    },
    activeConversation(state) {
      return (
        state.conversations.find(
          (conversation) =>
            conversation.conversation_id === state.activeConversationId,
        ) ?? null
      )
    },
  },

  actions: {
    async fetchConversations(): Promise<void> {
      this.loadingConversations = true
      this.conversationListError = null
      try {
        this.conversations = await conversationsApi.listConversations()
      } catch (error) {
        this.conversationListError = apiErrorMessage(
          error,
          '对话列表加载失败，请稍后重试',
        )
      } finally {
        this.loadingConversations = false
      }
    },

    /** 新对话 = draft：不产生后端对象（ADR-0008）。 */
    startNewChat(): void {
      this.activeConversationId = null
      this.messages = []
      this.failure = null
    },

    async openConversation(conversationId: string): Promise<void> {
      if (this.activeConversationId === conversationId && this.messages.length > 0) {
        return
      }
      this.activeConversationId = conversationId
      this.loadingMessages = true
      this.failure = null
      try {
        const detail = await conversationsApi.getConversation(conversationId)
        this.messages = this.attachSources(detail.messages)
      } finally {
        this.loadingMessages = false
      }
    },

    attachSources(messages: MessageOut[]): DisplayMessage[] {
      return messages.map((message) => {
        const display: DisplayMessage = { ...message }
        if (message.role === 'assistant') {
          const cached =
            this.sourceCache[`${this.activeConversationId}:${message.message_id}`]
          if (cached) {
            display.sources = cached.sources
            display.metadata = cached.metadata
          }
        }
        return display
      })
    },

    async sendMessage(text: string): Promise<SendResult> {
      if (this.inFlight) return { ok: false, message: '已有问题在回答中，请稍候' }
      const query = text.trim()
      if (!query) return { ok: false, message: '请输入问题' }

      let targetId = this.activeConversationId
      let createdConversationId: string | undefined
      this.inFlight = true
      this.failure = null

      const optimisticUser: DisplayMessage = {
        message_id: `local-${Date.now()}`,
        role: 'user',
        content: query,
        created_at: new Date().toISOString(),
        optimistic: true,
      }
      this.messages.push(optimisticUser)

      try {
        if (!targetId) {
          const conversation = await conversationsApi.createConversation({
            title: query.slice(0, TITLE_CHAR_LIMIT),
          })
          targetId = conversation.conversation_id
          createdConversationId = conversation.conversation_id
          this.activeConversationId = targetId
          this.conversations.unshift(conversation)
        }

        const response = await chatApi.sendChat({
          conversation_id: targetId,
          query,
        })

        // 会话列表刷新失败不应让发送看起来失败
        try {
          await this.fetchConversations()
        } catch {
          // 忽略：下次进入页面/发送时再刷新
        }

        const detail = await conversationsApi.getConversation(targetId)
        const lastAssistant = [...detail.messages]
          .reverse()
          .find((message) => message.role === 'assistant')
        if (lastAssistant) {
          this.sourceCache[`${targetId}:${lastAssistant.message_id}`] = {
            sources: response.sources,
            metadata: response.metadata,
          }
        }

        const finishedAway = this.activeConversationId !== targetId
        if (!finishedAway) {
          this.messages = this.attachSources(detail.messages)
        }
        return { ok: true, createdConversationId, finishedAway }
      } catch (error) {
        const message = apiErrorMessage(error, '回答失败，请稍后重试')
        this.failure = { conversationId: targetId, message }

        if (!targetId) {
          // 会话还没建成：乐观消息未落库，移除后保留输入框内容由用户决定
          this.messages = this.messages.filter(
            (item) => item.message_id !== optimisticUser.message_id,
          )
        } else if (this.activeConversationId === targetId) {
          // 失败语义：刷新历史，把可能已落库的 user Message 如实显示出来（spec §11）
          try {
            const detail = await conversationsApi.getConversation(targetId)
            this.messages = this.attachSources(detail.messages)
          } catch {
            // 详情刷新失败时保留乐观消息
          }
        }
        return { ok: false, message }
      } finally {
        this.inFlight = false
      }
    },

    async deleteConversation(conversationId: string): Promise<void> {
      await conversationsApi.deleteConversation(conversationId)
      this.conversations = this.conversations.filter(
        (conversation) => conversation.conversation_id !== conversationId,
      )
      for (const key of Object.keys(this.sourceCache)) {
        if (key.startsWith(`${conversationId}:`)) {
          delete this.sourceCache[key]
        }
      }
      if (this.activeConversationId === conversationId) {
        this.startNewChat()
      }
    },
  },
})
