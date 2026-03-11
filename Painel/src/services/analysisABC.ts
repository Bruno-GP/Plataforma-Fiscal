export type AbcClass = 'A' | 'B' | 'C';

export interface AbcInputItem {
  key: string;
  value: number;
}

export interface AbcResultItem {
  key: string;
  abcClass: AbcClass;
  cumulativePercent: number;
  participationPercent: number;
  value: number;
}

const sanitizeValue = (value: number) => (Number.isFinite(value) && value > 0 ? value : 0);

export const calculateAbcCurveList = (items: AbcInputItem[]): AbcResultItem[] => {
  const sortedItems = [...items]
    .map((item) => ({ ...item, value: sanitizeValue(item.value) }))
    .filter((item) => item.value > 0)
    .sort((a, b) => b.value - a.value);

  const totalValue = sortedItems.reduce((acc, item) => acc + item.value, 0);

  if (!totalValue) {
    return [];
  }

  let cumulativePercent = 0;

  return sortedItems.map((item, index) => {
    const participationPercent = (item.value / totalValue) * 100;
    cumulativePercent += participationPercent;

    const abcClass: AbcClass = cumulativePercent <= 80 || index === 0
      ? 'A'
      : cumulativePercent <= 95
        ? 'B'
        : 'C';

    return {
      key: item.key,
      abcClass,
      cumulativePercent,
      participationPercent,
      value: item.value,
    };
  });
};

export const calculateAbcCurve = (items: AbcInputItem[]): Map<string, AbcResultItem> =>
  new Map(calculateAbcCurveList(items).map((item) => [item.key, item]));