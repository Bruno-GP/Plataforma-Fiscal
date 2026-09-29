import { cn } from '@/lib/utils';

export function MetaDetailStat({
  title,
  value,
  description,
  tone = 'neutral',
}: {
  title: string;
  value: string;
  description: string;
  tone?: 'neutral' | 'positive' | 'warning';
}) {
  const toneClasses: Record<typeof tone, string> = {
    neutral: 'border-slate-800 bg-slate-900/80',
    positive: 'border-emerald-400/25 bg-emerald-400/10',
    warning: 'border-amber-400/25 bg-amber-400/10',
  };

  return (
    <div className={cn('min-w-0 rounded-md border p-4', toneClasses[tone])}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{title}</p>
      <p className="mt-2 break-words text-xl font-semibold text-slate-100">{value}</p>
      <p className="mt-1 break-words text-xs leading-5 text-slate-400">{description}</p>
    </div>
  );
}
