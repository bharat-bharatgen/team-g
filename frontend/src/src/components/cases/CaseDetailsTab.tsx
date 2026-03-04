import { useState, useCallback, useRef } from 'react';
import { Case, DocumentType, PipelineStatus, PipelineStatusDetail } from '@/types/case.types';
import { FileEntry } from '@/types/document.types';
import { documentService } from '@/services/document.service';
import { DocumentUploader } from '@/components/upload/DocumentUploader';
import { FilePreview } from '@/components/upload/FilePreview';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { DOCUMENT_TYPE_LABELS, DOCUMENT_TYPE_DESCRIPTIONS } from '@/utils/constants';
import {
  FileText,
  FlaskConical,
  Camera,
  CreditCard,
  Upload,
  ChevronDown,
  ChevronUp,
  Trash2,
  AlertCircle,
  CheckCircle2,
  PlayCircle,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface CaseDetailsTabProps {
  caseData: Case;
  pipelineDetails: { [key: string]: PipelineStatusDetail };
  onUpdate: () => void;
  onProcessAll: () => void;
  isProcessing: boolean;
}

const iconMap = {
  [DocumentType.MER]: FileText,
  [DocumentType.PATHOLOGY]: FlaskConical,
  [DocumentType.PHOTO]: Camera,
  [DocumentType.ID_PROOF]: CreditCard,
};

export const CaseDetailsTab = ({
  caseData,
  pipelineDetails,
  onUpdate,
  onProcessAll,
  isProcessing,
}: CaseDetailsTabProps) => {
  const [selectedType, setSelectedType] = useState<DocumentType | null>(null);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [expandedTypes, setExpandedTypes] = useState<Set<DocumentType>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRefs = useRef<{ [key in DocumentType]?: HTMLInputElement | null }>({});
  const documents = caseData.documents || {};

  const hasDocuments = useCallback(() => {
    return Object.values(documents).some((files) => files && files.length > 0);
  }, [documents]);

  const isAnyPipelineProcessing = () => {
    return Object.values(pipelineDetails).some(
      (detail) => detail.status === PipelineStatus.PROCESSING
    );
  };

  const toggleExpanded = (type: DocumentType) => {
    const newExpanded = new Set(expandedTypes);
    if (newExpanded.has(type)) {
      newExpanded.delete(type);
    } else {
      newExpanded.add(type);
    }
    setExpandedTypes(newExpanded);
  };

  const handleUploadClick = (type: DocumentType) => {
    setSelectedType(type);
    setError(null);
    fileInputRefs.current[type]?.click();
  };

  const handleFileSelect = (type: DocumentType, files: FileList | null) => {
    if (files && files.length > 0) {
      setSelectedType(type);
      setPendingFiles(Array.from(files));
      setIsUploadDialogOpen(true);
    }
  };

  const handleDialogClose = (open: boolean) => {
    if (!open) {
      setIsUploadDialogOpen(false);
      setPendingFiles([]);
      if (selectedType && fileInputRefs.current[selectedType]) {
        fileInputRefs.current[selectedType]!.value = '';
      }
    }
  };

  const handleUploadComplete = () => {
    setIsUploadDialogOpen(false);
    setPendingFiles([]);
    if (selectedType && fileInputRefs.current[selectedType]) {
      fileInputRefs.current[selectedType]!.value = '';
    }
    onUpdate();
  };

  const handleDelete = async (type: DocumentType, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Delete all ${DOCUMENT_TYPE_LABELS[type]} documents?`)) {
      return;
    }

    setIsDeleting(true);
    setError(null);

    try {
      await documentService.deleteDocuments(caseData.id, type);
      onUpdate();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete documents');
    } finally {
      setIsDeleting(false);
    }
  };

  const canProcess = hasDocuments() && !isAnyPipelineProcessing() && !isProcessing;

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Documents Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Documents</h3>
          {hasDocuments() && (
            <Button
              onClick={onProcessAll}
              disabled={!canProcess}
              size="sm"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Starting...
                </>
              ) : isAnyPipelineProcessing() ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <PlayCircle className="h-4 w-4 mr-2" />
                  Process All
                </>
              )}
            </Button>
          )}
        </div>

        <div className="grid gap-3">
          {Object.values(DocumentType).map((type) => {
            const Icon = iconMap[type];
            const files = documents[type] || [];
            const hasFiles = files.length > 0;
            const isExpanded = expandedTypes.has(type);

            return (
              <div
                key={type}
                className={cn(
                  'bg-white border rounded-lg transition-all',
                  hasFiles ? 'border-teal-200' : 'border-slate-200'
                )}
              >
                {/* Header */}
                <div
                  className={cn(
                    'flex items-center justify-between p-4',
                    hasFiles && 'cursor-pointer'
                  )}
                  onClick={() => hasFiles && toggleExpanded(type)}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        'p-2.5 rounded-lg',
                        hasFiles ? 'bg-teal-50' : 'bg-slate-100'
                      )}
                    >
                      <Icon
                        className={cn(
                          'h-5 w-5',
                          hasFiles ? 'text-teal-600' : 'text-slate-500'
                        )}
                      />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground">
                          {DOCUMENT_TYPE_LABELS[type]}
                        </span>
                        {hasFiles && (
                          <span className="inline-flex items-center gap-1 text-sm text-teal-700">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            {files.length}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {DOCUMENT_TYPE_DESCRIPTIONS[type]}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {hasFiles && (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={(e) => handleDelete(type, e)}
                          disabled={isDeleting}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        )}
                      </>
                    )}
                    <Button
                      variant={hasFiles ? 'outline' : 'default'}
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleUploadClick(type);
                      }}
                    >
                      <Upload className="h-4 w-4 mr-1" />
                      {hasFiles ? 'Add More' : 'Upload'}
                    </Button>
                  </div>
                </div>
                <input
                  type="file"
                  ref={(el) => (fileInputRefs.current[type] = el)}
                  className="hidden"
                  accept=".pdf,.jpg,.jpeg,.png"
                  multiple
                  onChange={(e) => handleFileSelect(type, e.target.files)}
                />

                {/* Expanded file list */}
                {hasFiles && isExpanded && (
                  <div className="px-4 pb-4 pt-0">
                    <div className="space-y-2 pl-12 border-t border-slate-100 pt-3">
                      {files.map((file: FileEntry) => (
                        <FilePreview key={file.id} file={file} />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Upload Dialog */}
      <Dialog open={isUploadDialogOpen} onOpenChange={handleDialogClose}>
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
              caseId={caseData.id}
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
