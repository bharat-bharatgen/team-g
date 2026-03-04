import { useState } from 'react';
import { X, FileText, Image as ImageIcon, Download, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { formatFileSize, isPDF, isImage } from '@/utils/formatters';
import { cn } from '@/lib/utils';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface FilePreviewProps {
  file: {
    name?: string;
    file_name?: string;
    size?: number;
    type?: string;
    content_type?: string;
    url?: string;
  };
  onRemove?: () => void;
  showPreview?: boolean;
}

export const FilePreview = ({ file, onRemove, showPreview = true }: FilePreviewProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  
  // Handle both formats: local files (type/name) and backend files (content_type/file_name)
  const contentType = file.content_type || file.type || '';
  const fileName = file.file_name || file.name || 'Unknown file';
  const isPdf = isPDF(contentType);
  const isImg = isImage(contentType);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNumber(1);
  };

  return (
    <>
      <div className="flex items-center gap-3 p-3 bg-secondary/30 rounded-lg border">
        <div className={cn('p-2 rounded', isPdf ? 'bg-red-100' : 'bg-blue-100')}>
          {isPdf ? (
            <FileText className="h-4 w-4 text-red-600" />
          ) : (
            <ImageIcon className="h-4 w-4 text-blue-600" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{fileName}</p>
          {file.size && (
            <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
          )}
        </div>
        <div className="flex gap-1">
          {showPreview && file.url && (isPdf || isImg) && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsOpen(true)}
              className="h-8 w-8"
              title="Preview"
            >
              <Eye className="h-4 w-4" />
            </Button>
          )}
          {file.url && (
            <Button
              variant="ghost"
              size="icon"
              asChild
              className="h-8 w-8"
              title="Download"
            >
              <a href={file.url} download={fileName} target="_blank" rel="noopener noreferrer">
                <Download className="h-4 w-4" />
              </a>
            </Button>
          )}
          {onRemove && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onRemove}
              className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50"
              title="Remove"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {file.url && (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogContent className="max-w-5xl max-h-[90vh] overflow-auto">
            <DialogHeader>
              <DialogTitle>{fileName}</DialogTitle>
            </DialogHeader>
            <div className="mt-4">
              {isImg ? (
                <img
                  src={file.url}
                  alt={fileName}
                  className="w-full h-auto rounded-lg"
                />
              ) : isPdf ? (
                <div className="flex flex-col items-center gap-4">
                  <Document
                    file={file.url}
                    onLoadSuccess={onDocumentLoadSuccess}
                    loading={
                      <div className="flex items-center justify-center p-8">
                        <div className="text-sm text-muted-foreground">Loading PDF...</div>
                      </div>
                    }
                    error={
                      <div className="flex items-center justify-center p-8">
                        <div className="text-sm text-red-600">Failed to load PDF. Try downloading instead.</div>
                      </div>
                    }
                  >
                    <Page
                      pageNumber={pageNumber}
                      width={Math.min(window.innerWidth * 0.8, 800)}
                      renderTextLayer={true}
                      renderAnnotationLayer={true}
                    />
                  </Document>
                  {numPages && numPages > 1 && (
                    <div className="flex items-center gap-4 bg-slate-100 px-4 py-2 rounded-lg">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPageNumber(page => Math.max(1, page - 1))}
                        disabled={pageNumber <= 1}
                      >
                        Previous
                      </Button>
                      <span className="text-sm">
                        Page {pageNumber} of {numPages}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPageNumber(page => Math.min(numPages, page + 1))}
                        disabled={pageNumber >= numPages}
                      >
                        Next
                      </Button>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
};
