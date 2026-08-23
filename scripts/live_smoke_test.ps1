<#
.SYNOPSIS
  DriftWatch LIVE smoke test - proves how far the real Bright Data path actually gets.

.DESCRIPTION
  Staged, fail-soft validation of the live vendor path used by
  backend/driftwatch_engine/brightdata/live.py. Every stage runs inside its own
  try/catch and reports PASS / FAIL / BLOCKED / SKIPPED, so a failure early on
  never hides what the later stages would have said.

  The point of the staging is diagnostic precision. "Bright Data doesn't work" is
  useless; "auth is fine, Web Unlocker retrieves data, AI discovery is live, and
  exactly one endpoint (automate_template) is refused 403 by the vendor" is
  actionable. The exit code encodes that distinction:

      0  every stage passed
      1  OUR fault   - CLI missing, auth broken, malformed handling, script error
      2  VENDOR block - a documented refusal we cannot fix client-side
                        (403 "Automation not allowed" / 503 "Self healing tool is
                        temporarily disabled" / AI-Flow concurrent-job cap)

  CI can therefore tell "we regressed" apart from "the vendor is still refusing".

.PARAMETER Url
  Target page. Defaults to books.toscrape.com - a public sandbox published by
  Zyte/Scrapinghub for the express purpose of being scraped ("We love being
  scraped!"), so no ToS is strained by running this repeatedly.

.PARAMETER Zone
  Web Unlocker zone name. Omitted => auto-picked as the first zone of type
  `unblocker` returned by stage 2.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\live_smoke_test.ps1

.NOTES
  Cost: stages 3-5 consume a few Bright Data credits.
  Reads BRIGHTDATA_API_KEY from the environment or the repo .env. The key is
  never echoed, logged, or written to any output file.
#>

[CmdletBinding()]
param(
  # Public, scraping-sanctioned sandbox site (Zyte's books.toscrape.com demo).
  [string]$Url  = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  [string]$Zone = ""
)

# A non-zero exit from a native command must NOT abort the run - the whole value
# of this script is that stage N+1 still reports after stage N fails. 'Continue'
# also stops PowerShell from turning CLI stderr chatter (spinners, "Scraping...")
# into a terminating NativeCommandError when we redirect stream 2.
$ErrorActionPreference = 'Continue'
$ProgressPreference    = 'SilentlyContinue'

# ---------------------------------------------------------------------------
# Credentials: env first, repo .env second. Same loader idiom as day0_spike.ps1.
# HARD RULE: the key is never printed. Only its presence is ever reported.
# ---------------------------------------------------------------------------
$repoRoot  = Split-Path $PSScriptRoot -Parent
$envFile   = Join-Path $repoRoot ".env"
$keySource = "environment"
if (-not $env:BRIGHTDATA_API_KEY -and (Test-Path $envFile)) {
  $keySource = ".env"
  Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
      [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim().Trim('"'))
    }
  }
}
if (-not $env:BRIGHTDATA_API_KEY) {
  Write-Host "FATAL: BRIGHTDATA_API_KEY is not set." -ForegroundColor Red
  Write-Host "  Export it, or add BRIGHTDATA_API_KEY=<key> to $envFile" -ForegroundColor Red
  Write-Host "  (issue a token at https://brightdata.com/cp/setting/users)" -ForegroundColor Red
  exit 1
}

$OutDir = Join-Path $PSScriptRoot "smoke_out"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# ---------------------------------------------------------------------------
# Result ledger
# ---------------------------------------------------------------------------
$script:StageLedger = New-Object System.Collections.Generic.List[object]

function Add-Result {
  param(
    [string]$Stage,
    [ValidateSet('PASS','FAIL','BLOCKED','SKIPPED')][string]$Status,
    [string]$Detail
  )
  $color = switch ($Status) {
    'PASS'    { 'Green' }
    'FAIL'    { 'Red' }
    'BLOCKED' { 'Yellow' }
    default   { 'DarkGray' }
  }
  Write-Host ("  [{0,-7}] {1} :: {2}" -f $Status, $Stage, $Detail) -ForegroundColor $color
  $script:StageLedger.Add([pscustomobject]@{ Stage = $Stage; Status = $Status; Detail = $Detail })
}

function Write-Banner {
  param([string]$Text)
  Write-Host ""
  Write-Host $Text -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# Vendor-refusal taxonomy.
#
# Mirrors VENDOR_ERROR_SIGNATURES in backend/driftwatch_engine/errors.py. These
# are strings Bright Data has actually returned to this account; each one is a
# refusal by the vendor, NOT a bug in this repo, so it must never be reported as
# a script failure - and never as a pass either.
# ---------------------------------------------------------------------------
$VendorSignatures = @(
  @{ Match = 'automation not allowed'
     Cause = 'HTTP 403 "Automation not allowed" from POST /dca/collectors/<id>/automate_template'
     Hint  = 'Account-level feature entitlement, NOT token scope. Verified 2026-08-23 by controlled experiment: an Admin-permission token lifts the 403 on /customer/balance but not on automate_template, so re-issuing the token does not help. The collector is still created and usable - only the AI generation step is withheld. Bright Data must enable Scraper Studio automation for this account.' },
  @{ Match = 'self healing tool is temporarily disabled'
     Cause = 'HTTP 503 "Self healing tool is temporarily disabled" from POST /dca/collectors/<id>/refactor_template'
     Hint  = 'Server-side feature flag, global. Not an account or credential problem; no client change can lift it. Retry when Bright Data re-enables the endpoint.' },
  @{ Match = 'lacks the required permissions'
     Cause = 'HTTP 403 - API token is under-scoped for this endpoint'
     Hint  = 'Re-issue the token with the required permissions at https://brightdata.com/cp/setting/users.' },
  @{ Match = 'automation not found'
     Cause = 'No automation job to resume (resume_automation_job)'
     Hint  = 'Downstream of a heal that never started. Expected when heal itself was refused.' },
  @{ Match = 'collector does not have a template'
     Cause = 'Collector exists but its template is still a stub - AI generation never ran'
     Hint  = 'Downstream symptom of a blocked automate_template trigger, not a run failure.' },
  @{ Match = 'cannot run more than'
     Cause = 'AI-Flow concurrent-job cap (HTTP 429)'
     Hint  = 'Serialise `scraper create` calls, or let the CLI back off (--max-retries).' }
)

# Envelope statuses that mean "the vendor refused". Kept in sync with
# FAILED_STATUSES in brightdata/live.py.
$VendorBlockedStatuses = @('ai_trigger_failed','heal_trigger_failed','resume_failed','stub_only')

function Get-VendorBlock {
  # Returns a hashtable {Cause;Hint;Evidence;Status} when the CLI result carries a
  # documented vendor refusal, else $null. Anything not matched here is our problem.
  param($Result)

  $evidence = ''
  $status   = ''
  if ($null -ne $Result.Json -and $Result.Json -is [psobject]) {
    $errProp = $Result.Json.PSObject.Properties['error']
    if ($errProp -and $errProp.Value) { $evidence = [string]$errProp.Value }
    $stProp = $Result.Json.PSObject.Properties['status']
    if ($stProp -and $stProp.Value) { $status = [string]$stProp.Value }
  }
  $haystack = ($evidence + ' ' + [string]$Result.StdErr).ToLowerInvariant()

  foreach ($sig in $VendorSignatures) {
    if ($haystack.Contains($sig.Match)) {
      $ev = $evidence
      if (-not $ev) { $ev = $sig.Match }
      return @{ Cause = $sig.Cause; Hint = $sig.Hint; Evidence = $ev; Status = $status }
    }
  }
  if ($status -and ($VendorBlockedStatuses -contains $status)) {
    $ev = $evidence
    if (-not $ev) { $ev = $status }
    return @{
      Cause    = "vendor envelope status '$status'"
      Hint     = 'The CLI reached Bright Data but the AI job never started. Check https://brightdata.com/cp/scrapers.'
      Evidence = $ev
      Status   = $status
    }
  }
  return $null
}

# ---------------------------------------------------------------------------
# CLI transport
# ---------------------------------------------------------------------------
$script:Cli = $null

function Resolve-BdCli {
  # `bdata` is an ALIAS for `brightdata`: @brightdata/cli ships both names in its
  # npm `bin` map, pointing at the same dist/index.js. Either is fine.
  # Prefer the .cmd shim over the .ps1 shim so stream-2 redirection behaves.
  foreach ($name in @('brightdata','bdata')) {
    $all = @(Get-Command $name -All -ErrorAction SilentlyContinue)
    if ($all.Count -eq 0) { continue }
    $pick = $all | Where-Object { $_.CommandType -eq 'Application' -and $_.Source -like '*.cmd' } | Select-Object -First 1
    if (-not $pick) { $pick = $all | Where-Object { $_.CommandType -eq 'Application' } | Select-Object -First 1 }
    if (-not $pick) { $pick = $all[0] }
    return $pick
  }
  return $null
}

function Invoke-Bd {
  # Runs the CLI, capturing stdout (pure JSON) and stderr (human progress) apart.
  # Never throws on a non-zero exit: the JSON error envelope on stdout is the
  # richest diagnostic the vendor gives us and callers must get to inspect it.
  param(
    [Parameter(Mandatory=$true)][string[]]$BdArgs,
    [string]$SaveAs = ''
  )
  $errFile = Join-Path ([System.IO.Path]::GetTempPath()) ("bd_{0}.err" -f ([guid]::NewGuid().ToString('N')))
  $stdout  = ''
  $code    = -1
  try {
    $stdout = (& $script:Cli @BdArgs 2> $errFile | Out-String)
    $code   = $LASTEXITCODE
  } catch {
    $stdout = ''
    $code   = -1
  }
  $stderr = ''
  if (Test-Path -LiteralPath $errFile) {
    $stderr = [string](Get-Content -LiteralPath $errFile -Raw -ErrorAction SilentlyContinue)
    Remove-Item -LiteralPath $errFile -Force -ErrorAction SilentlyContinue
  }

  $savedPath = ''
  if ($SaveAs) {
    $savedPath = Join-Path $OutDir $SaveAs
    # UTF8 without BOM so the saved envelopes stay machine-readable evidence.
    [System.IO.File]::WriteAllText($savedPath, $stdout, (New-Object System.Text.UTF8Encoding($false)))
  }

  $json = $null
  if ($stdout.Trim()) {
    try { $json = $stdout | ConvertFrom-Json } catch { $json = $null }
  }

  return [pscustomobject]@{
    ExitCode = $code
    StdOut   = $stdout
    StdErr   = $stderr
    Json     = $json
    SavedAs  = $savedPath
  }
}

function Get-CliMessage {
  # Pull the vendor's own sentence out of the CLI's human-readable stderr.
  param($Result)
  if ($null -ne $Result.Json -and $Result.Json -is [psobject]) {
    $errProp = $Result.Json.PSObject.Properties['error']
    if ($errProp -and $errProp.Value) { return [string]$errProp.Value }
  }
  # The CLI prints a three-line block: "Error: <what>", "Status: <http>",
  # "Hint: <what to do>". Keep the what and the what-to-do together.
  $what = ''
  $hint = ''
  $http = ''
  foreach ($line in ([string]$Result.StdErr -split "`r?`n")) {
    $t = $line.Trim()
    if (-not $what -and $t -match '(?i)^[^A-Za-z0-9]*error:\s*(.+)$')  { $what = $matches[1].Trim(); continue }
    if (-not $http -and $t -match '(?i)^[^A-Za-z0-9]*status:\s*(\d{3})') { $http = $matches[1]; continue }
    if (-not $hint -and $t -match '(?i)^[^A-Za-z0-9]*hint:\s*(.+)$')   { $hint = $matches[1].Trim(); continue }
  }
  if ($what) {
    $msg = $what
    if ($http) { $msg += " (HTTP $http)" }
    if ($hint) { $msg += " | $hint" }
    return $msg
  }
  $tail = ([string]$Result.StdErr -split "`r?`n" | Where-Object { $_.Trim() } | Select-Object -Last 1)
  if ($tail) { return $tail.Trim() }
  return "CLI exited $($Result.ExitCode) with no diagnostic output"
}

function Get-FirstRecord {
  # Mirrors live.py::_first_record - normalise `scraper run` output to one record.
  param($Json)
  if ($null -eq $Json) { return $null }
  if ($Json -is [System.Array]) {
    foreach ($item in $Json) {
      if ($item -is [psobject] -and @($item.PSObject.Properties).Count -gt 0) { return $item }
    }
    return $null
  }
  if ($Json -is [psobject]) {
    foreach ($key in @('data','results','records')) {
      $prop = $Json.PSObject.Properties[$key]
      if (-not $prop) { continue }
      $inner = $prop.Value
      if ($inner -is [System.Array]) {
        foreach ($item in $inner) {
          if ($item -is [psobject] -and @($item.PSObject.Properties).Count -gt 0) { return $item }
        }
      } elseif ($inner -is [psobject] -and @($inner.PSObject.Properties).Count -gt 0) {
        return $inner
      }
    }
    if (@($Json.PSObject.Properties).Count -gt 0) { return $Json }
  }
  return $null
}

function Get-Snippet {
  param([string]$Text, [int]$Max = 120)
  if (-not $Text) { return '' }
  $t = ($Text -replace '\s+', ' ').Trim()
  if ($t.Length -le $Max) { return $t }
  return $t.Substring(0, $Max) + '...'
}

# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "DriftWatch live smoke test" -ForegroundColor White
Write-Host "  target : $Url"
Write-Host "  key    : present (loaded from $keySource; value never printed)"
Write-Host "  output : $OutDir"

$zoneName  = $Zone
$collector = $null
$createdOk = $false

# --- Stage 1: CLI present ---------------------------------------------------
Write-Banner "Stage 1/6 - Bright Data CLI present"
try {
  $cmd = Resolve-BdCli
  if (-not $cmd) {
    Add-Result 'cli' 'FAIL' 'brightdata/bdata not on PATH - run: npm i -g @brightdata/cli'
  } else {
    if ($cmd.Source) { $script:Cli = $cmd.Source } else { $script:Cli = $cmd.Name }
    $verOut  = (& $script:Cli --version 2>&1 | Out-String).Trim()
    $verCode = $LASTEXITCODE
    $version = ($verOut -split "`r?`n" | Where-Object { $_ -match '\d+\.\d+\.\d+' } | Select-Object -First 1)
    if ($verCode -ne 0 -or -not $version) {
      Add-Result 'cli' 'FAIL' ("--version exited $verCode : " + (Get-Snippet $verOut))
    } else {
      Add-Result 'cli' 'PASS' ("@brightdata/cli " + $version.Trim() + " at " + $script:Cli)
    }
  }
} catch {
  Add-Result 'cli' 'FAIL' ("script error: " + $_.Exception.Message)
}

$cliOk = @($script:StageLedger | Where-Object { $_.Stage -eq 'cli' -and $_.Status -eq 'PASS' }).Count -gt 0

# --- Stage 2: auth + zone read ---------------------------------------------
Write-Banner "Stage 2/6 - auth + zone read (brightdata zones --json)"
$zonesOk = $false
if (-not $cliOk) {
  Add-Result 'auth.zones' 'SKIPPED' 'no CLI'
} else {
  try {
    $r     = Invoke-Bd -BdArgs @('zones','--json') -SaveAs 'zones.json'
    $block = Get-VendorBlock $r
    $zones = @()
    if ($r.Json -is [System.Array]) {
      $zones = @($r.Json)
    } elseif ($r.Json -is [psobject] -and $r.Json.PSObject.Properties['zones']) {
      $zones = @($r.Json.zones)
    }

    if ($r.ExitCode -ne 0 -or $zones.Count -eq 0) {
      $msg = Get-CliMessage $r
      if ($block) {
        Add-Result 'auth.zones' 'BLOCKED' ($block.Cause + ' | ' + $block.Hint)
      } elseif ($msg -match '(?i)invalid credentials|unauthorized|HTTP 401|invalid or expired') {
        # A rejected key is ours to fix (rotate/re-issue), not a vendor refusal:
        # it must exit 1, never 2, or CI would shrug it off as "vendor again".
        Add-Result 'auth.zones' 'FAIL' ("BRIGHTDATA_API_KEY rejected (HTTP 401) - the key in " +
          "$keySource is invalid, expired, or revoked. Issue a new token at " +
          "https://brightdata.com/cp/setting/users (or run ``brightdata login``) and update .env.")
      } else {
        Add-Result 'auth.zones' 'FAIL' ("could not list zones: " + (Get-Snippet $msg))
      }
    } else {
      $zonesOk = $true
      $desc = ($zones | ForEach-Object { "$($_.name)[$($_.type)]" }) -join ', '
      Add-Result 'auth.zones' 'PASS' ("key authenticates; $($zones.Count) zone(s): $desc")
      if (-not $zoneName) {
        $pick = $zones | Where-Object { "$($_.type)" -eq 'unblocker' } | Select-Object -First 1
        if ($pick) { $zoneName = $pick.name }
      }
    }
  } catch {
    Add-Result 'auth.zones' 'FAIL' ("script error: " + $_.Exception.Message)
  }
}

# --- Stage 3: Web Unlocker fetch -------------------------------------------
Write-Banner "Stage 3/6 - Web Unlocker fetch (brightdata scrape)"
if (-not $zonesOk) {
  Add-Result 'unlocker.scrape' 'SKIPPED' 'no authenticated zone list'
} elseif (-not $zoneName) {
  Add-Result 'unlocker.scrape' 'FAIL' 'no zone of type unblocker on this account; pass -Zone <name> or create one'
} else {
  try {
    $r     = Invoke-Bd -BdArgs @('scrape', $Url, '--zone', $zoneName, '--json') -SaveAs 'scrape.json'
    $block = Get-VendorBlock $r
    # `scrape --json` with the default markdown format returns a JSON *string*.
    $content = ''
    if ($r.Json -is [string]) {
      $content = $r.Json
    } elseif ($r.Json -is [psobject]) {
      foreach ($k in @('body','content','data','html','markdown')) {
        $p = $r.Json.PSObject.Properties[$k]
        if ($p -and $p.Value) { $content = [string]$p.Value; break }
      }
    }
    if ($r.ExitCode -ne 0 -or -not $content.Trim()) {
      if ($block) {
        Add-Result 'unlocker.scrape' 'BLOCKED' ($block.Cause + ' | ' + $block.Hint)
      } else {
        Add-Result 'unlocker.scrape' 'FAIL' ("zone '$zoneName': " + (Get-Snippet (Get-CliMessage $r)))
      }
    } else {
      Add-Result 'unlocker.scrape' 'PASS' ("zone '$zoneName' retrieved $($content.Length) chars of live page content")
    }
  } catch {
    Add-Result 'unlocker.scrape' 'FAIL' ("script error: " + $_.Exception.Message)
  }
}

# --- Stage 4: AI discovery --------------------------------------------------
Write-Banner "Stage 4/6 - AI discovery (brightdata discover)"
if (-not $cliOk) {
  Add-Result 'discover' 'SKIPPED' 'no CLI'
} else {
  try {
    $r = Invoke-Bd -BdArgs @(
      'discover', 'SaaS pricing pages with published per-seat prices',
      '--intent', 'vendor pricing page listing plan tiers and numeric prices',
      '--num-results', '5', '--timeout', '240', '--json'
    ) -SaveAs 'discover.json'
    $block   = Get-VendorBlock $r
    $discovered = @()
    if ($r.Json -is [psobject] -and $r.Json.PSObject.Properties['results']) {
      $discovered = @($r.Json.results)
    } elseif ($r.Json -is [System.Array]) {
      $discovered = @($r.Json)
    }

    if ($r.ExitCode -ne 0) {
      if ($block) {
        Add-Result 'discover' 'BLOCKED' ($block.Cause + ' | ' + $block.Hint)
      } else {
        Add-Result 'discover' 'FAIL' (Get-Snippet (Get-CliMessage $r))
      }
    } elseif ($discovered.Count -eq 0) {
      # Exit 0 with an empty `results` array is a contract break, not a refusal.
      Add-Result 'discover' 'FAIL' 'discover returned exit 0 but an empty results array (envelope contract broken)'
    } else {
      $top   = $discovered[0]
      $link  = if ($top.PSObject.Properties['link']) { $top.link } else { $top.url }
      $score = if ($top.PSObject.Properties['relevance_score']) { $top.relevance_score } else { $top.score }
      Add-Result 'discover' 'PASS' ("$($discovered.Count) ranked result(s); top=$link score=$score")
    }
  } catch {
    Add-Result 'discover' 'FAIL' ("script error: " + $_.Exception.Message)
  }
}

# --- Stage 5: scraper create (AI Flow) --------------------------------------
Write-Banner "Stage 5/6 - Scraper Studio AI Flow (brightdata scraper create)"
if (-not $cliOk) {
  Add-Result 'scraper.create' 'SKIPPED' 'no CLI'
} else {
  try {
    $name = "driftwatch-smoke-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
    $desc = "Extract the book title, price as a number, availability text as unit_context, and star rating"
    Write-Host "  (AI generation can take several minutes when it is permitted)" -ForegroundColor DarkGray
    $r = Invoke-Bd -BdArgs @(
      'scraper','create', $Url, $desc, '--name', $name,
      '--timeout','420','--max-retries','1','--json'
    ) -SaveAs 'create.json'

    if ($r.Json -is [psobject] -and $r.Json.PSObject.Properties['collector_id'] -and $r.Json.collector_id) {
      $collector = [string]$r.Json.collector_id
      Write-Host "  collector_id: $collector" -ForegroundColor DarkGray
    }
    $block  = Get-VendorBlock $r
    $status = ''
    if ($r.Json -is [psobject] -and $r.Json.PSObject.Properties['status']) { $status = [string]$r.Json.status }

    if ($block) {
      # Documented vendor refusal. NOT a script bug, and emphatically not a pass.
      $detail = $block.Cause
      if ($collector) { $detail += " (collector $collector was created, template left a stub)" }
      $detail += " | VENDOR SAID: '" + $block.Evidence + "' | REMEDIATION: " + $block.Hint
      Add-Result 'scraper.create' 'BLOCKED' $detail
    } elseif ($r.ExitCode -ne 0) {
      Add-Result 'scraper.create' 'FAIL' (Get-Snippet (Get-CliMessage $r))
    } elseif (-not $collector) {
      Add-Result 'scraper.create' 'FAIL' 'exit 0 but no collector_id in the envelope (envelope contract broken)'
    } else {
      $createdOk = $true
      Add-Result 'scraper.create' 'PASS' "collector $collector status='$status'"
    }
  } catch {
    Add-Result 'scraper.create' 'FAIL' ("script error: " + $_.Exception.Message)
  }
}

# --- Stage 6: run -> heal -> approve -> verify ------------------------------
# Only meaningful on a collector with a real generated template. Running these
# against a stub collector would only re-report the create block as four more
# failures, which is noise, not evidence.
Write-Banner "Stage 6/6 - run -> heal -> approve -> verify re-run"
if (-not $createdOk) {
  foreach ($s in @('scraper.run','scraper.heal','scraper.approve','scraper.verify')) {
    Add-Result $s 'SKIPPED' 'no usable collector from stage 5'
  }
} else {
  $runOk = $false

  # 6a - baseline run
  try {
    $r      = Invoke-Bd -BdArgs @('scraper','run',$collector,$Url,'--timeout','420','--json') -SaveAs 'run1.json'
    $block  = Get-VendorBlock $r
    $record = Get-FirstRecord $r.Json
    if ($block) {
      Add-Result 'scraper.run' 'BLOCKED' ($block.Cause + ' | ' + $block.Hint)
    } elseif ($r.ExitCode -ne 0) {
      Add-Result 'scraper.run' 'FAIL' (Get-Snippet (Get-CliMessage $r))
    } elseif ($null -eq $record) {
      # HTTP 200 is not an outcome: an empty run is a scraper failure.
      Add-Result 'scraper.run' 'FAIL' 'run returned no structured record (an empty payload is a failure, not a green run)'
    } else {
      $runOk  = $true
      $fields = (@($record.PSObject.Properties.Name) -join ',')
      Add-Result 'scraper.run' 'PASS' ("structured record with fields: " + (Get-Snippet $fields))
    }
  } catch {
    Add-Result 'scraper.run' 'FAIL' ("script error: " + $_.Exception.Message)
  }

  # 6b - heal
  $healOk = $false
  if (-not $runOk) {
    Add-Result 'scraper.heal' 'SKIPPED' 'baseline run did not produce a record'
  } else {
    try {
      $prompt = "Price returns a string with a currency symbol; it must be a plain number. Keep all other fields."
      $r = Invoke-Bd -BdArgs @('scraper','heal',$collector,$prompt,'--url',$Url,'--timeout','420','--max-retries','1','--json') -SaveAs 'heal.json'
      $block = Get-VendorBlock $r
      if ($block) {
        Add-Result 'scraper.heal' 'BLOCKED' ($block.Cause + ' | REMEDIATION: ' + $block.Hint)
      } elseif ($r.ExitCode -ne 0) {
        Add-Result 'scraper.heal' 'FAIL' (Get-Snippet (Get-CliMessage $r))
      } else {
        $healOk = $true
        $st = 'unknown'
        if ($r.Json -is [psobject] -and $r.Json.PSObject.Properties['status']) { $st = [string]$r.Json.status }
        Add-Result 'scraper.heal' 'PASS' "heal envelope status='$st' (approval gate reached)"
      }
    } catch {
      Add-Result 'scraper.heal' 'FAIL' ("script error: " + $_.Exception.Message)
    }
  }

  # 6c - approve
  $approveOk = $false
  if (-not $healOk) {
    Add-Result 'scraper.approve' 'SKIPPED' 'no heal awaiting approval'
  } else {
    try {
      # --url is a real flag on `scraper approve` (verified against
      # `brightdata scraper approve --help`, @brightdata/cli 0.3.5): it only
      # weaves the verify target into the returned next_step hint.
      $r     = Invoke-Bd -BdArgs @('scraper','approve',$collector,'--url',$Url,'--timeout','420','--json') -SaveAs 'approve.json'
      $block = Get-VendorBlock $r
      if ($block) {
        Add-Result 'scraper.approve' 'BLOCKED' ($block.Cause + ' | ' + $block.Hint)
      } elseif ($r.ExitCode -ne 0) {
        Add-Result 'scraper.approve' 'FAIL' (Get-Snippet (Get-CliMessage $r))
      } else {
        $approveOk = $true
        $st = 'unknown'
        if ($r.Json -is [psobject] -and $r.Json.PSObject.Properties['status']) { $st = [string]$r.Json.status }
        Add-Result 'scraper.approve' 'PASS' "approve envelope status='$st'"
      }
    } catch {
      Add-Result 'scraper.approve' 'FAIL' ("script error: " + $_.Exception.Message)
    }
  }

  # 6d - verification re-run on the SAME collector id
  if (-not $approveOk) {
    Add-Result 'scraper.verify' 'SKIPPED' 'nothing approved to verify'
  } else {
    try {
      $r      = Invoke-Bd -BdArgs @('scraper','run',$collector,$Url,'--timeout','420','--json') -SaveAs 'run2.json'
      $block  = Get-VendorBlock $r
      $record = Get-FirstRecord $r.Json
      if ($block) {
        Add-Result 'scraper.verify' 'BLOCKED' ($block.Cause + ' | ' + $block.Hint)
      } elseif ($r.ExitCode -ne 0) {
        Add-Result 'scraper.verify' 'FAIL' (Get-Snippet (Get-CliMessage $r))
      } elseif ($null -eq $record) {
        Add-Result 'scraper.verify' 'FAIL' "verification re-run on $collector returned no record"
      } else {
        $fields = (@($record.PSObject.Properties.Name) -join ',')
        Add-Result 'scraper.verify' 'PASS' ("same collector $collector re-ran; fields: " + (Get-Snippet $fields))
      }
    } catch {
      Add-Result 'scraper.verify' 'FAIL' ("script error: " + $_.Exception.Message)
    }
  }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
$rule = ('=' * 100)
Write-Host ""
Write-Host $rule -ForegroundColor DarkGray
Write-Host "SUMMARY" -ForegroundColor White
Write-Host $rule -ForegroundColor DarkGray
Write-Host ("{0,-18} {1,-8} {2}" -f 'STAGE','STATUS','DETAIL')
Write-Host ("{0,-18} {1,-8} {2}" -f ('-' * 18), ('-' * 8), ('-' * 60))
foreach ($row in $script:StageLedger) {
  $color = switch ($row.Status) {
    'PASS'    { 'Green' }
    'FAIL'    { 'Red' }
    'BLOCKED' { 'Yellow' }
    default   { 'DarkGray' }
  }
  Write-Host ("{0,-18} {1,-8} {2}" -f $row.Stage, $row.Status, $row.Detail) -ForegroundColor $color
}
Write-Host $rule -ForegroundColor DarkGray
Write-Host "Envelopes saved to $OutDir"

$fails   = @($script:StageLedger | Where-Object { $_.Status -eq 'FAIL' })
$blocked = @($script:StageLedger | Where-Object { $_.Status -eq 'BLOCKED' })

Write-Host ""
if ($fails.Count -gt 0) {
  Write-Host "RESULT: $($fails.Count) stage(s) failed for reasons that are OURS to fix." -ForegroundColor Red
  foreach ($f in $fails) { Write-Host "  - $($f.Stage): $($f.Detail)" -ForegroundColor Red }
  if ($blocked.Count -gt 0) {
    Write-Host "  ($($blocked.Count) further stage(s) were vendor-blocked - see above.)" -ForegroundColor Yellow
  }
  Write-Host "exit 1 (our fault)" -ForegroundColor Red
  exit 1
}
if ($blocked.Count -gt 0) {
  Write-Host "RESULT: VENDOR BLOCK. Everything under our control passed." -ForegroundColor Yellow
  Write-Host "The stage(s) below were refused by Bright Data, not by this repo:" -ForegroundColor Yellow
  foreach ($b in $blocked) { Write-Host "  - $($b.Stage): $($b.Detail)" -ForegroundColor Yellow }
  Write-Host "This is NOT a script failure, and NOT a passing run." -ForegroundColor Yellow
  Write-Host "exit 2 (vendor block)" -ForegroundColor Yellow
  exit 2
}
Write-Host "RESULT: all stages passed against the live Bright Data API." -ForegroundColor Green
Write-Host "exit 0" -ForegroundColor Green
exit 0
