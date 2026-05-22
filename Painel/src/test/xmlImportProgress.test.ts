import { describe, expect, it } from 'vitest';

import {
  buildXmlImportProgressLabel,
  chunkItems,
  formatElapsedTime,
  getImportProgress,
  getProcessingProgressRange,
} from '@/utils/xmlImportProgress';

describe('xmlImportProgress helpers', () => {
  it('formata tempo decorrido em minutos e segundos', () => {
    expect(formatElapsedTime(125)).toBe('2m 5s');
  });

  it('divide itens em lotes menores', () => {
    expect(chunkItems([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]]);
  });

  it('calcula progresso da etapa de importacao', () => {
    expect(getImportProgress(100, 200, 55)).toBe(28);
    expect(getImportProgress(100, 0, 55)).toBe(0);
  });

  it('calcula faixa de progresso da etapa de processamento', () => {
    expect(getProcessingProgressRange(1, 3, 55, 100)).toEqual({
      rangeStart: 70,
      rangeEnd: 85,
    });
    expect(getProcessingProgressRange(0, 0, 55, 100)).toEqual({
      rangeStart: 100,
      rangeEnd: 100,
    });
  });

  it('monta labels por estagio da operacao', () => {
    expect(buildXmlImportProgressLabel({
      stage: 'importing',
      progress: 27.6,
      elapsedSeconds: 65,
    })).toBe('Importando XMLs - 28% - 1m 5s');

    expect(buildXmlImportProgressLabel({
      stage: 'processing',
      progress: 60,
      elapsedSeconds: 70,
      jobMessage: 'Processando CNPJ',
    })).toBe('Processando CNPJ - 60% - 1m 10s');

    expect(buildXmlImportProgressLabel({
      stage: 'completed',
      progress: 99,
      elapsedSeconds: 75,
    })).toBe('Processamento terminado - 100% - 1m 15s');

    expect(buildXmlImportProgressLabel({
      stage: 'cancelled',
      progress: 40,
      elapsedSeconds: 80,
    })).toBe('Operação cancelada - 40% - 1m 20s');

    expect(buildXmlImportProgressLabel({
      stage: 'idle',
      progress: 0,
      elapsedSeconds: 0,
    })).toBe('0% - 0m 0s');
  });
});
