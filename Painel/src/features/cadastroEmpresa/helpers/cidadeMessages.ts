import type { UFCatalogoItem } from '@/services/municipios';

export function getCidadeEmptyMessage(selectedUf: UFCatalogoItem | null, isLoading: boolean) {
  if (!selectedUf) {
    return 'Selecione uma UF valida para listar cidades.';
  }

  return isLoading ? 'Carregando...' : 'Nenhuma cidade encontrada.';
}
