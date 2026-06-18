import type { LucideIcon } from 'lucide-react';

export type DetailMode = 'nota' | 'regiao' | 'fiscal';

export type DetailModeOption = {
  key: DetailMode;
  title: string;
  description: string;
};

export type DetailLevelButton = {
  key: string;
  title: string;
  isOpen: boolean;
  onClick: () => void;
};

export type DetailStat = {
  title: string;
  value: string;
  description: string;
  icon: LucideIcon;
  trend: 'up' | 'down';
  accentClass: string;
  appendPreviousMonthLabel?: boolean;
};
