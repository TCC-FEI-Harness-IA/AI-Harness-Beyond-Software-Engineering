# Compilador do TCC.tex com suporte a SVG (via Inkscape) e bibliografia (biber)
# Uso: ./compilar.ps1

$env:PATH = $env:PATH + ";C:\Program Files\Inkscape\bin"

Write-Host "==> Passagem 1: pdflatex (gera .aux e converte SVGs)" -ForegroundColor Cyan
pdflatex -shell-escape -interaction=nonstopmode TCC.tex
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) { Write-Host "ERRO na passagem 1" -ForegroundColor Red; exit 1 }

Write-Host "`n==> Rodando Biber (bibliografia)" -ForegroundColor Cyan
biber TCC
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) { Write-Host "ERRO no Biber" -ForegroundColor Red; exit 1 }

Write-Host "`n==> Passagem 2: pdflatex (resolve referencias)" -ForegroundColor Cyan
pdflatex -shell-escape -interaction=nonstopmode TCC.tex
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) { Write-Host "ERRO na passagem 2" -ForegroundColor Red; exit 1 }

Write-Host "`n==> Passagem 3: pdflatex (finaliza cross-references)" -ForegroundColor Cyan
pdflatex -shell-escape -interaction=nonstopmode TCC.tex
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) { Write-Host "ERRO na passagem 3" -ForegroundColor Red; exit 1 }

Write-Host "`n[OK] Compilacao concluida! PDF gerado: TCC.pdf" -ForegroundColor Green

# Abre o PDF automaticamente
if (Test-Path "TCC.pdf") {
    Start-Process "TCC.pdf"
}
