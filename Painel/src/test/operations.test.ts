import { beforeEach, describe, expect, it } from 'vitest';

import { readFiscalOperations, saveFiscalOperation } from '@/services/operations';

describe('operations helpers', () => {
  beforeEach(() => {
    const storage = new Map<string, string>();

    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => {
          storage.set(key, value);
        },
        removeItem: (key: string) => {
          storage.delete(key);
        },
      },
    });
  });

  it('salva eventos operacionais no topo do histórico', () => {
    saveFiscalOperation({
      type: 'xml-import',
      status: 'success',
      title: 'Importacao XML concluida',
      description: 'Tudo certo.',
      cnpj: '12345678000199',
    });

    saveFiscalOperation({
      type: 'xml-process',
      status: 'warning',
      title: 'Processamento XML com alertas',
      description: 'Houve duplicados.',
      cnpj: '12345678000199',
    });

    const operations = readFiscalOperations();
    expect(operations).toHaveLength(2);
    expect(operations[0]?.type).toBe('xml-process');
    expect(operations[1]?.type).toBe('xml-import');
  });
});
