param(
    [string]$AsOf = '2022-01-03T23:00:00+00:00',
    [string]$DiscoveryPolicy = '',
    [string]$PortfolioPolicy = ''
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$refreshArguments = @('run', 'baghunter', 'demo', '--asof', $AsOf)
if ($DiscoveryPolicy) { $refreshArguments += @('--policy', $DiscoveryPolicy) }
if ($PortfolioPolicy) { $refreshArguments += @('--portfolio-policy', $PortfolioPolicy) }
& uv @refreshArguments
if ($LASTEXITCODE -ne 0) { throw "Fixture refresh failed ($LASTEXITCODE)" }
# Manual template: registers no task and requests no provider data.
