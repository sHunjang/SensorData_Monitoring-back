"""
집계 테이블 자동 선택기

이 모듈은 시간 범위와 요청된 포인트 수에 따라 최적의 집계 테이블을 자동으로 선택합니다.

주요 기능:
    1. 시간 범위에 따른 최적 집계 레벨 자동 선택
    2. maxpoints를 고려한 데이터 밀도 계산
    3. 성능 최적화를 위한 테이블 선택

사용법:
    from src.aggregator.aggregation_selector import select_optimal_table
    
    table, actual_preset = select_optimal_table(
        device_type="modbus",
        device_id=11,
        start_time=start,
        end_time=end,
        requested_preset="auto",
        maxpoints=1000
    )

작성일: 2025-10-10
"""

from datetime import datetime, timedelta
from typing import Tuple


def select_optimal_table(
    device_type: str,
    device_id: int,
    start_time: datetime,
    end_time: datetime,
    requested_preset: str = "auto",
    maxpoints: int = 1000
) -> Tuple[str, str]:
    """
    최적의 집계 테이블 자동 선택
    
    이 함수는 시간 범위와 요청된 포인트 수를 고려하여
    가장 적절한 집계 레벨을 자동으로 선택합니다.
    
    Args:
        device_type: 디바이스 타입 ("modbus", "env", "solar")
        device_id: 디바이스 ID
        start_time: 시작 시각
        end_time: 종료 시각
        requested_preset: 요청된 preset ("auto" 또는 "1m", "15m" 등)
        maxpoints: 최대 반환 포인트 수
    
    Returns:
        Tuple[str, str]: (테이블명, 실제 사용된 preset)
    
    선택 로직:
        1. requested_preset이 "auto"가 아니면 해당 preset 사용
        2. 시간 범위 계산
        3. 각 집계 레벨의 예상 포인트 수 계산
        4. maxpoints에 가장 가까운 레벨 선택
    
    예시:
        >>> select_optimal_table("modbus", 11, start, end, "auto", 1000)
        ("modbus_data_11_15m", "15m")
    
    집계 레벨별 포인트 밀도:
        - 1m: 60 points/hour
        - 15m: 4 points/hour
        - 1h: 1 point/hour
        - 1d: 1 point/day
    """
    
    # ========================================
    # 1. 명시적 preset이 지정된 경우
    # ========================================
    if requested_preset != "auto":
        table_name = f"{device_type}_data_{device_id}_{requested_preset}"
        return table_name, requested_preset
    
    # ========================================
    # 2. 시간 범위 계산
    # ========================================
    duration = end_time - start_time
    hours = duration.total_seconds() / 3600
    
    # ========================================
    # 3. 각 집계 레벨의 예상 포인트 수 계산
    # ========================================
    # 포인트 밀도 (points per hour)
    density = {
        "1m": 60,      # 1분 = 60 points/hour
        "15m": 4,      # 15분 = 4 points/hour
        "1h": 1,       # 1시간 = 1 point/hour
        "1d": 1/24,    # 1일 = 1/24 points/hour
    }
    
    # 각 레벨의 예상 포인트 수
    estimated_points = {
        level: int(hours * points_per_hour)
        for level, points_per_hour in density.items()
    }
    
    # ========================================
    # 4. maxpoints에 가장 가까운 레벨 선택
    # ========================================
    # 목표: estimated_points가 maxpoints 이하인 것 중 가장 큰 것
    # 또는 모든 레벨이 maxpoints를 초과하면 가장 작은 것
    
    best_preset = "1m"  # 기본값
    best_points = estimated_points["1m"]
    
    # maxpoints 이하인 레벨 중 가장 세밀한 것 선택
    for level in ["1m", "15m", "1h", "1d"]:
        points = estimated_points[level]
        
        if points <= maxpoints:
            # maxpoints 이하면서 가장 세밀한 레벨
            best_preset = level
            best_points = points
            break
    
    # ========================================
    # 5. 테이블명 생성
    # ========================================
    table_name = f"{device_type}_data_{device_id}_{best_preset}"
    
    return table_name, best_preset


# ========================================
# 직접 실행 시 테스트
# ========================================
if __name__ == "__main__":
    """
    집계 테이블 선택기 테스트
    
    사용법:
        python -m src.aggregator.aggregation_selector
    """
    import logging
    
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("selector_test")
    
    log.info("=" * 60)
    log.info("🧪 집계 테이블 선택기 테스트")
    log.info("=" * 60)
    
    # 테스트 케이스
    test_cases = [
        {
            "name": "1시간 범위, 1000 포인트",
            "duration": timedelta(hours=1),
            "maxpoints": 1000,
            "expected": "1m"
        },
        {
            "name": "6시간 범위, 1000 포인트",
            "duration": timedelta(hours=6),
            "maxpoints": 1000,
            "expected": "15m"
        },
        {
            "name": "24시간 범위, 1000 포인트",
            "duration": timedelta(hours=24),
            "maxpoints": 1000,
            "expected": "15m"
        },
        {
            "name": "7일 범위, 1000 포인트",
            "duration": timedelta(days=7),
            "maxpoints": 1000,
            "expected": "1h"
        },
        {
            "name": "30일 범위, 1000 포인트",
            "duration": timedelta(days=30),
            "maxpoints": 1000,
            "expected": "1h"
        },
    ]
    
    # 테스트 실행
    now = datetime.now()
    
    for i, test in enumerate(test_cases, 1):
        log.info(f"\n테스트 {i}: {test['name']}")
        
        end_time = now
        start_time = now - test['duration']
        
        table_name, preset = select_optimal_table(
            device_type="modbus",
            device_id=11,
            start_time=start_time,
            end_time=end_time,
            requested_preset="auto",
            maxpoints=test['maxpoints']
        )
        
        log.info(f"   범위: {test['duration']}")
        log.info(f"   maxpoints: {test['maxpoints']}")
        log.info(f"   선택된 preset: {preset}")
        log.info(f"   테이블: {table_name}")
        log.info(f"   예상: {test['expected']}")
        
        if preset == test['expected']:
            log.info(f"   ✅ 통과")
        else:
            log.warning(f"   ⚠️  예상과 다름 (예상: {test['expected']}, 실제: {preset})")
    
    log.info("\n" + "=" * 60)
    log.info("✅ 테스트 완료")
    log.info("=" * 60)
