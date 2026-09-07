import apiClient from './client'
import type { DocumentOut, DocumentType } from '../types/document'

export interface ListDocumentsParams {
  page?: number
  page_size?: number
}

export async function listDocuments(
  params: ListDocumentsParams = {},
): Promise<DocumentOut[]> {
  const { data } = await apiClient.get<DocumentOut[]>('/documents', { params })
  return data
}

export async function getDocument(documentId: string): Promise<DocumentOut> {
  const { data } = await apiClient.get<DocumentOut>(`/documents/${documentId}`)
  return data
}

export async function uploadDocument(
  file: File,
  documentType: DocumentType,
): Promise<DocumentOut> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('document_type', documentType)
  const { data } = await apiClient.post<DocumentOut>('/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    // 50MB 上传可能超过通用 30s 超时，按请求覆盖
    timeout: 120_000,
  })
  return data
}

export async function deleteDocument(documentId: string): Promise<void> {
  await apiClient.delete(`/documents/${documentId}`)
}

export async function retryDocument(documentId: string): Promise<DocumentOut> {
  const { data } = await apiClient.post<DocumentOut>(
    `/documents/${documentId}/retry`,
  )
  return data
}
