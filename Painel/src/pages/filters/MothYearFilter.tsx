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
    <div className={cn('flex items-center gap-2', className)}>
      <Select value={selectedMonth} onValueChange={onMonthChange} >
        <SelectTrigger className="w-36">
          <SelectValue className="bg-black" placeholder={monthPlaceholder} />
        </SelectTrigger>
        <SelectContent className="bg-popover">
          {includeAllMonths && <SelectItem value="all">{allMonthsLabel}</SelectItem>}
          {monthLabels.map((label, index) => (
            <SelectItem key={label} value={(index + 1).toString()}>
              {label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={selectedYear} onValueChange={onYearChange}>
        <SelectTrigger className="w-32">
          <SelectValue placeholder={yearPlaceholder} />
        </SelectTrigger>
        <SelectContent className="bg-popover">
          {availableYears.map((yearOption) => (
            <SelectItem key={yearOption} value={String(yearOption)}>
              {yearOption}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}