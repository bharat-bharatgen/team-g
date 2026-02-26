import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ACCEPTED_FILE_TYPES } from '@/utils/constants';

interface FileDropzoneProps {
  onDrop: (files: File[]) => void;
  disabled?: boolean;
}

export const FileDropzone = ({ onDrop, disabled }: FileDropzoneProps) => {
  const handleDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (!disabled) {
        onDrop(acceptedFiles);
      }
    },
    [onDrop, disabled]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleDrop,
    accept: ACCEPTED_FILE_TYPES,
    disabled,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
        isDragActive && 'border-primary bg-primary/5',
        !isDragActive && 'border-slate-300 hover:border-primary',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-2">
        <div className="bg-slate-100 p-3 rounded-full">
          <Upload className="h-6 w-6 text-slate-600" />
        </div>
        <div>
          <p className="font-medium">
            {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            or click to browse
          </p>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Supports PDF, JPEG, PNG
        </p>
      </div>
    </div>
  );
};
