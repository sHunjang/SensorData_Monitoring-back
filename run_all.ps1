Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║               COMPLETE AGGREGATION EXECUTION                       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$SuccessCount = 0
$FailCount = 0

# ============================================================================
# Modbus 집계
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "MODBUS Aggregations (Device 11-15)" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

python src/db/aggreagte_modbus/aggregate_modbus_1m.py --hours 168
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggreagte_modbus/aggregate_modbus_15m.py --hours 168
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggreagte_modbus/aggregate_modbus_1h.py --hours 168
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggreagte_modbus/aggregate_modbus_1d.py --days 7
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggreagte_modbus/aggregate_modbus_1w.py --weeks 4
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggreagte_modbus/aggregate_modbus_1mo.py --months 6
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggreagte_modbus/aggregate_modbus_6mo.py --years 2
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggreagte_modbus/aggregate_modbus_1y.py --years 5
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

Write-Host ""

# ============================================================================
# Env 집계
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "ENV Aggregations (Device 21-23)" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green

python src/db/aggregate_env/aggregate_env_1m.py --hours 168
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_env/aggregate_env_15m.py --hours 168
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_env/aggregate_env_1h.py --hours 168
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_env/aggregate_env_1d.py --days 7
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_env/aggregate_env_1w.py --weeks 4
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_env/aggregate_env_1mo.py --months 6
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_env/aggregate_env_6mo.py --years 2
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_env/aggregate_env_1y.py --years 5
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

Write-Host ""

# ============================================================================
# Solar 집계
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host "SOLAR Aggregations (Device 31)" -ForegroundColor Magenta
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta

python src/db/aggregate_solar/aggregate_solar_1m.py --hours 168
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_solar/aggregate_solar_15m.py --hours 168
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_solar/aggregate_solar_1h.py --hours 168
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_solar/aggregate_solar_1d.py --days 7
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_solar/aggregate_solar_1w.py --weeks 4
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_solar/aggregate_solar_1mo.py --months 6
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_solar/aggregate_solar_6mo.py --years 2
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

python src/db/aggregate_solar/aggregate_solar_1y.py --years 5
if ($LASTEXITCODE -eq 0) { $SuccessCount++ } else { $FailCount++ }

Write-Host ""

# ============================================================================
# 최종 결과
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                        FINAL SUMMARY                               ║" -ForegroundColor Cyan
Write-Host "╠════════════════════════════════════════════════════════════════════╣" -ForegroundColor Cyan

$TotalScripts = 24
$SuccessPercent = [math]::Round(($SuccessCount / $TotalScripts) * 100, 1)

Write-Host "║  Total Scripts:  $TotalScripts                                              ║" -ForegroundColor White
Write-Host "║  Success:        $SuccessCount                                               ║" -ForegroundColor Green
Write-Host "║  Failed:         $FailCount                                                ║" -ForegroundColor $(if ($FailCount -eq 0) { "Green" } else { "Red" })
Write-Host "║  Success Rate:   $SuccessPercent%                                           ║" -ForegroundColor $(if ($SuccessPercent -eq 100) { "Green" } else { "Yellow" })
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($FailCount -eq 0) {
    Write-Host "🎉 All aggregations completed successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️  $FailCount aggregation(s) failed. Check logs above." -ForegroundColor Yellow
}
