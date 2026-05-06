export type FiscalOperationType = 'xml-import' | 'xml-process' | 'sped-import' | 'sped-process';
export type FiscalOperationStatus = 'success' | 'warning' | 'error' | 'cancelled' | 'queued' | 'running';

export interface FiscalOperationEntry {
  id: string;
  type: FiscalOperationType;
  status: FiscalOperationStatus;
  title: string;
  description: string;
  cnpj: string;
  createdAt: string;
  jobId?: string;
  jobStatus?: string;
  backendMessage?: string;
}

const OPERATIONS_STORAGE_KEY = 'fiscal_operations';
const MAX_OPERATION_ENTRIES = 12;

export const readFiscalOperations = (): FiscalOperationEntry[] => {
  const rawValue = localStorage.getItem(OPERATIONS_STORAGE_KEY);
  if (!rawValue) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawValue) as FiscalOperationEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

export const saveFiscalOperation = (entry: Omit<FiscalOperationEntry, 'id' | 'createdAt'>) => {
  const nextEntry: FiscalOperationEntry = {
    ...entry,
    id: `${entry.type}-${Date.now()}`,
    createdAt: new Date().toISOString(),
  };

  const currentEntries = readFiscalOperations();
  const nextEntries = [nextEntry, ...currentEntries].slice(0, MAX_OPERATION_ENTRIES);
  localStorage.setItem(OPERATIONS_STORAGE_KEY, JSON.stringify(nextEntries));
};
