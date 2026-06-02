interface PrintReportInput {
  container: HTMLElement | null;
  title: string;
  subtitle: string;
  documentRef?: Document;
  windowRef?: Window;
}

export const createReportPrintHtml = ({
  reportHtml,
  styleTags,
  title,
  subtitle,
}: {
  reportHtml: string;
  styleTags: string;
  title: string;
  subtitle: string;
}) => `
  <!doctype html>
  <html lang="pt-BR">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>${title}</title>
      ${styleTags}
      <style>
        body {
          margin: 0;
          padding: 32px;
          background:
            radial-gradient(circle at top right, rgb(37 99 235 / 0.18), transparent 24rem),
            linear-gradient(180deg, rgb(15 23 42 / 0.98), rgb(2 6 23 / 1));
          color: #e2e8f0;
          font-family: ui-sans-serif, system-ui, sans-serif;
        }

        .pdf-shell {
          max-width: 1120px;
          margin: 0 auto;
        }

        .pdf-header {
          margin-bottom: 20px;
          padding: 20px 22px;
          border: 1px solid rgb(51 65 85 / 0.72);
          border-radius: 24px;
          background: linear-gradient(180deg, rgb(15 23 42 / 0.92), rgb(15 23 42 / 0.7));
        }

        .pdf-title {
          margin: 0;
          font-size: 28px;
          font-weight: 700;
          color: #f8fafc;
        }

        .pdf-subtitle {
          margin: 8px 0 0;
          font-size: 14px;
          color: #94a3b8;
        }

        @page {
          size: A4;
          margin: 12mm;
        }

        @media print {
          body {
            padding: 0;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
        }
      </style>
    </head>
    <body>
      <div class="pdf-shell">
        <div class="pdf-header">
          <h1 class="pdf-title">${title}</h1>
          <p class="pdf-subtitle">${subtitle}</p>
        </div>
        ${reportHtml}
      </div>
    </body>
  </html>
`;

export const printReportElement = ({
  container,
  title,
  subtitle,
  documentRef = document,
  windowRef = window,
}: PrintReportInput): string | null => {
  if (!container) {
    return 'Nao foi possivel preparar o relatorio para exportacao.';
  }

  const reportHtml = container.innerHTML;
  const styleTags = Array.from(documentRef.querySelectorAll('style, link[rel="stylesheet"]'))
    .map((node) => node.outerHTML)
    .join('\n');

  const iframe = documentRef.createElement('iframe');
  iframe.setAttribute('aria-hidden', 'true');
  iframe.style.position = 'fixed';
  iframe.style.right = '0';
  iframe.style.bottom = '0';
  iframe.style.width = '0';
  iframe.style.height = '0';
  iframe.style.border = '0';
  documentRef.body.appendChild(iframe);

  const iframeDocument = iframe.contentDocument;
  if (!iframeDocument) {
    documentRef.body.removeChild(iframe);
    return 'Nao foi possivel abrir a visualizacao de impressao do PDF.';
  }

  iframeDocument.open();
  iframeDocument.write(createReportPrintHtml({
    reportHtml,
    styleTags,
    title,
    subtitle,
  }));
  iframeDocument.close();

  const printFrame = iframe.contentWindow;
  if (!printFrame) {
    documentRef.body.removeChild(iframe);
    return 'Nao foi possivel iniciar a geracao do PDF.';
  }

  windowRef.setTimeout(() => {
    printFrame.focus();
    printFrame.print();
    windowRef.setTimeout(() => {
      if (documentRef.body.contains(iframe)) {
        documentRef.body.removeChild(iframe);
      }
    }, 1000);
  }, 250);

  return null;
};
