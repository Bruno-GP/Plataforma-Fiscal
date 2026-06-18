import { getXmlPendingNoticeMessage } from '../helpers/importacaoXmlView';
import type { ImportacaoXmlPendingNoticeProps } from '../types';

export function ImportacaoXmlPendingNotice({ pendingCount }: ImportacaoXmlPendingNoticeProps) {
  if (pendingCount <= 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      {getXmlPendingNoticeMessage(pendingCount)}
    </div>
  );
}
