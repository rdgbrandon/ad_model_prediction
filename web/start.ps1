$workspacePath = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $workspacePath '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create the workspace virtual environment and install sases_eval/requirements-rerun.txt first.'
}
& $pythonPath (Join-Path $PSScriptRoot 'server.py')
