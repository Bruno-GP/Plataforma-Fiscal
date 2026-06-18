import { FileUp } from 'lucide-react';

import { CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function ImportacaoSpedCardHeader() {
  return (
    <CardHeader>
      <CardTitle className="flex items-center gap-2">
        <FileUp className="h-5 w-5" />
        Enviar arquivos SPED (.txt)
      </CardTitle>
      <CardDescription>
        Faça a importação para staging e depois rode o processamento dos registros fiscais.
      </CardDescription>
    </CardHeader>
  );
}
