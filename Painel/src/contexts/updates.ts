export interface UpdateEntry {
  version: string;
  date: string;
  title: string;
  changes: string[];
}

export const UPDATES_STORAGE_KEY = 'painel:last-seen-update-version';

export const UPDATE_LOG: UpdateEntry[] = [
  {
    version: '2026.04.1',
    date: '08/04/2026',
    title: 'Documentacao revisada sem alterar o layout',
    changes: [
      'Atualizado: a documentacao agora reflete as rotas ativas do painel e os modulos reais da API.',
      'Atualizado: as descricoes de fluxo passaram a separar com clareza os cenarios XML/NFe e SPED.',
      'Adicionado: registro da Analise Fiscal com drill-down por Estado, Cidade, NCM e Produto.',
      'Adicionado: registro da Central de inconsistencias, incluindo pendencias fiscais e historico local de operacoes.',
      'Adicionado: registro do modulo NCM/IBPT da API, com sincronizacao e consulta tributaria.',
      'Tirado: as paginas Atualizacoes e Configuracoes sairam da lista de rotas ativas e foram documentadas como fora do roteador principal.',
      'Tirado: o chat deixou de aparecer como funcionalidade ativa e ficou documentado como recurso desabilitado.',
    ],
  },
  {
    version: '2026.02.1',
    date: '27/02/2026',
    title: 'Pagina de atualizacoes com aviso visual',
    changes: [
      'Criada a nova pagina de Atualizacoes para centralizar novidades e correcoes.',
      'Adicionado alerta amarelo para destacar quando existirem novas informacoes ainda nao lidas.',
      'Incluido indicador "Novo" no menu lateral para facilitar a identificacao de atualizacoes recentes.',
    ],
  },
];

export const getLatestUpdateVersion = () => UPDATE_LOG[0]?.version ?? '0';

export const hasUnreadUpdates = () => {
  if (typeof window === 'undefined') {
    return false;
  }

  const latestVersion = getLatestUpdateVersion();
  const lastSeenVersion = localStorage.getItem(UPDATES_STORAGE_KEY);

  return lastSeenVersion !== latestVersion;
};
