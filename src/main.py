"""
FastAPI 앱 시작점
- .env 로드 (MODE=real/dummy)
- CORS 허용
- /data/modbus, /data/env, /data/solar 라우터 제공
- Collector (실센서/더미) 병렬 실행
- 프론트 정적 파일 서빙 (Vite SPA fallback 포함)
"""

import os, sys, threading, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from src.api import modbus_router, env_router, solar_router
from src.common.logging_config import setup_logging

# 실제 Collectors
from src.collectors import modbus_collector, solar_collector, env_collector
# # 더미 Collectors
from src.collectors import dummy_env_collector, dummy_modbus_collector, dummy_solar_collector

# ✅ .env 로드
load_dotenv()


# ✅ Lifespan 이벤트 핸들러
@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = os.getenv("MODE", "real").lower()
    log = logging.getLogger("collector")
    log.info(f"Collector starting in {mode} mode")

    if mode == "real":
        threading.Thread(target=modbus_collector.main, daemon=True).start()
        # threading.Thread(target=solar_collector.main, daemon=True).start()
        # threading.Thread(target=env_collector.main, daemon=True).start()
    else:  # dummy mode
        # def run_dummy_env(): dummy_env_collector.run_collector(interval=10)
        def run_dummy_modbus(): dummy_modbus_collector.run_collector(interval=10)
        # def run_dummy_solar(): dummy_solar_collector.run_collector(interval=10)

        # threading.Thread(target=run_dummy_env, daemon=True).start()
        threading.Thread(target=run_dummy_modbus, daemon=True).start()
        # threading.Thread(target=run_dummy_solar, daemon=True).start()

    yield


# ✅ FastAPI 앱
app = FastAPI(lifespan=lifespan)
setup_logging()

# ✅ CORS
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 라우터 등록
app.include_router(modbus_router.router)
app.include_router(env_router.router)
app.include_router(solar_router.router)

# ✅ 정적 파일 서빙
if getattr(sys, "frozen", False):  # exe 실행 시
    base_path = sys._MEIPASS
else:  # 개발 모드
    base_path = os.path.dirname(__file__)

static_dir = os.path.join(base_path, "static")   # ✅ exe 내부에서는 그냥 "static"
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
else:
    logging.getLogger("main").warning(f"Static directory not found: {static_dir}")

# ✅ Vite SPA fallback (index.html)
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html not found"}


# ✅ uvicorn 실행 (exe 지원)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
