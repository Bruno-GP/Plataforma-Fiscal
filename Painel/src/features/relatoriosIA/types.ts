export type ReportType = 'compras' | 'vendas' | 'clientes';

export type ReportFormat = 'executivo' | 'analitico';

export interface ReportOption<T extends string = string> {
  value: T;
  label: string;
  description?: string;
}
