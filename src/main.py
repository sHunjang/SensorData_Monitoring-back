"""
FastAPI Main Application

단 하나의 명령어로 모든 것이 동작:
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

자동 실행:
    1. 데이터베이스 초기화 (테이블 생성)
    2. 더미 데이터 수집 (백그라운드)
    3. 스케줄러 실행 (1분/15분 집계)
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.common.logging_config import setup_logging

# Routers
from src.api.health_router import router as health_router
from src.api.modbus_router import router as modbus_router
from src.api.env_router import router as env_router
from src.api.solar_router import router as solar_router

# Background tasks - 모듈 전체 import (run() 함수 사용)
# from src.collectors import dummy_modbus_collector
# from src.collectors import dummy_env_collector
# from src.collectors import dummy_solar_collector
from src.aggregator.scheduler import start_scheduler

# Bootstrap
from src.db.bootstrap import init_db_schema

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# ============================================================
# Background Task Manager
# ============================================================

class BackgroundTaskManager:
    """백그라운드 태스크 관리자"""
    
    def __init__(self):
        self.tasks = []
        self.running = False
    
    async def start(self):
        """모든 백그라운드 태스크 시작"""
        if self.running:
            logger.warning("⚠️  백그라운드 태스크가 이미 실행 중입니다.")
            return
        
        self.running = True
        logger.info("🚀 백그라운드 태스크 시작...")
        
        # 1. 더미 데이터 수집기 시작
        logger.info("📊 더미 데이터 수집기 시작...")
        
        # ✅ 올바른 방법: 함수를 직접 import
        from src.collectors.dummy_modbus_collector import run as run_modbus
        from src.collectors.dummy_env_collector import run as run_env
        from src.collectors.dummy_solar_collector import run as run_solar
        
        # asyncio.to_thread()로 blocking 함수를 async로 실행
        self.tasks.append(asyncio.create_task(asyncio.to_thread(run_modbus)))
        self.tasks.append(asyncio.create_task(asyncio.to_thread(run_env)))
        self.tasks.append(asyncio.create_task(asyncio.to_thread(run_solar)))
        
        logger.info("✅ 더미 데이터 수집기 시작 완료")
        
        # 2. 스케줄러 시작
        logger.info("⏰ 데이터 집계 스케줄러 시작...")
        start_scheduler()
        
        logger.info("✅ 모든 백그라운드 태스크 시작 완료")
        
    async def stop(self):
        """모든 백그라운드 태스크 중지"""
        if not self.running:
            return
        
        logger.info("🛑 백그라운드 태스크 중지 중...")
        
        for task in self.tasks:
            task.cancel()
        
        # 모든 태스크가 취소될 때까지 대기
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks.clear()
        self.running = False
        logger.info("✅ 모든 백그라운드 태스크 중지 완료")

# 전역 태스크 매니저
task_manager = BackgroundTaskManager()

# ============================================================
# Lifespan Context Manager
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프사이클 관리
    
    시작 시:
        1. 데이터베이스 스키마 초기화
        2. 백그라운드 태스크 시작
    
    종료 시:
        1. 백그라운드 태스크 중지
    """
    logger.info("=" * 60)
    logger.info("🚀 애플리케이션 시작")
    logger.info("=" * 60)
    
    # 1. 데이터베이스 초기화
    logger.info("📊 데이터베이스 스키마 초기화 중...")
    try:
        init_db_schema()
        logger.info("✅ 데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
        logger.warning("⚠️  애플리케이션은 계속 실행되지만 DB 오류가 발생할 수 있습니다.")
    
    # 2. 백그라운드 태스크 시작
    await task_manager.start()
    
    # 설정 정보 출력
    logger.info("\n📋 설정 정보:")
    logger.info(f"   MODE: {settings.MODE}")
    logger.info(f"   Modbus 3상 3선: {settings.MODBUS_3W_IDS}")
    logger.info(f"   Modbus 3상 4선: {settings.MODBUS_4W_IDS}")
    logger.info(f"   Env Devices: {settings.ENV_IDS}")
    logger.info(f"   Solar Device: {settings.SOLAR_ID}")
    logger.info(f"   Collection Interval: {settings.COLLECTION_INTERVAL}초")
    
    logger.info("\n✅ 애플리케이션 준비 완료")
    logger.info("=" * 60)
    
    # 애플리케이션 실행
    yield
    
    # 종료 시
    logger.info("\n" + "=" * 60)
    logger.info("🛑 애플리케이션 종료 중...")
    logger.info("=" * 60)
    
    await task_manager.stop()
    
    logger.info("✅ 애플리케이션 종료 완료")
    logger.info("=" * 60)

# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="IoT Monitoring System",
    description="실시간 IoT 센서 모니터링 시스템 API",
    version="2.0.0",
    lifespan=lifespan
)

# ============================================================
# CORS Middleware
# ============================================================

allowed_origins = [
    "http://localhost:3000",      # Vite 기본 포트
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3000",      # React 기본 포트
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://localhost:8000",
]

logger.info(f"🌐 CORS 설정: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Routers
# ============================================================

app.include_router(health_router)
app.include_router(modbus_router)
app.include_router(env_router)
app.include_router(solar_router)

# ============================================================
# Root Endpoint
# ============================================================

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "IoT Monitoring System",
        "version": "2.0.0",
        "status": "running",
        "mode": settings.MODE,
        "docs": "/docs",
        "health": "/health"
    }

# ============================================================
# Error Handlers
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """전역 예외 핸들러"""
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return {
        "error": "Internal Server Error",
        "detail": str(exc)
    }
