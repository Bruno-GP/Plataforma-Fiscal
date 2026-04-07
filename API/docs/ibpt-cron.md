# Sincronização automática do IBPT

## Comando para o servidor

Use o comando abaixo para sincronizar todas as UFs sem depender de chamada HTTP:

```bash
cd /caminho/da/API
python scripts/sync_ibpt.py --todas-ufs
```

Esse comando:

- consulta a API do IBPT para todas as UFs
- grava em `ncm_catalogo` e `ncm_tributacao`
- ignora updates quando os dados recebidos são iguais aos já salvos

## Exemplo de cron

Para rodar a cada 24 horas, sempre às 03:00:

```cron
0 3 * * * cd /caminho/da/API && /usr/bin/python3 scripts/sync_ibpt.py --todas-ufs >> /var/log/plataforma-fiscal-ibpt.log 2>&1
```

## Observações

- se o servidor usar `venv`, prefira o binário absoluto do ambiente virtual
- se quiser mudar o horário, basta ajustar a expressão do cron
- se o banco ou a API externa estiverem indisponíveis, o cron registrará falha no log
