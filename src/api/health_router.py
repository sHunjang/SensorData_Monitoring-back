"""
Health Check Router

시스템 상태 및 설정 정보를 제공하는 엔드포인트

작성일: 2025-10-10
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config.settings import settings
from src.db.client import get_cursor

log = logging.getLogger("health")

router = APIRouter(tags=["Health"])


# ========================================
# Response Models
# ========================================

class HealthResponse(BaseModel):
    """헬스 체크 응답 모델"""
    status: str
    timestamp: str
    database: str
    mode: str
    devices: Dict[str, Any]


# ========================================
# Endpoints
# ========================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    시스템 헬스 체크
    
    Returns:
        HealthResponse: 시스템 상태 및 설정 정보
        
    Raises:
        HTTPException: 데이터베이스 연결 실패 시 500 에러
    
    Example:
        GET /health
        
        Response:
        {
            "status": "ok",
            "timestamp": "2025-10-10T14:43:26.123Z",
            "database": "connected",
            "mode": "dummy",
            "devices": {
                "modbus_3w": [11, 12, 13],
                "modbus_4w": [14, 15],
                "env": [21, 22, 23],
                "solar": 31
            }
        }
    """
    try:
        # 데이터베이스 연결 확인
        with get_cursor() as cur:
            cur.execute("SELECT 1")
            db_status = "connected"
    except Exception as e:
        log.error(f"❌ Database connection failed: {e}")
        db_status = "disconnected"
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}"
        )
    
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "mode": settings.MODE,
        "devices": {
            "modbus_3w": settings.MODBUS_3W_IDS,  # ✅ 수정: THREE_PHASE_THREE_WIRE_IDS → MODBUS_3W_IDS
            "modbus_4w": settings.MODBUS_4W_IDS,  # ✅ 수정: THREE_PHASE_FOUR_WIRE_IDS → MODBUS_4W_IDS
            "env": settings.ENV_IDS,
            "solar": settings.SOLAR_ID,
        }
    }


@router.get("/health/db")
async def health_check_db():
    """
    데이터베이스 상세 헬스 체크
    
    Returns:
        dict: 각 센서별 테이블 존재 여부 및 레코드 수
        
    Example:
        GET /health/db
        
        Response:
        {
            "status": "ok",
            "tables": {
                "modbus_data_11_1m": {"exists": true, "count": 1234},
                "env_data_21_1m": {"exists": true, "count": 567},
                ...
            }
        }
    """
    try:
        table_status = {}
        
        with get_cursor() as cur:
            # Modbus 테이블 확인
            all_modbus = settings.MODBUS_3W_IDS + settings.MODBUS_4W_IDS
            for device_id in all_modbus:
                table_name = f"modbus_data_{device_id}_1m"
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cur.fetchone()[0]
                table_status[table_name] = {"exists": True, "count": count}
            
            # Env 테이블 확인
            for device_id in settings.ENV_IDS:
                table_name = f"env_data_{device_id}_1m"
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cur.fetchone()[0]
                table_status[table_name] = {"exists": True, "count": count}
            
            # Solar 테이블 확인
            table_name = f"solar_data_{settings.SOLAR_ID}_1m"
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            table_status[table_name] = {"exists": True, "count": count}
        
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tables": table_status
        }
        
    except Exception as e:
        log.error(f"❌ Database health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database health check failed: {str(e)}"
        )
