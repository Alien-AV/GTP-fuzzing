param(
    [Parameter(Mandatory = $true)]
    [string]$Summary,

    [string]$ClientBase = "GTPv2_CreateSessionRequest.xml",
    [string]$ServerBase = "GTPv2_CreateSessionResponse.xml"
)

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$ledgerPath = Join-Path $workspaceRoot "gtp_mts_fuzz_iterations.log"

$maxId = 0
if (Test-Path $ledgerPath) {
    foreach ($line in Get-Content $ledgerPath) {
        if ($line -match 'iter-(\d{4})') {
            $value = [int]$Matches[1]
            if ($value -gt $maxId) {
                $maxId = $value
            }
        }
    }
}

$nextId = $maxId + 1
$iterationId = "iter-{0:d4}" -f $nextId
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"
$entry = "$timestamp $iterationId $Summary"
Add-Content -Path $ledgerPath -Value $entry

$clientName = "codex_{0}_{1}" -f $iterationId, $ClientBase
$serverName = "codex_{0}_{1}" -f $iterationId, $ServerBase

Write-Output "ITERATION_ID=$iterationId"
Write-Output "LEDGER_FILE=$ledgerPath"
Write-Output "LEDGER_ENTRY=$entry"
Write-Output "CLIENT_XML=$clientName"
Write-Output "SERVER_XML=$serverName"
Write-Output "REMOTE_CLIENT_DIR=~/mts/tutorial/gtp/load/Release13/codex_fuzz/client"
Write-Output "REMOTE_SERVER_DIR=~/mts/tutorial/gtp/load/Release13/codex_fuzz/server"
