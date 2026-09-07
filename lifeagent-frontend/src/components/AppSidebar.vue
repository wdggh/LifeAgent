<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiErrorMessage } from '../api/errors'
import { FALLBACK_CONVERSATION_TITLE } from '../constants/ui'
import { useAuthStore } from '../stores/auth'
import { useConversationStore } from '../stores/conversation'

const router = useRouter()
const auth = useAuthStore()
const conversations = useConversationStore()

onMounted(() => {
  void conversations.fetchConversations()
})

function handleNewChat(): void {
  conversations.startNewChat()
  void router.push({ name: 'chat' })
}

async function handleOpenConversation(conversationId: string): Promise<void> {
  try {
    await conversations.openConversation(conversationId)
    void router.push({ name: 'conversation', params: { conversationId } })
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, '对话加载失败'))
    await conversations.fetchConversations()
  }
}

async function handleDeleteConversation(conversationId: string): Promise<void> {
  try {
    await ElMessageBox.confirm('删除后无法恢复，确定删除这个对话吗？', '删除对话', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await conversations.deleteConversation(conversationId)
    ElMessage.success('对话已删除')
    void router.push({ name: 'chat' })
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, '删除失败，请稍后重试'))
  }
}

function isActive(conversationId: string): boolean {
  return conversations.activeConversationId === conversationId
}

function handleLogout(): void {
  auth.logout()
  void router.replace({ name: 'login' })
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-brand">LifeAgent</div>

    <el-button class="new-chat-button" type="primary" @click="handleNewChat">
      新对话
    </el-button>

    <div class="sidebar-section">
      <div class="sidebar-section-title">对话</div>
      <div v-if="conversations.loadingConversations && conversations.conversations.length === 0" class="sidebar-empty">
        加载中…
      </div>
      <div v-else-if="conversations.conversationListError" class="sidebar-error">
        {{ conversations.conversationListError }}
        <el-button text type="primary" size="small" @click="conversations.fetchConversations()">
          重试
        </el-button>
      </div>
      <div v-else-if="conversations.conversations.length === 0" class="sidebar-empty">
        还没有对话
      </div>
      <div v-else class="conversation-list">
        <div
          v-for="conversation in conversations.conversations"
          :key="conversation.conversation_id"
          class="conversation-item"
          :class="{ active: isActive(conversation.conversation_id) }"
          @click="handleOpenConversation(conversation.conversation_id)"
        >
          <span class="conversation-title">
            {{ conversation.title ?? FALLBACK_CONVERSATION_TITLE }}
          </span>
          <el-button
            class="conversation-delete"
            text
            type="danger"
            size="small"
            @click.stop="handleDeleteConversation(conversation.conversation_id)"
          >
            删除
          </el-button>
        </div>
      </div>
    </div>

    <nav class="sidebar-nav">
      <RouterLink to="/documents" class="nav-item">我的文档</RouterLink>
    </nav>

    <div class="sidebar-user">
      <span class="user-name">{{ auth.user?.username ?? '...' }}</span>
      <el-button text type="primary" @click="handleLogout">退出登录</el-button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 240px;
  min-height: 100vh;
  padding: 16px;
  border-right: 1px solid #e4e7ed;
  background: #fff;
  box-sizing: border-box;
}

.sidebar-brand {
  font-size: 18px;
  font-weight: 700;
}

.new-chat-button {
  width: 100%;
}

.sidebar-section-title {
  margin-bottom: 8px;
  font-size: 12px;
  color: #909399;
}

.sidebar-empty {
  padding: 8px 0;
  font-size: 13px;
  color: #c0c4cc;
}

.sidebar-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  padding: 4px 0;
  font-size: 12px;
  color: #f56c6c;
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.conversation-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
}

.conversation-item:hover {
  background: #f5f7fa;
}

.conversation-item.active {
  background: #ecf5ff;
}

.conversation-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.conversation-delete {
  visibility: hidden;
  flex-shrink: 0;
}

.conversation-item:hover .conversation-delete {
  visibility: visible;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  padding: 8px 10px;
  border-radius: 6px;
  color: #303133;
  font-size: 14px;
  text-decoration: none;
}

.nav-item:hover {
  background: #f5f7fa;
}

.sidebar-user {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  border-top: 1px solid #ebeef5;
  padding-top: 12px;
}

.user-name {
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
