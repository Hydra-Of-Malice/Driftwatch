<#
.SYNOPSIS
    Deterministic break-and-heal demonstration for DriftWatch, driven entirely
    from the terminal over the backend's HTTP API. No clicking.

.DESCRIPTION
    Walks the full autonomous repair loop against the controlled mirror world:

        1. baseline extraction verified green
        2. controlled break introduced (mirror variant -> v2_redesign)
        3. run triggered; contract verification FAILS; failing gates shown
        4. the machine-composed heal prompt shown
        5. the heal preview re-verified against the FULL contract (4 gates)
        6. the approval decision + template version bump shown
        7. re-run; data restored
        8. the world is restored to the baseline variant (always, incl. on failure)

    HONESTY NOTE. This script demonstrates the repair loop in REPLAY mode.
    Bright Data's self-healing endpoint (POST /dca/collectors/{id}/refactor_template)
    currently returns HTTP 503 "Self healing tool is temporarily disabled" -- a
    server-side global feature disable, not an account problem. The vendor
    TRANSPORT is therefore replayed. Everything this script prints -- prompt
    composition, the four verification gates, the three-band approval policy,
    the version pin, the audit ledger -- is the real production code path.
    See docs/LIVE_VALIDATION.md for the raw evidence, and docs/DEMO_SCRIPT.md
    for the presenter script.

.PARAMETER BaseUrl
    Target an already-running backend (e.g. http://localhost:8000). When omitted
    the script probes localhost:8000 and, if nothing answers, starts its own
    backend against a throwaway database and shuts it down afterwards.

.EXAMPLE
    powershell -NoProfile -File scripts\heal_demo.ps1

.EXAMPLE
    powershell -NoProfile -File scripts\heal_demo.ps1 -BaseUrl http://localhost:8000
#>

[CmdletBinding()]
param(
    [string] $BaseUrl,
    [string] $SourceId        = 'nimbusai-pricing',
    [string] $BaselineVariant = 'v1_baseline',
    [string] $BreakVariant    = 'v2_redesign',
    [int]    $Port            = 8000,
    [int]    $StartupTimeoutSeconds = 45
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# presentation helpers
# ---------------------------------------------------------------------------

$script:StepNumber = 0

function Write-Rule {
    Write-Host ('-' * 78) -ForegroundColor DarkGray
}

function Write-Step {
    param([string] $Title)
    $script:StepNumber++
    Write-Host ''
    Write-Rule
    Write-Host ("STEP {0}. {1}" -f $script:StepNumber, $Title) -ForegroundColor Cyan
    Write-Rule
}

function Write-Say {
    param([string] $Text)
    Write-Host ("  > {0}" -f $Text) -ForegroundColor Gray
}

function Write-Fact {
    param([string] $Label, $Value, [string] $Color = 'White')
    Write-Host ("    {0,-24} " -f ($Label + ':')) -NoNewline
    Write-Host $Value -ForegroundColor $Color
}

function Write-Cmd {
    param([string] $Text)
    Write-Host ("    $ {0}" -f $Text) -ForegroundColor DarkCyan
}

function Write-Ok {
    param([string] $Text)
    Write-Host ("    [OK]   {0}" -f $Text) -ForegroundColor Green
}

function Write-Bad {
    param([string] $Text)
    Write-Host ("    [FAIL] {0}" -f $Text) -ForegroundColor Red
}

function Stop-Demo {
    param([string] $Message)
    throw ("DEMO CHECK FAILED: {0}" -f $Message)
}

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

function Invoke-Api {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [string] $Method = 'GET',
        $Body,
        [int] $TimeoutSec = 120
    )
    $uri = "$script:Api$Path"
    $req = @{ Uri = $uri; Method = $Method; TimeoutSec = $TimeoutSec }
    if ($null -ne $Body) {
        $req['Body']        = ($Body | ConvertTo-Json -Depth 10 -Compress)
        $req['ContentType'] = 'application/json'
    }
    if ($script:ApiToken) {
        $req['Headers'] = @{ Authorization = "Bearer $script:ApiToken" }
    }
    return Invoke-RestMethod @req
}

function Test-Backend {
    param([string] $Root)
    try {
        $headers = @{}
        if ($script:ApiToken) { $headers['Authorization'] = "Bearer $script:ApiToken" }
        $null = Invoke-RestMethod -Uri "$Root/api/stats" -TimeoutSec 3 -Headers $headers
        return $true
    } catch {
        return $false
    }
}

# ---------------------------------------------------------------------------
# payload helpers
# ---------------------------------------------------------------------------

function Show-Gates {
    param($Verdict, [string] $Caption)
    if ($null -eq $Verdict) {
        Write-Host '    (no verdict recorded)' -ForegroundColor DarkYellow
        return @()
    }
    if ($Caption) { Write-Host ("    {0}" -f $Caption) -ForegroundColor White }
    $failed = @()
    $ordered = @('schema', 'invariants', 'semantics', 'continuity')
    foreach ($name in $ordered) {
        $gate = $Verdict.gates | Where-Object { $_.gate -eq $name } | Select-Object -First 1
        if ($null -eq $gate) {
            Write-Host ("      {0,-12} (not evaluated)" -f $name) -ForegroundColor DarkYellow
            continue
        }
        if ($gate.passed) {
            Write-Host ("      {0,-12} PASS" -f $gate.gate) -ForegroundColor Green
        } else {
            $failed += $gate.gate
            Write-Host ("      {0,-12} FAIL" -f $gate.gate) -ForegroundColor Red
            foreach ($d in (@($gate.details) | Select-Object -First 3)) {
                Write-Host ("                     - {0}" -f $d) -ForegroundColor DarkRed
            }
        }
    }
    $verdictWord = if ($Verdict.passed) { 'PASSED' } else { 'FAILED' }
    $verdictColor = if ($Verdict.passed) { 'Green' } else { 'Red' }
    Write-Host ("      composite    {0}  (confidence {1})" -f $verdictWord, $Verdict.confidence) -ForegroundColor $verdictColor
    return $failed
}

function Show-Models {
    param($Payload, [string] $Caption)
    if ($Caption) { Write-Host ("    {0}" -f $Caption) -ForegroundColor White }
    if ($null -eq $Payload -or $null -eq $Payload.models) {
        Write-Host '      (no models in payload)' -ForegroundColor DarkYellow
        return
    }
    Write-Host ("      {0,-18} {1,10} {2,11}  {3}" -f 'model_id', 'in/1M', 'out/1M', 'unit_context') -ForegroundColor DarkGray
    foreach ($m in $Payload.models) {
        $inp  = if ($null -eq $m.price_input_per_1m)  { 'null' } else { $m.price_input_per_1m }
        $outp = if ($null -eq $m.price_output_per_1m) { 'null' } else { $m.price_output_per_1m }
        $unit = if ($null -eq $m.unit_context)        { 'null' } else { $m.unit_context }
        $color = if ($null -eq $m.price_input_per_1m) { 'Red' } else { 'Green' }
        Write-Host ("      {0,-18} {1,10} {2,11}  {3}" -f $m.model_id, $inp, $outp, $unit) -ForegroundColor $color
    }
}

function Get-NullPriceCount {
    param($Payload)
    if ($null -eq $Payload -or $null -eq $Payload.models) { return -1 }
    return @($Payload.models | Where-Object { $null -eq $_.price_input_per_1m }).Count
}

function Write-Wrapped {
    param([string] $Text, [int] $Width = 72, [string] $Indent = '      ')
    if ([string]::IsNullOrWhiteSpace($Text)) {
        Write-Host ("{0}(empty)" -f $Indent) -ForegroundColor DarkYellow
        return
    }
    $line = ''
    foreach ($word in ($Text -split '\s+')) {
        if (($line.Length + $word.Length + 1) -gt $Width) {
            Write-Host ("{0}{1}" -f $Indent, $line) -ForegroundColor Yellow
            $line = $word
        } else {
            $line = if ($line) { "$line $word" } else { $word }
        }
    }
    if ($line) { Write-Host ("{0}{1}" -f $Indent, $line) -ForegroundColor Yellow }
}

# ---------------------------------------------------------------------------
# banner -- the very first line states replay mode, per the honesty rule
# ---------------------------------------------------------------------------

$mode = if ($env:DW_MODE) { $env:DW_MODE.Trim().ToLower() } else { 'replay' }

if ($mode -eq 'replay') {
    Write-Host 'RUNNING IN REPLAY MODE: the Bright Data transport is replayed against the controlled mirror world. The heal logic below is the real production code path; only the vendor call is replayed.' -ForegroundColor Yellow
} else {
    Write-Host ("RUNNING IN '{0}' MODE." -f $mode) -ForegroundColor Yellow
}
Write-Host ''
Write-Host '  DriftWatch -- autonomous break-and-heal demonstration' -ForegroundColor White
Write-Host ''
Write-Host '  Why replay: Bright Data self-healing (POST /dca/collectors/{id}/refactor_template)' -ForegroundColor DarkGray
Write-Host '  currently answers HTTP 503 "Self healing tool is temporarily disabled" -- a' -ForegroundColor DarkGray
Write-Host '  server-side global feature disable, not an account problem. Live-provable today:' -ForegroundColor DarkGray
Write-Host '  auth, zones, Web Unlocker retrieval, POST /dca/collector (real c_* ids), discover.' -ForegroundColor DarkGray
Write-Host '  Raw evidence: docs/LIVE_VALIDATION.md   Presenter script: docs/DEMO_SCRIPT.md' -ForegroundColor DarkGray
Write-Host ''

if ($mode -ne 'replay') {
    Write-Host ''
    Write-Bad ("DW_MODE={0}. This script is the REPLAY demonstration and refuses to pretend" -f $mode)
    Write-Bad '       a live heal happened: the vendor heal endpoint returns HTTP 503 today.'
    Write-Bad '       Unset DW_MODE (or set DW_MODE=replay) and re-run.'
    exit 2
}

# ---------------------------------------------------------------------------
# resolve / start the backend
# ---------------------------------------------------------------------------

$repoRoot        = Split-Path -Parent $PSScriptRoot
$script:ApiToken = $env:DW_API_TOKEN
$startedServer   = $null
$tempDb          = $null
$serverLog       = $null
$serverErr       = $null
$attached        = $false
$exitCode        = 0
$script:BackendReady = $false

try {
    if ($BaseUrl) {
        $script:Api = $BaseUrl.TrimEnd('/')
        if (-not (Test-Backend $script:Api)) {
            Stop-Demo ("no DriftWatch backend answered at {0}/api/stats" -f $script:Api)
        }
        $attached = $true
    } else {
        $script:Api = "http://localhost:$Port"
        if (Test-Backend $script:Api) {
            $attached = $true
        }
    }

    if ($attached) {
        Write-Host ("  Using the DriftWatch backend already running at {0}" -f $script:Api) -ForegroundColor DarkGray
        Write-Host '  NOTE: that process may already carry demo state from an earlier run. If the' -ForegroundColor DarkGray
        Write-Host '  break below does not break, restart the backend for a clean demonstration.' -ForegroundColor DarkGray
        $script:BackendReady = $true
    } else {
        $tempDb    = Join-Path ([System.IO.Path]::GetTempPath()) ("driftwatch-healdemo-{0}.db" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
        $serverLog = [System.IO.Path]::ChangeExtension($tempDb, '.out.log')
        $serverErr = [System.IO.Path]::ChangeExtension($tempDb, '.err.log')

        Write-Host ("  No backend on port {0}; starting a private one on a throwaway database." -f $Port) -ForegroundColor DarkGray
        Write-Cmd ("py -3.12 backend/serve.py    (DW_MODE=replay, DW_DB_PATH={0})" -f $tempDb)

        $prevDb   = $env:DW_DB_PATH
        $prevPort = $env:DW_PORT
        $prevMode = $env:DW_MODE
        $env:DW_DB_PATH = $tempDb
        $env:DW_PORT    = "$Port"
        $env:DW_MODE    = 'replay'
        try {
            $startedServer = Start-Process -FilePath 'py' `
                -ArgumentList @('-3.12', 'backend/serve.py') `
                -WorkingDirectory $repoRoot `
                -RedirectStandardOutput $serverLog `
                -RedirectStandardError  $serverErr `
                -WindowStyle Hidden -PassThru
        } finally {
            $env:DW_DB_PATH = $prevDb
            $env:DW_PORT    = $prevPort
            $env:DW_MODE    = $prevMode
        }

        $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
        while (-not (Test-Backend $script:Api)) {
            if ($startedServer.HasExited) {
                if (Test-Path $serverErr) { Get-Content $serverErr | Select-Object -Last 20 | ForEach-Object { Write-Host "      $_" -ForegroundColor DarkRed } }
                Stop-Demo 'the backend process exited during startup'
            }
            if ((Get-Date) -gt $deadline) {
                Stop-Demo ("backend did not become ready within {0}s" -f $StartupTimeoutSeconds)
            }
            Start-Sleep -Milliseconds 400
        }
        $script:BackendReady = $true
        Write-Ok ("backend ready at {0} (pid {1})" -f $script:Api, $startedServer.Id)
    }

    # -----------------------------------------------------------------------
    # STEP 1 -- baseline: a valid contract and a green extraction
    # -----------------------------------------------------------------------
    Write-Step 'Baseline. Valid contract, verified extraction.'
    Write-Say ("Source '{0}' is watched against a semantic contract in fixtures/contracts/{0}.yaml." -f $SourceId)
    Write-Say 'We pin the mirror world to the baseline page and run the collector once.'

    Write-Cmd ("POST /api/demo/state  {{source_id: {0}, variant: {1}}}" -f $SourceId, $BaselineVariant)
    $null = Invoke-Api -Path '/api/demo/state' -Method POST -Body @{ source_id = $SourceId; variant = $BaselineVariant }

    Write-Cmd ("POST /api/run/{0}" -f $SourceId)
    $baselineRun = Invoke-Api -Path ("/api/run/{0}" -f $SourceId) -Method POST
    Write-Fact 'run_id'      $baselineRun.run_id
    Write-Fact 'state'       $baselineRun.state 'Green'
    Write-Fact 'drift class' $baselineRun.class

    $detail = Invoke-Api -Path ("/api/sources/{0}" -f $SourceId)
    $scraperBefore = $detail.scraper
    Write-Fact 'collector_id'    $scraperBefore.collector_id
    Write-Fact 'active version'  ("v{0}" -f $scraperBefore.active_version)
    Show-Models $detail.latest_snapshot.payload 'extracted, published, un-quarantined:'
    $baselineGates = @(Show-Gates $detail.latest_snapshot.verdict 'contract verdict on the published snapshot:')

    if ($baselineRun.state -ne 'published') {
        Stop-Demo ("baseline run did not publish (state={0})" -f $baselineRun.state)
    }
    if ($null -eq $detail.latest_snapshot -or $null -eq $detail.latest_snapshot.verdict) {
        Stop-Demo 'no published snapshot with a contract verdict at baseline'
    }
    if ((Get-NullPriceCount $detail.latest_snapshot.payload) -ne 0) {
        Stop-Demo 'baseline extraction contains null prices; the world is not at a clean baseline'
    }
    if ($baselineGates.Count -ne 0) {
        Stop-Demo ("baseline verdict has failing gates: {0}" -f ($baselineGates -join ', '))
    }
    Write-Ok 'baseline extraction verified: all four gates green, prices present.'

    # -----------------------------------------------------------------------
    # STEP 2 -- introduce the controlled break
    # -----------------------------------------------------------------------
    Write-Step 'Break. The page is redesigned overnight.'
    Write-Say 'We flip the controlled mirror site to the redesigned layout. Nothing else changes:'
    Write-Say 'same collector id, same contract, same schedule. This is the silent-failure case.'

    Write-Cmd ("POST /api/demo/state  {{source_id: {0}, variant: {1}}}" -f $SourceId, $BreakVariant)
    $null = Invoke-Api -Path '/api/demo/state' -Method POST -Body @{ source_id = $SourceId; variant = $BreakVariant }
    $worldNow = Invoke-Api -Path '/api/demo/state'
    $currentVariant = $worldNow.$SourceId
    Write-Fact 'mirror variant now' $currentVariant 'Yellow'
    Write-Fact 'mirror page'        ("{0}/mirror/{1}" -f $script:Api, $SourceId)
    if ($currentVariant -ne $BreakVariant) {
        Stop-Demo ("mirror world did not flip to {0} (got {1})" -f $BreakVariant, $currentVariant)
    }
    Write-Ok ("world is broken on purpose: {0} -> {1}" -f $BaselineVariant, $BreakVariant)

    # -----------------------------------------------------------------------
    # STEP 3 -- run; verification fails; show WHICH gates failed
    # -----------------------------------------------------------------------
    Write-Step 'Detection. The run fails contract verification.'
    Write-Say 'One run does the whole loop without a human: detect, diagnose, heal, verify,'
    Write-Say 'decide, re-run. We trigger it, then read back exactly what happened inside it.'

    Write-Cmd ("POST /api/run/{0}" -f $SourceId)
    $breakRun = Invoke-Api -Path ("/api/run/{0}" -f $SourceId) -Method POST
    Write-Fact 'run_id'      $breakRun.run_id
    Write-Fact 'drift class' ("{0} (1 = structural drift)" -f $breakRun.class) 'Yellow'
    Write-Fact 'final state' $breakRun.state
    Write-Fact 'healed'      $breakRun.healed

    if ($breakRun.class -ne 1) {
        Write-Bad ("expected drift class 1 (structural), got {0}." -f $breakRun.class)
        if ($attached) {
            Write-Bad 'The attached backend has most likely already healed this variant in its'
            Write-Bad 'in-memory replay world. Restart the backend and re-run for a clean demo.'
        }
        Stop-Demo 'the controlled break did not produce structural drift'
    }

    # The run summary carries the POST-heal "redesign absorbed" event. The DETECTION
    # event -- the one holding the quarantined broken extraction and its failing
    # verdict -- is the heal's trigger event. Pull the heal first, then that event.
    Write-Cmd 'GET /api/heals'
    $heals = Invoke-Api -Path '/api/heals'
    $heal = @($heals | Where-Object { $_.source_id -eq $SourceId }) | Select-Object -First 1
    if ($null -eq $heal) { Stop-Demo 'no heal event was recorded for this source' }
    if ($null -eq $heal.trigger_event_id) { Stop-Demo 'the heal event has no trigger drift event' }

    $eventId = $heal.trigger_event_id
    Write-Cmd ("GET /api/events/{0}    # the heal's trigger event" -f $eventId)
    $event = Invoke-Api -Path ("/api/events/{0}" -f $eventId)
    if ([int]$event.run_id -ne [int]$breakRun.run_id) {
        Stop-Demo ("the newest heal belongs to run {0}, not to the run we just triggered ({1})" -f $event.run_id, $breakRun.run_id)
    }
    Write-Fact 'detection event' ("#{0} -- {1}" -f $event.id, $event.class_label) 'Yellow'
    Write-Fact 'severity' $event.severity
    Write-Fact 'summary'  $event.summary
    Show-Models $event.after_payload 'what the OUTDATED template extracted (HTTP 200, valid JSON):'
    $failedGates = @(Show-Gates $event.after_verdict 'contract verdict -- this is the detection:')

    if ($null -eq $event.after_verdict) {
        Stop-Demo 'the drift event carries no contract verdict to show'
    }
    if ($event.after_verdict.passed) {
        Stop-Demo 'the broken extraction unexpectedly PASSED contract verification'
    }
    if ($failedGates.Count -eq 0) {
        Stop-Demo 'expected at least one failing gate on the broken extraction'
    }
    Write-Ok ("verification FAILED. Failing gate(s): {0}" -f ($failedGates -join ', '))
    Write-Say 'The scraper returned HTTP 200 and well-formed JSON. A liveness check would have'
    Write-Say 'stayed green. Only the contract noticed. That snapshot is quarantined, not published.'

    # -----------------------------------------------------------------------
    # STEP 4 -- the machine-composed heal prompt
    # -----------------------------------------------------------------------
    Write-Step 'Repair. The machine-composed heal prompt.'
    Write-Say "Bright Data's heal API expects a human-written prompt of at most 1000 characters."
    Write-Say 'DriftWatch is that human: it composes the prompt from the diagnosis, deterministically.'

    Write-Fact 'heal_event id' $heal.id
    Write-Fact 'triggered by'  ("drift event #{0}" -f $heal.trigger_event_id)
    Write-Fact 'prompt length' ("{0} chars (limit 1000)" -f $heal.composed_prompt.Length)
    Write-Host '    composed prompt (verbatim, machine-written):' -ForegroundColor White
    Write-Wrapped $heal.composed_prompt
    if ([string]::IsNullOrWhiteSpace($heal.composed_prompt)) {
        Stop-Demo 'the heal prompt is empty'
    }
    if ($heal.composed_prompt.Length -gt 1000) {
        Stop-Demo ("heal prompt exceeds the 1000-char vendor limit ({0})" -f $heal.composed_prompt.Length)
    }
    Write-Ok 'prompt composed from the failing fields, coverage drop and last-known-good examples.'

    # -----------------------------------------------------------------------
    # STEP 5 -- the preview is re-verified against the FULL contract
    # -----------------------------------------------------------------------
    Write-Step 'Verification. The repair preview is re-proven, not trusted.'
    Write-Say "The heal returns a preview at Bright Data's approval gate. DriftWatch never trusts"
    Write-Say 'the heal status -- it replays the preview through the same four gates as live data.'

    Show-Models $heal.preview_payload 'heal preview payload:'
    $previewFailed = @(Show-Gates $heal.verification 'preview re-verified against the FULL contract:')
    if ($previewFailed.Count -ne 0) {
        Stop-Demo ("heal preview failed gates: {0}" -f ($previewFailed -join ', '))
    }
    if (-not $heal.verification.passed) {
        Stop-Demo 'heal preview verdict did not pass'
    }
    if ((Get-NullPriceCount $heal.preview_payload) -ne 0) {
        Stop-Demo 'heal preview still contains null prices'
    }
    Write-Ok ("preview verified: 4/4 gates PASS, confidence {0}" -f $heal.verification.confidence)

    # -----------------------------------------------------------------------
    # STEP 6 -- three-band approval + version pin
    # -----------------------------------------------------------------------
    Write-Step 'Approval. Three-band policy and the version pin.'
    Write-Say 'Policy: confidence >= 0.90 auto-approve; <= 0.50 auto-reject plus one refined retry;'
    Write-Say 'anything in between goes to a human review queue. Nothing else can approve a heal.'

    $band = 'HUMAN REVIEW  (0.50 - 0.90)'
    if ($heal.verification.confidence -ge 0.90) {
        $band = 'AUTO-APPROVE  (>= 0.90)'
    } elseif ($heal.verification.confidence -le 0.50) {
        $band = 'AUTO-REJECT   (<= 0.50)'
    }
    Write-Fact 'confidence' $heal.verification.confidence
    Write-Fact 'band'       $band 'Green'
    Write-Fact 'decision'   $heal.decision 'Green'
    Write-Fact 'decided_by' $heal.decided_by
    Write-Fact 'status'     $heal.status
    Write-Fact 'version'    ("v{0} -> v{1}" -f $heal.version_before, $heal.version_after) 'Green'
    Write-Fact 'MTTR'       ("{0} s (measured, replay transport has no network latency)" -f $heal.mttr_seconds)

    if ($heal.status -ne 'approved') { Stop-Demo ("heal status is '{0}', expected 'approved'" -f $heal.status) }
    if ($heal.decided_by -ne 'machine') { Stop-Demo ("heal was decided by '{0}', expected 'machine'" -f $heal.decided_by) }
    if ($heal.version_after -ne ($heal.version_before + 1)) {
        Stop-Demo ("version did not advance by exactly one (v{0} -> v{1})" -f $heal.version_before, $heal.version_after)
    }

    Write-Cmd 'GET /api/ledger'
    $ledger = Invoke-Api -Path '/api/ledger?limit=200'
    $ledgerActions = @($ledger | ForEach-Object { $_.action })
    foreach ($needed in @('heal.requested', 'heal.preview_verified', 'heal.auto_approved', 'heal.rerun_verified')) {
        if ($ledgerActions -contains $needed) {
            Write-Ok ("audit ledger records: {0}" -f $needed)
        } else {
            Stop-Demo ("audit ledger is missing '{0}'" -f $needed)
        }
    }

    # -----------------------------------------------------------------------
    # STEP 7 -- re-run: data restored
    # -----------------------------------------------------------------------
    Write-Step 'Recovery. Same collector id, new template version, data flowing.'
    Write-Say 'The version pin only advances after a verified re-run. That re-run already happened'
    Write-Say 'inside the healing run; it published the event below. Now we run the SAME collector'
    Write-Say 'once more against the redesigned page and confirm the pipeline is quiet and green.'

    if ($breakRun.event_id) {
        $absorbed = Invoke-Api -Path ("/api/events/{0}" -f $breakRun.event_id)
        Write-Fact 'post-heal event' ("#{0} -- {1} / {2}" -f $absorbed.id, $absorbed.class_label, $absorbed.severity)
        Write-Fact 'summary'         $absorbed.summary
    }

    Write-Cmd ("POST /api/run/{0}" -f $SourceId)
    $recoveryRun = Invoke-Api -Path ("/api/run/{0}" -f $SourceId) -Method POST
    Write-Fact 'run_id'      $recoveryRun.run_id
    Write-Fact 'drift class' ("{0} (0 = no change since last published snapshot)" -f $recoveryRun.class) 'Green'
    Write-Fact 'state'       $recoveryRun.state 'Green'

    $after = Invoke-Api -Path ("/api/sources/{0}" -f $SourceId)
    Write-Fact 'collector_id'   $after.scraper.collector_id
    Write-Fact 'active version' ("v{0}  (was v{1})" -f $after.scraper.active_version, $scraperBefore.active_version) 'Green'
    Show-Models $after.latest_snapshot.payload 'published data after the heal:'
    $afterGates = @(Show-Gates $after.latest_snapshot.verdict 'contract verdict on the restored snapshot:')

    if ($recoveryRun.state -ne 'published') {
        Stop-Demo ("recovery run did not publish (state={0})" -f $recoveryRun.state)
    }
    if ($afterGates.Count -ne 0) {
        Stop-Demo ("restored snapshot has failing gates: {0}" -f ($afterGates -join ', '))
    }
    if ((Get-NullPriceCount $after.latest_snapshot.payload) -ne 0) {
        Stop-Demo 'restored snapshot still contains null prices'
    }
    if ($after.scraper.collector_id -ne $scraperBefore.collector_id) {
        Stop-Demo 'the collector id changed; the demo must re-run the SAME collector'
    }
    if ([int]$after.scraper.active_version -ne ([int]$scraperBefore.active_version + 1)) {
        Stop-Demo ("active template version did not advance by one (v{0} -> v{1})" -f $scraperBefore.active_version, $after.scraper.active_version)
    }
    Write-Ok 'data restored. Same collector, template v+1, four gates green, nothing quarantined.'

    Write-Host ''
    Write-Rule
    Write-Host '  RESULT: break -> detect -> heal -> verify -> approve -> recover, with no human' -ForegroundColor Green
    Write-Host '  in the loop, and every step provable from the audit ledger.' -ForegroundColor Green
    Write-Host '  We did not build another scraper. We built infrastructure that keeps scrapers alive.' -ForegroundColor Green
    Write-Rule

} catch {
    $exitCode = 1
    Write-Host ''
    Write-Bad $_.Exception.Message
    if ($_.ScriptStackTrace) {
        Write-Host ("    {0}" -f ($_.ScriptStackTrace -split "`n" | Select-Object -First 3 | Out-String).Trim()) -ForegroundColor DarkRed
    }
} finally {
    # ---- required by the brief: always restore the world to a valid state ----
    Write-Host ''
    Write-Rule
    Write-Host 'CLEANUP. Restoring the demo world to the baseline variant.' -ForegroundColor Cyan
    Write-Rule
    if ($script:BackendReady) {
        try {
            $null = Invoke-Api -Path '/api/demo/state' -Method POST -Body @{ source_id = $SourceId; variant = $BaselineVariant }
            $final = Invoke-Api -Path '/api/demo/state'
            if ($final.$SourceId -eq $BaselineVariant) {
                Write-Ok ("mirror world restored: {0} = {1}" -f $SourceId, $BaselineVariant)
            } else {
                Write-Bad ("could not confirm restore; {0} = {1}" -f $SourceId, $final.$SourceId)
                $exitCode = 1
            }
        } catch {
            Write-Bad ("world restore failed: {0}" -f $_.Exception.Message)
            $exitCode = 1
        }
    } else {
        Write-Say 'no backend was reachable; there is no demo world to restore.'
    }

    if ($startedServer) {
        try {
            if (-not $startedServer.HasExited) {
                Stop-Process -Id $startedServer.Id -Force -ErrorAction SilentlyContinue
                Write-Ok ("stopped the backend started by this script (pid {0})" -f $startedServer.Id)
            }
        } catch {
            Write-Bad ("could not stop backend pid {0}: {1}" -f $startedServer.Id, $_.Exception.Message)
        }
        foreach ($path in @($tempDb, "$tempDb-wal", "$tempDb-shm", $serverLog, $serverErr)) {
            if ($path -and (Test-Path $path)) { Remove-Item $path -Force -ErrorAction SilentlyContinue }
        }
        Write-Ok 'throwaway database and logs removed'
    } elseif ($attached) {
        Write-Say 'the backend was already running and was left running.'
    }

    Write-Host ''
    if ($exitCode -eq 0) {
        Write-Host 'heal_demo.ps1: PASS (all steps behaved as expected)' -ForegroundColor Green
    } else {
        Write-Host 'heal_demo.ps1: FAIL' -ForegroundColor Red
    }
    Write-Host ''
    exit $exitCode
}
