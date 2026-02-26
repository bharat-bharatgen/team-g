import { useState, useEffect, useRef } from 'react';
import { documentService } from '@/services/document.service';
import { useUploadStore } from '@/store/uploadStore';
import { DocumentType } from '@/types/case.types';
import { FileDropzone } from './FileDropzone';
import { FilePreview } from './FilePreview';
import { UploadProgress } from './UploadProgress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

interface DocumentUploaderProps {
  caseId: string;
  documentType: DocumentType;
  onUploadComplete: () => void;
  initialFiles?: File[];
}

export const DocumentUploader = ({
  caseId,
  documentType,
  onUploadComplete,
  initialFiles = [],
}: DocumentUploaderProps) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>(initialFiles);
  const [error, setError] = useState<string | null>(null);
  const { uploads, addUpload, updateUpload, clearUploads, isUploading, setIsUploading } =
    useUploadStore();

  const isUploadingRef = useRef(false);

  const handleDrop = (files: File[]) => {
    setSelectedFiles((prev) => [...prev, ...files]);
  };

  // Auto-upload when files are selected
  useEffect(() => {
    if (selectedFiles.length > 0 && !isUploading && !isUploadingRef.current) {
      handleUpload();
    }
  }, [selectedFiles]);

  const handleRemove = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0 || isUploadingRef.current) return;

    isUploadingRef.current = true;
    setIsUploading(true);
    setError(null);
    clearUploads();

    try {
      // Step 1: Get pre-signed URLs
      const uploadUrlResponse = await documentService.getUploadUrls(caseId, {
        document_type: documentType,
        files: selectedFiles.map((file) => ({
          file_name: file.name,
          content_type: file.type,
        })),
      });

      // Step 2: Upload each file to S3
      const fileIds: string[] = [];
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const urlData = uploadUrlResponse.files[i];

        addUpload({
          file_name: file.name,
          progress: 0,
          status: 'uploading',
        });

        try {
          // Upload to S3
          await documentService.uploadToS3(urlData.upload_url, file);

          updateUpload(file.name, {
            progress: 100,
            status: 'completed',
          });

          fileIds.push(urlData.file_id);
        } catch (err) {
          updateUpload(file.name, {
            status: 'error',
          });
          throw new Error(`Failed to upload ${file.name}`);
        }
      }

      // Step 3: Confirm upload
      await documentService.confirmUpload(caseId, {
        document_type: documentType,
        file_ids: fileIds,
      });

      // Success!
      setSelectedFiles([]);
      setTimeout(() => {
        clearUploads();
        onUploadComplete();
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
      isUploadingRef.current = false;
    }
  };

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <FileDropzone onDrop={handleDrop} disabled={isUploading} />

      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Selected Files ({selectedFiles.length})</h4>
          <div className="space-y-2">
            {selectedFiles.map((file, index) => (
              <FilePreview
                key={index}
                file={{
                  name: file.name,
                  size: file.size,
                  type: file.type,
                }}
                onRemove={() => handleRemove(index)}
                showPreview={false}
              />
            ))}
          </div>
        </div>
      )}

      <UploadProgress uploads={uploads} />
    </div>
  );
};
