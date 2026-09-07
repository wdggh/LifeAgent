import type {
  DocumentStatus,
  DocumentType,
  ProcessingStage,
} from '../types/document'

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  contract: '合同',
  purchase_record: '购买记录',
  warranty: '保修凭证',
  manual: '说明书',
  note: '笔记',
  other: '其他',
}

export const DOCUMENT_TYPE_OPTIONS: Array<{ value: DocumentType; label: string }> =
  (Object.entries(DOCUMENT_TYPE_LABELS) as Array<[DocumentType, string]>).map(
    ([value, label]) => ({ value, label }),
  )

export const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, string> = {
  uploaded: '已上传',
  processing: '处理中',
  completed: '已完成',
  failed: '处理失败',
}

export const PROCESSING_STAGE_LABELS: Record<ProcessingStage, string> = {
  parsing: '解析中',
  chunking: '切分中',
  embedding: '向量化中',
  indexing: '索引中',
}

export const ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.txt', '.md'] as const

export const MAX_FILE_SIZE_MB = 50

/** Conversation title 为 null 时列表/标题的兜底显示（spec：不做“空会话”术语）。 */
export const FALLBACK_CONVERSATION_TITLE = '未命名对话'

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function formatDurationMs(durationMs: number): string {
  const seconds = durationMs / 1000
  return `${seconds.toFixed(1)}s`
}
