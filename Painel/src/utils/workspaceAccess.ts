import type { SessionUser } from '@/services/api';

export const isXmlOnboardingLocked = (
  user: Pick<SessionUser, 'tem_sped' | 'tem_conta_azul' | 'tem_xml' | 'tem_xml_importado_valido'> | null | undefined,
) => Boolean(user && !user.tem_sped && !user.tem_conta_azul && !user.tem_xml && !user.tem_xml_importado_valido);

export const getDefaultWorkspaceRoute = (
  user: Pick<SessionUser, 'tem_sped' | 'tem_conta_azul' | 'tem_xml' | 'tem_xml_importado_valido'> | null | undefined,
) =>
  isXmlOnboardingLocked(user) ? '/importacao-xml' : '/dashboard';

export const isContaAzulDashboardOnly = (
  user: Pick<SessionUser, 'tem_conta_azul'> | null | undefined,
) => Boolean(user?.tem_conta_azul);
