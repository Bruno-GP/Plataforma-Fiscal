import { createElement, Fragment, type ReactNode, useMemo } from 'react';

const allowedTags = new Set([
  'section',
  'header',
  'div',
  'article',
  'p',
  'h2',
  'h3',
  'ul',
  'li',
  'table',
  'thead',
  'tbody',
  'tr',
  'th',
  'td',
  'footer',
  'strong',
  'span',
]);

const allowedClasses = new Set([
  'ia-report',
  'ia-report__hero',
  'ia-report__eyebrow',
  'ia-report__title',
  'ia-report__subtitle',
  'ia-report__meta',
  'ia-report__meta-item',
  'ia-report__grid',
  'ia-report__card',
  'ia-report__card--highlight',
  'ia-report__card--positive',
  'ia-report__card--warning',
  'ia-report__card--danger',
  'ia-report__section-title',
  'ia-report__kpi-value',
  'ia-report__kpi-label',
  'ia-report__list',
  'ia-report__table',
  'ia-report__badge',
  'ia-report__badge--positive',
  'ia-report__badge--warning',
  'ia-report__badge--danger',
  'ia-report__action-list',
  'ia-report__footer',
]);

const sanitizeHtml = (html: string): ReactNode[] => {
  if (typeof window === 'undefined') {
    return [];
  }

  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');

  const sanitizeNode = (node: Node, keyPrefix: string): ReactNode | null => {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent ?? '';
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
      return null;
    }

    const element = node as HTMLElement;
    const tagName = element.tagName.toLowerCase();

    if (!allowedTags.has(tagName)) {
      const children = Array.from(element.childNodes)
        .map((child, index) => sanitizeNode(child, `${keyPrefix}-${index}`))
        .filter((child): child is ReactNode => child !== null);

      return createElement(Fragment, { key: keyPrefix }, ...children);
    }

    const classNames = (element.getAttribute('class') ?? '')
      .split(/\s+/)
      .filter((className) => allowedClasses.has(className));

    const props: Record<string, string> = {};
    if (classNames.length > 0) {
      props.className = classNames.join(' ');
    }
    props.key = keyPrefix;

    const children = Array.from(element.childNodes)
      .map((child, index) => sanitizeNode(child, `${keyPrefix}-${index}`))
      .filter((child): child is ReactNode => child !== null);

    return createElement(tagName, props, ...children);
  };

  return Array.from(doc.body.childNodes)
    .map((child, index) => sanitizeNode(child, `report-${index}`))
    .filter((child): child is ReactNode => child !== null);
};

interface IAReportPreviewProps {
  report: string;
}

export function IAReportPreview({ report }: IAReportPreviewProps) {
  const isHtml = /<\s*[a-z][\s\S]*>/i.test(report);
  const sanitizedReport = useMemo(
    () => (isHtml ? sanitizeHtml(report) : ''),
    [isHtml, report],
  );

  if (!isHtml) {
    return (
      <div className="whitespace-pre-wrap rounded-2xl border border-border/70 bg-muted/30 p-5 text-sm leading-7 text-foreground">
        {report}
      </div>
    );
  }

  return (
    <div
      className="ia-report-surface overflow-hidden rounded-2xl border border-slate-800/80 bg-slate-950/70 shadow-[0_24px_70px_-48px_rgba(15,23,42,1)]"
    >
      {sanitizedReport}
    </div>
  );
}
