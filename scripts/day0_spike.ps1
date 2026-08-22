# Day-0 spike (Windows PowerShell): verify the real Bright Data Scraper Studio lifecycle
# end-to-end on a toy page BEFORE the hackathon clock starts.
#
#   powershell -ExecutionPolicy Bypass -File scripts\day0_spike.ps1
#
# Needs Node >= 20 (installs @brightdata/cli if missing). Reads BRIGHTDATA_API_KEY from the
# environment or from the repo's .env. Exercises create -> run -> heal -> approval gate ->
# approve -> run, saving every JSON envelope to scripts\spike_out\. Cost: ~4 free credits.

$ErrorActionPreference = "Stop"

# Load .env if the key isn't already exported (repo root = parent of this scripts dir).
$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) ".env"
if (-not $env:BRIGHTDATA_API_KEY -and (Test-Path $envFile)) {
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
      [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim().Trim('"'))
    }
  }
}
if (-not $env:BRIGHTDATA_API_KEY) { throw "BRIGHTDATA_API_KEY not set (env or .env)" }

if (-not (Get-Command brightdata -ErrorAction SilentlyContinue)) {
  Write-Host "Installing @brightdata/cli..."
  npm i -g "@brightdata/cli"
}

$out = Join-Path $PSScriptRoot "spike_out"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$url = if ($env:SPIKE_URL) { $env:SPIKE_URL }
       else { "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html" }

Write-Host "1/5 create (Scraper Studio AI Flow - takes a few minutes)..."
brightdata scraper create $url `
  "Extract the book title, price as a number, availability text as unit_context, and star rating" `
  --name driftwatch-spike -o "$out\create.json"
$collector = (Get-Content "$out\create.json" -Raw | ConvertFrom-Json).collector_id
Write-Host "   collector: $collector"

Write-Host "2/5 run..."
brightdata scraper run $collector $url -o "$out\run1.json"

Write-Host "3/5 heal (stops at the approval gate - inspect preview_result in heal.json)..."
brightdata scraper heal $collector `
  "Price returns a string with currency symbol; it must be a plain number. Keep all other fields." `
  --url $url -o "$out\heal.json"

Write-Host "4/5 approve..."
try { brightdata scraper approve $collector --url $url -o "$out\approve.json" }
catch { Write-Host "   (approve returned non-zero - check approve.json / control panel)" }

Write-Host "5/5 verify run..."
brightdata scraper run $collector $url -o "$out\run2.json"

Write-Host ""
Write-Host "Done. Envelopes in $out"
Write-Host "Paste the contents of create.json and heal.json back to your coding agent to confirm"
Write-Host "driftwatch_engine/brightdata/envelopes.py matches your CLI version."
