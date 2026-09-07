<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

function handleLogout(): void {
  auth.logout()
  void router.replace({ name: 'login' })
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-brand">LifeAgent</div>

    <el-button class="new-chat-button" type="primary" @click="router.push({ name: 'chat' })">
      新对话
    </el-button>

    <div class="sidebar-section">
      <div class="sidebar-section-title">对话</div>
      <!-- 对话列表：由 03 会话 + Chat ticket 填充 -->
      <div class="sidebar-empty">还没有对话</div>
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
