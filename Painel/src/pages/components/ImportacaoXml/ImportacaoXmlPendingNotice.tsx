export const getXmlPendingNoticeMessage = (pendingCount: number) =>
  `Ainda faltam XMLs a serem processados (${pendingCount}). Uma nova operação volta a processar os pendentes automaticamente.`;

interface ImportacaoXmlPendingNoticeProps {
  pendingCount: number;
}

export function ImportacaoXmlPendingNotice({
  pendingCount,
}: ImportacaoXmlPendingNoticeProps) {
  if (pendingCount <= 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      {getXmlPendingNoticeMessage(pendingCount)}
    </div>
  );
}
