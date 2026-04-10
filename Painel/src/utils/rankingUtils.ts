import { formatCurrency, parseDecimal } from './formatters';

interface BaseRankingItem {
  valor_total?: number | string;
  quantidade_total?: number | string;
  [key: string]: any;
}

const CITY_UF_SUFFIX_REGEX = /^(.*?)(?:\s*[-/]\s*|\s*\(\s*)([A-Z]{2})(?:\s*\))?$/;

const normalizeWhitespace = (value: string) => value.replace(/\s+/g, ' ').trim();

export const normalizeCityUfLabel = (cityValue?: string | null, ufValue?: string | null) => {
  const fallbackCity = 'Cidade nao identificada';
  const cityRaw = normalizeWhitespace(String(cityValue ?? ''));
  const ufRaw = normalizeWhitespace(String(ufValue ?? '')).toUpperCase();

  if (!cityRaw) {
    return ufRaw ? `${fallbackCity} - ${ufRaw}` : fallbackCity;
  }

  const cityMatch = cityRaw.match(CITY_UF_SUFFIX_REGEX);
  const cityFromLabel = normalizeWhitespace(cityMatch?.[1] ?? cityRaw);
  const ufFromLabel = cityMatch?.[2]?.toUpperCase() ?? '';
  const resolvedCity = cityFromLabel || fallbackCity;
  const resolvedUf = ufRaw || ufFromLabel;

  return resolvedUf ? `${resolvedCity} - ${resolvedUf}` : resolvedCity;
};

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
      titleStr = normalizeCityUfLabel(item['cidade'], item['uf']);
    } else {
      titleStr = titleStr ?? fallbackTitle;
    }

    const defaultSubtitle = percentual !== null && percentual !== undefined
      ? `${percentual.toFixed(1)}% do total`
      : 'Participacao nao informada';

    return {
      key: `${titleStr}-${index}`,
      title: titleStr,
      subtitle: subtitleFormatter ? subtitleFormatter(percentual) : defaultSubtitle,
      value: formatValue(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });
}
