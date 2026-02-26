import api from './api';

export interface LocationSource {
  source_type: string;  // "photo" | "id_card" | "lab"
  status: string;       // "found" | "not_found" | "skipped" | "geocode_failed"
  raw_input?: string;
  address?: string;
  coords?: [number, number];
  message?: string;
}

export interface DistanceResult {
  source_a: string;
  source_b: string;
  distance_km: number;
  flag: boolean;
}

export interface LocationCheckResult {
  id: string;
  case_id: string;
  version: number;
  photo_file_id?: string;
  id_file_id?: string;
  pathology_version?: number;
  photo_url?: string;
  id_url?: string;
  sources: LocationSource[];
  distances: DistanceResult[];
  sources_detected: string[];
  sources_not_detected: string[];
  decision: string;  // "pass" | "fail" | "insufficient"
  flags: string[];
  message: string;
  review_status: string;  // "pending" | "approved" | "rejected"
  reviewed_by?: string;
  reviewed_at?: string;
  review_comment?: string;
  created_at: string;
}

export interface LocationCheckReviewRequest {
  status: 'approved' | 'rejected';
  comment?: string;
}

export interface LocationCheckReviewResponse {
  case_id: string;
  review_status: string;
  reviewed_by: string;
  reviewed_at: string;
  review_comment?: string;
  message: string;
}

export const locationCheckService = {
  getResult: async (caseId: string): Promise<LocationCheckResult> => {
    const response = await api.get(`/cases/${caseId}/location-check`);
    return response.data;
  },

  reviewResult: async (
    caseId: string,
    reviewData: LocationCheckReviewRequest
  ): Promise<LocationCheckReviewResponse> => {
    const response = await api.patch(
      `/cases/${caseId}/location-check/review`,
      reviewData
    );
    return response.data;
  },
};
