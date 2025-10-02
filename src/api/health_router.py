# src/api/health_router.py
"""
Health check 라우터.
- /health : 앱 상태, DB 접속 가능 여부(간단 쿼리) 반환.
- 목적: 로드밸런서/모니터링의 기본 헬스엔드포인트와 수동 점검용.
- 경량 구현: DB 접속은 get_connection()이 아닌 get_cursor()를 사용해
  설정에 따라 dummy 모드에서도 안전하게 동작함.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import logging

from src.db.client import get_cursor

router = APIRouter()
log = logging.getLogger("api.health")


@router.get("/health", tags=["health"])
def health():
    """
    반환 예:
      { "status": "ok", "db": True }
      { "status": "fail", "db": False, "error": "..." }
    - DB 체크는 간단한 SELECT 1 실행.
    - 실패 시 에러 메시지를 포함하지만 민감정보(DSN) 노출 금지.
    """
    db_ok = False
    db_err = None
    try:
        with get_cursor() as cur:
            # get_cursor은 dummy 모드에서 DummyCursor를 반환할 수 있으므로 안전함
            cur.execute("SELECT 1")
            # 일부 DummyCursor는 fetchone을 구현하지 않으므로 try/except 사용
            try:
                _ = cur.fetchone()
            except Exception:
                pass
        db_ok = True
    except Exception as e:
        db_ok = False
        db_err = str(e)

    status = "ok" if db_ok else "fail"
    payload = {"status": status, "db": db_ok}
    if db_err:
        payload["error"] = db_err

    return JSONResponse(content=payload)
