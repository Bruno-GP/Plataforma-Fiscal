import { MonthYearFilter } from '../../filters/MothYearFilter';

interface DashboardHeaderProps {
  title: string;
  subtitle: string;

  selectedMonth: string;
  selectedYear: string;
  availableYears: number[];
  monthLabels: string[];
  onMonthChange: (value: string) => void;
  onYearChange: (value: string) => void;
}

export function DashboardHeader({ 
  title, 
  subtitle
 }: DashboardHeaderProps) {
  return (
    <div>
      <h1 className="text-3xl font-bold">{title}</h1>
      <p className="text-muted-foreground">{subtitle}</p>
    </div>
  );
}