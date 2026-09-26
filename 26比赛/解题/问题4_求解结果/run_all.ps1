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
    & $Q4Runtime (Join-Path $Q4Root 'code\precooling.py')
    if ($LASTEXITCODE -ne 0) { throw 'Precooling failed.' }
    & $Q4Runtime (Join-Path $Q4Root 'code\reoptimize_controls.py')
    if ($LASTEXITCODE -ne 0) { throw 'Feedback search failed.' }
    & $Q4Runtime (Join-Path $Q4Root 'code\compare_constant_pareto.py')
    if ($LASTEXITCODE -ne 0) { throw 'Constant-power search failed.' }
}
& $Q4Runtime (Join-Path $Q4Root 'code\run_problem4.py') --reuse-controls
if ($LASTEXITCODE -ne 0) { throw 'Main numerical solve failed.' }
& $Q4Runtime (Join-Path $Q4Root 'code\compare_constant_pareto.py') --reuse-controls
if ($LASTEXITCODE -ne 0) { throw 'Frozen constant-control reproduction failed.' }
if ($Reoptimize) {
    & $Q4Runtime (Join-Path $Q4Root 'code\robust_design.py')
} else {
    & $Q4Runtime (Join-Path $Q4Root 'code\robust_design.py') --reuse-controls
}
if ($LASTEXITCODE -ne 0) { throw 'Guarded controller stage failed.' }
foreach ($Q4Script in @('compare_robustness.py','observer_examples.py','refine_convergence.py','normalize_event_fields.py','verify_model.py','verify_exports.py','verify_revision.py','finalize_tables.py','plot_results.py','build_report.py','verify_delivery.py')) {
    & $Q4Runtime (Join-Path $Q4Root ('code\' + $Q4Script))
    if ($LASTEXITCODE -ne 0) { throw ('Stage failed: ' + $Q4Script) }
}
Write-Host 'Q4 results, checks, tables and figures regenerated.'
