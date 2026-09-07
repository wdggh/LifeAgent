<script setup lang="ts">
import { computed, ref } from 'vue'
import { DOCUMENT_TYPE_OPTIONS } from '../constants/ui'
import { useDocumentStore, type UploadQueueItem } from '../stores/document'
import type { DocumentType } from '../types/document'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()

const store = useDocumentStore()
const selectedType = ref<DocumentType>('other')
const fileInput = ref<HTMLInputElement>()
const selectedFiles = ref<File[]>([])

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const canStart = computed(
  () => !store.uploading && selectedFiles.value.length > 0,
)

const STATUS_LABELS: Record<UploadQueueItem['status'], string> = {
  validating: '预校验',
  uploading: '上传中',
  processing: '处理中',
  completed: '已完成',
  failed: '处理失败',
}

function chooseFiles(): void {
  if (store.uploading) return
  fileInput.value?.click()
}

function onFilesChange(event: Event): void {
  const input = event.target as HTMLInputElement
  if (input.files) {
    selectedFiles.value = Array.from(input.files)
  }
  input.value = ''
}

function removeSelected(index: number): void {
  selectedFiles.value.splice(index, 1)
}

async function handleStart(): Promise<void> {
  if (!canStart.value) return
  const files = [...selectedFiles.value]
  selectedFiles.value = []
  await store.startUpload(files, selectedType.value)
}

function handleClose(): void {
  if (store.uploading) return
  store.clearQueue()
  dialogVisible.value = false
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="上传文档"
    width="560px"
    :close-on-click-modal="false"
    :close-on-press-escape="!store.uploading"
    :show-close="!store.uploading"
    @open="selectedFiles = []"
  >
    <el-form label-position="top">
      <el-form-item label="文档类型">
        <el-select v-model="selectedType" class="type-select">
          <el-option
            v-for="option in DOCUMENT_TYPE_OPTIONS"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="文件（支持 PDF / TXT / Markdown，单个 ≤50MB）">
        <input
          ref="fileInput"
          class="hidden-input"
          type="file"
          multiple
          accept=".pdf,.txt,.md"
          @change="onFilesChange"
        />
        <el-button :disabled="store.uploading" @click="chooseFiles">选择文件</el-button>
      </el-form-item>
    </el-form>

    <div v-if="selectedFiles.length > 0" class="selected-list">
      <div v-for="(file, index) in selectedFiles" :key="index" class="selected-row">
        <span class="selected-name">{{ file.name }}</span>
        <el-button text type="danger" :disabled="store.uploading" @click="removeSelected(index)">
          移除
        </el-button>
      </div>
    </div>

    <div v-if="store.uploadQueue.length > 0" class="queue-list">
      <div v-for="item in store.uploadQueue" :key="item.key" class="queue-row">
        <span class="queue-name">{{ item.filename }}</span>
        <el-tag :type="item.status === 'failed' ? 'danger' : item.status === 'completed' ? 'success' : 'warning'" size="small">
          {{ STATUS_LABELS[item.status] }}
        </el-tag>
        <el-button
          v-if="!store.uploading"
          text
          type="info"
          size="small"
          @click="store.removeQueueItem(item.key)"
        >
          移除
        </el-button>
        <div v-if="item.error" class="queue-error">{{ item.error }}</div>
      </div>
      <div v-if="store.uploadQueue.some((item) => item.status === 'failed')" class="queue-hint">
        处理失败的文档可关闭对话框后在列表中选择「重试」
      </div>
    </div>

    <template #footer>
      <el-button :disabled="store.uploading" @click="handleClose">关闭</el-button>
      <el-button
        type="primary"
        :loading="store.uploading"
        :disabled="!canStart"
        @click="handleStart"
      >
        开始上传
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.hidden-input {
  display: none;
}

.type-select {
  width: 240px;
}

.selected-list,
.queue-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 220px;
  margin-top: 8px;
  overflow-y: auto;
}

.selected-row,
.queue-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 6px;
  background: #f5f7fa;
}

.selected-name,
.queue-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.queue-hint {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

.queue-row {
  flex-wrap: wrap;
}

.queue-error {
  width: 100%;
  font-size: 12px;
  color: #f56c6c;
}
</style>
