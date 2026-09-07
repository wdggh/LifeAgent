<script setup lang="ts">
import { formatDurationMs } from '../constants/ui'
import type { ChatMetadata, ChatSource } from '../types/chat'

defineProps<{
  sources: ChatSource[]
  metadata?: ChatMetadata
}>()
</script>

<template>
  <div class="source-list">
    <div v-if="sources.length === 0" class="source-empty">本次未引用文档</div>
    <template v-else>
      <div class="source-title">来源</div>
      <div v-for="source in sources" :key="source.document_id" class="source-item">
        <span class="source-name">📄 {{ source.document_name }}</span>
        <el-progress
          class="source-progress"
          :percentage="Math.round(source.relevance * 100)"
          :show-text="false"
          :stroke-width="4"
        />
        <span class="source-relevance">{{ Math.round(source.relevance * 100) }}%</span>
      </div>
    </template>
    <div v-if="metadata" class="source-metadata">
      检索 {{ metadata.retrieval_count }} 次 · 用时 {{ formatDurationMs(metadata.duration_ms) }}
    </div>
  </div>
</template>

<style scoped>
.source-list {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.55);
}

.source-empty {
  font-size: 12px;
  color: #909399;
}

.source-title {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
  font-size: 12px;
}

.source-name {
  max-width: 55%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-progress {
  flex: 1;
}

.source-relevance {
  color: #909399;
}

.source-metadata {
  margin-top: 6px;
  font-size: 11px;
  color: #c0c4cc;
}
</style>
