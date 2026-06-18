import type { MunicipioCatalogoItem, UFCatalogoItem } from '@/services/municipios';

import type { CatalogSelectionValidation } from '../types';

export function validateCatalogSelection(
  selectedUf: UFCatalogoItem | null,
  selectedCidade: MunicipioCatalogoItem | null,
): CatalogSelectionValidation {
  if (!selectedUf?.uf) {
    return {
      isValid: false,
      error: 'Selecione uma UF antes de cadastrar a empresa.',
    };
  }

  if (!selectedCidade) {
    return {
      isValid: false,
      error: 'Selecione uma cidade vinculada ao catalogo de municipios.',
    };
  }

  if (!selectedCidade.municipio_id || !selectedCidade.codigo_ibge) {
    return {
      isValid: false,
      error: 'A cidade selecionada precisa ter municipio_id e codigo_ibge validos.',
    };
  }

  return {
    isValid: true,
    selectedUf,
    selectedCidade,
  };
}
