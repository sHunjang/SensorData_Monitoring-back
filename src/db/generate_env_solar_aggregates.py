"""
Env & Solar 집계 스크립트 자동 생성기

생성 대상:
  - Env (Device 21-23): 8단계 = 8개 스크립트
  - Solar (Device 31): 8단계 = 8개 스크립트
  총 16개 파일 자동 생성

실행:
  python -m src.db.generate_env_solar_aggregates
"""

from pathlib import Path

# ============================================================================
# Env 집계 템플릿
# ============================================================================

ENV_TEMPLATE = '''"""
Env {stage_name} 집계 스크립트 (Device 21-23)

실행:
  python src/db/aggregate_env/aggregate_env_{stage}.py {arg_example}
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

if __name__ == '__main__':
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.db.client import get_cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger("agg_env_{stage}")

DEVICE_IDS = [21, 22, 23]

def get_aggregate_sql(device_id: int, start_time: datetime, end_time: datetime) -> str:
    return f"""
    INSERT INTO agg_env_{{device_id}}_{stage} (
        bucket, avg_temperature, max_temperature, min_temperature,
        avg_humidity, max_humidity, min_humidity, sample_count
    )
    SELECT
        time_bucket('{time_bucket}', {source_column}) AS bucket_{stage},
        AVG({prefix}temperature),
        MAX({max_col}temperature),
        MIN({min_col}temperature),
        AVG({prefix}humidity),
        MAX({max_col}humidity),
        MIN({min_col}humidity),
        {count_expr} AS sample_count
    FROM {source_table}{{device_id}}{suffix}
    WHERE {source_column} >= %s AND {source_column} < %s
    GROUP BY bucket_{stage}
    ON CONFLICT (bucket) DO UPDATE SET
        avg_temperature = EXCLUDED.avg_temperature,
        max_temperature = EXCLUDED.max_temperature,
        min_temperature = EXCLUDED.min_temperature,
        avg_humidity = EXCLUDED.avg_humidity,
        max_humidity = EXCLUDED.max_humidity,
        min_humidity = EXCLUDED.min_humidity,
        sample_count = EXCLUDED.sample_count;
    """

def aggregate_device(device_id: int, start_time: datetime, end_time: datetime) -> int:
    sql = get_aggregate_sql(device_id, start_time, end_time)
    try:
        with get_cursor() as cur:
            cur.execute(sql, (start_time, end_time))
            row_count = cur.rowcount
        log.info(f"Device {{device_id}}: {{row_count}} rows aggregated")
        return row_count
    except Exception as e:
        log.error(f"Device {{device_id}} aggregation failed: {{e}}")
        return 0

def aggregate_all({param_name}: int = {default_val}):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta({time_delta})
    
    log.info("=" * 70)
    log.info("Env {stage_name} Aggregation")
    log.info("=" * 70)
    log.info(f"Period: {{start_time}} ~ {{end_time}}")
    log.info(f"Devices: {{DEVICE_IDS}}")
    log.info("")
    
    total_rows = 0
    for device_id in DEVICE_IDS:
        rows = aggregate_device(device_id, start_time, end_time)
        total_rows += rows
    
    log.info("")
    log.info("=" * 70)
    log.info(f"Total aggregated: {{total_rows}} rows")
    log.info("=" * 70)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Env {stage_name} Aggregation")
    parser.add_argument('--{param_name}', type=int, default={default_val})
    args = parser.parse_args()
    aggregate_all({param_name}=args.{param_name})

if __name__ == '__main__':
    main()
'''

# ============================================================================
# Solar 집계 템플릿
# ============================================================================

SOLAR_TEMPLATE = '''"""
Solar {stage_name} 집계 스크립트 (Device 31)

실행:
  python src/db/aggregate_solar/aggregate_solar_{stage}.py {arg_example}
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

if __name__ == '__main__':
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.db.client import get_cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger("agg_solar_{stage}")

def get_aggregate_sql(start_time: datetime, end_time: datetime) -> str:
    return f"""
    INSERT INTO agg_solar_{stage} (
        bucket, avg_irradiance, max_irradiance, min_irradiance, sample_count
    )
    SELECT
        time_bucket('{time_bucket}', {source_column}) AS bucket_{stage},
        AVG({prefix}irradiance),
        MAX({max_col}irradiance),
        MIN({min_col}irradiance),
        {count_expr} AS sample_count
    FROM {source_table}{suffix}
    WHERE {source_column} >= %s AND {source_column} < %s
    GROUP BY bucket_{stage}
    ON CONFLICT (bucket) DO UPDATE SET
        avg_irradiance = EXCLUDED.avg_irradiance,
        max_irradiance = EXCLUDED.max_irradiance,
        min_irradiance = EXCLUDED.min_irradiance,
        sample_count = EXCLUDED.sample_count;
    """

def aggregate(start_time: datetime, end_time: datetime) -> int:
    sql = get_aggregate_sql(start_time, end_time)
    try:
        with get_cursor() as cur:
            cur.execute(sql, (start_time, end_time))
            row_count = cur.rowcount
        log.info(f"Solar: {{row_count}} rows aggregated")
        return row_count
    except Exception as e:
        log.error(f"Solar aggregation failed: {{e}}")
        return 0

def aggregate_all({param_name}: int = {default_val}):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta({time_delta})
    
    log.info("=" * 70)
    log.info("Solar {stage_name} Aggregation")
    log.info("=" * 70)
    log.info(f"Period: {{start_time}} ~ {{end_time}}")
    log.info("")
    
    rows = aggregate(start_time, end_time)
    
    log.info("")
    log.info("=" * 70)
    log.info(f"Total aggregated: {{rows}} rows")
    log.info("=" * 70)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Solar {stage_name} Aggregation")
    parser.add_argument('--{param_name}', type=int, default={default_val})
    args = parser.parse_args()
    aggregate_all({param_name}=args.{param_name})

if __name__ == '__main__':
    main()
'''

# ============================================================================
# 집계 단계 설정
# ============================================================================

STAGES_CONFIG = {
    '1m': {
        'stage_name': '1-Minute',
        'time_bucket': '1 minute',
        'source_table': {'env': 'env_data_', 'solar': 'solar_data'},
        'source_column': 'time_stamp',
        'suffix': {'env': '', 'solar': ''},
        'prefix': '',
        'max_col': '',
        'min_col': '',
        'count_expr': 'COUNT(*)',
        'param_name': 'hours',
        'default_val': 24,
        'time_delta': 'hours=hours',
        'arg_example': '--hours 168'
    },
    '15m': {
        'stage_name': '15-Minute',
        'time_bucket': '15 minutes',
        'source_table': {'env': 'agg_env_', 'solar': 'agg_solar_'},
        'source_column': 'bucket',
        'suffix': {'env': '_1m', 'solar': '1m'},
        'prefix': 'avg_',
        'max_col': 'max_',
        'min_col': 'min_',
        'count_expr': 'SUM(sample_count)',
        'param_name': 'hours',
        'default_val': 24,
        'time_delta': 'hours=hours',
        'arg_example': '--hours 168'
    },
    '1h': {
        'stage_name': '1-Hour',
        'time_bucket': '1 hour',
        'source_table': {'env': 'agg_env_', 'solar': 'agg_solar_'},
        'source_column': 'bucket',
        'suffix': {'env': '_15m', 'solar': '15m'},
        'prefix': 'avg_',
        'max_col': 'max_',
        'min_col': 'min_',
        'count_expr': 'SUM(sample_count)',
        'param_name': 'hours',
        'default_val': 24,
        'time_delta': 'hours=hours',
        'arg_example': '--hours 168'
    },
    '1d': {
        'stage_name': '1-Day',
        'time_bucket': '1 day',
        'source_table': {'env': 'agg_env_', 'solar': 'agg_solar_'},
        'source_column': 'bucket',
        'suffix': {'env': '_1h', 'solar': '1h'},
        'prefix': 'avg_',
        'max_col': 'max_',
        'min_col': 'min_',
        'count_expr': 'SUM(sample_count)',
        'param_name': 'days',
        'default_val': 7,
        'time_delta': 'days=days',
        'arg_example': '--days 7'
    },
    '1w': {
        'stage_name': '1-Week',
        'time_bucket': '7 days',
        'source_table': {'env': 'agg_env_', 'solar': 'agg_solar_'},
        'source_column': 'bucket',
        'suffix': {'env': '_1d', 'solar': '1d'},
        'prefix': 'avg_',
        'max_col': 'max_',
        'min_col': 'min_',
        'count_expr': 'SUM(sample_count)',
        'param_name': 'weeks',
        'default_val': 4,
        'time_delta': 'weeks=weeks',
        'arg_example': '--weeks 4'
    },
    '1mo': {
        'stage_name': '1-Month',
        'time_bucket': '1 month',
        'source_table': {'env': 'agg_env_', 'solar': 'agg_solar_'},
        'source_column': 'bucket',
        'suffix': {'env': '_1d', 'solar': '1d'},
        'prefix': 'avg_',
        'max_col': 'max_',
        'min_col': 'min_',
        'count_expr': 'SUM(sample_count)',
        'param_name': 'months',
        'default_val': 6,
        'time_delta': 'days=months * 30',
        'arg_example': '--months 6'
    },
    '6mo': {
        'stage_name': '6-Month',
        'time_bucket': '6 months',
        'source_table': {'env': 'agg_env_', 'solar': 'agg_solar_'},
        'source_column': 'bucket',
        'suffix': {'env': '_1mo', 'solar': '1mo'},
        'prefix': 'avg_',
        'max_col': 'max_',
        'min_col': 'min_',
        'count_expr': 'SUM(sample_count)',
        'param_name': 'years',
        'default_val': 2,
        'time_delta': 'days=years * 365',
        'arg_example': '--years 2'
    },
    '1y': {
        'stage_name': '1-Year',
        'time_bucket': '1 year',
        'source_table': {'env': 'agg_env_', 'solar': 'agg_solar_'},
        'source_column': 'bucket',
        'suffix': {'env': '_6mo', 'solar': '6mo'},
        'prefix': 'avg_',
        'max_col': 'max_',
        'min_col': 'min_',
        'count_expr': 'SUM(sample_count)',
        'param_name': 'years',
        'default_val': 5,
        'time_delta': 'days=years * 365',
        'arg_example': '--years 5'
    }
}

# ============================================================================
# 메인 실행
# ============================================================================

def main():
    project_root = Path(__file__).resolve().parent
    
    # 디렉토리 생성
    env_dir = project_root / "aggregate_env"
    solar_dir = project_root / "aggregate_solar"
    env_dir.mkdir(exist_ok=True)
    solar_dir.mkdir(exist_ok=True)
    
    # __init__.py 생성
    (env_dir / "__init__.py").touch()
    (solar_dir / "__init__.py").touch()
    
    print("=" * 70)
    print("Env & Solar Aggregation Script Generator")
    print("=" * 70)
    print()
    
    # Env 스크립트 생성
    print("📦 Generating Env scripts...")
    for stage, config in STAGES_CONFIG.items():
        filename = env_dir / f"aggregate_env_{stage}.py"
        
        # Env용 설정 변환
        env_config = config.copy()
        env_config['source_table'] = config['source_table']['env']
        env_config['suffix'] = config['suffix']['env']
        
        code = ENV_TEMPLATE.format(stage=stage, **env_config)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"  ✅ {filename.name}")
    
    # Solar 스크립트 생성
    print()
    print("☀️  Generating Solar scripts...")
    for stage, config in STAGES_CONFIG.items():
        filename = solar_dir / f"aggregate_solar_{stage}.py"
        
        # Solar용 설정 변환
        solar_config = config.copy()
        solar_config['source_table'] = config['source_table']['solar']
        solar_config['suffix'] = config['suffix']['solar']
        
        code = SOLAR_TEMPLATE.format(stage=stage, **solar_config)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"  ✅ {filename.name}")
    
    print()
    print("=" * 70)
    print("Generation Complete!")
    print("=" * 70)
    print()
    print("Generated:")
    print(f"  - Env: 8 files in {env_dir}")
    print(f"  - Solar: 8 files in {solar_dir}")
    print()
    print("Next: Run aggregations")
    print("  # Env")
    print("  python src/db/aggregate_env/aggregate_env_1m.py --hours 168")
    print("  python src/db/aggregate_env/aggregate_env_15m.py --hours 168")
    print("  ...")
    print()
    print("  # Solar")
    print("  python src/db/aggregate_solar/aggregate_solar_1m.py --hours 168")
    print("  python src/db/aggregate_solar/aggregate_solar_15m.py --hours 168")
    print("  ...")

if __name__ == '__main__':
    main()
