import { DocumentType } from './case.types';

export interface FileUploadRequest {
  file_name: string;
  content_type: string;
}

export interface UploadUrlRequest {
  document_type: DocumentType;
  files: FileUploadRequest[];
}

export interface FileUploadUrlResponse {
  file_id: string;
  file_name: string;
  upload_url: string;
}

export interface UploadUrlResponse {
  document_type: DocumentType;
  files: FileUploadUrlResponse[];
}

export interface ConfirmUploadRequest {
  document_type: DocumentType;
  file_ids: string[];
}

export interface DocumentsResponse {
  documents: {
    [key in DocumentType]: FileEntry[];
  };
}

export interface FileEntry {
  id: string;
  file_name: string;
  content_type: string;
  url: string;
  uploaded_at: string;
}

export interface UploadProgress {
  file_name: string;
  progress: number;
  status: 'uploading' | 'completed' | 'error';
}
