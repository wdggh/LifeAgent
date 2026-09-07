// 与后端 app/schemas/document.py 对齐（Backend API contract is the source of truth）。

export type FileType = 'pdf' | 'txt' | 'markdown'

export type DocumentType =
  | 'contract'
  | 'purchase_record'
  | 'warranty'
  | 'manual'
  | 'note'
  | 'other'

export type DocumentStatus = 'uploaded' | 'processing' | 'completed' | 'failed'

export type ProcessingStage = 'parsing' | 'chunking' | 'embedding' | 'indexing'

export interface DocumentOut {
  document_id: string
  filename: string
  file_type: FileType
  document_type: DocumentType
  file_size: number
  status: DocumentStatus
  processing_stage: ProcessingStage | null
  error_message: string | null
  created_at: string | null
  updated_at: string | null
}
