import { Shield } from 'lucide-react';

export function SettingsHero() {
  return (
    <div className="mt-4 relative overflow-hidden rounded-3xl border border-slate-800/80 bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.18),_transparent_36%),linear-gradient(135deg,_rgba(8,15,28,0.94),_rgba(15,23,42,0.92))] p-6 shadow-[0_24px_80px_-48px_rgba(2,132,199,0.6)] sm:p-8">
      <div className="absolute -right-8 top-0 h-32 w-32 rounded-full bg-sky-400/10 blur-3xl" />
      <div className="relative flex flex-col gap-3 pt-2 sm:pt-4">
        <div className="inline-flex w-fit items-center gap-2 rounded-full border border-sky-400/30 bg-sky-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-sky-200">
          <Shield className="h-3.5 w-3.5" />
          Configuracoes de conta
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50 sm:text-4xl">
          Dados da empresa
        </h1>
        {/* <p className="max-w-2xl text-sm text-slate-300 sm:text-base">
          Os dados cadastrais exibidos abaixo sao somente leitura. A unica acao disponivel nesta tela e a
          alteracao da senha do usuario autenticado.
        </p> */}
      </div>
    </div>
  );
}
