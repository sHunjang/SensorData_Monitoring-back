"""
FastAPI 앱 시작점
- CORS 허용
- /data/modbus, /data/env 라우터 제공
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import modbus_router, env_router, solar_router
from src.common.logging_config import setup_logging

# collector 실행용
import threading
from src.ingest import modbus_collector

app = FastAPI()
setup_logging()

# ✅ CORS 허용
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # 허용할 프론트 주소
    allow_credentials=True,
    allow_methods=["*"],            # GET, POST 등 전부 허용
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(modbus_router.router)
app.include_router(env_router.router)
app.include_router(solar_router.router)

@app.on_event("startup")
def startup_event():
    """
    서버 시작 시 Modbus Collector를 백그라운드 스레드로 실행
    """
    def run_collector():
        try:
            modbus_collector.main()
        except Exception as e:
            import logging
            logging.getLogger("collector").error(f"Collector crashed: {e}")

    thread = threading.Thread(target=run_collector, daemon=True)
    thread.start()
