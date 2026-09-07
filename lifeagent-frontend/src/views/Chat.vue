<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiErrorMessage } from '../api/errors'
import ChatMessage from '../components/ChatMessage.vue'
import { FALLBACK_CONVERSATION_TITLE } from '../constants/ui'
import { useConversationStore } from '../stores/conversation'

const route = useRoute()
const router = useRouter()
const conversations = useConversationStore()

const input = ref('')
const messageListRef = ref<HTMLElement>()

const routeConversationId = computed(() => {
  const value = route.params.conversationId
  return typeof value === 'string' ? value : null
})

const pageTitle = computed(() => {
  if (conversations.isDraft) return '新对话'
  return conversations.activeConversation?.title ?? FALLBACK_CONVERSATION_TITLE
})

const showFailure = computed(
  () =>
    conversations.failure !== null &&
    conversations.failure.conversationId === conversations.activeConversationId,
)

watch(
  routeConversationId,
  async (conversationId) => {
    if (!conversationId) {
      if (!conversations.isDraft) {
        conversations.startNewChat()
      }
      return
    }
    if (conversations.activeConversationId === conversationId) return
    try {
      await conversations.openConversation(conversationId)
    } catch (error) {
      ElMessage.error(apiErrorMessage(error, '对话加载失败'))
      await conversations.fetchConversations()
      void router.replace({ name: 'chat' })
    }
  },
  { immediate: true },
)

// 会话被删除等导致 active 置空时，把地址栏从 /chat/:id 收回 /chat
watch(
  () => conversations.activeConversationId,
  (activeId) => {
    if (activeId === null && routeConversationId.value) {
      void router.replace({ name: 'chat' })
    }
  },
)

watch(
  () => [conversations.messages.length, conversations.inFlight],
  async () => {
    await nextTick()
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  },
)

async function handleSend(): Promise<void> {
  const text = input.value
  if (!text.trim() || conversations.inFlight) return

  const startedConversationId = conversations.activeConversationId
  const result = await conversations.sendMessage(text)
  if (result.ok) {
    const stayed =
      startedConversationId !== null
        ? conversations.activeConversationId === startedConversationId
        : conversations.activeConversationId === result.createdConversationId
    if (stayed) {
      input.value = ''
    }
    if (result.createdConversationId && stayed) {
      void router.replace({
        name: 'conversation',
        params: { conversationId: result.createdConversationId },
      })
    }
    if (result.finishedAway && !stayed) {
      ElMessage.success('回答已完成，可在对应对话中查看')
    }
    return
  }

  const away = conversations.failure?.conversationId !== conversations.activeConversationId
  if (away) {
    ElMessage.error(result.message)
  }
}

function clearFailure(): void {
  conversations.failure = null
}
</script>

<template>
  <div class="chat-page">
    <header class="chat-header">
      <h2 class="chat-title">{{ pageTitle }}</h2>
    </header>

    <div ref="messageListRef" v-loading="conversations.loadingMessages" class="message-list">
      <ChatMessage v-for="message in conversations.messages" :key="message.message_id" :message="message" />

      <div v-if="conversations.inFlight" class="thinking-row">思考中…</div>

      <div v-if="conversations.messages.length === 0 && !conversations.inFlight" class="empty-state">
        <p class="empty-title">新对话</p>
        <p class="empty-hint">从你的文档知识库提问，例如：「我的健身会员还有必要续吗？」</p>
      </div>
    </div>

    <div v-if="showFailure" class="failure-box">
      <span>
        {{ conversations.failure?.message }} —— 之前的提问可能已保存，若再次发送会在历史中留下重复提问，请自行决定。
      </span>
      <el-button text type="primary" size="small" @click="clearFailure">知道了</el-button>
    </div>

    <footer class="chat-input-area">
      <el-input
        v-model="input"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 5 }"
        :disabled="conversations.inFlight"
        placeholder="输入你的问题…（Enter 发送，Shift+Enter 换行）"
        @keydown.enter.exact.prevent="handleSend"
      />
      <el-button
        type="primary"
        class="send-button"
        :disabled="!input.trim() || conversations.inFlight"
        @click="handleSend"
      >
        发送
      </el-button>
    </footer>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 48px);
  max-width: 900px;
  margin: 0 auto;
}

.chat-header {
  padding-bottom: 12px;
}

.chat-title {
  margin: 0;
  font-size: 18px;
}

.message-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  padding: 8px 2px;
}

.thinking-row {
  align-self: flex-start;
  color: #909399;
  font-size: 13px;
}

.empty-state {
  margin: auto;
  text-align: center;
}

.empty-title {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 600;
  color: #303133;
}

.empty-hint {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.failure-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #fef0f0;
  color: #f56c6c;
  font-size: 13px;
}

.chat-input-area {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding-top: 12px;
}

.send-button {
  height: 40px;
}
</style>
