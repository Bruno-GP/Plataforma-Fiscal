import { Button } from '@/components/ui/button';
import type { DetailMode } from '@/pages/components/detalhamentoVendasHelpers';

const modeButtonBaseClass =
  'h-auto justify-start rounded-md border px-4 py-3 text-left transition-colors';
const modeButtonActiveClass =
  'border-white bg-white text-[#0E1525] hover:bg-white/90 hover:text-[#0E1525]';
const modeButtonInactiveClass =
  'border-slate-700 bg-slate-900/80 text-slate-100 hover:border-sky-500/60 hover:bg-slate-800';

type ModeOption = {
  key: DetailMode;
  title: string;
  description: string;
};

type Props = {
  detailMode: DetailMode;
  onChange: (mode: DetailMode) => void;
  options?: ModeOption[];
};

const defaultModeButtons: ModeOption[] = [
  { key: 'nota', title: 'Detalhamento por nota', description: 'Nota > cliente > NCM > produto' },
  { key: 'regiao', title: 'Detalhamento por regiao', description: 'Estado > cidade > cliente > produto' },
];

export function DetalhamentoVendasModeSelector({
  detailMode,
  onChange,
  options = defaultModeButtons,
}: Props) {
  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-950/40 px-4 py-4">
      <div className={`mx-auto grid max-w-5xl gap-3 ${options.length > 1 ? 'md:grid-cols-2' : 'md:grid-cols-1'}`}>
        {options.map((button) => {
          const isActive = detailMode === button.key;

          return (
            <Button
              key={button.key}
              type="button"
              variant="outline"
              onClick={() => onChange(button.key)}
              className={`${modeButtonBaseClass} ${isActive ? modeButtonActiveClass : modeButtonInactiveClass}`}
            >
              <span className="flex flex-col items-start gap-1">
                <span
                  className={`text-xs font-semibold uppercase tracking-[0.24em] ${
                    isActive ? 'text-[#0E1525]/70' : 'text-slate-400'
                  }`}
                >
                  Modo
                </span>
                <span className={`text-sm font-medium ${isActive ? 'text-[#0E1525]' : 'text-slate-100'}`}>
                  {button.title}
                </span>
                <span className={`text-xs ${isActive ? 'text-[#0E1525]/70' : 'text-slate-400'}`}>
                  {button.description}
                </span>
              </span>
            </Button>
          );
        })}
      </div>
    </div>
  );
}
