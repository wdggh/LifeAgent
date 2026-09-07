<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiErrorMessage } from '../api/errors'
import DocumentUploadDialog from '../components/DocumentUploadDialog.vue'
import {
  DOCUMENT_STATUS_LABELS,
  DOCUMENT_TYPE_LABELS,
  PROCESSING_STAGE_LABELS,
  formatFileSize,
} from '../constants/ui'
import { useDocumentStore } from '../stores/document'
import type {
  DocumentOut,
  DocumentStatus,
  DocumentType,
  ProcessingStage,
} from '../types/document'

const documents = useDocumentStore()
const uploadDialogOpen = ref(false)

const expandRowKeys = computed(() =>
  documents.expandedDocumentId ? [documents.expandedDocumentId] : [],
)

onMounted(() => {
  void documents.fetchDocuments()
})

onBeforeUnmount(() => {
  documents.stopPolling()
})

function statusTagType(status: DocumentStatus): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'processing') return 'warning'
  return 'info'
}

function processingStageLabel(stage: ProcessingStage | null | undefined): string {
  return stage ? PROCESSING_STAGE_LABELS[stage] : '—'
}

function documentTypeLabel(documentType: DocumentType): string {
  return DOCUMENT_TYPE_LABELS[documentType]
}

function documentStatusLabel(status: DocumentStatus): string {
  return DOCUMENT_STATUS_LABELS[status]
}

function formatDateTime(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN', { hour12: false })
}

function handleExpandChange(_row: DocumentOut, expandedRows: DocumentOut[]): void {
  documents.expandedDocumentId = expandedRows[0]?.document_id ?? null
}

async function handleDelete(document: DocumentOut): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `删除「${document.filename}」会同时移除它的向量与检索内容，确定删除吗？`,
      '删除文档',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await documents.deleteDocument(document.document_id)
    ElMessage.success('文档已删除')
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, '删除失败，请稍后重试'))
  }
}

async function handleRetry(document: DocumentOut): Promise<void> {
  try {
    await documents.retryDocument(document.document_id)
    ElMessage.success('已重新提交处理')
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, '重试失败，请稍后重试'))
  }
}
</script>

<template>
  <div class="documents-page">
    <header class="documents-header">
      <h2 class="documents-title">我的文档</h2>
      <el-button type="primary" @click="uploadDialogOpen = true">上传文档</el-button>
    </header>

    <div v-if="documents.listError" class="list-error">
      {{ documents.listError }}
      <el-button text type="primary" @click="documents.fetchDocuments()">重试</el-button>
    </div>

    <el-table
      v-loading="documents.loadingList"
      :data="documents.documents"
      row-key="document_id"
      :expand-row-keys="expandRowKeys"
      class="documents-table"
      @expand-change="handleExpandChange"
    >
      <el-table-column type="expand">
        <template #default="{ row }">
          <el-descriptions :column="2" size="small" border class="document-detail">
            <el-descriptions-item label="处理阶段">
              {{ processingStageLabel(row.processing_stage) }}
            </el-descriptions-item>
            <el-descriptions-item label="文件类型">{{ row.file_type }}</el-descriptions-item>
            <el-descriptions-item label="大小">{{ formatFileSize(row.file_size) }}</el-descriptions-item>
            <el-descriptions-item label="文档类型">
              {{ documentTypeLabel(row.document_type) }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDateTime(row.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatDateTime(row.updated_at) }}</el-descriptions-item>
            <el-descriptions-item v-if="row.error_message" label="错误信息" :span="2">
              {{ row.error_message }}
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </el-table-column>
      <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
      <el-table-column label="文档类型" width="120">
        <template #default="{ row }">{{ documentTypeLabel(row.document_type) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">
            {{ documentStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="更新时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button v-if="row.status === 'failed'" text type="primary" size="small" @click="handleRetry(row)">
            重试
          </el-button>
          <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="还没有文档，点击右上角「上传文档」开始建立知识库" />
      </template>
    </el-table>

    <DocumentUploadDialog v-model="uploadDialogOpen" />
  </div>
</template>

<style scoped>
.documents-page {
  max-width: 1000px;
  margin: 0 auto;
}

.documents-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.documents-title {
  margin: 0;
  font-size: 20px;
}

.list-error {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #f56c6c;
  font-size: 13px;
}

.documents-table {
  background: #fff;
  border-radius: 8px;
}

.document-detail {
  margin: 10px 14px;
}
</style>
