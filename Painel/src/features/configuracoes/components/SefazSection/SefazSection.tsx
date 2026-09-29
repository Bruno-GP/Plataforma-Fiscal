import { useMemo } from 'react';
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  Copy,
  Download,
  FileCog,
  FileText,
  Loader2,
  RefreshCcw,
  ShieldCheck,
  Upload,
  XCircle,
} from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useToast } from '@/hooks/use-toast';

import { useSefazSectionData } from './useSefazSectionData';
import type { SefazDocumento, SefazManifestacaoTipo, SefazSyncLog } from './sefaz.types';

const CERTIFICADO_WARNING_DAYS = 30;

const getDocumentoSituacaoLabel = (situacao: SefazDocumento['situacao']) => {
  switch (situacao) {
    case 'autorizada':
      return 'Autorizada';
    case 'cancelada':
      return 'Cancelada';
    case 'denegada':
      return 'Denegada';
    default:
      return situacao ? situacao : 'Nao informado';
  }
};

const getDocumentoSituacaoBadge = (situacao: SefazDocumento['situacao']) => {
  switch (situacao) {
    case 'autorizada':
      return 'default';
    case 'cancelada':
      return 'outline';
    case 'denegada':
      return 'destructive';
    default:
      return 'secondary';
  }
};

const getDirecaoLabel = (direcao: SefazDocumento['direcao']) => (direcao === 'emitida' ? 'Emitida' : 'Recebida');

const getFiscalLabel = (documento: SefazDocumento) => {
  if (documento.direcao !== 'emitida') {
    return 'Nao aplicavel';
  }
  return documento.processado_fiscal_em ? 'No Fiscal' : 'Pendente';
};

const getFiscalBadge = (documento: SefazDocumento) => {
  if (documento.direcao !== 'emitida') {
    return 'outline' as const;
  }
  return documento.processado_fiscal_em ? ('default' as const) : ('secondary' as const);
};

const getManifestacaoLabel = (valor: string | null) => {
  switch (valor) {
    case 'pendente':
      return 'Pendente';
    case 'ciencia':
      return 'Ciência';
    case 'confirmada':
      return 'Confirmada';
    case 'desconhecida':
      return 'Desconhecida';
    case 'nao_realizada':
      return 'Não realizada';
    default:
      return valor || 'Nao informado';
  }
};

const getManifestacaoBadge = (valor: string | null) => {
  switch (valor) {
    case 'pendente':
      return 'warning';
    case 'confirmada':
      return 'default';
    case 'ciencia':
      return 'secondary';
    case 'desconhecida':
      return 'outline';
    case 'nao_realizada':
      return 'destructive';
    default:
      return 'secondary';
  }
};

const formatDate = (value: string | null) => {
  if (!value) {
    return 'Nao informado';
  }

  const dateValue = new Date(value);
  if (Number.isNaN(dateValue.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
    timeZone: 'America/Sao_Paulo',
  }).format(dateValue);
};

const formatOnlyDate = (value: string | null) => {
  if (!value) {
    return 'Nao informado';
  }

  const dateValue = new Date(value);
  if (Number.isNaN(dateValue.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeZone: 'America/Sao_Paulo',
  }).format(dateValue);
};

const formatCurrency = (value: string | number | null) => {
  if (value === null || value === undefined || value === '') {
    return 'Nao informado';
  }

  const numericValue = typeof value === 'number' ? value : Number(String(value).replace(',', '.'));
  if (Number.isNaN(numericValue)) {
    return String(value);
  }

  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(numericValue);
};

const formatCooldown = (seconds: number) => {
  if (seconds >= 3600) {
    const hours = Math.ceil(seconds / 3600);
    return `${hours} h`;
  }

  if (seconds >= 60) {
    const minutes = Math.ceil(seconds / 60);
    return `${minutes} min`;
  }

  return `${Math.max(1, seconds)} s`;
};

const truncateKey = (value: string) => `${value.slice(0, 12)}...${value.slice(-8)}`;

const decodeBase64ToText = (value: string) => {
  try {
    const binary = window.atob(value);
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    return new TextDecoder().decode(bytes);
  } catch {
    return null;
  }
};

const getCertificateState = (status: {
  ativo: boolean;
  cnpj_titular: string | null;
  data_validade: string | null;
  dias_restantes: number | null;
}) => {
  if (!status.ativo && !status.data_validade && !status.cnpj_titular) {
    return {
      label: 'Nao configurado',
      badgeVariant: 'outline' as const,
      tone: 'muted' as const,
      description: 'Nenhum certificado foi carregado ainda.',
    };
  }

  if (!status.ativo) {
    return {
      label: 'Expirado',
      badgeVariant: 'destructive' as const,
      tone: 'critical' as const,
      description: 'O certificado esta vencido ou inativo.',
    };
  }

  if ((status.dias_restantes ?? 0) < 0) {
    return {
      label: 'Expirado',
      badgeVariant: 'destructive' as const,
      tone: 'critical' as const,
      description: 'O certificado ja passou da data de validade.',
    };
  }

  if ((status.dias_restantes ?? 0) < CERTIFICADO_WARNING_DAYS) {
    return {
      label: 'Vigente com alerta',
      badgeVariant: 'warning' as const,
      tone: 'warning' as const,
      description: 'O certificado esta valido, mas a renovacao ja se aproxima.',
    };
  }

  return {
    label: 'Valido',
    badgeVariant: 'default' as const,
    tone: 'success' as const,
    description: 'O certificado esta ativo e apto para consultas.',
  };
};

const certificateStatusIcon = {
  muted: FileCog,
  warning: CalendarDays,
  critical: XCircle,
  success: CheckCircle2,
} as const;

type CertificateTone = keyof typeof certificateStatusIcon;

const manifestacaoActions: Array<{ label: string; tipo: SefazManifestacaoTipo }> = [
  { label: 'Ciência da Operação', tipo: 'ciencia' },
  { label: 'Confirmação', tipo: 'confirmada' },
  { label: 'Desconhecimento', tipo: 'desconhecida' },
  { label: 'Operação não Realizada', tipo: 'nao_realizada' },
];

export function SefazSection() {
  const { toast } = useToast();
  const data = useSefazSectionData();

  const certificateState = data.statusQuery.data ? getCertificateState(data.statusQuery.data) : null;
  const CertificateIcon = certificateState
    ? certificateStatusIcon[certificateState.tone as CertificateTone]
    : FileCog;
  const selectedDocumento = data.documentoDetalheQuery.data ?? null;

  const documentosPaginated = data.documentosQuery.data?.resultados ?? [];
  const syncLogPaginated = data.syncLogQuery.data?.resultados ?? [];

  const xmlPreview = useMemo(() => {
    if (!selectedDocumento?.xml_armazenado_base64) {
      return null;
    }

    return decodeBase64ToText(selectedDocumento.xml_armazenado_base64);
  }, [selectedDocumento?.xml_armazenado_base64]);

  const handleCopyKey = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      toast({
        title: 'Chave copiada',
        description: 'A chave de acesso completa foi copiada para a area de transferencia.',
      });
    } catch {
      toast({
        variant: 'destructive',
        title: 'Nao foi possivel copiar',
        description: 'O navegador bloqueou a copia da chave de acesso.',
      });
    }
  };

  const handleDownloadXml = () => {
    if (!selectedDocumento?.xml_armazenado_base64) {
      return;
    }

    const binary = window.atob(selectedDocumento.xml_armazenado_base64);
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    const blob = new Blob([bytes], { type: 'application/xml' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `sefaz-documento-${selectedDocumento.id}.xml`;
    anchor.click();
    window.URL.revokeObjectURL(url);
  };

  const certificadoInativo = !data.statusQuery.data?.ativo;
  const syncCooldownActive = data.syncCooldownSeconds > 0;
  const syncDisabled = data.sincronizandoAgora || certificadoInativo || syncCooldownActive;
  const syncButtonLabel = data.sincronizandoAgora
    ? 'Sincronizando...'
    : syncCooldownActive
      ? `Sincronizar em ${formatCooldown(data.syncCooldownSeconds)}`
      : 'Sincronizar agora';

  return (
    <>
      <Card className="border-slate-800/80 bg-slate-950/80 shadow-[0_24px_80px_-52px_rgba(15,23,42,0.9)]">
        <CardHeader className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-400/25 bg-cyan-400/10 text-cyan-300">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-xl">SEFAZ</CardTitle>
              <CardDescription>Certificado digital, consulta de documentos, manifestacao e historico de sync.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {data.statusQuery.isError ? (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{data.statusQuery.error.message}</AlertDescription>
            </Alert>
          ) : null}

          <Tabs value={data.activeTab} onValueChange={(value) => data.setActiveTab(value as typeof data.activeTab)}>
            <TabsList className="grid h-auto w-full grid-cols-3 bg-slate-900/70 p-1 text-slate-300">
              <TabsTrigger value="certificado" className="text-sm">
                Certificado
              </TabsTrigger>
              <TabsTrigger value="documentos" className="text-sm">
                Documentos
              </TabsTrigger>
              <TabsTrigger value="historico" className="text-sm">
                Historico
              </TabsTrigger>
            </TabsList>

            <TabsContent value="certificado" className="mt-5 space-y-5">
              <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
                <Card className="border-slate-800/70 bg-slate-900/55">
                  <CardHeader>
                    <CardTitle className="text-lg">Upload do certificado</CardTitle>
                    <CardDescription>Envie um arquivo .pfx ou .p12 e a senha correspondente. A senha nunca e exibida depois.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="sefaz-certificado-file" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                        Arquivo do certificado
                      </Label>
                      <Input
                        id="sefaz-certificado-file"
                        type="file"
                        accept=".pfx,.p12"
                        className="hidden"
                        onChange={(event) => {
                          data.setCertificadoFile(event.target.files?.[0] ?? null);
                          event.currentTarget.value = '';
                        }}
                      />
                      <div className="flex flex-wrap items-center gap-3">
                        <Button asChild variant="secondary" className="gap-2">
                          <label htmlFor="sefaz-certificado-file" className="cursor-pointer">
                            <Upload className="h-4 w-4" />
                            Selecionar certificado
                          </label>
                        </Button>
                        <span className="text-sm text-slate-400">
                          {data.certificadoFile ? data.certificadoFile.name : 'Nenhum arquivo selecionado.'}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="sefaz-certificado-senha" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                        Senha do certificado
                      </Label>
                      <Input
                        id="sefaz-certificado-senha"
                        type="password"
                        value={data.certificadoSenha}
                        onChange={(event) => data.setCertificadoSenha(event.target.value)}
                        autoComplete="off"
                        className="h-11 border-slate-700/80 bg-slate-950/60 text-slate-100 shadow-none focus-visible:ring-sky-400/70"
                      />
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                      <Button
                        type="button"
                        onClick={data.uploadCertificado}
                        disabled={data.certificadoUploadPending || !data.certificadoFile || !data.certificadoSenha.trim()}
                        className="gap-2"
                      >
                        {data.certificadoUploadPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
                        {data.certificadoUploadPending ? 'Enviando...' : 'Salvar certificado'}
                      </Button>
                      <p className="text-xs text-slate-400">O arquivo fica associado ao CNPJ logado e o backend valida a extensao e o tamanho.</p>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-slate-800/70 bg-slate-900/55">
                  <CardHeader>
                    <CardTitle className="text-lg">Status do certificado</CardTitle>
                    <CardDescription>Validade, dias restantes e condicao atual.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {data.statusQuery.isLoading ? (
                      <div className="space-y-3">
                        <div className="h-9 animate-pulse rounded-xl bg-slate-800/70" />
                        <div className="h-20 animate-pulse rounded-2xl bg-slate-800/70" />
                      </div>
                    ) : certificateState ? (
                      <>
                        <div className="flex items-center gap-3">
                          <Badge variant={certificateState.badgeVariant}>{certificateState.label}</Badge>
                          <span className="text-sm text-slate-300">{certificateState.description}</span>
                        </div>

                        <div className="grid gap-3 md:grid-cols-2">
                          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Validade</p>
                            <p className="mt-2 text-sm text-slate-100">{formatOnlyDate(data.statusQuery.data?.data_validade ?? null)}</p>
                          </div>
                          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Dias restantes</p>
                            <p className="mt-2 text-sm text-slate-100">
                              {data.statusQuery.data?.dias_restantes ?? 'Nao informado'}
                            </p>
                          </div>
                        </div>

                        {data.statusQuery.data?.cnpj_titular ? (
                          <Alert className="border-slate-700/80 bg-slate-950/70 text-slate-100">
                            <CertificateIcon className="h-4 w-4" />
                            <AlertDescription>
                              Certificado vinculado ao CNPJ {data.statusQuery.data.cnpj_titular}.
                            </AlertDescription>
                          </Alert>
                        ) : null}

                        {data.statusQuery.data?.dias_restantes !== null &&
                        data.statusQuery.data?.dias_restantes !== undefined &&
                        data.statusQuery.data.dias_restantes < CERTIFICADO_WARNING_DAYS &&
                        data.statusQuery.data.ativo ? (
                          <Alert className="border-amber-500/30 bg-amber-500/10 text-amber-100">
                            <CalendarDays className="h-4 w-4" />
                            <AlertDescription>O certificado vence em menos de 30 dias. Vale revisar a renovacao.</AlertDescription>
                          </Alert>
                        ) : null}
                      </>
                    ) : (
                      <div className="rounded-2xl border border-dashed border-slate-800/80 bg-slate-950/40 p-4 text-sm text-slate-400">
                        Nenhum certificado configurado ainda.
                      </div>
                    )}

                    <Separator className="bg-slate-800/80" />

                    <div className="flex flex-wrap items-center gap-3">
                      <Button type="button" onClick={data.syncNow} disabled={syncDisabled} className="gap-2">
                        {data.sincronizandoAgora ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCcw className="h-4 w-4" />}
                        {syncButtonLabel}
                      </Button>
                      {certificadoInativo ? (
                        <span className="text-sm text-slate-400">A sincronizacao depende de um certificado ativo.</span>
                      ) : syncCooldownActive ? (
                        <span className="text-sm text-slate-400">
                          A ultima sincronizacao trouxe notas. Nova tentativa em {formatCooldown(data.syncCooldownSeconds)}.
                        </span>
                      ) : null}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="documentos" className="mt-5 space-y-5">
              <Card className="border-slate-800/70 bg-slate-900/55">
                <CardHeader>
                  <CardTitle className="text-lg">Filtros</CardTitle>
                  <CardDescription>Refine a listagem por direcao, periodo, situacao e pendencia de manifestacao.</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 lg:grid-cols-5">
                  <div className="space-y-2">
                    <Label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">Direcao</Label>
                    <Select value={data.documentoFilters.direcao} onValueChange={(value) => data.setDocumentoFilters.setDirecao(value as typeof data.documentoFilters.direcao)}>
                      <SelectTrigger>
                        <SelectValue placeholder="Todas" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="todas">Todas</SelectItem>
                        <SelectItem value="emitidas">Emitidas</SelectItem>
                        <SelectItem value="recebidas">Recebidas</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">Situacao</Label>
                    <Select value={data.documentoFilters.situacao} onValueChange={(value) => data.setDocumentoFilters.setSituacao(value as typeof data.documentoFilters.situacao)}>
                      <SelectTrigger>
                        <SelectValue placeholder="Todas" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="todas">Todas</SelectItem>
                        <SelectItem value="autorizada">Autorizada</SelectItem>
                        <SelectItem value="cancelada">Cancelada</SelectItem>
                        <SelectItem value="denegada">Denegada</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">Manifestacao</Label>
                    <Select
                      value={data.documentoFilters.manifestacaoPendente}
                      onValueChange={(value) => data.setDocumentoFilters.setManifestacaoPendente(value as typeof data.documentoFilters.manifestacaoPendente)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Todas" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="todas">Todas</SelectItem>
                        <SelectItem value="sim">Pendente</SelectItem>
                        <SelectItem value="nao">Nao pendente</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="sefaz-data-inicio" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                      Data inicial
                    </Label>
                    <Input id="sefaz-data-inicio" type="date" value={data.documentoFilters.dataInicio} onChange={(event) => data.setDocumentoFilters.setDataInicio(event.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="sefaz-data-fim" className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-300">
                      Data final
                    </Label>
                    <div className="flex gap-2">
                      <Input id="sefaz-data-fim" type="date" value={data.documentoFilters.dataFim} onChange={(event) => data.setDocumentoFilters.setDataFim(event.target.value)} />
                      <Button type="button" variant="outline" onClick={data.setDocumentoFilters.clear}>
                        Limpar
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-slate-800/70 bg-slate-900/55">
                <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
                  <div>
                    <CardTitle className="text-lg">Documentos fiscais</CardTitle>
                    <CardDescription>
                      {data.documentosQuery.isLoading
                        ? 'Carregando documentos...'
                        : `${data.documentosQuery.data?.total ?? 0} documento(s) encontrados.`}
                    </CardDescription>
                  </div>
                  <Button type="button" variant="outline" onClick={() => void data.refreshAll()}>
                    Recarregar
                  </Button>
                </CardHeader>
                <CardContent className="space-y-4">
                  {data.documentosQuery.isError ? (
                    <Alert variant="destructive">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>{data.documentosQuery.error.message}</AlertDescription>
                    </Alert>
                  ) : null}

                  {data.documentosQuery.isLoading ? (
                    <div className="space-y-3">
                      <div className="h-12 animate-pulse rounded-xl bg-slate-800/70" />
                      <div className="h-12 animate-pulse rounded-xl bg-slate-800/70" />
                      <div className="h-12 animate-pulse rounded-xl bg-slate-800/70" />
                    </div>
                  ) : documentosPaginated.length ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Chave de acesso</TableHead>
                          <TableHead>Direcao</TableHead>
                          <TableHead>Emitente</TableHead>
                          <TableHead>Destinatario</TableHead>
                          <TableHead>Emissao</TableHead>
                          <TableHead>Valor</TableHead>
                          <TableHead>Situacao</TableHead>
                          <TableHead>Manifestacao</TableHead>
                          <TableHead>Fiscal</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {documentosPaginated.map((documento) => (
                          <TableRow
                            key={documento.id}
                            className="cursor-pointer"
                            onClick={() => data.setSelectedDocumentoId(documento.id)}
                          >
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{truncateKey(documento.chave_acesso)}</span>
                                <Button
                                  type="button"
                                  size="icon"
                                  variant="ghost"
                                  className="h-8 w-8"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    void handleCopyKey(documento.chave_acesso);
                                  }}
                                >
                                  <Copy className="h-4 w-4" />
                                </Button>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge variant={documento.direcao === 'recebida' ? 'warning' : 'secondary'}>
                                {getDirecaoLabel(documento.direcao)}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-sm text-slate-300">{documento.cnpj_emitente}</TableCell>
                            <TableCell className="text-sm text-slate-300">{documento.cnpj_destinatario || 'Nao informado'}</TableCell>
                            <TableCell>{formatOnlyDate(documento.data_emissao)}</TableCell>
                            <TableCell>{formatCurrency(documento.valor_total)}</TableCell>
                            <TableCell>
                              <Badge variant={getDocumentoSituacaoBadge(documento.situacao)}>{getDocumentoSituacaoLabel(documento.situacao)}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant={getManifestacaoBadge(documento.manifestacao_status)}>
                                {getManifestacaoLabel(documento.manifestacao_status)}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant={getFiscalBadge(documento)}>{getFiscalLabel(documento)}</Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <div className="rounded-2xl border border-dashed border-slate-800/80 bg-slate-950/40 p-6 text-sm text-slate-400">
                      Nenhum documento encontrado com os filtros atuais.
                    </div>
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm text-slate-400">
                      Pagina {data.documentosPage} de {data.totalDocumentosPages}
                    </p>
                    <div className="flex items-center gap-2">
                      <Button type="button" variant="outline" onClick={() => data.setDocumentosPage(Math.max(1, data.documentosPage - 1))} disabled={data.documentosPage <= 1}>
                        Anterior
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => data.setDocumentosPage(Math.min(data.totalDocumentosPages, data.documentosPage + 1))}
                        disabled={data.documentosPage >= data.totalDocumentosPages}
                      >
                        Proxima
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="historico" className="mt-5 space-y-5">
              <Card className="border-slate-800/70 bg-slate-900/55">
                <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
                  <div>
                    <CardTitle className="text-lg">Historico de sincronizacao</CardTitle>
                    <CardDescription>Execucoes manuais e automáticas do sincronizador SEFAZ.</CardDescription>
                  </div>
                  <Button type="button" variant="outline" onClick={() => void data.refreshAll()}>
                    Recarregar
                  </Button>
                </CardHeader>
                <CardContent className="space-y-4">
                  {data.syncLogQuery.isError ? (
                    <Alert variant="destructive">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>{data.syncLogQuery.error.message}</AlertDescription>
                    </Alert>
                  ) : null}

                  {data.syncLogQuery.isLoading ? (
                    <div className="space-y-3">
                      <div className="h-12 animate-pulse rounded-xl bg-slate-800/70" />
                      <div className="h-12 animate-pulse rounded-xl bg-slate-800/70" />
                      <div className="h-12 animate-pulse rounded-xl bg-slate-800/70" />
                    </div>
                  ) : syncLogPaginated.length ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Inicio</TableHead>
                          <TableHead>Fim</TableHead>
                          <TableHead>Novos docs</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Detalhe</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {syncLogPaginated.map((item: SefazSyncLog) => (
                          <TableRow key={item.id}>
                            <TableCell>{formatDate(item.iniciado_em)}</TableCell>
                            <TableCell>{formatDate(item.finalizado_em)}</TableCell>
                            <TableCell>{item.documentos_novos}</TableCell>
                            <TableCell>
                              <Badge
                                variant={
                                  item.status === 'sucesso'
                                    ? 'default'
                                    : item.status === 'erro'
                                      ? 'destructive'
                                      : 'warning'
                                }
                              >
                                {item.status}
                              </Badge>
                            </TableCell>
                            <TableCell className="max-w-[360px]">
                              {item.erro_detalhe ? (
                                <p className="truncate text-sm text-slate-300">{item.erro_detalhe}</p>
                              ) : (
                                <span className="text-sm text-slate-500">Sem erro</span>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <div className="rounded-2xl border border-dashed border-slate-800/80 bg-slate-950/40 p-6 text-sm text-slate-400">
                      Nenhum historico de sincronizacao encontrado.
                    </div>
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm text-slate-400">
                      Pagina {data.syncLogPage} de {data.totalSyncLogPages}
                    </p>
                    <div className="flex items-center gap-2">
                      <Button type="button" variant="outline" onClick={() => data.setSyncLogPage(Math.max(1, data.syncLogPage - 1))} disabled={data.syncLogPage <= 1}>
                        Anterior
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => data.setSyncLogPage(Math.min(data.totalSyncLogPages, data.syncLogPage + 1))}
                        disabled={data.syncLogPage >= data.totalSyncLogPages}
                      >
                        Proxima
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <Dialog open={Boolean(selectedDocumento)} onOpenChange={(open) => !open && data.setSelectedDocumentoId(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle>Detalhe do documento</DialogTitle>
            <DialogDescription>
              Informacoes completas do documento SEFAZ selecionado e acoes de manifestacao, quando disponiveis.
            </DialogDescription>
          </DialogHeader>

          {data.documentoDetalheQuery.isLoading ? (
            <div className="space-y-3">
              <div className="h-10 animate-pulse rounded-xl bg-slate-800/70" />
              <div className="h-24 animate-pulse rounded-xl bg-slate-800/70" />
            </div>
          ) : data.documentoDetalheQuery.isError ? (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{data.documentoDetalheQuery.error.message}</AlertDescription>
            </Alert>
          ) : selectedDocumento ? (
            <div className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Chave de acesso</p>
                  <p className="mt-2 break-all text-sm text-slate-100">{selectedDocumento.chave_acesso}</p>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">NSU</p>
                  <p className="mt-2 text-sm text-slate-100">{selectedDocumento.nsu}</p>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Emitente</p>
                  <p className="mt-2 text-sm text-slate-100">{selectedDocumento.cnpj_emitente}</p>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Destinatario</p>
                  <p className="mt-2 text-sm text-slate-100">{selectedDocumento.cnpj_destinatario || 'Nao informado'}</p>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Situacao</p>
                  <p className="mt-2 text-sm text-slate-100">{getDocumentoSituacaoLabel(selectedDocumento.situacao)}</p>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Manifestacao</p>
                  <p className="mt-2 text-sm text-slate-100">{getManifestacaoLabel(selectedDocumento.manifestacao_status)}</p>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Valor total</p>
                  <p className="mt-2 text-sm text-slate-100">{formatCurrency(selectedDocumento.valor_total)}</p>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Emissao</p>
                  <p className="mt-2 text-sm text-slate-100">{formatDate(selectedDocumento.data_emissao)}</p>
                </div>
                <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Tipo / Direcao</p>
                  <p className="mt-2 text-sm text-slate-100">
                    {selectedDocumento.tipo_documento} - {getDirecaoLabel(selectedDocumento.direcao)}
                  </p>
                </div>
              </div>

              {selectedDocumento.xml_armazenado_base64 ? (
                <div className="space-y-3 rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">XML armazenado</p>
                      <p className="mt-1 text-sm text-slate-300">A visualizacao abaixo vem do XML em base64 retornado pelo backend.</p>
                    </div>
                    <Button type="button" variant="outline" className="gap-2" onClick={handleDownloadXml}>
                      <Download className="h-4 w-4" />
                      Baixar XML
                    </Button>
                  </div>
                  <Textarea readOnly value={xmlPreview ?? 'Nao foi possivel decodificar o XML.'} className="min-h-64 border-slate-700/80 bg-slate-950/70 font-mono text-xs text-slate-100" />
                </div>
              ) : (
                <Alert>
                  <FileText className="h-4 w-4" />
                  <AlertDescription>Este documento nao possui XML armazenado no backend.</AlertDescription>
                </Alert>
              )}

              {selectedDocumento.manifestacao_status === 'pendente' && selectedDocumento.direcao === 'recebida' ? (
                <div className="space-y-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4">
                  <div>
                    <p className="text-sm font-semibold text-amber-100">Manifestacao pendente</p>
                    <p className="text-sm text-amber-100/80">Escolha uma das acoes abaixo. Depois vamos pedir confirmacao antes de enviar.</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {manifestacaoActions.map((action) => (
                      <Button
                        key={action.tipo}
                        type="button"
                        variant="outline"
                        className="border-amber-500/30 bg-slate-950/40 text-amber-100 hover:bg-amber-500/15"
                        onClick={() => data.setManifestacaoPendenteConfirmacao({ documentoId: selectedDocumento.id, tipo: action.tipo })}
                        disabled={data.manifestandoDocumento}
                      >
                        {action.label}
                      </Button>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="rounded-2xl border border-slate-800/70 bg-slate-950/55 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Observacao</p>
                <p className="mt-2 text-sm text-slate-300">
                  O backend atual nao expõe historico de eventos no detalhe do documento. Se essa informacao for
                  necessaria, precisamos de um endpoint adicional.
                </p>
              </div>
            </div>
          ) : null}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => data.setSelectedDocumentoId(null)}>
              Fechar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(data.manifestacaoPendenteConfirmacao)}
        onOpenChange={(open) => !open && data.setManifestacaoPendenteConfirmacao(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirmar manifestacao?</DialogTitle>
            <DialogDescription>
              Essa acao gera evento fiscal. Confirme apenas se voce tiver certeza do tipo de manifestacao.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => data.setManifestacaoPendenteConfirmacao(null)}>
              Cancelar
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={data.manifestandoDocumento}
              onClick={async () => {
                await data.confirmarManifestacao();
              }}
            >
              {data.manifestandoDocumento ? 'Enviando...' : 'Confirmar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
