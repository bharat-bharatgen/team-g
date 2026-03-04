import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { UploadProgress as UploadProgressType } from '@/types/document.types';

interface UploadProgressProps {
  uploads: UploadProgressType[];
}

export const UploadProgress = ({ uploads }: UploadProgressProps) => {
  if (uploads.length === 0) return null;

  return (
    <div className="space-y-2">
      {uploads.map((upload) => (
        <div key={upload.file_name} className="flex items-center gap-3 p-2 bg-slate-50 rounded">
          <div className="flex-1">
            <p className="text-sm font-medium">{upload.file_name}</p>
            <div className="mt-1 bg-slate-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-primary h-full transition-all duration-300"
                style={{ width: `${upload.progress}%` }}
              />
            </div>
          </div>
          <div>
            {upload.status === 'uploading' && (
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
            )}
            {upload.status === 'completed' && (
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            )}
            {upload.status === 'error' && (
              <XCircle className="h-5 w-5 text-red-600" />
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
