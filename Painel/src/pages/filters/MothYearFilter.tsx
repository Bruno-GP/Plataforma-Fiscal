import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { cn } from '@/lib/utils';

interface MonthYearFilterProps {
  selectedMonth: string;
  selectedYear: string;
  availableYears: number[];
  monthLabels: string[];
  onMonthChange: (value: string) => void;
  onYearChange: (value: string) => void;
  includeAllMonths?: boolean;
  monthPlaceholder?: string;
  yearPlaceholder?: string;
  className?: string;
}

export function MonthYearFilter({
  selectedMonth,
  selectedYear,
  availableYears,
  monthLabels,
  onMonthChange,
  onYearChange,
  includeAllMonths = true,
  monthPlaceholder = 'Mês',
  yearPlaceholder = 'Ano',
  className,
}: MonthYearFilterProps) {
  return (
    <div className={cn('grid w-full grid-cols-2 gap-2 sm:w-auto sm:flex sm:items-end', className)}>
      <div className="space-y-1.5">
        <span className="block text-xs font-medium text-slate-300">Mês</span>
        <Select value={selectedMonth} onValueChange={onMonthChange}>
          <SelectTrigger className="h-9 w-full min-w-0 border-slate-700 bg-slate-900/80 text-slate-100 sm:w-36">
            <SelectValue placeholder={monthPlaceholder} />
          </SelectTrigger>

          <SelectContent className="border-slate-700 bg-slate-950 text-slate-100">
            {includeAllMonths && <SelectItem value="all">Todos</SelectItem>}
            {monthLabels.map((label, index) => (
              <SelectItem key={label} value={(index + 1).toString()}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <span className="block text-xs font-medium text-slate-300">Ano</span>
        <Select value={selectedYear} onValueChange={onYearChange}>
          <SelectTrigger className="h-9 w-full min-w-0 border-slate-700 bg-slate-900/80 text-slate-100 sm:w-28">
            <SelectValue placeholder={yearPlaceholder} />
          </SelectTrigger>

          <SelectContent className="border-slate-700 bg-slate-950 text-slate-100">
            {availableYears.map((yearOption) => (
              <SelectItem key={yearOption} value={String(yearOption)}>
                {yearOption}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
