import { describe, expect, it } from 'vitest';

import { getXmlImportPrimaryActionLabel } from '@/pages/components/ImportacaoXml/ImportacaoXmlActions';
import { getXmlFileSelectionSummary } from '@/pages/components/ImportacaoXml/ImportacaoXmlFileSelection';
import { getXmlImportOperationTitle } from '@/pages/components/ImportacaoXml/ImportacaoXmlOperationFeedback';
import { getXmlPendingNoticeMessage } from '@/pages/components/ImportacaoXml/ImportacaoXmlPendingNotice';
import { getXmlImportResultSummary } from '@/pages/components/ImportacaoXml/ImportacaoXmlResultsPanel';
import type { ImportacaoXmlArquivoResultado } from '@/services/nfe';

describe('ImportacaoXML component helpers', () => {
  it('resolve rotulo da acao principal de importacao XML', () => {
    expect(getXmlImportPrimaryActionLabel({
      isImporting: false,
      isProcessing: false,
    })).toBe('Importar e processar');

    expect(getXmlImportPrimaryActionLabel({
      isImporting: true,
      isProcessing: false,
    })).toBe('Importando...');

    expect(getXmlImportPrimaryActionLabel({
      isImporting: false,
      isProcessing: true,
    })).toBe('Processando...');
  });

  it('monta resumo da selecao de arquivos XML', () => {
    expect(getXmlFileSelectionSummary({
      maxFiles: 10000,
      selectedCount: 3,
      totalSizeLabel: '12.5 KB',
    })).toBe('3/10000 arquivo(s) • 12.5 KB');
  });

  it('resolve titulos por estagio da operacao XML', () => {
    expect(getXmlImportOperationTitle('processing')).toBe('Processando');
    expect(getXmlImportOperationTitle('completed')).toBe('Processamento terminado');
    expect(getXmlImportOperationTitle('cancelled')).toBe('Operação cancelada');
    expect(getXmlImportOperationTitle('error')).toBe('Falha no processamento');
    expect(getXmlImportOperationTitle('idle')).toBe('Início do processamento');
  });

  it('monta mensagem do aviso de pendencias XML', () => {
    expect(getXmlPendingNoticeMessage(12)).toBe(
      'Ainda faltam XMLs a serem processados (12). Uma nova operação volta a processar os pendentes automaticamente.',
    );
  });

  it('resume resultados da importacao XML', () => {
    const results: ImportacaoXmlArquivoResultado[] = [
      { arquivo: 'a.xml', status: 'importado', mensagem: 'Importado' },
      { arquivo: 'b.xml', status: 'duplicado', mensagem: 'Duplicado' },
      { arquivo: 'c.xml', status: 'erro', mensagem: 'Erro' },
      { arquivo: 'd.xml', status: 'importado', mensagem: 'Importado' },
    ];

    expect(getXmlImportResultSummary(results, 10)).toEqual({
      evaluated: 10,
      imported: 2,
      duplicated: 1,
      errors: 1,
    });
  });
});
