import { create } from 'zustand';
import { UploadProgress } from '@/types/document.types';

interface UploadState {
  uploads: UploadProgress[];
  isUploading: boolean;
  setUploads: (uploads: UploadProgress[]) => void;
  addUpload: (upload: UploadProgress) => void;
  updateUpload: (fileName: string, updates: Partial<UploadProgress>) => void;
  clearUploads: () => void;
  setIsUploading: (isUploading: boolean) => void;
}

export const useUploadStore = create<UploadState>((set) => ({
  uploads: [],
  isUploading: false,

  setUploads: (uploads) => set({ uploads }),

  addUpload: (upload) =>
    set((state) => ({
      uploads: [...state.uploads, upload],
    })),

  updateUpload: (fileName, updates) =>
    set((state) => ({
      uploads: state.uploads.map((u) =>
        u.file_name === fileName ? { ...u, ...updates } : u
      ),
    })),

  clearUploads: () => set({ uploads: [] }),

  setIsUploading: (isUploading) => set({ isUploading }),
}));
