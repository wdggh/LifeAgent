import { defineStore } from 'pinia'
import * as documentsApi from '../api/documents'
import { apiErrorMessage } from '../api/errors'
import {
  ALLOWED_DOCUMENT_EXTENSIONS,
  MAX_FILE_SIZE_MB,
} from '../constants/ui'
import type { DocumentOut, DocumentType } from '../types/document'

export type UploadItemStatus =
  | 'validating'
  | 'uploading'
  | 'processing'
  | 'completed'
  | 'failed'

export interface UploadQueueItem {
  key: string
  filename: string
  file: File
  status: UploadItemStatus
  error: string | null
  document_id: string | null
}

const POLL_INTERVAL_MS = 3_000
let uid = 0

function nextKey(): string {
  uid += 1
  return `upload-${Date.now()}-${uid}`
}

let pollTimer: ReturnType<typeof setInterval> | null = null
let pollBusy = false

export const useDocumentStore = defineStore('document', {
  state: () => ({
    documents: [] as DocumentOut[],
    loadingList: false,
    listError: null as string | null,
    uploadQueue: [] as UploadQueueItem[],
    uploading: false,
    expandedDocumentId: null as string | null,
  }),

  getters: {
    processingDocumentIds(state): string[] {
      return state.documents
        .filter((document) => document.status === 'processing')
        .map((document) => document.document_id)
    },
  },

  actions: {
    async fetchDocuments(): Promise<void> {
      this.loadingList = true
      this.listError = null
      try {
        this.documents = await documentsApi.listDocuments({
          page: 1,
          page_size: 100,
        })
        this.syncQueueFromDocuments()
      } catch (error) {
        this.listError = apiErrorMessage(error, '文档列表加载失败，请稍后重试')
      } finally {
        this.loadingList = false
      }
      this.ensurePolling()
    },

    replaceDocument(document: DocumentOut): void {
      const index = this.documents.findIndex(
        (item) => item.document_id === document.document_id,
      )
      if (index >= 0) {
        this.documents[index] = document
      } else {
        this.documents.unshift(document)
      }
      this.syncQueueFromDocuments()
      this.ensurePolling()
    },

    /** 上传队列与后端文档状态同步（对话框停留时，列表轮询也会推动队列行）。 */
    syncQueueFromDocuments(): void {
      for (const item of this.uploadQueue) {
        if (!item.document_id) continue
        const document = this.documents.find(
          (candidate) => candidate.document_id === item.document_id,
        )
        if (!document) continue
        if (document.status === 'completed') {
          item.status = 'completed'
          item.error = null
        } else if (document.status === 'failed') {
          item.status = 'failed'
          item.error = document.error_message ?? '处理失败'
        }
      }
    },

    /** 只轮询“可见的 processing 文档”，全部终态后自动停止（spec §9）。 */
    ensurePolling(): void {
      if (this.processingDocumentIds.length > 0) {
        if (!pollTimer) {
          pollTimer = setInterval(() => {
            void this.refreshProcessingDocuments()
          }, POLL_INTERVAL_MS)
        }
      } else {
        this.stopPolling()
      }
    },

    async refreshProcessingDocuments(): Promise<void> {
      if (pollBusy) return
      const ids = this.processingDocumentIds
      if (ids.length === 0) {
        this.stopPolling()
        return
      }
      pollBusy = true
      try {
        const refreshed = await Promise.all(ids.map(documentsApi.getDocument))
        for (const document of refreshed) {
          this.replaceDocument(document)
        }
      } catch {
        // 单次轮询失败不打断页面；下一轮继续
      } finally {
        pollBusy = false
      }
      if (this.processingDocumentIds.length === 0) {
        this.stopPolling()
      }
    },

    stopPolling(): void {
      if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
      }
    },

    /** 逐个上传：每个文件独立状态行；单个失败不阻塞后续文件。 */
    async startUpload(files: File[], documentType: DocumentType): Promise<void> {
      if (this.uploading) return
      const items: UploadQueueItem[] = files.map((file) => ({
        key: nextKey(),
        filename: file.name,
        file,
        status: 'validating',
        error: null,
        document_id: null,
      }))
      this.uploadQueue.push(...items)
      this.uploading = true
      try {
        for (const item of items) {
          await this.uploadOne(item, documentType)
        }
      } finally {
        this.uploading = false
      }
      await this.fetchDocuments()
    },

    async uploadOne(
      item: UploadQueueItem,
      documentType: DocumentType,
    ): Promise<void> {
      const extension = `.${item.file.name.split('.').pop()?.toLowerCase() ?? ''}`
      if (!(ALLOWED_DOCUMENT_EXTENSIONS as readonly string[]).includes(extension)) {
        item.status = 'failed'
        item.error = '不支持的文件类型（支持 PDF/TXT/Markdown）'
        return
      }
      if (item.file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
        item.status = 'failed'
        item.error = '文件超过 50MB 限制'
        return
      }

      item.status = 'uploading'
      item.error = null
      try {
        const document = await documentsApi.uploadDocument(item.file, documentType)
        item.document_id = document.document_id
        if (document.status === 'completed') {
          item.status = 'completed'
        } else if (document.status === 'failed') {
          item.status = 'failed'
          item.error = document.error_message ?? '处理失败'
        } else {
          item.status = 'processing'
        }
        this.replaceDocument(document)
      } catch (error) {
        item.status = 'failed'
        item.error = apiErrorMessage(error, '上传失败，请稍后重试')
      }
    },

    clearQueue(): void {
      this.uploadQueue = []
    },

    removeQueueItem(key: string): void {
      this.uploadQueue = this.uploadQueue.filter((item) => item.key !== key)
    },

    async deleteDocument(documentId: string): Promise<void> {
      await documentsApi.deleteDocument(documentId)
      this.documents = this.documents.filter(
        (document) => document.document_id !== documentId,
      )
      if (this.expandedDocumentId === documentId) {
        this.expandedDocumentId = null
      }
      this.ensurePolling()
    },

    async retryDocument(documentId: string): Promise<void> {
      const document = await documentsApi.retryDocument(documentId)
      this.replaceDocument(document)
      this.ensurePolling()
    },
  },
})
