import api from './api';
import {
  FaceMatchResultResponse,
  FaceMatchReviewRequest,
  FaceMatchReviewResponse,
} from '@/types/case.types';

export const faceMatchService = {
  /**
   * Get face match result for a case
   */
  getResult: async (caseId: string): Promise<FaceMatchResultResponse> => {
    const response = await api.get(`/cases/${caseId}/face-match`);
    return response.data;
  },

  /**
   * Review (approve/reject) a face match result
   */
  reviewResult: async (
    caseId: string,
    reviewData: FaceMatchReviewRequest
  ): Promise<FaceMatchReviewResponse> => {
    const response = await api.patch(
      `/cases/${caseId}/face-match/review`,
      reviewData
    );
    return response.data;
  },
};
