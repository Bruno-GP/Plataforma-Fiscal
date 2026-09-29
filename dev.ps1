<#
Atalho para subir a plataforma local sem digitar caminho/comando.

Uso (de qualquer pasta):
  .\dev.ps1 api        # API FastAPI (uvicorn --reload)
  .\dev.ps1 painel     # Painel Vite (npm run dev)
  .\dev.ps1 nfe        # worker Celery fila nfe
  .\dev.ps1 sped       # worker Celery fila sped
  .\dev.ps1 all        # API + Painel, cada um em janela propria
  .\dev.ps1 migrate    # alembic upgrade head
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet('api', 'painel', 'nfe', 'sped', 'conta_azul', 'sefaz', 'beat', 'all', 'migrate')]
    [string]$Alvo = 'all'
)

$Raiz = $PSScriptRoot
$Api = Join-Path $Raiz 'API'
$Painel = Join-Path $Raiz 'Painel'
$Scripts = Join-Path $Api '.venv-local\Scripts'

function Invoke-Alvo([string]$nome) {
    switch ($nome) {
        'api' { Set-Location $Api; & (Join-Path $Scripts 'uvicorn.exe') app.main:app --reload }
        'painel' { Set-Location $Painel; npm run dev }
        'migrate' { Set-Location $Api; & (Join-Path $Scripts 'alembic.exe') -c app/alembic.ini upgrade head }
        'beat' { Set-Location $Api; & (Join-Path $Scripts 'celery.exe') -A app.workers.celery_app beat --loglevel=info }
        default { Set-Location $Api; & (Join-Path $Scripts 'celery.exe') -A app.workers.celery_app worker --loglevel=info --pool=solo -Q $nome }
    }
}

if ($Alvo -eq 'all') {
    foreach ($n in 'api', 'painel') {
        Start-Process powershell -ArgumentList '-NoExit', '-File', "`"$PSCommandPath`"", $n
    }
} else {
    Invoke-Alvo $Alvo
}
