# main.py
"""
앱 진입점. FastAPI 앱 생성, CORS 설정, 라우터 등록, 수집기(collector) 스레드 시작,
정적 파일(dist) 서빙을 담당.
환경변수:
 - MODE: "real" (실장비) 또는 "dummy" (더미 수집기)
 - CORS_ORIGINS: 콤마로 구분된 허용 origin 리스트 (예: "http://localhost:5173")
 - 기타 DB/시리얼 설정은 src/config/settings.py에서 관리
"""

import os
import threading
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# 프로젝트 내부 모듈 (경로는 프로젝트 구조에 맞춰 조정)
# - api 라우터들: /data/modbus, /data/env, /data/solar
# - collectors: 실제 수집기와 더미 수집기 제공 (모듈명이 다를 경우 경로 맞출 것)
from src.api import health_router
from src.api import modbus_router, env_router, solar_router
from src.collectors import modbus_collector, env_collector, solar_collector
from src.collectors import dummy_modbus_collector, dummy_env_collector, dummy_solar_collector
from src.config.settings import settings  # 중앙화된 설정 (환경변수 파싱 등)
from src.common.logging_config import setup_logging
from src.db.bootstrap import ensure_schema

# .env 파일 자동 로드 (개발 편의)
load_dotenv()

# 로깅 초기화: logging_config.setup_logging() 에서 포맷/핸들러 설정
setup_logging()
log = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan hook.
    - DB 스키마 초기화 시도 (실패해도 앱이 시작되도록 예외 처리)
    - MODE에 따라 실제 또는 더미 수집기를 백그라운드 스레드로 시작
    """
    try:
        ensure_schema()
        log.info("DB schema ensured or created.")
    except Exception as e:
        # 부트스트랩 실패 시 경고만 기록. 운영 환경에서는 치명적일 수 있으니 모니터링 필요.
        log.warning("bootstrap skipped: %s", e)

    # MODE: real 또는 dummy (개발용)
    mode = os.getenv("MODE", "real").lower()
    log.info("collector mode = %s", mode)

    if mode == "real":
        # 실장비 수집기: 데몬 스레드로 실행 (프로세스 종료 시 자동 종료)
        threading.Thread(target=modbus_collector.main, daemon=True, name="modbus_collector").start()
        threading.Thread(target=env_collector.main, daemon=True, name="env_collector").start()
        threading.Thread(target=solar_collector.main, daemon=True, name="solar_collector").start()
        log.info("Real collectors started.")
    else:
        # 더미 수집기: 빠른 간격으로 동작하여 개발/테스트 편의 제공
        threading.Thread(target=lambda: dummy_modbus_collector.run_collector(interval=3), daemon=True, name="dummy_modbus").start()
        threading.Thread(target=lambda: dummy_env_collector.run_collector(interval=3), daemon=True, name="dummy_env").start()
        threading.Thread(target=lambda: dummy_solar_collector.run_collector(interval=3), daemon=True, name="dummy_solar").start()
        log.info("Dummy collectors started.")

    # lifespan yield 시점에 앱이 ready 상태가 됨
    yield


# FastAPI 앱 생성, lifespan 훅 연결
app = FastAPI(lifespan=lifespan, title="Sensor Monitoring API")

# CORS 설정
# 우선 settings.cors_origins에 명시된 값을 사용.
# 없으면 기본 개발 origin 목록을 허용 (개발 편의).
_raw = (settings.cors_origins or os.getenv("CORS_ORIGINS") or "").strip()
if _raw:
    # 쉼표 구분으로 여러 origin을 허용할 수 있도록 처리
    origins = [o.strip() for o in _raw.split(",") if o.strip()]
else:
    # 개발 환경에서 흔히 사용하는 로컬 origin들
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

log.info("CORS origins = %s", origins)

# CORSMiddleware: 인증 쿠키가 필요하면 allow_credentials=True 로 유지
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
# 프론트와의 계약(contract)을 명확히 하기 위해 라우터별 prefix를 명시.
app.include_router(modbus_router.router, tags=["modbus"])
app.include_router(env_router.router, tags=["env"])
app.include_router(solar_router.router, tags=["solar"])

# 신규: 헬스 라우터 등록 (루트 경로 /health)
app.include_router(health_router.router, prefix="", tags=["health"])

# 정적 SPA 파일 서빙 (Vite build 결과물: dist/)
# - 운영에서 backend + static 서빙을 단일 프로세스로 배포할 경우 사용.
# - 없다면 개발 모드로 실행한다고 판단하고 static mount 하지 않음.
if os.path.isdir("dist"):
    # index.html fallback 허용 (SPA)
    app.mount("/", StaticFiles(directory="dist", html=True), name="static")
    log.info("Static files mounted from 'dist' directory.")
else:
    log.info("No 'dist' directory found. Static files not mounted. (If you want SPA served, run `npm run build` to produce dist/.)")
