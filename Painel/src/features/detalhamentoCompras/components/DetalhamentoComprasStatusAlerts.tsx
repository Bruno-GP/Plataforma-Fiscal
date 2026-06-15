import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

type Props = {
  isSped: boolean;
  notasComprasError: unknown;
  dashboardError: unknown;
  hasDetalhamentoCompras: boolean;
  isDashboardLoading: boolean;
};

export function DetalhamentoComprasStatusAlerts({
  isSped,
  notasComprasError,
  dashboardError,
  hasDetalhamentoCompras,
  isDashboardLoading,
}: Props) {
  return (
    <>
      {isSped && (
        <Alert>
          <AlertTitle>Detalhamento por nota ainda nao disponivel para SPED</AlertTitle>
          <AlertDescription>
            Esta versao foi conectada a estrutura detalhada de NFe/XML. Se voce quiser, eu posso preparar a mesma
            experiencia para SPED no proximo passo.
          </AlertDescription>
        </Alert>
      )}

      {!isSped && notasComprasError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar notas de compra</AlertTitle>
          <AlertDescription>
            {notasComprasError instanceof Error
              ? notasComprasError.message
              : 'Nao foi possivel consultar as notas detalhadas de compra deste periodo.'}
          </AlertDescription>
        </Alert>
      )}

      {dashboardError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar detalhamento de compras</AlertTitle>
          <AlertDescription>
            {dashboardError instanceof Error
              ? dashboardError.message
              : 'Nao foi possivel consultar os dados detalhados de compras deste periodo.'}
          </AlertDescription>
        </Alert>
      )}

      {!isDashboardLoading && !dashboardError && !hasDetalhamentoCompras && (
        <Alert>
          <AlertTitle>Detalhamento indisponivel para compras neste periodo</AlertTitle>
          <AlertDescription>
            Nao existem visoes detalhadas de compras disponiveis na fonte atual para o recorte selecionado.
          </AlertDescription>
        </Alert>
      )}
    </>
  );
}

