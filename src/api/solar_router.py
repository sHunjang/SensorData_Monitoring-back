"""
일사량(Solar) 센서 데이터 API Router

이 모듈은 일사량 센서 데이터를 조회하는 REST API 엔드포인트를 제공합니다.

주요 엔드포인트:
    GET /data/solar/query
        - 시간 범위 및 집계 레벨에 따른 히스토리 데이터 조회
        - preset 파라미터로 자동 집계 테이블 선택
    
    GET /data/solar/realtime
        - 실시간 최신 데이터 조회

자동 집계 테이블 선택:
    - preset에 따라 최적의 집계 레벨 자동 선택
    - 1m, 15m, 1h, 1d, 1w, 1mo 지원

작성일: 2025-10-10
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from src.db.client import get_cursor
from src.config.settings import settings
import logging

router = APIRouter(prefix="/data/solar", tags=["solar"])
logger = logging.getLogger(__name__)

# ========================================
# 허용된 Preset 목록
# ========================================
ALLOWED_PRESETS = {"1m", "15m", "1h", "1d", "1w", "1mo"}

# Solar 디바이스 ID (고정)
SOLAR_DEVICE = settings.SOLAR_ID  # 31

# ========================================
# 집계 테이블 선택 함수
# ========================================
def select_table_by_preset(preset: str) -> str:
    """
    Preset에 따라 적절한 집계 테이블 선택
    
    Args:
        preset: 시간 프리셋 ("1m", "15m", "1h", "1d", "1w", "1mo")
    
    Returns:
        str: 테이블 이름
    
    선택 로직:
        - 1m: solar_data_31_1m (1분 집계)
        - 15m: solar_data_31_15m (15분 집계)
        - 1h, 1d, 1w, 1mo: solar_data_31_1m (1분 집계로 샘플링)
    """
    if preset == "1m":
        return f"solar_data_{SOLAR_DEVICE}_1m"
    elif preset == "15m":
        return f"solar_data_{SOLAR_DEVICE}_15m"
    else:  # 1h, 1d, 1w, 1mo
        return f"solar_data_{SOLAR_DEVICE}_1m"

# ========================================
# 히스토리 데이터 조회 엔드포인트
# ========================================
@router.get("/query")
async def get_solar_data(
    preset: str = Query(..., description="Time preset: 1m, 15m, 1h, 1d, 1w, 1mo"),
    maxpoints: int = Query(100, description="Maximum data points", ge=1, le=10000),
    deviceid: int = Query(31, description="Solar device ID"),
    start: Optional[str] = Query(None, description="Start time (ISO 8601)"),
    end: Optional[str] = Query(None, description="End time (ISO 8601)"),
) -> Dict[str, Any]:
    """
    일사량 센서 히스토리 데이터 조회
    
    이 엔드포인트는 지정된 시간 범위와 집계 레벨에 따라
    일사량 데이터를 조회합니다.
    
    Args:
        preset: 시간 단위 ("1m", "15m", "1h", "1d", "1w", "1mo")
        maxpoints: 반환할 최대 데이터 포인트 수 (1-10000)
        deviceid: Solar 센서 ID (31)
        start: 시작 시각 (ISO 8601 형식)
        end: 종료 시각 (ISO 8601 형식)
    
    Returns:
        Dict: JSON 응답 (Frontend 호환 형식)
            {
                "data": [
                    {
                        "bucket": "2025-10-10T00:00:00+00:00",
                        "irradiance": 850.5
                    },
                    ...
                ]
            }
    
    Raises:
        HTTPException 400: 잘못된 파라미터
        HTTPException 500: 서버 오류
    
    예시:
        GET /data/solar/query?preset=1h&maxpoints=100&deviceid=31
    """
    
    # ========================================
    # 1. 파라미터 검증
    # ========================================
    if preset not in ALLOWED_PRESETS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid preset. Allowed: {', '.join(ALLOWED_PRESETS)}"
        )
    
    if deviceid != SOLAR_DEVICE:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid device_id. Solar only supports device_id={SOLAR_DEVICE}"
        )
    
    # ========================================
    # 2. 시간 범위 파싱
    # ========================================
    try:
        if end:
            end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
        else:
            end_time = datetime.now(timezone.utc)
        
        if start:
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
        else:
            # preset에 따른 기본 범위
            if preset == "1m":
                start_time = end_time - timedelta(minutes=1)
            elif preset == "15m":
                start_time = end_time - timedelta(minutes=15)
            elif preset == "1h":
                start_time = end_time - timedelta(hours=1)
            elif preset == "1d":
                start_time = end_time - timedelta(days=1)
            elif preset == "1w":
                start_time = end_time - timedelta(weeks=1)
            elif preset == "1mo":
                start_time = end_time - timedelta(days=30)
            else:
                start_time = end_time - timedelta(hours=1)
                
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid datetime format: {e}"
        )
    
    # ========================================
    # 3. 테이블 선택
    # ========================================
    table_name = select_table_by_preset(preset)
    
    logger.info(
        f"📊 Solar query: preset={preset}, device={deviceid}, "
        f"table={table_name}, range={start_time} to {end_time}"
    )
    
    # ========================================
    # 4. 데이터 조회
    # ========================================
    try:
        with get_cursor() as cur:
            # 데이터 개수 확인
            count_sql = f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE timestamp BETWEEN %s AND %s;
            """
            cur.execute(count_sql, (start_time, end_time))
            total_count = cur.fetchone()[0]
            
            if total_count == 0:
                logger.warning(f"⚠️ No data for range: {start_time} to {end_time}")
                return {"data": []}
            
            # 샘플링 간격 계산
            if total_count > maxpoints:
                # LIMIT으로 샘플링
                data_sql = f"""
                    SELECT 
                        timestamp,
                        avg_irradiance_w_per_m2
                    FROM {table_name}
                    WHERE timestamp BETWEEN %s AND %s
                    ORDER BY timestamp
                    LIMIT %s;
                """
                cur.execute(data_sql, (start_time, end_time, maxpoints))
            else:
                # 전체 데이터 반환
                data_sql = f"""
                    SELECT 
                        timestamp,
                        avg_irradiance_w_per_m2
                    FROM {table_name}
                    WHERE timestamp BETWEEN %s AND %s
                    ORDER BY timestamp;
                """
                cur.execute(data_sql, (start_time, end_time))
            
            rows = cur.fetchall()
            
            # ========================================
            # 5. 응답 데이터 구성 (Frontend 호환 형식)
            # ========================================
            data = [
                {
                    "bucket": row[0].isoformat(),
                    "irradiance": round(row[1], 1) if row[1] is not None else None,
                }
                for row in rows
            ]
            
            logger.info(f"✅ Solar query success: {len(data)} points returned")
            
            return {"data": data}
            
    except Exception as e:
        logger.exception(f"❌ Query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

# ========================================
# 실시간 데이터 조회 엔드포인트
# ========================================
@router.get("/realtime")
async def get_solar_realtime() -> Dict[str, Any]:
    """
    일사량 센서 실시간 데이터 조회
    
    최신 1건의 데이터를 반환합니다.
    
    Returns:
        Dict: JSON 응답
            {
                "device_id": 31,
                "timestamp": "2025-10-10T10:30:00+00:00",
                "irradiance": 850.5
            }
    
    예시:
        GET /data/solar/realtime
    """
    
    table_name = f"solar_data_{SOLAR_DEVICE}_1m"
    
    try:
        with get_cursor() as cur:
            sql = f"""
                SELECT 
                    timestamp,
                    avg_irradiance_w_per_m2
                FROM {table_name}
                ORDER BY timestamp DESC
                LIMIT 1;
            """
            cur.execute(sql)
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="No data available"
                )
            
            return {
                "device_id": SOLAR_DEVICE,
                "timestamp": row[0].isoformat(),
                "irradiance": round(row[1], 1) if row[1] is not None else None,
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Realtime query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )
