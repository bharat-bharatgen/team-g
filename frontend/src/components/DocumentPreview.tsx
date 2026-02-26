import { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import { Button } from '@/components/ui/button';
import { FileText, Download, Loader2, ExternalLink } from 'lucide-react';
import { isPdfUrl } from '@/utils/formatters';

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface DocumentPreviewProps {
  url: string | null | undefined;
  alt: string;
  downloadFileName: string;
  minHeight?: string;
  className?: string;
}

export const DocumentPreview = ({
  url,
  alt,
  downloadFileName,
  minHeight = '400px',
  className = '',
}: DocumentPreviewProps) => {
  const [pdfNumPages, setPdfNumPages] = useState(1);
  const isPdf = url ? isPdfUrl(url) : false;

  if (!url) {
    return (
      <div className={`flex flex-col items-center justify-center text-muted-foreground ${className}`} style={{ minHeight }}>
        <FileText className="h-12 w-12 mx-auto mb-2" />
        <p>Not available</p>
      </div>
    );
  }

  const actionButtons = (
    <div className="p-4 border-t flex gap-2">
      <Button variant="outline" size="sm" className="flex-1" onClick={() => window.open(url, '_blank')}>
        <FileText className="h-4 w-4 mr-2" />
        Open
      </Button>
      <Button
        variant="outline"
        size="sm"
        className="flex-1"
        onClick={() => {
          const a = document.createElement('a');
          a.href = url;
          a.download = downloadFileName;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }}
      >
        <Download className="h-4 w-4 mr-2" />
        Download
      </Button>
    </div>
  );

  if (isPdf) {
    return (
      <>
        <div
          className={`overflow-auto bg-gray-50 flex items-center justify-center ${className}`}
          style={{ minHeight }}
        >
          <Document
            file={url}
            onLoadSuccess={({ numPages }) => setPdfNumPages(numPages)}
            loading={
              <div className="flex items-center justify-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">Loading PDF...</span>
              </div>
            }
            error={
              <div className="flex flex-col items-center justify-center p-8 text-center space-y-4">
                <FileText className="h-12 w-12 text-muted-foreground" />
                <p className="text-sm text-red-600">Failed to load PDF</p>
                <div className="flex gap-2">
                  <Button variant="default" size="sm" onClick={() => window.open(url, '_blank')}>
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Open in New Tab
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = downloadFileName;
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                    }}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download
                  </Button>
                </div>
              </div>
            }
          >
            <div className="flex flex-col items-center gap-4 p-4">
              {Array.from({ length: pdfNumPages }, (_, i) => (
                <div key={i} className="shadow-lg">
                  <Page
                    pageNumber={i + 1}
                    width={400}
                    renderTextLayer={true}
                    renderAnnotationLayer={true}
                  />
                </div>
              ))}
            </div>
          </Document>
        </div>
        {actionButtons}
      </>
    );
  }

  return (
    <>
      <div className={`relative bg-gray-50 flex items-center justify-center ${className}`} style={{ minHeight }}>
        <img
          src={url}
          alt={alt}
          className="max-w-full max-h-full object-contain"
          style={{ maxHeight: minHeight }}
          onError={(e) => {
            e.currentTarget.src = '';
            e.currentTarget.style.display = 'none';
          }}
        />
      </div>
      {actionButtons}
    </>
  );
};
