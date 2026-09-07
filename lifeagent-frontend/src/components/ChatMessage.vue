<script setup lang="ts">
import { computed } from 'vue'
import SourceList from './SourceList.vue'
import type { DisplayMessage } from '../stores/conversation'

const props = defineProps<{
  message: DisplayMessage
}>()

const isUser = computed(() => props.message.role === 'user')

function formatTime(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
</script>

<template>
  <div class="message-row" :class="{ 'is-user': isUser }">
    <div class="message-bubble" :class="{ 'is-user': isUser }">
      <div class="message-content">{{ message.content }}</div>
      <SourceList
        v-if="message.sources || message.metadata"
        :sources="message.sources ?? []"
        :metadata="message.metadata"
      />
      <div v-if="!message.optimistic" class="message-time">
        {{ isUser ? '你' : '助手' }} · {{ formatTime(message.created_at) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-row {
  display: flex;
}

.message-row.is-user {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.message-bubble.is-user {
  border-top-right-radius: 2px;
  background: #ecf5ff;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.message-time {
  margin-top: 6px;
  font-size: 11px;
  color: #c0c4cc;
}
</style>
