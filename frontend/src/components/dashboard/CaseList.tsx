import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CaseDashboardSummary, PipelineStatus } from '@/types/case.types';
import { formatDate } from '@/utils/formatters';
import { ChevronRight, AlertTriangle, Loader2, CheckCircle2, XCircle, HelpCircle, Minus, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { caseService } from '@/services/case.service';

interface CaseListProps {
  cases: CaseDashboardSummary[];
  onCaseDeleted?: (caseId: string) => void;
}

// Helper to check if a pipeline is processing
const isProcessing = (status?: string) => status === PipelineStatus.PROCESSING;

// Risk level indicator
const RiskIndicator = ({ level, isProcessing: processing }: { level?: string; isProcessing?: boolean }) => {
  if (processing) return <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-400" />;
  if (!level) return <span className="text-slate-400">—</span>;

  const colors = {
    High: 'text-red-600 bg-red-50',
    Intermediate: 'text-amber-600 bg-amber-50',
    Low: 'text-green-600 bg-green-50',
  };

  return (
    <span className={cn('px-2 py-0.5 rounded text-xs font-medium', colors[level as keyof typeof colors] || 'text-slate-500')}>
      {level === 'Intermediate' ? 'Med' : level}
    </span>
  );
};

// Tests indicator (X/Y)
const TestsIndicator = ({ required, found, isProcessing: processing }: { required?: number; found?: number; isProcessing?: boolean }) => {
  if (processing) return <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-400" />;
  if (required === undefined || found === undefined) return <span className="text-slate-400">—</span>;

  const isMissing = found < required;
  return (
    <span className={cn('text-sm font-medium', isMissing ? 'text-red-600' : 'text-green-600')}>
      {found}/{required}
    </span>
  );
};

// MER confidence indicator
const MERIndicator = ({ pct, isProcessing: processing }: { pct?: number; isProcessing?: boolean }) => {
  if (processing) return <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-400" />;
  if (pct === undefined) return <span className="text-slate-400">—</span>;

  const isLow = pct < 90;
  return (
    <span className={cn('text-sm font-medium', isLow ? 'text-amber-600' : 'text-green-600')}>
      {Math.round(pct)}%
    </span>
  );
};

// Face match indicator
const FaceIndicator = ({ decision, isProcessing: processing }: { decision?: string; isProcessing?: boolean }) => {
  if (processing) return <Loader2 className="h-4 w-4 animate-spin text-slate-400" />;
  if (!decision) return <Minus className="h-4 w-4 text-slate-300" />;

  if (decision === 'match') {
    return (
      <div className="p-1 rounded-full bg-green-50">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
      </div>
    );
  }
  if (decision === 'no_match') {
    return (
      <div className="p-1 rounded-full bg-red-50">
        <XCircle className="h-4 w-4 text-red-600" />
      </div>
    );
  }
  return (
    <div className="p-1 rounded-full bg-amber-50">
      <HelpCircle className="h-4 w-4 text-amber-600" />
    </div>
  );
};

// Location check indicator
const GeoIndicator = ({ decision, isProcessing: processing }: { decision?: string; isProcessing?: boolean }) => {
  if (processing) return <Loader2 className="h-4 w-4 animate-spin text-slate-400" />;
  if (!decision) return <Minus className="h-4 w-4 text-slate-300" />;

  if (decision === 'pass') {
    return (
      <div className="p-1 rounded-full bg-green-50">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
      </div>
    );
  }
  if (decision === 'fail') {
    return (
      <div className="p-1 rounded-full bg-red-50">
        <XCircle className="h-4 w-4 text-red-600" />
      </div>
    );
  }
  return (
    <div className="p-1 rounded-full bg-amber-50">
      <HelpCircle className="h-4 w-4 text-amber-600" />
    </div>
  );
};

// Status badge
const StatusBadge = ({ decision, hasProcessing }: { decision?: string; hasProcessing: boolean }) => {
  if (hasProcessing) {
    return (
      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-600 flex items-center gap-1.5">
        <Loader2 className="h-3 w-3 animate-spin" />
        Running
      </span>
    );
  }

  if (!decision) {
    return (
      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
        Pending
      </span>
    );
  }

  const badges = {
    approved: 'bg-green-50 text-green-700',
    review: 'bg-amber-50 text-amber-700',
    declined: 'bg-red-50 text-red-700',
  };

  const labels = {
    approved: 'Approved',
    review: 'Review',
    declined: 'Declined',
  };

  return (
    <span className={cn('px-2.5 py-1 rounded-full text-xs font-medium capitalize', badges[decision as keyof typeof badges])}>
      {labels[decision as keyof typeof labels] || decision}
    </span>
  );
};

export const CaseList = ({ cases, onCaseDeleted }: CaseListProps) => {
  const navigate = useNavigate();
  const [deleteTarget, setDeleteTarget] = useState<CaseDashboardSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await caseService.deleteCase(deleteTarget.id);
      onCaseDeleted?.(deleteTarget.id);
      setDeleteTarget(null);
    } catch (error) {
      console.error('Failed to delete case:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  if (cases.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No cases found</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header row */}
      <div className="hidden md:grid grid-cols-[1fr,28px,90px,70px,70px,60px,60px,60px,100px,24px] gap-4 px-5 py-2 text-xs font-medium text-slate-500 uppercase tracking-wider">
        <div>Case</div>
        <div></div>
        <div className="text-center">Date</div>
        <div className="text-center">Risk</div>
        <div className="text-center">Tests</div>
        <div className="text-center">MER</div>
        <div className="text-center">Face</div>
        <div className="text-center">Geo</div>
        <div className="text-center">Status</div>
        <div></div>
      </div>

      {/* Case rows */}
      <div className="grid gap-2.5">
        {cases.map((caseData) => {
          const ps = caseData.pipeline_status;
          const hasAnyProcessing =
            isProcessing(ps.mer) ||
            isProcessing(ps.pathology) ||
            isProcessing(ps.risk) ||
            isProcessing(ps.face_match) ||
            isProcessing(ps.location_check) ||
            isProcessing(ps.test_verification);

          return (
            <div
              key={caseData.id}
              className="group relative bg-white border border-slate-200 rounded-lg px-5 py-3.5 cursor-pointer transition-all hover:shadow-soft hover:border-slate-300"
              onClick={() => navigate(`/cases/${caseData.id}`)}
            >
              {/* Delete button - top right on hover, half outside card */}
              <button
                className="absolute -top-2 -right-2 p-1 rounded-full bg-slate-200 text-slate-500 hover:bg-red-500 hover:text-white opacity-0 group-hover:opacity-100 transition-all z-10 shadow-sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setDeleteTarget(caseData);
                }}
              >
                <X className="h-3.5 w-3.5" />
              </button>

              {/* Desktop layout */}
              <div className="hidden md:grid grid-cols-[1fr,28px,90px,70px,70px,60px,60px,60px,100px,24px] gap-4 items-center">
                {/* Case name */}
                <div className="min-w-0">
                  <span className="font-medium text-foreground truncate block">
                    {caseData.case_name || 'Untitled Case'}
                  </span>
                </div>

                {/* Attention indicator */}
                <div className="flex justify-center">
                  {caseData.needs_attention && (
                    <AlertTriangle className="h-4 w-4 text-orange-500" />
                  )}
                </div>

                {/* Date */}
                <div className="text-sm text-slate-500 text-center">
                  {formatDate(caseData.created_at)}
                </div>

                {/* Risk */}
                <div className="flex justify-center">
                  <RiskIndicator level={caseData.risk_level} isProcessing={isProcessing(ps.risk)} />
                </div>

                {/* Tests */}
                <div className="flex justify-center">
                  <TestsIndicator
                    required={caseData.tests_required}
                    found={caseData.tests_found}
                    isProcessing={isProcessing(ps.test_verification)}
                  />
                </div>

                {/* MER */}
                <div className="flex justify-center">
                  <MERIndicator pct={caseData.mer_high_confidence_pct} isProcessing={isProcessing(ps.mer)} />
                </div>

                {/* Face */}
                <div className="flex justify-center">
                  <FaceIndicator decision={caseData.face_match_decision} isProcessing={isProcessing(ps.face_match)} />
                </div>

                {/* Geo */}
                <div className="flex justify-center">
                  <GeoIndicator decision={caseData.location_check_decision} isProcessing={isProcessing(ps.location_check)} />
                </div>

                {/* Status */}
                <div className="flex justify-center">
                  <StatusBadge decision={caseData.decision} hasProcessing={hasAnyProcessing} />
                </div>

                {/* Arrow */}
                <ChevronRight className="h-5 w-5 text-slate-400" />
              </div>

              {/* Mobile layout */}
              <div className="md:hidden space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {caseData.needs_attention && (
                      <AlertTriangle className="h-4 w-4 text-orange-500 shrink-0" />
                    )}
                    <span className="font-medium text-foreground truncate">
                      {caseData.case_name || 'Untitled Case'}
                    </span>
                  </div>
                  <ChevronRight className="h-5 w-5 text-slate-400 shrink-0" />
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-slate-500">{formatDate(caseData.created_at)}</span>
                  <RiskIndicator level={caseData.risk_level} isProcessing={isProcessing(ps.risk)} />
                  <StatusBadge decision={caseData.decision} hasProcessing={hasAnyProcessing} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Case</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deleteTarget?.case_name || 'Untitled Case'}"? This will remove the case from your dashboard.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={isDeleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
