import api from './api';
import { PathologyResultResponse, PathologyVersionsResponse, PathologyImportResponse, PathologySummaryResponse } from '@/types/case.types';

export const pathologyService = {
  getResult: async (caseId: string, version?: number): Promise<PathologyResultResponse> => {
    const params = version ? `?version=${version}` : '';
    const response = await api.get<PathologyResultResponse>(`/cases/${caseId}/pathology/result${params}`);
    return response.data;
  },

  getSummary: async (caseId: string, version?: number): Promise<PathologySummaryResponse> => {
    const params = version ? `?version=${version}` : '';
    const response = await api.get<PathologySummaryResponse>(`/cases/${caseId}/pathology/summary${params}`);
    return response.data;
  },

  getVersions: async (caseId: string): Promise<PathologyVersionsResponse> => {
    const response = await api.get<PathologyVersionsResponse>(`/cases/${caseId}/pathology/versions`);
    return response.data;
  },

  exportExcel: async (caseId: string, version?: number): Promise<Blob> => {
    const params = version ? `?version=${version}` : '';
    const response = await api.get(`/cases/${caseId}/pathology/export-excel${params}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  importExcel: async (caseId: string, file: File): Promise<PathologyImportResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post<PathologyImportResponse>(
      `/cases/${caseId}/pathology/import-excel`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },
};
