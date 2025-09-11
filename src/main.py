"""
FastAPI 앱 시작점
- CORS 허용
- /data/modbus, /data/env 라우터 제공
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading

from src.api import modbus_router, env_router, solar_router
from src.common.logging_config import setup_logging

# 실제 Collector 파일 실행
from src.collectors import modbus_collector, solar_collector, env_collector

# 더미 데이터 Collector 파일 실행
from src.collectors import dummy_env_collector, dummy_modbus_collector, dummy_solar_collector



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



# 실제 센서 데이터 수집
@app.on_event("startup")
def startup_event():
    """
    서버 시작 시 Collector들을 백그라운드 스레드로 실행
    """
    import logging

    def run_modbus():
        try:
            modbus_collector.main()
        except Exception as e:
            logging.getLogger("collector").error(f"Modbus collector crashed: {e}")

    def run_solar():
        try:
            solar_collector.main()
        except Exception as e:
            logging.getLogger("collector").error(f"Solar collector crashed: {e}")
            
    def run_env():
        try:
            env_collector.main()
        except Exception as e:
            logging.getLogger("collector").error(f"Solar collector crashed: {e}")

    threading.Thread(target=run_modbus, daemon=True).start()
    threading.Thread(target=run_solar, daemon=True).start()
    threading.Thread(target=run_env, daemon=True).start()



# ✅ 서버 시작 시 더미 collectors 실행 (스레드 기반)
@app.on_event("startup")
def start_dummy_collectors():
    def run_env():
        dummy_env_collector.run_collector(interval=10)
    def run_modbus():
        dummy_modbus_collector.run_collector(interval=10)
    # def run_solar():
    #     dummy_solar_collector.run_collector(interval=10)

    threading.Thread(target=run_env, daemon=True).start()
    threading.Thread(target=run_modbus, daemon=True).start()
    # threading.Thread(target=run_solar, daemon=True).start()