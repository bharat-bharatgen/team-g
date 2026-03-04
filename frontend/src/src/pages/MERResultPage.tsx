import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { documentService } from '@/services/document.service';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loading } from '@/components/ui/loading';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, FileText, Download, AlertCircle, ExternalLink, Edit, Save, X, Loader2, CheckCircle2, PanelLeftClose, PanelLeft } from 'lucide-react';
import { API_BASE_URL, STORAGE_KEYS } from '@/utils/constants';
import api, { uploadMERExcel } from '@/services/api';
import * as XLSX from 'xlsx';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface MERField {
  id: string;
  key: string;
  field_name?: string;
  answer: string | null;
  details: string | null;
  source: string;
  confidence?: number;
  page?: number;
  page_number?: number;
  section?: string;
}

interface MERResultResponse {
  id: string;
  case_id: string;
  version: number;
  source: string;
  classification: any;
  pages: any;
  fields: MERField[];
  created_at: string;
}

export const MERResultPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [merData, setMerData] = useState<MERResultResponse | null>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // URL params for citation navigation
  const pageParam = searchParams.get('page');  // MER page number (1-4)
  const fieldParam = searchParams.get('field');  // field key to highlight
  const fromPage = searchParams.get('from');  // 'risk' if navigated from risk analysis
  
  // Ref for scrolling to highlighted row
  const highlightedRowRef = useRef<HTMLTableRowElement>(null);
  
  // PDF viewer state
  const [pdfNumPages, setPdfNumPages] = useState<number>(1);
  const pdfContainerRef = useRef<HTMLDivElement>(null);
  const pdfPageRefs = useRef<(HTMLDivElement | null)[]>([]);
  
  // Inline editing state
  const [editMode, setEditMode] = useState(false);
  const [editedFields, setEditedFields] = useState<Record<string, { answer?: string; details?: string }>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  
  // Panel visibility state
  const [showDocPanel, setShowDocPanel] = useState(true);

  useEffect(() => {
    fetchData();
  }, [id]);

  // Scroll to PDF page when navigated with page param
  useEffect(() => {
    if (pageParam && pdfNumPages > 0) {
      const pageNum = parseInt(pageParam);
      console.log(`[MER PDF Scroll] pageParam=${pageParam}, pdfNumPages=${pdfNumPages}, target page=${pageNum}`);
      if (pageNum >= 1 && pageNum <= pdfNumPages) {
        // Retry mechanism - pages may take time to render
        const scrollToPage = (attempt: number) => {
          const pageRef = pdfPageRefs.current[pageNum - 1];
          const container = pdfContainerRef.current;
          console.log(`[MER PDF Scroll] attempt ${attempt}: pageRef exists: ${!!pageRef}, container exists: ${!!container}`);
          
          if (pageRef && container) {
            const containerRect = container.getBoundingClientRect();
            const pageRect = pageRef.getBoundingClientRect();
            const scrollTop = container.scrollTop + (pageRect.top - containerRect.top) - 16;
            console.log(`[MER PDF Scroll] scrolling to scrollTop=${scrollTop}`);
            container.scrollTo({ top: scrollTop, behavior: 'smooth' });
          } else if (attempt < 5) {
            // Retry after delay
            setTimeout(() => scrollToPage(attempt + 1), 500);
          }
        };
        
        // Start after initial delay
        setTimeout(() => scrollToPage(1), 500);
      }
    }
  }, [pageParam, pdfNumPages]);

  // Scroll to highlighted row
  useEffect(() => {
    if (highlightedRowRef.current && fieldParam) {
      setTimeout(() => {
        highlightedRowRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      }, 300);
    }
  }, [merData, fieldParam]);

  const fetchData = async () => {
    if (!id) return;

    setIsLoading(true);
    setError(null);

    try {
      const [resultResponse, docsData] = await Promise.all([
        api.get(`/cases/${id}/mer/result`),
        documentService.getDocuments(id),
      ]);

      setMerData(resultResponse.data);
      
      const merDocs = docsData.documents.mer || [];
      console.log('MER Documents:', merDocs); // Debug log
      setDocuments(merDocs);
      
      if (merDocs.length > 0) {
        console.log('Selected document URL:', merDocs[0].url); // Debug log
        console.log('Content type:', merDocs[0].content_type); // Debug log
        setSelectedDocument(merDocs[0].url);
      }
    } catch (err: any) {
      console.error('Error loading MER data:', err);
      setError(err.response?.data?.detail || 'Failed to load MER results');
    } finally {
      setIsLoading(false);
    }
  };

  const isPDF = (doc: any) => {
    if (!doc) return false;
    // Check content_type first, then fallback to URL
    if (doc.content_type) {
      return doc.content_type === 'application/pdf';
    }
    // Check URL for .pdf (before query params)
    const urlWithoutQuery = doc.url ? doc.url.split('?')[0] : '';
    return urlWithoutQuery.toLowerCase().endsWith('.pdf');
  };

  const getSelectedDocData = () => {
    return documents.find(doc => doc.url === selectedDocument);
  };

  const handleDownloadExcel = async () => {
    if (!id) return;

    try {
      const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      const url = `${API_BASE_URL}/cases/${id}/mer/export-excel`;
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `MER_${id}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  // Inline editing handlers
  const handleFieldEdit = (fieldId: string, key: 'answer' | 'details', newValue: string) => {
    setEditedFields(prev => ({
      ...prev,
      [fieldId]: {
        ...prev[fieldId],
        [key]: newValue
      }
    }));
  };

  const isFieldEdited = (fieldId: string) => {
    return editedFields.hasOwnProperty(fieldId);
  };

  const getFieldAnswer = (field: MERField) => {
    return editedFields[field.id]?.answer !== undefined 
      ? editedFields[field.id].answer 
      : (field.answer || '');
  };

  const getFieldDetails = (field: MERField) => {
    return editedFields[field.id]?.details !== undefined 
      ? editedFields[field.id].details 
      : (field.details || '');
  };

  // Questions where "Yes" is the IDEAL answer (not a flag)
  const positiveQuestions = new Set([
    "5) Does applicant appear medically fit?",
    "7) Is your vision and hearing normal?",
  ]);

  const isNonIdealAnswer = (field: MERField) => {
    const answer = (getFieldAnswer(field) || '').toLowerCase().trim();
    const fieldKey = field.key || field.field_name || '';
    
    // "Yes" on negative questions = flag
    if (answer === 'yes' && !positiveQuestions.has(fieldKey)) {
      return true;
    }
    // "No" on positive questions = flag
    if (answer === 'no' && positiveQuestions.has(fieldKey)) {
      return true;
    }
    return false;
  };

  const generateExcelFromEdits = (): Blob => {
    if (!merData) throw new Error('No data available');

    // Create workbook
    const wb = XLSX.utils.book_new();
    
    // Prepare data rows
    const data: any[] = [];
    
    // Header row (matches backend excel_export.py columns)
    data.push(['__field_id__', 'Page', 'Section', 'Field', 'Answer', 'Details', 'Confidence', 'Source']);
    
    // Metadata row
    data.push(['__meta__', `case_id=${id}`, `version=${merData.version}`, `fields_count=${merData.fields.length}`]);
    
    // Field rows with edited values
    merData.fields.forEach(field => {
      const answer = editedFields[field.id]?.answer !== undefined ? editedFields[field.id].answer : field.answer;
      const details = editedFields[field.id]?.details !== undefined ? editedFields[field.id].details : field.details;
      data.push([
        field.id,
        field.page_number || field.page || 0,
        field.section || '',
        field.key || field.field_name || '',
        answer || '',
        details || '',
        field.confidence || 0,
        field.source || 'llm'
      ]);
    });

    // Create worksheet
    const ws = XLSX.utils.aoa_to_sheet(data);
    
    // Hide column A (field IDs)
    ws['!cols'] = [{ hidden: true }];
    
    // Add worksheet to workbook
    XLSX.utils.book_append_sheet(wb, ws, 'MER Data');
    
    // Generate Excel file
    const excelBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    return new Blob([excelBuffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  };

  const handleSaveChanges = async () => {
    if (!id || Object.keys(editedFields).length === 0) return;

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    try {
      // Generate Excel file with edits
      const excelBlob = generateExcelFromEdits();
      const excelFile = new File([excelBlob], `MER_${id}_edited.xlsx`, {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });

      // Upload using existing Excel import endpoint
      const response = await uploadMERExcel(id, excelFile);
      
      setSaveSuccess(
        `Successfully updated! Version ${response.version} created with ${response.changed_fields} field(s) changed.`
      );
      
      // Clear edits and exit edit mode
      setEditedFields({});
      setEditMode(false);
      
      // Refresh data
      await fetchData();
    } catch (err: any) {
      console.error('Save failed:', err);
      setSaveError(err.message || 'Failed to save changes');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditedFields({});
    setEditMode(false);
    setSaveError(null);
  };

  const getConfidenceColor = (confidence?: number) => {
    if (!confidence) return '';
    if (confidence >= 0.9) return 'bg-green-50';
    if (confidence >= 0.8) return 'bg-yellow-50';
    return 'bg-red-50';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loading text="Loading MER results..." />
      </div>
    );
  }

  if (error || !merData) {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error || 'MER results not found'}</AlertDescription>
        </Alert>
        <div className="flex gap-3 mt-4">
          <Button variant="outline" onClick={() => navigate(`/cases/${id}`)}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Case
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      {/* Header - sticky */}
      <div className="flex-shrink-0 pb-2 bg-background">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {fromPage === 'risk' && (
              <Button variant="outline" size="sm" onClick={() => navigate(`/cases/${id}/risk-analysis`)}>
                <ArrowLeft className="h-4 w-4 mr-1" />
                Risk
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={() => navigate(`/cases/${id}`)}>
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back
            </Button>
            <span className="text-muted-foreground">|</span>
            <h1 className="text-lg font-semibold">MER Results</h1>
            <Badge variant="outline" className="text-xs">{merData.fields?.length || 0} fields</Badge>
            <Badge variant="secondary" className="text-xs">v{merData.version}</Badge>
            {/* Inline alerts */}
            {saveSuccess && (
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 text-xs">
                <CheckCircle2 className="h-3 w-3 mr-1" /> Saved
              </Badge>
            )}
            {saveError && (
              <Badge variant="destructive" className="text-xs">
                <AlertCircle className="h-3 w-3 mr-1" /> Error
              </Badge>
            )}
            {editMode && (
              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">
                Editing
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {editMode ? (
              <>
                {Object.keys(editedFields).length > 0 && (
                  <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">
                    {Object.keys(editedFields).length} edited
                  </Badge>
                )}
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                >
                  <X className="h-4 w-4" />
                </Button>
                <Button 
                  variant="default" 
                  size="sm" 
                  onClick={handleSaveChanges}
                  disabled={isSaving || Object.keys(editedFields).length === 0}
                >
                  {isSaving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline" size="sm" onClick={handleDownloadExcel}>
                  <Download className="h-4 w-4" />
                </Button>
                <Button 
                  variant="default" 
                  size="sm" 
                  onClick={() => setEditMode(true)}
                >
                  <Edit className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Debug: Show if no fields */}
      {(!merData.fields || merData.fields.length === 0) && (
        <Alert className="flex-shrink-0 mb-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No extracted fields found. The extraction may still be processing or failed.
          </AlertDescription>
        </Alert>
      )}

      {/* Split View - fills remaining space */}
      <div className={`flex-1 min-h-0 grid gap-3 ${showDocPanel ? 'grid-cols-2' : 'grid-cols-1'}`}>
        {/* Left: Documents Viewer (collapsible) */}
        {showDocPanel && (
          <Card className="overflow-hidden flex flex-col">
            <CardHeader className="py-2 px-3 flex-shrink-0">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Documents ({documents.length})
                </CardTitle>
                <div className="flex items-center gap-1">
                  {/* Document Tabs */}
                  {documents.length > 1 && (
                    <>
                      {documents.map((doc, idx) => (
                        <Button
                          key={doc.id}
                          variant={selectedDocument === doc.url ? 'default' : 'outline'}
                          size="sm"
                          className="h-6 px-2 text-xs"
                          onClick={() => setSelectedDocument(doc.url)}
                        >
                          {idx + 1}
                        </Button>
                      ))}
                    </>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 ml-1"
                    onClick={() => setShowDocPanel(false)}
                    title="Hide documents panel"
                  >
                    <PanelLeftClose className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0 flex-1 overflow-hidden">
            
            {/* Document Viewer */}
            <div className="h-full">
              {selectedDocument && (() => {
                const docData = getSelectedDocData();
                const isPDFFile = isPDF(docData);
                
                return (
                  <div className="w-full h-full">
                    {isPDFFile ? (
                      <div className="w-full h-full flex flex-col">
                        {/* PDF Viewer with react-pdf - all pages scrollable */}
                        <div 
                          ref={pdfContainerRef}
                          className="flex-1 overflow-auto bg-gray-100 p-4"
                        >
                          <Document
                            file={selectedDocument}
                            onLoadSuccess={({ numPages }) => {
                              setPdfNumPages(numPages);
                              pdfPageRefs.current = new Array(numPages).fill(null);
                            }}
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
                                  <Button
                                    variant="default"
                                    size="sm"
                                    onClick={() => window.open(selectedDocument, '_blank')}
                                  >
                                    <ExternalLink className="h-4 w-4 mr-2" />
                                    Open in New Tab
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                      const a = document.createElement('a');
                                      a.href = selectedDocument;
                                      a.download = docData?.file_name || 'document.pdf';
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
                            <div className="flex flex-col items-center gap-4">
                              {Array.from({ length: pdfNumPages }, (_, i) => (
                                <div
                                  key={i}
                                  ref={(el) => { pdfPageRefs.current[i] = el; }}
                                  className="shadow-lg"
                                >
                                  <Page
                                    pageNumber={i + 1}
                                    width={480}
                                    renderTextLayer={true}
                                    renderAnnotationLayer={true}
                                  />
                                </div>
                              ))}
                            </div>
                          </Document>
                        </div>
                        
                        {/* Page indicator */}
                        {pdfNumPages > 1 && (
                          <div className="flex items-center justify-center py-2 bg-slate-100 border-t text-sm text-gray-600">
                            {pdfNumPages} pages — scroll to view
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center justify-center p-4 h-full bg-gray-50">
                        <img
                          src={selectedDocument}
                          alt="MER Document"
                          className="max-w-full max-h-full object-contain rounded shadow-lg"
                          style={{ maxHeight: '700px' }}
                          onError={(e) => {
                            console.error('Image failed to load:', selectedDocument);
                            const target = e.currentTarget;
                            target.style.display = 'none';
                            const parent = target.parentElement;
                            if (parent) {
                              parent.innerHTML = `
                                <div class="text-center text-muted-foreground">
                                  <p>Failed to load image</p>
                                  <p class="text-sm mt-2">The document may have expired or is unavailable.</p>
                                </div>
                              `;
                            }
                          }}
                          onLoad={() => console.log('Image loaded successfully')}
                        />
                      </div>
                    )}
                  </div>
                );
              })()}
              {!selectedDocument && (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  No documents available
                </div>
              )}
            </div>
          </CardContent>
        </Card>
        )}

        {/* Right: Extracted Data */}
        <Card className="overflow-hidden flex flex-col">
          <CardHeader className="py-2 px-3 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {!showDocPanel && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={() => setShowDocPanel(true)}
                    title="Show documents panel"
                  >
                    <PanelLeft className="h-4 w-4" />
                  </Button>
                )}
                <CardTitle className="text-sm font-medium">Extracted Data</CardTitle>
              </div>
              <div className="flex items-center gap-1" title="Legend: Green=High conf, Yellow=Medium conf, Red=Flag, Purple=User saved, Blue=Editing">
                <div className="w-2.5 h-2.5 rounded-sm bg-green-100 border border-green-300" title="High confidence (≥90%)"></div>
                <div className="w-2.5 h-2.5 rounded-sm bg-yellow-100 border border-yellow-300" title="Medium confidence (80-90%)"></div>
                <div className="w-2.5 h-2.5 rounded-sm bg-red-100 border border-red-300" title="Non-ideal answer (flag)"></div>
                <div className="w-2.5 h-2.5 rounded-sm bg-purple-100 border border-purple-300" title="User saved"></div>
                {editMode && <div className="w-2.5 h-2.5 rounded-sm bg-blue-100 border border-blue-300" title="Currently editing"></div>}
                <span className="text-xs text-muted-foreground ml-1 cursor-help" title="Hover over colors for details">?</span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0 flex-1 overflow-auto">
              <table className="w-full">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
                      Field
                    </th>
                    <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
                      Answer
                    </th>
                    <th className="px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b">
                      Details
                    </th>
                    <th className="px-2 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider border-b w-12">
                      Pg
                    </th>
                    <th className="px-2 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider border-b w-14">
                      Conf
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {merData.fields && merData.fields.length > 0 ? (
                    merData.fields.map((field, idx) => {
                      const fieldKey = field.key || field.field_name || '';
                      const isHighlighted = fieldParam && fieldKey.toLowerCase().includes(fieldParam.toLowerCase());
                      // Get MER form page, then look up actual PDF page from classification mapping
                      const merFormPage = field.page_number || field.page;
                      const pdfPage = merFormPage 
                        ? merData.classification?.mapping_summary?.[String(merFormPage)]?.source_page || merFormPage
                        : undefined;
                      const isFlag = isNonIdealAnswer(field);
                      
                      return (
                      <tr 
                        key={field.id || idx}
                        ref={isHighlighted ? highlightedRowRef : null}
                        className={`${
                          isHighlighted ? 'bg-yellow-100 ring-2 ring-yellow-400' :
                          isFieldEdited(field.id) ? 'bg-blue-50' :
                          field.source === 'user' ? 'bg-purple-50' :
                          isFlag ? 'bg-red-50' : getConfidenceColor(field.confidence)
                        } hover:bg-gray-100 transition-colors ${pdfPage ? 'cursor-pointer' : ''}`}
                        onClick={() => {
                          if (pdfPage && pdfPage >= 1 && pdfPage <= pdfNumPages) {
                            const pageRef = pdfPageRefs.current[pdfPage - 1];
                            const container = pdfContainerRef.current;
                            if (pageRef && container) {
                              const containerRect = container.getBoundingClientRect();
                              const pageRect = pageRef.getBoundingClientRect();
                              const scrollTop = container.scrollTop + (pageRect.top - containerRect.top) - 16;
                              container.scrollTo({ top: scrollTop, behavior: 'smooth' });
                            }
                          }
                        }}
                      >
                        <td className="px-2 py-1.5 text-sm font-medium text-gray-900">
                          {field.key || field.field_name || 'N/A'}
                        </td>
                        <td className="px-2 py-1.5 text-sm text-gray-900">
                          {editMode ? (
                            <input
                              type="text"
                              value={getFieldAnswer(field)}
                              onChange={(e) => handleFieldEdit(field.id, 'answer', e.target.value)}
                              className={`
                                w-full px-2 py-1 border rounded text-sm
                                ${isFieldEdited(field.id) 
                                  ? 'border-blue-500 bg-white ring-2 ring-blue-200' 
                                  : 'border-gray-300 bg-white'}
                                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                                transition-all
                              `}
                              placeholder="-"
                            />
                          ) : (
                            <span className={`font-semibold ${isFlag ? 'text-red-600' : ''}`}>
                              {field.answer || '-'}
                            </span>
                          )}
                        </td>
                        <td className="px-2 py-1.5 text-sm text-gray-900">
                          {editMode ? (
                            <input
                              type="text"
                              value={getFieldDetails(field)}
                              onChange={(e) => handleFieldEdit(field.id, 'details', e.target.value)}
                              className={`
                                w-full px-2 py-1 border rounded text-sm
                                ${isFieldEdited(field.id) 
                                  ? 'border-blue-500 bg-white ring-2 ring-blue-200' 
                                  : 'border-gray-300 bg-white'}
                                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                                transition-all
                              `}
                              placeholder="-"
                            />
                          ) : (
                            <span>
                              {field.details || '-'}
                            </span>
                          )}
                        </td>
                        <td className="px-2 py-1.5 text-xs text-gray-500 text-center">
                          {field.page || field.page_number || '-'}
                        </td>
                        <td className="px-2 py-1.5 text-xs text-center">
                          {field.source === 'user' ? (
                            <Badge variant="success" className="text-xs px-1">U</Badge>
                          ) : field.confidence ? (
                            <span className={`
                              ${field.confidence >= 0.9 ? 'text-green-600' : 
                                field.confidence >= 0.8 ? 'text-yellow-600' : 
                                'text-red-600'}
                              font-medium
                            `}>
                              {(field.confidence * 100).toFixed(0)}%
                            </span>
                          ) : '-'}
                        </td>
                      </tr>
                    );})
                  ) : (
                    <tr>
                      <td colSpan={5} className="px-2 py-8 text-center text-muted-foreground">
                        No data available
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
