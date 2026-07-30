import { normalizeCnpj } from '@/utils/formatters';

export const formatCnpj = (value: string) => {
  const digits = normalizeCnpj(value).slice(0, 14);
  if (digits.length !== 14) {
    return value;
  }

  return digits.replace(/^(.{2})(.{3})(.{3})(.{4})(\d{2})$/, '$1.$2.$3/$4-$5');
};
