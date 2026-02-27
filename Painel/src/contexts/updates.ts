export interface UpdateEntry {
  version: string;
  date: string;
  title: string;
  changes: string[];
}

export const UPDATES_STORAGE_KEY = 'painel:last-seen-update-version';

export const UPDATE_LOG: UpdateEntry[] = [
  {
    version: '2026.02.1',
    date: '27/02/2026',
    title: 'Página de atualizações com aviso visual',
    changes: [
      'Criada a nova página de Atualizações para centralizar novidades e correções.',
      'Adicionado alerta amarelo para destacar quando existirem novas informações ainda não lidas.',
      'Incluído indicador "Novo" no menu lateral para facilitar a identificação de atualizações recentes.',
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