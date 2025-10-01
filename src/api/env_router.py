"""
env_router.py - 환경 데이터(온도/습도) API 라우터 (수정된 버전)

주요 기능:
- 4단계 preset 지원: 1h(1시간), 1d(1일), 1w(1주일), 1mo(1달)
- 1주일/1달 preset에서 날짜별 집계로 X축 라벨 중복 문제 해결
- 기존 client.py의 get_cursor() 사용
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from src.db.client import get_cursor  # 🔧 올바른 임포트 경로
import logging

router = APIRouter(prefix="/data/env", tags=["env"])
logger = logging.getLogger(__name__)

@router.get("/query")
async def get_env_data(
    deviceid: int = Query(..., description="Device ID (21-23)"),
    preset: str = Query(..., description="Time preset: 1h, 1d, 1w, 1mo"),
    maxpoints: int = Query(100, description="Maximum data points"),
    start: Optional[str] = Query(None, description="Start time (ISO format)"),
    end: Optional[str] = Query(None, description="End time (ISO format)")
) -> Dict[str, Any]:
    """
    환경 데이터 조회 API
    """
    
    try:
        # 시간 범위 설정
        if start and end:
            # 드릴다운: 특정 시간 범위
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
            logger.info(f"환경 드릴다운 모드: {start_time} ~ {end_time}")
        else:
            # 기본 모드: preset에 따른 범위
            end_time = datetime.now(timezone.utc)
            if preset == '1h':
                start_time = end_time - timedelta(hours=1)
            elif preset == '1d':
                start_time = end_time - timedelta(days=1)
            elif preset == '1w':
                start_time = end_time - timedelta(days=7)
            elif preset == '1mo':
                start_time = end_time - timedelta(days=30)
            else:
                raise HTTPException(status_code=400, detail=f"Invalid preset: {preset}")
        
        # 🔧 기존 client.py의 get_cursor() 사용
        with get_cursor() as cursor:
            # 🔧 핵심 수정: preset별 집계 쿼리 (환경 데이터용)
            if preset in ['1w', '1mo']:
                # 1주일/1달: 날짜별 집계 (X축 라벨 중복 문제 해결)
                query = """
                SELECT 
                    date_trunc('day', time_stamp) AS bucket,
                    AVG(temperature) AS temperature,
                    AVG(humidity) AS humidity
                FROM env_data
                WHERE device_id = %s 
                    AND time_stamp >= %s 
                    AND time_stamp <= %s
                GROUP BY 1
                ORDER BY 1
                LIMIT %s
                """
            else:
                # 1시간/1일: 원본 데이터 (분/시간 단위)
                if preset == '1h':
                    # 1시간: 1분 간격 집계
                    query = """
                    SELECT 
                        date_trunc('minute', time_stamp) AS bucket,
                        AVG(temperature) AS temperature,
                        AVG(humidity) AS humidity
                    FROM env_data
                    WHERE device_id = %s 
                        AND time_stamp >= %s 
                        AND time_stamp <= %s
                    GROUP BY 1
                    ORDER BY 1
                    LIMIT %s
                    """
                else:
                    # 1일: 원본 데이터
                    query = """
                    SELECT 
                        time_stamp AS bucket,
                        temperature,
                        humidity
                    FROM env_data
                    WHERE device_id = %s 
                        AND time_stamp >= %s 
                        AND time_stamp <= %s
                    ORDER BY time_stamp DESC
                    LIMIT %s
                    """
            
            # 쿼리 실행
            cursor.execute(query, (deviceid, start_time, end_time, maxpoints))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            # 결과 변환
            data = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                # bucket을 ISO 문자열로 변환
                if row_dict['bucket']:
                    row_dict['bucket'] = row_dict['bucket'].isoformat()
                data.append(row_dict)
        
        logger.info(f"환경 데이터 조회 완료: device={deviceid}, preset={preset}, count={len(data)}")
        
        return {
            "data": data,
            "count": len(data),
            "preset": preset,
            "device_id": deviceid,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
    
    except Exception as e:
        logger.error(f"환경 데이터 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/devices")
async def get_env_devices() -> Dict[str, Any]:
    """사용 가능한 환경 센서 장치 목록 반환"""
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT device_id 
                FROM env_data 
                WHERE device_id BETWEEN 21 AND 23
                ORDER BY device_id
            """)
            
            device_ids = [row[0] for row in cursor.fetchall()]
        
        return {
            "devices": device_ids,
            "count": len(device_ids)
        }
    
    except Exception as e:
        logger.error(f"환경 장치 목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """환경 API 상태 확인"""
    return {"status": "ok", "service": "env"}
