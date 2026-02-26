import api from './api';
import { TestVerificationResultResponse } from '@/types/case.types';

export const testVerificationService = {
  getResult: async (caseId: string): Promise<TestVerificationResultResponse> => {
    const response = await api.get<TestVerificationResultResponse>(
      `/cases/${caseId}/test-verification/result`
    );
    return response.data;
  },

  process: async (caseId: string): Promise<{ status: string; message: string }> => {
    const response = await api.post(`/cases/${caseId}/test-verification/process`);
    return response.data;
  },
};
