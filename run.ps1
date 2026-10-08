cd D:\_USER_FOLDERS\Documents\GitHub\hermes-agent

$dev = 'D:\_USER_FOLDERS\Documents\GitHub\.hermes-orchestration-dev'
$node = 'C:\Users\MAKSIDZE\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$env:PATH = "$(Split-Path $node);$env:PATH"

$env:HERMES_DESKTOP_HERMES_ROOT = "$PWD"
$env:HERMES_DESKTOP_PYTHON = "$dev\graph-env\Scripts\python.exe"
$env:HERMES_HOME = "$dev\app-home"
$env:HERMES_DESKTOP_USER_DATA_DIR = "$dev\desktop-data"
$env:HERMES_RUNTIME_DIR = "$dev\runtime"
$env:TEMP = $dev
$env:TMP = $dev
$env:npm_config_cache = "$dev\npm-cache"
$env:electron_config_cache = "$dev\electron-cache"

& $node apps\desktop\node_modules\electron\install.js
npm --prefix apps/desktop run dev
