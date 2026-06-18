import type { ChangeEvent } from 'react';

import type { MunicipioCatalogoItem, UFCatalogoItem } from '@/services/municipios';

export interface CatalogoComboboxProps<TItem> {
  label: string;
  placeholder: string;
  searchPlaceholder: string;
  emptyMessage: string;
  disabled?: boolean;
  selectedLabel: string;
  searchValue: string;
  onSearchValueChange: (value: string) => void;
  onSelectItem: (item: TItem) => void;
  items: TItem[];
  isLoading: boolean;
  itemLabel: (item: TItem) => string;
  itemDescription?: (item: TItem) => string;
}

export interface TextInputFieldProps {
  id: string;
  label: string;
  type: string;
  placeholder: string;
  value: string;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  inputMode?: 'numeric';
  maxLength?: number;
  minLength?: number;
}

export type CatalogSelectionValidation =
  | {
      isValid: false;
      error: string;
    }
  | {
      isValid: true;
      selectedUf: UFCatalogoItem;
      selectedCidade: MunicipioCatalogoItem;
    };
