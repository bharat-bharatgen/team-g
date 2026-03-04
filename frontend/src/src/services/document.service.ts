import api from './api';
import {
  UploadUrlRequest,
  UploadUrlResponse,
  ConfirmUploadRequest,
  DocumentsResponse,
} from '@/types/document.types';
import { DocumentType } from '@/types/case.types';

export const documentService = {
  getUploadUrls: async (
    caseId: string,
    data: UploadUrlRequest
  ): Promise<UploadUrlResponse> => {
    const response = await api.post<UploadUrlResponse>(
      `/cases/${caseId}/documents/upload-url`,
      data
    );
    return response.data;
  },

  uploadToS3: async (url: string, file: File): Promise<void> => {
    await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': file.type,
      },
      body: file,
    });
  },

  confirmUpload: async (
    caseId: string,
    data: ConfirmUploadRequest
  ): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>(
      `/cases/${caseId}/documents/confirm-upload`,
      data
    );
    return response.data;
  },

  getDocuments: async (caseId: string): Promise<DocumentsResponse> => {
    const response = await api.get<DocumentsResponse>(`/cases/${caseId}/documents`);
    return response.data;
  },

  deleteDocuments: async (
    caseId: string,
    documentType: DocumentType
  ): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(
      `/cases/${caseId}/documents/${documentType}`
    );
    return response.data;
  },
};
