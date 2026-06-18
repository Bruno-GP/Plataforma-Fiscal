import type { ClienteComRisco } from '../types';

export const countClientesEmRisco = (clientes: ClienteComRisco[]) =>
  clientes.filter((cliente) => cliente.temRisco).length;

export const countClientesSemRisco = (clientes: ClienteComRisco[]) =>
  clientes.filter((cliente) => !cliente.temRisco).length;

export const calculateRiskCompliancePercent = (
  totalClientes: number,
  clientesSemRisco: number,
) => (totalClientes ? Math.round((clientesSemRisco / totalClientes) * 100) : 0);
