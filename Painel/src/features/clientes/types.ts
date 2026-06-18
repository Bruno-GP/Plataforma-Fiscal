export interface ClienteComRisco {
  cliente: string;
  valorTotal: number;
  percentual: number | null;
  temRisco: boolean;
}

export interface ClienteRankingItem {
  key: string;
  title: string;
  subtitle: string;
  value: string;
  rawValue: number;
  percent: number | null;
  badgeLabel: string;
  badgeClassName: string;
}
