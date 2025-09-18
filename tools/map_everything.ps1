<#
.SYNOPSIS
    Run the complete "map everything" workflow and gather per-stage reports.

.DESCRIPTION
    This wrapper runs the curated sequence of experiment scripts shipped with
    the repository.  Each stage writes its stdout/stderr to a log, produces a
    lightweight REPORT.json with key metadata, and the script finally emits a
    top-level SUMMARY.md that links to every report.

.PARAMETER Python
    Optional explicit path to the Python interpreter.  When omitted the script
    searches for ``python``, ``python3`` or ``py`` in $Env:PATH.

.EXAMPLE
    PS> ./tools/map_everything.ps1

    Run the workflow with the default interpreter resolution.

.EXAMPLE
    PS> ./tools/map_everything.ps1 -Python "C:\\Python311\\python.exe"

    Use a specific interpreter when multiple versions are available.
#>
[CmdletBinding()]
param(
    [string]$Python
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-PythonInterpreter {
    param(
        [string]$Preferred
    )

    if ($Preferred) {
        $command = Get-Command -LiteralPath $Preferred -ErrorAction SilentlyContinue
        if (-not $command) {
            throw "Python interpreter '$Preferred' was not found."
        }
        return $command.Source
    }

    foreach ($candidate in @('python', 'python3', 'py')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }

    throw 'Unable to locate a Python interpreter. Pass -Python to specify one explicitly.'
}

function Invoke-Stage {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        [Parameter(Mandatory)]
        [string[]]$Command,
        [Parameter(Mandatory)]
        [string]$OutputDir,
        [hashtable]$Context,
        [scriptblock]$PostProcess,
        [Parameter(Mandatory)]
        [string]$RepoRoot
    )

    Write-Host "=== $Name ==="
    $null = New-Item -ItemType Directory -Path $OutputDir -Force
    $logPath = Join-Path $OutputDir 'run.log'
    $exe = $Command[0]
    $args = if ($Command.Count -gt 1) { $Command[1..($Command.Count - 1)] } else { @() }
    $commandLine = ($Command -join ' ')
    $startTime = Get-Date

    & $exe @args 2>&1 | Tee-Object -FilePath $logPath
    $exitCode = if ($LASTEXITCODE -ne $null) { [int]$LASTEXITCODE } else { 0 }
    $duration = (Get-Date) - $startTime

    $outputFull = Convert-Path -LiteralPath $OutputDir
    $logFull = Convert-Path -LiteralPath $logPath
    $status = if ($exitCode -eq 0) { 'completed' } else { 'failed' }

    $report = [ordered]@{
        stage = $Name
        command = $commandLine
        status = $status
        exit_code = $exitCode
        started = $startTime.ToString('o')
        duration_seconds = [Math]::Round($duration.TotalSeconds, 3)
        output_dir = $outputFull
        output_relative = [System.IO.Path]::GetRelativePath($RepoRoot, $outputFull)
        log = $logFull
        log_relative = [System.IO.Path]::GetRelativePath($RepoRoot, $logFull)
    }

    if ($Context) {
        $report.context = $Context
    }

    if ($PostProcess) {
        $extra = & $PostProcess -StageName $Name -OutputDir $OutputDir -ExitCode $exitCode -LogPath $logPath -RepoRoot $RepoRoot -Context $Context
        if ($extra -is [System.Collections.IDictionary]) {
            foreach ($key in $extra.Keys) {
                if ($null -ne $extra[$key]) {
                    $report[$key] = $extra[$key]
                }
            }
        }
    }

    $reportPath = Join-Path $OutputDir 'REPORT.json'
    $reportJson = $report | ConvertTo-Json -Depth 8
    Set-Content -LiteralPath $reportPath -Value $reportJson -Encoding UTF8

    $reportFull = Convert-Path -LiteralPath $reportPath
    $reportRelative = [System.IO.Path]::GetRelativePath($RepoRoot, $reportFull)

    return [pscustomobject]@{
        Name = $Name
        Command = $commandLine
        Status = $status
        ExitCode = $exitCode
        ReportPath = $reportFull
        ReportRelative = $reportRelative
        LogPath = $logFull
        Succeeded = ($exitCode -eq 0)
    }
}

function Write-Summary {
    param(
        [string]$RepoRoot,
        [System.Collections.IList]$StageResults,
        [bool]$HadFailure
    )

    if (-not $StageResults -or $StageResults.Count -eq 0) {
        return
    }

    $summaryPath = Join-Path $RepoRoot 'SUMMARY.md'
    $lines = @(
        '# Map Everything Run Summary',
        '',
        '| Stage | Status | Report |',
        '| --- | --- | --- |'
    )

    foreach ($result in $StageResults) {
        $emoji = if ($result.Succeeded) { '✅' } else { '❌' }
        $lines += "| $($result.Name) | $emoji $($result.Status) | [$($result.ReportRelative)]($($result.ReportRelative)) |"
    }

    $lines += ''
    if ($HadFailure) {
        $lines += '> ⚠️ At least one stage failed. Inspect the linked reports for details.'
    } else {
        $lines += '> ✅ All stages completed successfully.'
    }

    Set-Content -LiteralPath $summaryPath -Value ($lines -join "`n") -Encoding UTF8
    Write-Host "Summary written to $summaryPath"
}

$repoRoot = (Get-Item -LiteralPath (Join-Path $PSScriptRoot '..')).FullName
$pythonExe = Resolve-PythonInterpreter -Preferred $Python
$stageResults = New-Object System.Collections.Generic.List[object]
$failureMessage = $null
$caughtError = $null

Push-Location -LiteralPath $repoRoot
try {
    $mapRoot = Join-Path $repoRoot 'artifacts'
    $mapRoot = Join-Path $mapRoot 'map_everything'
    $null = New-Item -ItemType Directory -Path $mapRoot -Force

    $gateBScript = Join-Path $repoRoot 'cwt-sim\experiments\gateB_ridge_finder\run.py'
    $hotspotScript = Join-Path $repoRoot 'cwt-sim\experiments\loop_at_hotspot\run.py'
    $adiabaticScript = Join-Path $repoRoot 'cwt-sim\experiments\adiabatic_boundary\run.py'
    $torusScript = Join-Path $repoRoot 'cwt-sim\experiments\torus_plateau\run.py'
    $familyScript = Join-Path $repoRoot 'cwt-sim\experiments\graph_family\run.py'

    $gateBTauZetaOut = Join-Path $mapRoot 'gateB_tau_zeta'
    $gateBTauZetaPhaseOut = Join-Path $mapRoot 'gateB_tau_zeta_phase'
    $hotspotOut = Join-Path $mapRoot 'hotspot_loops'
    $adiabaticOut = Join-Path $mapRoot 'adiabatic_boundary'
    $torusOut = Join-Path $mapRoot 'torus_plateau'
    $familyTauZetaOut = Join-Path $mapRoot 'graph_family_tau_zeta'
    $familyTauZetaPhaseOut = Join-Path $mapRoot 'graph_family_tau_zeta_phase'

    $hotspotSource = Join-Path $gateBTauZetaOut 'ring3\top_omega_tiles.json'

    $stages = @(
        @{
            Name = 'gateB_tau_zeta'
            OutputDir = $gateBTauZetaOut
            Command = @($pythonExe, $gateBScript, '--axes', 'tau', 'zeta', '--output-dir', $gateBTauZetaOut)
            Context = @{
                axes = @('tau', 'zeta')
                grid_size = 21
                description = 'Gate B ridge scan in the (τ, ζ) plane'
            }
            PostProcess = {
                param($StageName, $OutputDir, $ExitCode, $LogPath, $RepoRoot, $Context)
                $result = @{}
                $artifacts = @()
                $summaryPath = Join-Path $OutputDir 'summary.json'
                if (Test-Path -LiteralPath $summaryPath) {
                    $artifacts += [System.IO.Path]::GetRelativePath($RepoRoot, (Convert-Path -LiteralPath $summaryPath))
                    try {
                        $summaryContent = Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json
                        $result.summary = $summaryContent
                    } catch {
                        $result.summary_error = $_.Exception.Message
                    }
                }
                $tiles = Get-ChildItem -Path $OutputDir -Filter 'top_omega_tiles.json' -File -Recurse -ErrorAction SilentlyContinue
                if ($tiles) {
                    $artifacts += $tiles | ForEach-Object {
                        [System.IO.Path]::GetRelativePath($RepoRoot, (Convert-Path -LiteralPath $_.FullName))
                    }
                }
                $artifacts = $artifacts | Where-Object { $_ }
                if ($artifacts) {
                    $result.artifacts = $artifacts
                }
                $graphs = Get-ChildItem -Path $OutputDir -Directory -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
                if ($graphs) {
                    $result.graphs = $graphs
                }
                if ($Context) {
                    $result.axes = $Context.axes
                }
                return $result
            }
        },
        @{
            Name = 'gateB_tau_zeta_phase'
            OutputDir = $gateBTauZetaPhaseOut
            Command = @($pythonExe, $gateBScript, '--axes', 'tau', 'zeta_phase', '--output-dir', $gateBTauZetaPhaseOut)
            Context = @{
                axes = @('tau', 'zeta_phase')
                grid_size = 21
                description = 'Gate B ridge scan in the (τ, ζ_phase) plane'
            }
            PostProcess = {
                param($StageName, $OutputDir, $ExitCode, $LogPath, $RepoRoot, $Context)
                $result = @{}
                $artifacts = @()
                $summaryPath = Join-Path $OutputDir 'summary.json'
                if (Test-Path -LiteralPath $summaryPath) {
                    $artifacts += [System.IO.Path]::GetRelativePath($RepoRoot, (Convert-Path -LiteralPath $summaryPath))
                    try {
                        $result.summary = Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json
                    } catch {
                        $result.summary_error = $_.Exception.Message
                    }
                }
                $tiles = Get-ChildItem -Path $OutputDir -Filter 'top_omega_tiles.json' -File -Recurse -ErrorAction SilentlyContinue
                if ($tiles) {
                    $artifacts += $tiles | ForEach-Object {
                        [System.IO.Path]::GetRelativePath($RepoRoot, (Convert-Path -LiteralPath $_.FullName))
                    }
                }
                $artifacts = $artifacts | Where-Object { $_ }
                if ($artifacts) {
                    $result.artifacts = $artifacts
                }
                $graphs = Get-ChildItem -Path $OutputDir -Directory -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
                if ($graphs) {
                    $result.graphs = $graphs
                }
                if ($Context) {
                    $result.axes = $Context.axes
                }
                return $result
            }
        },
        @{
            Name = 'hotspot_loops'
            OutputDir = $hotspotOut
            Command = @(
                $pythonExe,
                $hotspotScript,
                '--hotspots', $hotspotSource,
                '--extents', '0.02', '0.05', '0.08',
                '--limit', '4'
            )
            Context = @{
                hotspots_relative = [System.IO.Path]::GetRelativePath($repoRoot, $hotspotSource)
                hotspots_absolute = $hotspotSource
                extents = @(0.02, 0.05, 0.08)
                axes = @('tau', 'zeta')
                limit = 4
            }
            PostProcess = {
                param($StageName, $OutputDir, $ExitCode, $LogPath, $RepoRoot, $Context)
                $result = @{}
                $artifacts = @()
                if ($Context -and $Context.hotspots_absolute -and (Test-Path -LiteralPath $Context.hotspots_absolute)) {
                    $artifacts += [System.IO.Path]::GetRelativePath($RepoRoot, (Convert-Path -LiteralPath $Context.hotspots_absolute))
                }
                if ($artifacts) {
                    $result.artifacts = $artifacts
                }
                if (Test-Path -LiteralPath $LogPath) {
                    $tail = Get-Content -LiteralPath $LogPath -Tail 25
                    $notes = @()
                    $accept = $tail | Where-Object { $_ -match 'Acceptance criteria satisfied' }
                    if ($accept) {
                        $notes += ($accept | Select-Object -Last 1)
                    }
                    $failure = $tail | Where-Object { $_ -match 'Acceptance criteria failed' }
                    if ($failure) {
                        $notes += ($failure | Select-Object -Last 1)
                    }
                    if (-not $notes) {
                        $lastHotspot = $tail | Where-Object { $_ -match '^Hotspot #' }
                        if ($lastHotspot) {
                            $notes += ($lastHotspot | Select-Object -Last 1)
                        }
                    }
                    if ($notes) {
                        $result.highlights = $notes
                    }
                }
                return $result
            }
        },
        @{
            Name = 'adiabatic_boundary'
            OutputDir = $adiabaticOut
            Command = @($pythonExe, $adiabaticScript, '--output-dir', $adiabaticOut)
            Context = @{
                extents = @('0.02', '0.04', '0.08')
                steps = @('48', '96', '192')
            }
            PostProcess = {
                param($StageName, $OutputDir, $ExitCode, $LogPath, $RepoRoot, $Context)
                $result = @{}
                $artifacts = @()
                foreach ($name in @('kappa_surface.csv', 'fs_histograms.json', 'boundary.csv')) {
                    $path = Join-Path $OutputDir $name
                    if (Test-Path -LiteralPath $path) {
                        $artifacts += [System.IO.Path]::GetRelativePath($RepoRoot, (Convert-Path -LiteralPath $path))
                    }
                }
                if ($artifacts) {
                    $result.artifacts = $artifacts
                }
                return $result
            }
        },
        @{
            Name = 'torus_plateau'
            OutputDir = $torusOut
            Command = @($pythonExe, $torusScript, '--axes', 'tau', 'zeta_phase', '--grid-size', '33', '--disorder', '0.0', '0.02', '0.05', '0.1')
            Context = @{
                axes = @('tau', 'zeta_phase')
                grid_size = 33
                disorder = @(0.0, 0.02, 0.05, 0.1)
            }
            PostProcess = {
                param($StageName, $OutputDir, $ExitCode, $LogPath, $RepoRoot, $Context)
                $result = @{}
                if (Test-Path -LiteralPath $LogPath) {
                    $tail = Get-Content -LiteralPath $LogPath -Tail 20 | Where-Object { $_ -match '^disorder=' -or $_ -match 'Plateau stable' -or $_ -match 'Stability warning' -or $_ -match 'No large integral jumps' }
                    if ($tail) {
                        $result.highlights = $tail
                    }
                }
                return $result
            }
        },
        @{
            Name = 'graph_family_tau_zeta'
            OutputDir = $familyTauZetaOut
            Command = @(
                $pythonExe,
                $familyScript,
                '--families', 'ring,rr,sw,sf,mod',
                '--axes', 'tau', 'zeta',
                '--center', 'tau=0.8,zeta=0.0',
                '--extents', '0.02',
                '--grid-size', '21',
                '--seed', '123'
            )
            Context = @{
                families = @('ring', 'rr', 'sw', 'sf', 'mod')
                axes = @('tau', 'zeta')
                center = 'tau=0.8,zeta=0.0'
                extent = 0.02
                seed = 123
            }
            PostProcess = {
                param($StageName, $OutputDir, $ExitCode, $LogPath, $RepoRoot, $Context)
                $result = @{}
                if (Test-Path -LiteralPath $LogPath) {
                    $lines = Get-Content -LiteralPath $LogPath
                    $best = $lines | Where-Object { $_ -match 'Highest modularity ensemble' }
                    if ($best) {
                        $result.highlights = ($best | Select-Object -Last 1)
                    }
                }
                return $result
            }
        },
        @{
            Name = 'graph_family_tau_zeta_phase'
            OutputDir = $familyTauZetaPhaseOut
            Command = @(
                $pythonExe,
                $familyScript,
                '--families', 'ring,mod',
                '--axes', 'tau', 'zeta_phase',
                '--center', 'tau=0.7,zeta_phase=0.1',
                '--extents', '0.03',
                '--grid-size', '25',
                '--seed', '321'
            )
            Context = @{
                families = @('ring', 'mod')
                axes = @('tau', 'zeta_phase')
                center = 'tau=0.7,zeta_phase=0.1'
                extent = 0.03
                seed = 321
            }
            PostProcess = {
                param($StageName, $OutputDir, $ExitCode, $LogPath, $RepoRoot, $Context)
                $result = @{}
                if (Test-Path -LiteralPath $LogPath) {
                    $lines = Get-Content -LiteralPath $LogPath
                    $best = $lines | Where-Object { $_ -match 'Highest modularity ensemble' }
                    if ($best) {
                        $result.highlights = ($best | Select-Object -Last 1)
                    }
                }
                return $result
            }
        }
    )

    foreach ($stage in $stages) {
        $result = Invoke-Stage -RepoRoot $repoRoot @stage
        $stageResults.Add($result)
        if (-not $result.Succeeded) {
            $failureMessage = "Stage '$($result.Name)' failed with exit code $($result.ExitCode)."
            break
        }
    }
}
catch {
    $caughtError = $_
}
finally {
    Pop-Location
}

$hadFailure = [bool]$failureMessage -or [bool]$caughtError
Write-Summary -RepoRoot $repoRoot -StageResults $stageResults -HadFailure $hadFailure

if ($caughtError) {
    throw $caughtError
}

if ($failureMessage) {
    throw $failureMessage
}
