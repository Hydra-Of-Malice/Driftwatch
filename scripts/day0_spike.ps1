# Day-0 spike (Windows PowerShell): verify the real Bright Data Scraper Studio lifecycle
# end-to-end on a toy page BEFORE the hackathon clock starts.
#
#   powershell -ExecutionPolicy Bypass -File scripts\day0_spike.ps1
#
# Needs Node >= 20 (installs @brightdata/cli if missing). Reads BRIGHTDATA_API_KEY from the
# environment or from the repo's .env. Exercises create -> run -> heal -> approval gate ->
# approve -> run, saving every JSON envelope to scripts\spike_out\. Cost: ~4 free credits.
#
# NOTE on the two CLI names: the @brightdata/cli npm package ships BOTH `brightdata` and
# `bdata` in its `bin` map, pointing at the same dist/index.js. `bdata` is an ALIAS, not a
# different tool - so when an envelope's `next_step` field prints `bdata scraper run ...`,
# that is this same CLI, and `brightdata scraper run ...` is interchangeable with it.
#
# This is the raw evidence-capture spike: it keeps going and prints what the vendor said.
# For the staged pass/fail/blocked version with a CI-usable exit code, see
# scripts\live_smoke_test.ps1.

# Deliberately NOT "Stop": a non-zero CLI exit still writes a JSON error envelope, and that
# envelope is the whole point of this spike. Aborting on it would throw away the evidence.
$ErrorActionPreference = "Continue"

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

# Envelope statuses that mean "the vendor refused / could not complete". These are real
# @brightdata/cli 0.3.x statuses (ai_trigger_failed on a 403 "Automation not allowed",
# heal_trigger_failed on a 503 "Self healing tool is temporarily disabled"). Reporting them
# by name beats dying opaquely on a $null collector_id three lines later.
$failedStatuses = @('failed','error','cancelled','ai_trigger_failed','heal_trigger_failed',
                    'resume_failed','stub_only')

function Show-Envelope {
  # Print what the vendor actually said for one saved envelope; return $true if it is healthy.
  param([string]$Label, [string]$Path)
  if (-not (Test-Path $Path)) {
    Write-Host "   ! $Label produced no envelope at $Path" -ForegroundColor Yellow
    return $false
  }
  $raw = Get-Content $Path -Raw
  $doc = $null
  try { $doc = $raw | ConvertFrom-Json } catch {
    Write-Host "   ! $Label wrote non-JSON output:" -ForegroundColor Yellow
    Write-Host "     $($raw.Trim())"
    return $false
  }
  $status = ''
  $err    = ''
  if ($doc -is [psobject]) {
    if ($doc.PSObject.Properties['status']) { $status = [string]$doc.status }
    if ($doc.PSObject.Properties['error'])  { $err    = [string]$doc.error }
  }
  if ($err -or ($status -and ($failedStatuses -contains $status))) {
    Write-Host "   ! $Label BLOCKED by Bright Data: status='$status' error='$err'" -ForegroundColor Yellow
    Write-Host "     (envelope kept at $Path - this is evidence, not a script bug)" -ForegroundColor Yellow
    return $false
  }
  Write-Host "   $Label ok (status='$status')" -ForegroundColor Green
  return $true
}

Write-Host "1/5 create (Scraper Studio AI Flow - takes a few minutes)..."
brightdata scraper create $url `
  "Extract the book title, price as a number, availability text as unit_context, and star rating" `
  --name driftwatch-spike -o "$out\create.json"
$createOk = Show-Envelope "create" "$out\create.json"

$collector = $null
if (Test-Path "$out\create.json") {
  try { $collector = (Get-Content "$out\create.json" -Raw | ConvertFrom-Json).collector_id } catch { }
}
if (-not $collector) {
  # No id at all means there is nothing the remaining four steps could address.
  throw "create returned no collector_id - inspect $out\create.json"
}
Write-Host "   collector: $collector"
if (-not $createOk) {
  Write-Host "   NOTE: the collector exists but its template was never AI-generated." -ForegroundColor Yellow
  Write-Host "   Steps 2-5 will therefore report 'Collector does not have a template'." -ForegroundColor Yellow
  Write-Host "   That is the downstream symptom, not a separate bug. Continuing to capture it." -ForegroundColor Yellow
}

Write-Host "2/5 run..."
brightdata scraper run $collector $url -o "$out\run1.json"
Show-Envelope "run1" "$out\run1.json" | Out-Null

Write-Host "3/5 heal (stops at the approval gate - inspect preview_result in heal.json)..."
brightdata scraper heal $collector `
  "Price returns a string with currency symbol; it must be a plain number. Keep all other fields." `
  --url $url -o "$out\heal.json"
Show-Envelope "heal" "$out\heal.json" | Out-Null

Write-Host "4/5 approve..."
# `--url` IS a valid flag on `scraper approve` - verified against
# `brightdata scraper approve --help` on @brightdata/cli 0.3.5. It is not the approval
# target; it only weaves the verify URL into the `next_step` hint the envelope returns.
brightdata scraper approve $collector --url $url -o "$out\approve.json"
Show-Envelope "approve" "$out\approve.json" | Out-Null

Write-Host "5/5 verify run..."
brightdata scraper run $collector $url -o "$out\run2.json"
Show-Envelope "run2" "$out\run2.json" | Out-Null

Write-Host ""
Write-Host "Done. Envelopes in $out"
Write-Host "Paste the contents of create.json and heal.json back to your coding agent to confirm"
Write-Host "driftwatch_engine/brightdata/envelopes.py matches your CLI version."
