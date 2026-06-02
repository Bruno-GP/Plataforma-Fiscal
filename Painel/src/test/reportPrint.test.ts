import { describe, expect, it } from 'vitest';

import { createReportPrintHtml, printReportElement } from '@/utils/reportPrint';

describe('reportPrint helpers', () => {
  it('gera HTML de impressao com titulo, subtitulo e conteudo', () => {
    const html = createReportPrintHtml({
      title: 'Relatorio executivo',
      subtitle: 'Total vendido no periodo',
      reportHtml: '<section>Conteudo do relatorio</section>',
      styleTags: '<style>.report{color:red}</style>',
    });

    expect(html).toContain('<title>Relatorio executivo</title>');
    expect(html).toContain('<h1 class="pdf-title">Relatorio executivo</h1>');
    expect(html).toContain('<p class="pdf-subtitle">Total vendido no periodo</p>');
    expect(html).toContain('<section>Conteudo do relatorio</section>');
    expect(html).toContain('<style>.report{color:red}</style>');
  });

  it('retorna erro quando nao ha container para impressao', () => {
    expect(printReportElement({
      container: null,
      title: 'Relatorio',
      subtitle: 'Resumo',
    })).toBe('Nao foi possivel preparar o relatorio para exportacao.');
  });
});
