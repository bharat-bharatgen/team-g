import { CaseStatus } from '@/types/case.types';
import { CASE_STATUS_LABELS } from '@/utils/constants';
import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: CaseStatus;
}

export const StatusBadge = ({ status }: StatusBadgeProps) => {
  const statusConfig = {
    [CaseStatus.CREATED]: {
      dotColor: 'bg-slate-400',
      textColor: 'text-slate-600',
    },
    [CaseStatus.PROCESSING]: {
      dotColor: 'bg-amber-500',
      textColor: 'text-amber-700',
    },
    [CaseStatus.COMPLETED]: {
      dotColor: 'bg-teal-500',
      textColor: 'text-teal-700',
    },
    [CaseStatus.FAILED]: {
      dotColor: 'bg-red-500',
      textColor: 'text-red-700',
    },
  };

  const label = CASE_STATUS_LABELS[status];
  if (!label) {
    return null;
  }

  const config = statusConfig[status];

  return (
    <span className={cn('inline-flex items-center gap-1.5 text-sm', config.textColor)}>
      <span className={cn('w-2 h-2 rounded-full', config.dotColor)} />
      {label}
    </span>
  );
};
