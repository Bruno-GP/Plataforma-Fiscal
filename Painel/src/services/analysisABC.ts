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
}

const sanitizeValue = (value: number) => (Number.isFinite(value) && value > 0 ? value : 0);

export const calculateAbcCurve = (items: AbcInputItem[]): Map<string, AbcResultItem> => {
  const sortedItems = [...items]
    .map((item) => ({ ...item, value: sanitizeValue(item.value) }))
    .filter((item) => item.value > 0)
    .sort((a, b) => b.value - a.value);

  const totalValue = sortedItems.reduce((acc, item) => acc + item.value, 0);

  if (!totalValue) {
    return new Map();
  }

  let cumulativePercent = 0;

  return new Map(
    sortedItems.map((item, index) => {
      const participationPercent = (item.value / totalValue) * 100;
      cumulativePercent += participationPercent;

      const abcClass: AbcClass = cumulativePercent <= 80 || index === 0
        ? 'A'
        : cumulativePercent <= 95
          ? 'B'
          : 'C';

      return [
        item.key,
        {
          key: item.key,
          abcClass,
          cumulativePercent,
          participationPercent,
        },
      ];
    }),
  );
};