param([switch]$Reoptimize)
$ErrorActionPreference = 'Stop'
$Q4Root = $PSScriptRoot
$Q4Runtime = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $Q4Runtime)) {
    $Q4Command = Get-Command python -ErrorAction SilentlyContinue
    if (-not $Q4Command) { throw 'Python 3.12+ is required. Install the packages in requirements.txt first.' }
    $Q4Runtime = $Q4Command.Source
}
$env:PYTHONUTF8 = '1'
$env:MPLCONFIGDIR = Join-Path $Q4Root '.mplconfig'
if ($Reoptimize) {
    & $Q4Runtime (Join-Path $Q4Root 'code\run_problem4.py')
} else {
    & $Q4Runtime (Join-Path $Q4Root 'code\run_problem4.py') --reuse-controls
}
if ($LASTEXITCODE -ne 0) { throw 'Main numerical solve failed.' }
foreach ($Q4Script in @('robust_design.py','refine_convergence.py','verify_model.py','verify_exports.py','finalize_tables.py','plot_results.py','build_report.py','verify_delivery.py')) {
    & $Q4Runtime (Join-Path $Q4Root ('code\' + $Q4Script))
    if ($LASTEXITCODE -ne 0) { throw ('Stage failed: ' + $Q4Script) }
}
Write-Host 'Q4 results, checks, tables and figures regenerated.'
