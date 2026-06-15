import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

export function DetalhamentoComprasOverviewCard() {
  return (
    <Card className="border border-slate-800/80 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-800 text-white shadow-[0_28px_90px_-52px_rgba(15,23,42,1)]">
      <CardContent className="space-y-5 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <Badge className="border border-sky-400/20 bg-sky-400/10 text-sky-100 hover:bg-sky-400/10">
              Drill-down hierarquico
            </Badge>
            <h2 className="text-2xl font-semibold tracking-tight">Expansao em 4 niveis</h2>
            <p className="max-w-3xl text-sm text-slate-300">
              Esta tela usa exatamente os dados disponiveis no painel de compras. Quando um nivel nao existe nessa
              fonte, ele nao e exibido aqui.
            </p>
          </div>
          <Button asChild variant="secondary" className="gap-2 bg-white text-slate-900 hover:bg-slate-100">
            <Link to="/analise-compras">
              Voltar ao dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

