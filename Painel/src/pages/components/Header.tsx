import { MonthYearFilter } from '../filters/MothYearFilter';

interface HeaderProps {
  title: string;
  subtitle: string;

  selectedMonth: string;
  selectedYear: string;
  availableYears: number[];
  monthLabels: string[];
  onMonthChange: (value: string) => void;
  onYearChange: (value: string) => void;
}

export function Header({ 
  title, 
  subtitle,
  selectedMonth,
  selectedYear,
  availableYears,
  monthLabels,
  onMonthChange,
  onYearChange,
 }: HeaderProps) {
  return (
    <div className="flex flex-col gap-4 pt-2 md:flex-row md:items-end md:justify-between">
      <div className="space-y-1">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-100 md:text-4xl">{title}</h1>
        <p className="max-w-3xl text-base text-slate-300">{subtitle}</p>
      </div>
      <MonthYearFilter
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={onMonthChange}
        onYearChange={onYearChange}
        className="shrink-0"
      />
    </div>
  );
}
