import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { DocumentType } from '@/types/case.types';
import { DOCUMENT_TYPE_LABELS, DOCUMENT_TYPE_DESCRIPTIONS } from '@/utils/constants';
import { FileText, FlaskConical, Camera, CreditCard, CheckCircle2, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DocumentTypeCardProps {
  type: DocumentType;
  fileCount: number;
  isSelected?: boolean;
  onClick: () => void;
}

const iconMap = {
  [DocumentType.MER]: FileText,
  [DocumentType.PATHOLOGY]: FlaskConical,
  [DocumentType.PHOTO]: Camera,
  [DocumentType.ID_PROOF]: CreditCard,
};

export const DocumentTypeCard = ({
  type,
  fileCount,
  isSelected,
  onClick,
}: DocumentTypeCardProps) => {
  const Icon = iconMap[type];
  const hasFiles = fileCount > 0;

  return (
    <Card
      className={cn(
        'cursor-pointer transition-all group border-slate-200',
        'hover:shadow-soft hover:border-slate-300',
        isSelected && 'ring-2 ring-primary/60 border-primary/40 shadow-soft',
        hasFiles && !isSelected && 'border-teal-200'
      )}
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn(
              'p-2.5 rounded-lg transition-colors',
              hasFiles ? 'bg-teal-50' : 'bg-slate-100',
              isSelected && 'bg-primary/10'
            )}>
              <Icon className={cn(
                'h-5 w-5 transition-colors',
                hasFiles ? 'text-teal-600' : 'text-slate-500',
                isSelected && 'text-primary'
              )} />
            </div>
            <div>
              <CardTitle className="text-base font-medium">{DOCUMENT_TYPE_LABELS[type]}</CardTitle>
            </div>
          </div>
          {hasFiles ? (
            <div className="flex items-center gap-1.5 text-teal-700">
              <CheckCircle2 className="h-4 w-4" />
              <span className="text-sm font-medium">{fileCount}</span>
            </div>
          ) : (
            <ChevronRight className="h-4 w-4 text-slate-400 group-hover:text-slate-600 transition-colors" />
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <CardDescription className="text-xs text-muted-foreground leading-relaxed">
          {DOCUMENT_TYPE_DESCRIPTIONS[type]}
        </CardDescription>
      </CardContent>
    </Card>
  );
};
