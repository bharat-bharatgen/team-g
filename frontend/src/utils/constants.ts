import { DocumentType } from '@/types/case.types';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'InsureCopilot';

export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  USER_DATA: 'user_data',
} as const;

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  [DocumentType.MER]: 'Medical Examination Report',
  [DocumentType.PATHOLOGY]: 'Pathology Report',
  [DocumentType.PHOTO]: 'Geo-tagged Photo',
  [DocumentType.ID_PROOF]: 'ID Proof',
};

export const DOCUMENT_TYPE_DESCRIPTIONS: Record<DocumentType, string> = {
  [DocumentType.MER]: 'Upload medical examination reports',
  [DocumentType.PATHOLOGY]: 'Upload pathology or lab test reports',
  [DocumentType.PHOTO]: 'Upload geo-tagged photographs',
  [DocumentType.ID_PROOF]: 'Upload government-issued identification',
};

export const ACCEPTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
};

export const CASE_STATUS_COLORS = {
  created: 'bg-slate-100 text-slate-700',
  processing: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
} as const;

export const CASE_STATUS_LABELS = {
  created: 'Created',
  processing: 'Processing',
  completed: 'Completed',
  failed: 'Failed',
} as const;

export const RISK_LEVEL_COLORS = {
  Low: 'bg-green-100 text-green-800 border-green-200',
  Intermediate: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  High: 'bg-red-100 text-red-800 border-red-200',
} as const;

export const RISK_LEVEL_LABELS = {
  Low: 'Low Risk',
  Intermediate: 'Intermediate Risk',
  High: 'High Risk',
} as const;

