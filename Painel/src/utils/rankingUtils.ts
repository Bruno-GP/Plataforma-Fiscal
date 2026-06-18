import { formatCurrency, parseDecimal } from './formatters';

interface BaseRankingItem {
  valor_total?: number | string;
  quantidade_total?: number | string;
  [key: string]: any;
}

const CITY_UF_SUFFIX_REGEX = /^(.*?)(?:\s*[-/]\s*|\s*\(\s*)([A-Z]{2})(?:\s*\))?$/;

const normalizeWhitespace = (value: string) => value.replace(/\s+/g, ' ').trim();

/**
 * Normaliza rótulos que podem chegar como cidade separada de UF ou como "Cidade - UF".
 */
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

/**
 * Monta itens padronizados para cards de ranking a partir de respostas NFe/SPED heterogêneas.
 */
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
      ...(titleField === 'cidade_uf'
        ? {
            cidade: item['cidade'] ?? undefined,
            uf: item['uf'] ?? undefined,
          }
        : {}),
    };
  });
}

export const sumNumberField = <T extends Record<string, any>>(items: T[] = [], field: keyof T) =>
  items.reduce((acc, item) => acc + Number(item[field] ?? 0), 0);

export const sumDecimalField = <T extends Record<string, any>>(items: T[] = [], field: keyof T) =>
  items.reduce((acc, item) => acc + parseDecimal(item[field] ?? 0), 0);

export const buildPurchaseValueRankingItems = (
  rows: BaseRankingItem[] = [],
  options: {
    titleField: string;
    totalValue: number;
    fallbackTitle: string;
    subtitle: (row: BaseRankingItem) => string;
    keySuffix?: string;
    limit?: number;
  },
) => {
  const { titleField, totalValue, fallbackTitle, subtitle, keySuffix = '', limit = 5 } = options;

  return rows.slice(0, limit).map((row, index) => {
    const valorTotal = parseDecimal(row.valor_total);
    const percentual = totalValue ? (valorTotal / totalValue) * 100 : null;
    const title = row[titleField] ?? fallbackTitle;

    return {
      key: `${title}-${index}${keySuffix}`,
      title,
      subtitle: subtitle(row),
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });
};

export const buildPurchaseQuantityRankingItems = (
  rows: BaseRankingItem[] = [],
  totalQuantity: number,
  limit = 5,
) =>
  rows.slice(0, limit).map((row, index) => {
    const quantidade = parseDecimal(row.quantidade_total);
    const percentual = totalQuantity ? (quantidade / totalQuantity) * 100 : null;
    const valorTotal = parseDecimal(row.valor_total);
    const title = row.produto ?? 'Produto nao identificado';

    return {
      key: `${title}-${index}-quantidade`,
      title,
      subtitle: `${quantidade.toFixed(2)} itens comprados`,
      value: formatCurrency(valorTotal),
      rawValue: valorTotal,
      percent: percentual,
    };
  });

export const aggregateClientKpis = (items: any[] = []) => {
  const topClientesMap = new Map<string, number>();

  const aggregated = items.reduce(
    (acc, item) => {
      const kpi = item.kpis;
      acc.total_vendas += parseDecimal(kpi.total_vendas ?? 0);
      acc.total_icms += parseDecimal(kpi.total_icms ?? 0);
      acc.total_ipi += parseDecimal(kpi.total_ipi ?? 0);
      acc.total_pis += parseDecimal(kpi.total_pis ?? 0);
      acc.total_cofins += parseDecimal(kpi.total_cofins ?? 0);

      (kpi.top_clientes ?? []).forEach((cliente: any) => {
        const name = cliente.cliente ?? 'Cliente nao identificado';
        const value = parseDecimal(cliente.valor_total ?? 0);
        topClientesMap.set(name, (topClientesMap.get(name) ?? 0) + value);
      });

      return acc;
    },
    {
      total_vendas: 0,
      total_icms: 0,
      total_ipi: 0,
      total_pis: 0,
      total_cofins: 0,
    },
  );

  const topClientes = [...topClientesMap.entries()]
    .sort(([, valorA], [, valorB]) => valorB - valorA)
    .map(([cliente, valor_total]) => ({ cliente, valor_total, percentual: undefined }));

  return {
    ...aggregated,
    top_clientes: topClientes,
  };
};

export const buildClientRiskItems = (params: {
  resultados: any[];
  topClientes: any[];
  totalReceita: number;
}) => {
  const { resultados, topClientes, totalReceita } = params;
  const sortedResults = resultados
    .filter((item) => item.periodo_ano && item.periodo_mes)
    .sort((a, b) => {
      const anoA = a.periodo_ano ?? 0;
      const anoB = b.periodo_ano ?? 0;
      if (anoA !== anoB) {
        return anoA - anoB;
      }
      return (a.periodo_mes ?? 0) - (b.periodo_mes ?? 0);
    });

  const previousPeriod = sortedResults[sortedResults.length - 2];
  const previousMap = new Map<string, number>();
  (previousPeriod?.kpis.top_clientes ?? []).forEach((cliente: any, index: number) => {
    const nome = cliente.cliente ?? `Cliente nao identificado ${index + 1}`;
    previousMap.set(nome, parseDecimal(cliente.valor_total ?? 0));
  });

  return topClientes.map((cliente, index) => {
    const nome = cliente.cliente ?? `Cliente nao identificado ${index + 1}`;
    const valorTotal = parseDecimal(cliente.valor_total ?? 0);
    const percentual =
      cliente.percentual !== undefined && cliente.percentual !== null
        ? parseDecimal(cliente.percentual)
        : totalReceita > 0
          ? (valorTotal / totalReceita) * 100
          : null;

    const valorAnterior = previousMap.get(nome) ?? 0;
    const quedaForte = valorAnterior > 0 && valorTotal < valorAnterior * 0.7;
    const saiuDoRanking = valorAnterior > 0 && valorTotal === 0;

    return {
      cliente: nome,
      valorTotal,
      percentual,
      temRisco: quedaForte || saiuDoRanking,
    };
  });
};
