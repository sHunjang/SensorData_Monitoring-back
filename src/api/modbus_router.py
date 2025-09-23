# src/api/modbus_router.py
"""
FastAPI 라우터: /data/modbus

- 이 파일은 반드시 `router = APIRouter(...)`를 노출해야 합니다.
- 붙여넣기 후 `uvicorn src.main:app --reload`로 서버 재시작.
- 의존: src.services.modbus_service 에 query_modbus_window, query_modbus_realtime 구현 필요.
- 의존: src.api._utils 의 make_realtime_response (표준 응답 포맷) 사용.
"""

from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException

# 서비스 레이어 호출 (데이터 조회 로직은 서비스에 둠)
from src.services.modbus_service import query_modbus_window, query_modbus_realtime, get_today_energy_kwh
from src.api._utils import make_realtime_response

# 라우터 인스턴스: 반드시 이 이름(router)으로 main.py에서 포함하도록 함
router = APIRouter(prefix="/data/modbus", tags=["modbus"])


@router.get("/realtime")
def get_realtime(device_id: int = Query(..., description="장치 ID")):
    """
    실시간 최신값 조회
    - device_id: 필수
    - 서비스가 None 반환 시 503으로 응답
    - 반환 포맷: make_realtime_response 표준 포맷
    """
    try:
        data = query_modbus_realtime(device_id)
        if not data:
            # 장치에 데이터가 없음을 의미. 프론트엔드에서 503 처리하도록 함.
            raise HTTPException(status_code=503, detail="장치에서 데이터 없음")
        # data는 서비스에서 이미 키-값 형태로 정규화되어 있다고 가정
        metrics = {
            "p_kw": data.get("power"),
            "e_kwh": data.get("energy"),
            "v_ll": data.get("voltage_ll"),
            "v_ln": data.get("voltage_ln"),
            "i_sum": data.get("current"),
        }
        return make_realtime_response(device_id, data.get("time_stamp"), metrics, raw=data)
    except HTTPException:
        raise
    except Exception as e:
        # 내부 에러는 500으로 반환
        raise HTTPException(status_code=500, detail=f"예상치 못한 오류: {e}")


@router.get("/query")
def get_query(
    device_id: int = Query(..., description="장치 ID"),
    series: Optional[List[str]] = Query(default=None, description="조회 시리즈, 예: power,energy"),
    preset: Optional[str] = Query(default="1h", description="preset: 15m|1h|1d|1w|1mo"),
    start: Optional[str] = Query(default=None, description="ISO start datetime (optional)"),
    end: Optional[str] = Query(default=None, description="ISO end datetime (optional)"),
    max_points: int = Query(1000, ge=1, le=5000, description="최대 포인트 수"),
):
    """
    히스토리(집계) 조회 엔드포인트
    - device_id: 필수
    - series: 요청할 series 키 리스트 (없으면 기본값 사용)
    - preset/start/end: 시간 윈도우
    - 반환: 서비스(query_modbus_window)의 make_query_response 구조
    """
    try:
        keys = series or ["power", "current", "voltage"]
        return query_modbus_window(device_id=device_id, series=keys, preset=preset, start=start, end=end, max_points=max_points)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예상치 못한 오류: {e}")


@router.get("/today")
def modbus_today(device_id: int = Query(..., description="장치 ID")):
    """
    당일 전력량(kWh) 반환.
    - device_id 필수
    - 반환: { device_id: <int>, kwh: <float|null> }
    """
    try:
        kwh = get_today_energy_kwh(device_id)
        return {"device_id": device_id, "kwh": (None if kwh is None else round(kwh, 3))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))