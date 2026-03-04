import { useState, useRef } from 'react';
import { DocumentType } from '@/types/case.types';
import { FileEntry } from '@/types/document.types';
import { documentService } from '@/services/document.service';
import { DocumentTypeCard } from '@/components/upload/DocumentTypeCard';
import { DocumentUploader } from '@/components/upload/DocumentUploader';
import { FilePreview } from '@/components/upload/FilePreview';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { DOCUMENT_TYPE_LABELS } from '@/utils/constants';
import { Upload, Trash2, AlertCircle } from 'lucide-react';

interface DocumentSectionProps {
  caseId: string;
  documents: {
    [key in DocumentType]?: FileEntry[];
  };
  onUpdate: () => void;
}

export const DocumentSection = ({ caseId, documents, onUpdate }: DocumentSectionProps) => {
  const [selectedType, setSelectedType] = useState<DocumentType | null>(null);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  
  // Refs for hidden file inputs
  const fileInputRefs = useRef<{ [key in DocumentType]?: HTMLInputElement | null }>({});

  const handleUploadClick = (type: DocumentType) => {
    setSelectedType(type);
    setError(null);
    // Directly open file picker instead of dialog
    fileInputRefs.current[type]?.click();
  };

  const handleFileSelect = (type: DocumentType, files: FileList | null) => {
    if (files && files.length > 0) {
      setSelectedType(type);
      setPendingFiles(Array.from(files));
      setIsUploadDialogOpen(true);
    }
  };

  const handleUploadComplete = () => {
    setIsUploadDialogOpen(false);
    setPendingFiles([]);
    // Reset the file input value so the same file can be selected again
    if (selectedType && fileInputRefs.current[selectedType]) {
      fileInputRefs.current[selectedType]!.value = '';
    }
    onUpdate();
  };

  const handleDelete = async (type: DocumentType) => {
    if (!confirm(`Delete all ${DOCUMENT_TYPE_LABELS[type]} documents?`)) {
      return;
    }

    setIsDeleting(true);
    setError(null);

    try {
      await documentService.deleteDocuments(caseId, type);
      onUpdate();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete documents');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.values(DocumentType).map((type) => (
          <div key={type}>
            <DocumentTypeCard
              type={type}
              fileCount={documents[type]?.length || 0}
              onClick={() => handleUploadClick(type)}
            />
            {/* Hidden file input for direct file selection */}
            <input
              type="file"
              ref={(el) => (fileInputRefs.current[type] = el)}
              className="hidden"
              accept=".pdf,.jpg,.jpeg,.png"
              multiple
              onChange={(e) => handleFileSelect(type, e.target.files)}
            />
          </div>
        ))}
      </div>

      {Object.entries(documents).map(([type, files]) => {
        if (!files || files.length === 0) return null;

        return (
          <div key={type} className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">{DOCUMENT_TYPE_LABELS[type as DocumentType]}</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDelete(type as DocumentType)}
                disabled={isDeleting}
                className="text-red-600 hover:text-red-700"
              >
                <Trash2 className="h-4 w-4 mr-1" />
                Delete
              </Button>
            </div>
            <div className="space-y-2">
              {files.map((file) => (
                <FilePreview key={file.id} file={file} />
              ))}
            </div>
          </div>
        );
      })}

      <Dialog open={isUploadDialogOpen} onOpenChange={(open) => {
        setIsUploadDialogOpen(open);
        if (!open) {
          setPendingFiles([]);
          // Reset file input when dialog is closed
          if (selectedType && fileInputRefs.current[selectedType]) {
            fileInputRefs.current[selectedType]!.value = '';
          }
        }
      }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              <div className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Upload {selectedType && DOCUMENT_TYPE_LABELS[selectedType]}
              </div>
            </DialogTitle>
          </DialogHeader>
          {selectedType && (
            <DocumentUploader
              caseId={caseId}
              documentType={selectedType}
              onUploadComplete={handleUploadComplete}
              initialFiles={pendingFiles}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
