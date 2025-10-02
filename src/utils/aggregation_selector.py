"""
집계 테이블 자동 선택 유틸리티
"""

from datetime import datetime
from typing import Literal

AggregationLevel = Literal["raw", "1m", "15m", "1h", "1d", "1w", "1mo", "6mo", "1y"]


def select_aggregation_level(
    start_time: datetime,
    end_time: datetime
) -> tuple[AggregationLevel, str]:
    """
    시간 범위에 따라 최적의 집계 레벨 및 time_bucket 간격 선택
    
    Args:
        start_time: 시작 시간 (datetime)
        end_time: 종료 시간 (datetime)
    
    Returns:
        tuple: (집계 레벨, time_bucket 간격)
        
    예시:
        - 1시간 이하 → ("raw", "1 minute")
        - 1~6시간 → ("1m", "5 minutes")
        - 6시간~3일 → ("15m", "1 hour")
        - 3~7일 → ("1h", "6 hours")
        - 7일~1개월 → ("1d", "1 day")
        - 1~3개월 → ("1w", "1 week")
        - 3개월~1년 → ("1mo", "1 month")
        - 1~5년 → ("6mo", "6 months")
        - 5년 이상 → ("1y", "1 year")
    """
    duration = end_time - start_time
    hours = duration.total_seconds() / 3600
    days = duration.days
    
    if hours <= 1:
        return ("raw", "1 minute")
    elif hours <= 6:
        return ("1m", "5 minutes")
    elif days <= 3:
        return ("15m", "1 hour")
    elif days <= 7:
        return ("1h", "6 hours")
    elif days <= 30:
        return ("1d", "1 day")
    elif days <= 90:
        return ("1w", "1 week")
    elif days <= 365:
        return ("1mo", "1 month")
    elif days <= 1825:  # ~5년
        return ("6mo", "6 months")
    else:
        return ("1y", "1 year")


def get_table_suffix(agg_level: AggregationLevel) -> str:
    """
    집계 레벨에 따른 테이블 suffix 반환
    
    Args:
        agg_level: 집계 레벨
    
    Returns:
        str: 테이블 suffix (빈 문자열 또는 "_1m", "_15m" 등)
    """
    if agg_level == "raw":
        return ""
    return f"_{agg_level}"


def get_time_column(agg_level: AggregationLevel) -> str:
    """
    집계 레벨에 따른 시간 컬럼 이름
    
    Args:
        agg_level: 집계 레벨
    
    Returns:
        str: 시간 컬럼 이름 ("time_stamp" 또는 "bucket")
    """
    if agg_level == "raw":
        return "time_stamp"
    return "bucket"


def get_column_prefix(agg_level: AggregationLevel) -> tuple[str, str, str]:
    """
    집계 레벨에 따른 컬럼 prefix 반환
    
    Args:
        agg_level: 집계 레벨
    
    Returns:
        tuple: (avg_prefix, max_prefix, min_prefix)
        
    예시:
        - raw → ("", "", "")
        - 집계 → ("avg_", "max_", "min_")
    """
    if agg_level == "raw":
        return ("", "", "")
    return ("avg_", "max_", "min_")
