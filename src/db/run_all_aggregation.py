"""
전체 센서 집계 일괄 실행 스크립트

실행:
  python -m src.db.run_all_aggregations
  
옵션:
  python -m src.db.run_all_aggregations --sensor modbus  # Modbus만
  python -m src.db.run_all_aggregations --sensor env     # Env만
  python -m src.db.run_all_aggregations --sensor solar   # Solar만
"""

import subprocess
import sys
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger("run_all")

# ============================================================================
# 집계 실행 순서
# ============================================================================

MODBUS_AGGREGATIONS = [
    ('1m', 'aggregate_modbus_1m.py', '--hours', '168'),
    ('15m', 'aggregate_modbus_15m.py', '--hours', '168'),
    ('1h', 'aggregate_modbus_1h.py', '--hours', '168'),
    ('1d', 'aggregate_modbus_1d.py', '--days', '7'),
    ('1w', 'aggregate_modbus_1w.py', '--weeks', '4'),
    ('1mo', 'aggregate_modbus_1mo.py', '--months', '6'),
    ('6mo', 'aggregate_modbus_6mo.py', '--years', '2'),
    ('1y', 'aggregate_modbus_1y.py', '--years', '5'),
]

ENV_AGGREGATIONS = [
    ('1m', 'aggregate_env_1m.py', '--hours', '168'),
    ('15m', 'aggregate_env_15m.py', '--hours', '168'),
    ('1h', 'aggregate_env_1h.py', '--hours', '168'),
    ('1d', 'aggregate_env_1d.py', '--days', '7'),
    ('1w', 'aggregate_env_1w.py', '--weeks', '4'),
    ('1mo', 'aggregate_env_1mo.py', '--months', '6'),
    ('6mo', 'aggregate_env_6mo.py', '--years', '2'),
    ('1y', 'aggregate_env_1y.py', '--years', '5'),
]

SOLAR_AGGREGATIONS = [
    ('1m', 'aggregate_solar_1m.py', '--hours', '168'),
    ('15m', 'aggregate_solar_15m.py', '--hours', '168'),
    ('1h', 'aggregate_solar_1h.py', '--hours', '168'),
    ('1d', 'aggregate_solar_1d.py', '--days', '7'),
    ('1w', 'aggregate_solar_1w.py', '--weeks', '4'),
    ('1mo', 'aggregate_solar_1mo.py', '--months', '6'),
    ('6mo', 'aggregate_solar_6mo.py', '--years', '2'),
    ('1y', 'aggregate_solar_1y.py', '--years', '5'),
]

# ============================================================================
# 실행 함수
# ============================================================================

def run_aggregation(sensor_type: str, stage: str, script: str, arg_name: str, arg_val: str) -> bool:
    """
    집계 스크립트 실행
    
    Args:
        sensor_type: 'modbus', 'env', 'solar'
        stage: '1m', '15m', etc.
        script: 스크립트 파일명
        arg_name: 인자 이름
        arg_val: 인자 값
    
    Returns:
        bool: 성공 여부
    """
    log.info(f"[{sensor_type.upper()}] Running {stage} aggregation...")
    
    folder = f"aggreagte_{sensor_type}" if sensor_type == "modbus" else f"aggregate_{sensor_type}"
    script_path = Path(__file__).parent / folder / script
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), arg_name, arg_val],
            capture_output=True,
            text=True,
            timeout=300  # 5분 타임아웃
        )
        
        if result.returncode == 0:
            log.info(f"[{sensor_type.upper()}] {stage} ✅ Success")
            return True
        else:
            log.error(f"[{sensor_type.upper()}] {stage} ❌ Failed")
            log.error(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        log.error(f"[{sensor_type.upper()}] {stage} ⏱️  Timeout")
        return False
    except Exception as e:
        log.error(f"[{sensor_type.upper()}] {stage} ❌ Exception: {e}")
        return False


def run_sensor_aggregations(sensor_type: str, aggregations: list) -> dict:
    """
    특정 센서의 모든 집계 실행
    
    Args:
        sensor_type: 'modbus', 'env', 'solar'
        aggregations: 집계 설정 리스트
    
    Returns:
        dict: 결과 통계
    """
    log.info("=" * 70)
    log.info(f"{sensor_type.upper()} Aggregations Starting")
    log.info("=" * 70)
    log.info("")
    
    results = {'success': 0, 'failed': 0, 'stages': []}
    
    for stage, script, arg_name, arg_val in aggregations:
        success = run_aggregation(sensor_type, stage, script, arg_name, arg_val)
        
        if success:
            results['success'] += 1
        else:
            results['failed'] += 1
        
        results['stages'].append({
            'stage': stage,
            'success': success
        })
    
    log.info("")
    log.info("=" * 70)
    log.info(f"{sensor_type.upper()} Complete: {results['success']} success, {results['failed']} failed")
    log.info("=" * 70)
    log.info("")
    
    return results


def run_all(sensor_filter: str = 'all'):
    """
    모든 센서 집계 실행
    
    Args:
        sensor_filter: 'all', 'modbus', 'env', 'solar'
    """
    log.info("╔" + "═" * 68 + "╗")
    log.info("║" + " " * 20 + "ALL AGGREGATIONS START" + " " * 26 + "║")
    log.info("╚" + "═" * 68 + "╝")
    log.info("")
    
    total_results = {'success': 0, 'failed': 0}
    
    # Modbus
    if sensor_filter in ['all', 'modbus']:
        result = run_sensor_aggregations('modbus', MODBUS_AGGREGATIONS)
        total_results['success'] += result['success']
        total_results['failed'] += result['failed']
    
    # Env
    if sensor_filter in ['all', 'env']:
        result = run_sensor_aggregations('env', ENV_AGGREGATIONS)
        total_results['success'] += result['success']
        total_results['failed'] += result['failed']
    
    # Solar
    if sensor_filter in ['all', 'solar']:
        result = run_sensor_aggregations('solar', SOLAR_AGGREGATIONS)
        total_results['success'] += result['success']
        total_results['failed'] += result['failed']
    
    # 최종 결과
    log.info("")
    log.info("╔" + "═" * 68 + "╗")
    log.info("║" + " " * 22 + "FINAL SUMMARY" + " " * 33 + "║")
    log.info("╠" + "═" * 68 + "╣")
    log.info(f"║  Total Success: {total_results['success']:>3}                                                ║")
    log.info(f"║  Total Failed:  {total_results['failed']:>3}                                                ║")
    log.info("╚" + "═" * 68 + "╝")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run all sensor aggregations"
    )
    parser.add_argument(
        '--sensor',
        type=str,
        default='all',
        choices=['all', 'modbus', 'env', 'solar'],
        help='Sensor type to aggregate (default: all)'
    )
    
    args = parser.parse_args()
    
    run_all(sensor_filter=args.sensor)


if __name__ == '__main__':
    main()
