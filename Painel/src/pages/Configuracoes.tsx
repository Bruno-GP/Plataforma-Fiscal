import { CompanyDataCard } from '@/features/configuracoes/components/CompanyDataCard';
import { PasswordChangeCard } from '@/features/configuracoes/components/PasswordChangeCard';
import { SettingsHero } from '@/features/configuracoes/components/SettingsHero';
import { useConfiguracoesPageData } from '@/features/configuracoes/hooks/useConfiguracoesPageData';

export default function Configuracoes() {
  const { empresa, passwordForm, profileQuery } = useConfiguracoesPageData();

  return (
    <div className="space-y-6">
      <SettingsHero />

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <CompanyDataCard empresa={empresa} profileQuery={profileQuery} />
        <PasswordChangeCard passwordForm={passwordForm} />
      </div>
    </div>
  );
}
