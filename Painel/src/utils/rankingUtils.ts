import { formatCurrency, parseDecimal } from './formatters';

interface BaseRankingItem {
  valor_total?: number | string;
  quantidade_total?: number | string;
  [key: string]: any;
}

export function buildRankingItems(
  baseItems: BaseRankingItem[],
  titleField: string,
  fallbackTitle: string,
  resolvePercentual: (valorTotal: number) => number | null,
  formatValue: (valor: number) => string = formatCurrency,
  valueField: 'valor_total' | 'quantidade_total' = 'valor_total',
  subtitleFormatter?: (percentual: number | null) => string
) {
  return baseItems.slice(0, 5).map((item, index) => {
    const rawValueStr = item[valueField] ?? 0;
    const valorTotal = parseDecimal(rawValueStr);
    const percentual = resolvePercentual(valorTotal);

    let titleStr = item[titleField];
    if (titleField === 'cidade_uf') {
      const cidade = item['cidade']?.trim() ?? 'Cidade não identificada';
      const uf = item['uf']?.trim();
      titleStr = uf ? `${cidade} - ${uf.toUpperCase()}` : cidade;
    } else {
      titleStr = titleStr ?? fallbackTitle;
    }

    const defaultSubtitle = percentual !== null && percentual !== undefined
      ? `${percentual.toFixed(1)}% do total`
      : 'Participação não informada';

    return {
      key: `${item[titleField]}-${index}`,
      title: titleStr,
      subtitle: subtitleFormatter ? subtitleFormatter(percentual) : defaultSubtitle,
      value: formatValue(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });
}
