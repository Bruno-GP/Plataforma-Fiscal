import { MonthYearFilter } from '../../filters/MothYearFilter';

interface FaturamentoHeaderProps {
  selectedMonth: string;
  selectedYear: string;
  availableYears: number[];
  monthLabels: string[];
  onMonthChange: (value: string) => void;
  onYearChange: (value: string) => void;
}

export function FaturamentoHeader({
  selectedMonth,
  selectedYear,
  availableYears,
  monthLabels,
  onMonthChange,
  onYearChange,
}: FaturamentoHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-3xl font-bold">Faturamento</h1>
        <p className="text-muted-foreground">Acompanhe suas receitas e métricas financeiras</p>
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