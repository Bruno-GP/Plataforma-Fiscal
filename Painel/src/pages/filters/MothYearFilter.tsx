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
  allMonthsLabel?: string;
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
  allMonthsLabel = 'Todos os meses',
  monthPlaceholder = 'Mês',
  yearPlaceholder = 'Ano',
  className,
}: MonthYearFilterProps) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-300">Mês:</span>
        <Select value={selectedMonth} onValueChange={onMonthChange}>
          <SelectTrigger className="w-36 bg-[#0E1525] text-white border-[#1E293B]">
            <SelectValue placeholder={monthPlaceholder} />
          </SelectTrigger>

          <SelectContent className="bg-[#0E1525] text-white border-[#1E293B]">
            {includeAllMonths && (
              <SelectItem value="all">Todos</SelectItem>
            )}
            {monthLabels.map((label, index) => (
              <SelectItem
                key={label}
                value={(index + 1).toString()}
                className="focus:bg-[#1E293B]"
              >
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm text-slate-300">Ano:</span>
        <Select value={selectedYear} onValueChange={onYearChange}>
          <SelectTrigger className="w-32 bg-[#0E1525] text-white border-[#1E293B]">
            <SelectValue placeholder={yearPlaceholder} />
          </SelectTrigger>

        <SelectContent className="bg-[#0E1525] text-white border-[#1E293B]">
            {availableYears.map((yearOption) => (
              <SelectItem
                key={yearOption}
                value={String(yearOption)}
                className="focus:bg-[#1E293B]"
              >
                {yearOption}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}