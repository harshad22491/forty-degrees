# FortyDegrees task runner — executes the recommend or research prompt via Codex CLI.
# Usage:  .\run.ps1 recommend    (fortnightly pick + email; needs RESEND_API_KEY)
#         .\run.ps1 research     (weekly catalog growth)
param(
    [ValidateSet("recommend", "research")]
    [string]$task = "recommend"
)

Set-Location $PSScriptRoot
git pull -q

if ($task -eq "recommend" -and -not $env:RESEND_API_KEY) {
    Write-Host "RESEND_API_KEY is not set. Set it once with:" -ForegroundColor Yellow
    Write-Host '  setx RESEND_API_KEY "re_your_key_here"   (then open a NEW terminal)'
    exit 1
}

$prompt = Get-Content (Join-Path "prompts" ($task + ".md")) -Raw
codex exec --sandbox workspace-write -c sandbox_workspace_write.network_access=true $prompt
