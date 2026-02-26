import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { StatusBadge } from './StatusBadge';
import { Case } from '@/types/case.types';
import { formatDateTime } from '@/utils/formatters';
import { deriveOverallStatus } from '@/utils/caseHelpers';
import { caseService } from '@/services/case.service';
import { useCaseStore } from '@/store/caseStore';
import { Calendar, FileText, ChevronRight, X } from 'lucide-react';

interface CaseCardProps {
  case: Case;
}

export const CaseCard = ({ case: caseData }: CaseCardProps) => {
  const navigate = useNavigate();
  const removeCase = useCaseStore((state) => state.removeCase);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const documentCount = Object.values(caseData.documents).reduce(
    (acc, files) => acc + (files?.length || 0),
    0
  );

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await caseService.deleteCase(caseData.id);
      removeCase(caseData.id);
      setShowDeleteDialog(false);
    } catch (error) {
      console.error('Failed to delete case:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <Card className="group relative hover:shadow-soft hover:border-primary/20 transition-all cursor-pointer" onClick={() => navigate(`/cases/${caseData.id}`)}>
        {/* Delete button - appears on hover */}
        <button
          className="absolute top-2 right-2 p-1 rounded-full bg-muted/80 text-muted-foreground hover:bg-destructive hover:text-destructive-foreground opacity-0 group-hover:opacity-100 transition-opacity z-10"
          onClick={(e) => {
            e.stopPropagation();
            setShowDeleteDialog(true);
          }}
        >
          <X className="h-4 w-4" />
        </button>

        <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-lg">{caseData.case_name}</h3>
              <StatusBadge status={deriveOverallStatus(caseData.pipeline_status)} />
            </div>
            <div className="flex flex-col gap-1 text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                <span>{formatDateTime(caseData.created_at)}</span>
              </div>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/cases/${caseData.id}`);
            }}
          >
            <ChevronRight className="h-5 w-5" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              {documentCount} document{documentCount !== 1 ? 's' : ''} uploaded
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Delete confirmation dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Case</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{caseData.case_name}"? This will remove the case from your dashboard.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)} disabled={isDeleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};
