"""
FastAPI 메인 엔트리포인트
- .env 로드(MODE=real|dummy)
- CORS 허용
- 라우터 등록: /data/modbus, /data/env, /data/solar
- Lifespan에서 스키마 보장 + 수집기(실/더미) 스레드 기동
- 정적 파일(Vite 빌드) 서빙 + SPA fallback
- 헬스체크 /health
"""
import os, sys, threading, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# 라우터
from src.api import modbus_router, env_router, solar_router
# 로깅, 스키마 부트스트랩
from src.common.logging_config import setup_logging
from src.db.bootstrap import ensure_schema

# 실수집기
from src.collectors import modbus_collector, env_collector, solar_collector
# 더미수집기
from src.collectors import dummy_modbus_collector, dummy_env_collector, dummy_solar_collector


# ──────────────────────────────────────────────────────────────────────────────
# 초기화
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()              # .env 읽기
setup_logging()            # 로거 설정
log = logging.getLogger("main")


# ──────────────────────────────────────────────────────────────────────────────
# Lifespan: 앱 시작/종료 훅
#   - DB 스키마 보장
#   - MODE=real → 실제 수집기 스레드
#     MODE=dummy → 더미 수집기 스레드
#   - 각 수집기는 자체 내부에서 60초 주기/KST 저장을 수행
# ──────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_schema()
    except Exception as e:
        logging.getLogger("bootstrap").warning("bootstrap skipped: %s", e)

    mode = os.getenv("MODE", "real").lower()
    log.info("collector mode = %s", mode)

    if mode == "real":
        threading.Thread(target=modbus_collector.main, daemon=True).start()
        threading.Thread(target=env_collector.main, daemon=True).start()
        threading.Thread(target=solar_collector.main, daemon=True).start()
    else:
        threading.Thread(target=lambda: dummy_modbus_collector.run_collector(interval=3), daemon=True).start()
        threading.Thread(target=lambda: dummy_env_collector.run_collector(interval=3), daemon=True).start()
        threading.Thread(target=lambda: dummy_solar_collector.run_collector(interval=3), daemon=True).start()

    yield
    # 종료 훅: 데몬 스레드는 프로세스 종료 시 함께 종료됨


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI 앱
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(lifespan=lifespan)

# CORS

origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터
app.include_router(modbus_router.router)
app.include_router(env_router.router)
app.include_router(solar_router.router)

# 헬스체크
@app.get("/health", status_code=status.HTTP_200_OK)
def health():
    return {"ok": True}

# 정적 파일 서빙(배포용)
#  - PyInstaller 등으로 패키징될 경우 sys._MEIPASS 사용
base_path = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(__file__)
static_dir = os.path.join(base_path, "static")
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
else:
    log.warning("static directory not found: %s", static_dir)

# SPA fallback
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html not found"}


# uvicorn 로컬 실행(개발용)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")), reload=False)
