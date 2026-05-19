$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$outputDir = Join-Path $repoRoot "sample_data\out\fullrun"
$finalOutput = Join-Path $repoRoot "sample_data\out\analysis-run.public-sample.json"

Set-Location $repoRoot

python ai\pipeline\run_full_pipeline.py `
  --input sample_data\raw-posts.public-sample.json `
  --out-dir $outputDir `
  --final-output $finalOutput

Write-Host "AI pipeline output: $finalOutput"
