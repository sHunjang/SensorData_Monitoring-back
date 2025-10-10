"""
유틸리티 함수 모음

이 모듈은 공통으로 사용되는 유틸리티 함수를 제공합니다.

주요 기능:
    1. 시간 범위 파싱
    2. Preset에 따른 기본 시간 범위 계산
    3. 데이터 샘플링
    4. 날짜/시간 변환

작성일: 2025-10-10
"""

from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional


def parse_time_range(
    start: Optional[str],
    end: Optional[str],
    preset: str
) -> Tuple[datetime, datetime]:
    """
    시간 범위 파싱 및 기본값 계산
    
    Args:
        start: 시작 시각 (ISO 8601 형식) 또는 None
        end: 종료 시각 (ISO 8601 형식) 또는 None
        preset: 시간 프리셋 ("1m", "15m", "1h", "1d", "1w", "1mo")
    
    Returns:
        Tuple[datetime, datetime]: (start_time, end_time)
    
    동작:
        - end가 None이면 현재 시각 사용
        - start가 None이면 preset에 따라 자동 계산
        - 모든 시각은 UTC 기준
    
    예시:
        >>> parse_time_range(None, None, "1h")
        (datetime(2025, 10, 10, 12, 0), datetime(2025, 10, 10, 13, 0))
    
    Raises:
        ValueError: 잘못된 날짜 형식
    """
    # 종료 시각: 지정되지 않으면 현재 시각
    if end:
        end_time = datetime.fromisoformat(end)
    else:
        end_time = datetime.now(timezone.utc)
    
    # 시작 시각: 지정되지 않으면 preset에 따라 자동 계산
    if start:
        start_time = datetime.fromisoformat(start)
    else:
        # Preset에 따른 기본 범위
        preset_ranges = {
            "1m": timedelta(hours=1),      # 1분 데이터: 1시간 범위
            "15m": timedelta(hours=6),     # 15분 데이터: 6시간 범위
            "1h": timedelta(days=1),       # 1시간 데이터: 1일 범위
            "1d": timedelta(days=30),      # 1일 데이터: 30일 범위
            "1w": timedelta(days=90),      # 1주 데이터: 90일 범위
            "1mo": timedelta(days=365),    # 1개월 데이터: 1년 범위
        }
        
        delta = preset_ranges.get(preset, timedelta(hours=1))
        start_time = end_time - delta
    
    return start_time, end_time


def calculate_sample_interval(total_count: int, max_points: int) -> int:
    """
    샘플링 간격 계산
    
    Args:
        total_count: 전체 데이터 개수
        max_points: 최대 반환 포인트 수
    
    Returns:
        int: 샘플링 간격 (1 = 모든 데이터 반환)
    
    예시:
        >>> calculate_sample_interval(1000, 100)
        10  # 10개 중 1개씩 샘플링
    """
    if total_count <= max_points:
        return 1
    
    return max(1, total_count // max_points)


def truncate_to_bucket(dt: datetime, bucket: str) -> datetime:
    """
    시간을 지정된 버킷 단위로 truncate
    
    Args:
        dt: 대상 datetime
        bucket: 버킷 단위 ("1m", "15m", "1h", "1d")
    
    Returns:
        datetime: Truncate된 datetime
    
    예시:
        >>> dt = datetime(2025, 10, 10, 13, 27, 45)
        >>> truncate_to_bucket(dt, "1m")
        datetime(2025, 10, 10, 13, 27, 0)
        >>> truncate_to_bucket(dt, "15m")
        datetime(2025, 10, 10, 13, 15, 0)
        >>> truncate_to_bucket(dt, "1h")
        datetime(2025, 10, 10, 13, 0, 0)
    """
    if bucket == "1m":
        return dt.replace(second=0, microsecond=0)
    elif bucket == "15m":
        minute = (dt.minute // 15) * 15
        return dt.replace(minute=minute, second=0, microsecond=0)
    elif bucket == "1h":
        return dt.replace(minute=0, second=0, microsecond=0)
    elif bucket == "1d":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        return dt


def format_bytes(bytes_size: int) -> str:
    """
    바이트 크기를 사람이 읽기 쉬운 형식으로 변환
    
    Args:
        bytes_size: 바이트 크기
    
    Returns:
        str: 포맷된 문자열 (예: "1.5 MB")
    
    예시:
        >>> format_bytes(1024)
        "1.0 KB"
        >>> format_bytes(1536000)
        "1.5 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def validate_device_id(device_id: int, device_type: str) -> bool:
    """
    디바이스 ID 유효성 검증
    
    Args:
        device_id: 디바이스 ID
        device_type: 디바이스 타입 ("modbus", "env", "solar")
    
    Returns:
        bool: 유효하면 True
    
    예시:
        >>> validate_device_id(11, "modbus")
        True
        >>> validate_device_id(99, "modbus")
        False
    """
    from src.config.settings import settings
    
    if device_type == "modbus":
        return device_id in settings.MODBUS_3W_IDS
    elif device_type == "env":
        return device_id in settings.ENV_IDS
    elif device_type == "solar":
        return device_id == settings.SOLAR_ID
    else:
        return False


def get_table_name(device_id: int, device_type: str, preset: str) -> str:
    """
    디바이스와 preset에 따른 테이블명 생성
    
    Args:
        device_id: 디바이스 ID
        device_type: 디바이스 타입 ("modbus", "env", "solar")
        preset: 시간 프리셋 ("1m", "15m", "1h", etc.)
    
    Returns:
        str: 테이블명
    
    예시:
        >>> get_table_name(11, "modbus", "1m")
        "modbus_data_11_1m"
        >>> get_table_name(21, "env", "15m")
        "env_data_21_15m"
    """
    return f"{device_type}_data_{device_id}_{preset}"


# ========================================
# 직접 실행 시 테스트
# ========================================
if __name__ == "__main__":
    """
    유틸리티 함수 테스트
    
    사용법:
        python -m src.api.utils
    """
    import logging
    
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("utils_test")
    
    log.info("=" * 60)
    log.info("🧪 유틸리티 함수 테스트")
    log.info("=" * 60)
    
    # 1. 시간 범위 파싱 테스트
    log.info("\n📅 시간 범위 파싱 테스트:")
    start, end = parse_time_range(None, None, "1h")
    log.info(f"   Preset '1h': {start} ~ {end}")
    log.info(f"   Duration: {end - start}")
    
    # 2. 샘플링 간격 테스트
    log.info("\n📊 샘플링 간격 테스트:")
    interval = calculate_sample_interval(1000, 100)
    log.info(f"   Total: 1000, Max: 100 → Interval: {interval}")
    
    # 3. Truncate 테스트
    log.info("\n⏰ Truncate 테스트:")
    now = datetime.now()
    log.info(f"   Original: {now}")
    log.info(f"   1m: {truncate_to_bucket(now, '1m')}")
    log.info(f"   15m: {truncate_to_bucket(now, '15m')}")
    log.info(f"   1h: {truncate_to_bucket(now, '1h')}")
    
    # 4. 바이트 포맷 테스트
    log.info("\n💾 바이트 포맷 테스트:")
    log.info(f"   1024 B: {format_bytes(1024)}")
    log.info(f"   1536000 B: {format_bytes(1536000)}")
    log.info(f"   1073741824 B: {format_bytes(1073741824)}")
    
    # 5. 디바이스 ID 검증 테스트
    log.info("\n🔍 디바이스 ID 검증 테스트:")
    log.info(f"   Modbus 11: {validate_device_id(11, 'modbus')}")
    log.info(f"   Modbus 99: {validate_device_id(99, 'modbus')}")
    log.info(f"   Env 21: {validate_device_id(21, 'env')}")
    log.info(f"   Solar 31: {validate_device_id(31, 'solar')}")
    
    # 6. 테이블명 생성 테스트
    log.info("\n📋 테이블명 생성 테스트:")
    log.info(f"   Modbus 11, 1m: {get_table_name(11, 'modbus', '1m')}")
    log.info(f"   Env 21, 15m: {get_table_name(21, 'env', '15m')}")
    log.info(f"   Solar 31, 1h: {get_table_name(31, 'solar', '1h')}")
    
    log.info("\n" + "=" * 60)
    log.info("✅ 모든 테스트 완료")
    log.info("=" * 60)
