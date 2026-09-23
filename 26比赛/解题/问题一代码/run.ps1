# 在本机使用已准备好的 Python 3.12 环境。脚本位置可含中文和空格。
# 其他电脑可先 pip install -r requirements.txt，再 python run_question1.py。
$taskPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskPython = (Get-Command python -ErrorAction Stop).Source
}
& $taskPython -X utf8 (Join-Path $PSScriptRoot 'run_question1.py') @args
exit $LASTEXITCODE
