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
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-3xl font-bold">{title}</h1>
        <p className="text-muted-foreground">{subtitle}</p>
      </div>
      <MonthYearFilter
        selectedMonth={selectedMonth}
        selectedYear={selectedYear}
        availableYears={availableYears}
        monthLabels={monthLabels}
        onMonthChange={onMonthChange}
        onYearChange={onYearChange}
      />
    </div>
  );
}