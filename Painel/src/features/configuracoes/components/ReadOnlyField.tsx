import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface ReadOnlyFieldProps {
  id: string;
  label: string;
  value: string;
}

export function ReadOnlyField({ id, label, value }: ReadOnlyFieldProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
        {label}
      </Label>
      <Input
        id={id}
        value={value}
        readOnly
        aria-readonly="true"
        tabIndex={-1}
        className="h-11 cursor-default border-slate-700/80 bg-slate-950/60 text-slate-100 shadow-none pointer-events-none focus-visible:ring-0"
      />
    </div>
  );
}
