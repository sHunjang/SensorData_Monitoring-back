"""
센서 모니터링 시스템 - PyInstaller EXE 배포용 메인 파일

📁 시스템 구조:
- src/collectors/modbus_collector.py → 실제 TAC4300 전력계 통신
- src/collectors/env_collector.py → 실제 온습도 센서 통신
- src/collectors/solar_collector.py → 실제 태양광 센서 통신
- src/collectors/dummy_modbus_collector.py → 더미 전력 데이터 DB 저장
- src/collectors/dummy_env_collector.py → 더미 환경 데이터 DB 저장
- src/collectors/dummy_solar_collector.py → 더미 태양광 데이터 DB 저장
- src/aggregators/aggregator.py → 시계열 데이터 자동 집계
- src/api/*_router.py → DB에서 데이터 읽어서 API 응답

🎯 main.py 역할:
1. 운영 모드에 따라 실제/더미 수집기 선택 실행
2. 집계기 자동 시작 (1분/15분/1시간/1일 집계)
3. **시작 시 과거 데이터 자동 집계** ← NEW!
4. FastAPI 서버 및 React 프론트엔드 서빙
5. PyInstaller EXE 환경 완벽 지원
"""

import os
import sys
import threading
import logging
import webbrowser
import multiprocessing
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import uvicorn


# ============================================================
# PyInstaller 경로 처리
# ============================================================

def get_resource_path(relative_path: str) -> str:
    """
    PyInstaller EXE와 개발환경 모두 지원하는 리소스 경로 반환
    """
    try:
        base_path = sys._MEIPASS
        print(f"🎯 PyInstaller 모드 감지: {base_path}")
    except AttributeError:
        if relative_path == "dist":
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            resource_path = os.path.join(base_path, "front", "dist")
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            resource_path = os.path.join(base_path, relative_path)
        
        print(f"📁 개발 모드: {base_path}")
        print(f"📁 리소스 경로 매핑: {relative_path} → {resource_path}")
        return resource_path
    
    resource_path = os.path.join(base_path, relative_path)
    print(f"📦 PyInstaller 리소스: {relative_path} → {resource_path}")
    return resource_path


# ============================================================
# 환경변수 로드
# ============================================================

env_path = get_resource_path(".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ 환경변수 로드 완료: {env_path}")
else:
    print(f"⚠️ .env 파일 없음: {env_path}")


# ============================================================
# 모듈 임포트 (단계별 로드)
# ============================================================

REAL_COLLECTORS_LOADED = True
DUMMY_COLLECTORS_LOADED = False
API_ROUTERS_LOADED = False
AGGREGATOR_LOADED = False

# 1. 실제 센서 수집기 로드 시도
try:
    print("📦 실제 센서 수집기 모듈 로드 시도...")
    from src.collectors import modbus_collector, env_collector, solar_collector
    from src.sensors import modbus_reader, env_reader, solar_reader
    REAL_COLLECTORS_LOADED = True
    print("✅ 실제 센서 수집기 모듈 로드 성공")
except ImportError as e:
    print(f"⚠️ 실제 센서 모듈 로드 실패: {e}")
    REAL_COLLECTORS_LOADED = False

# 2. 더미 센서 수집기 로드 시도
try:
    print("📦 더미 센서 수집기 모듈 로드 시도...")
    from src.collectors import dummy_modbus_collector, dummy_env_collector, dummy_solar_collector
    DUMMY_COLLECTORS_LOADED = True
    print("✅ 더미 센서 수집기 모듈 로드 성공")
except ImportError as e:
    print(f"❌ 더미 센서 모듈 로드 실패: {e}")
    DUMMY_COLLECTORS_LOADED = False

# 3. API 라우터 및 설정 로드 시도
try:
    print("📦 API 라우터 모듈 로드 시도...")
    from src.api import health_router, modbus_router, env_router, solar_router
    from src.config.settings import settings
    from src.common.logging_config import setup_logging
    from src.db.bootstrap import ensure_schema
    API_ROUTERS_LOADED = True
    print("✅ API 라우터 모듈 로드 성공")
except ImportError as e:
    print(f"⚠️ API 라우터 모듈 로드 실패: {e}")
    API_ROUTERS_LOADED = False

# 4. 집계기 모듈 로드 시도
try:
    print("📦 집계기 모듈 로드 시도...")
    from src.aggregators.aggregator import AggregatorManager
    AGGREGATOR_LOADED = True
    print("✅ 집계기 모듈 로드 성공")
except ImportError as e:
    print(f"⚠️ 집계기 모듈 로드 실패: {e}")
    AGGREGATOR_LOADED = False

# 로드 상태 요약
print("=" * 70)
print(f"🎯 모듈 로드 상태:")
print(f"   실제 센서: {REAL_COLLECTORS_LOADED}")
print(f"   더미 센서: {DUMMY_COLLECTORS_LOADED}")
print(f"   API 라우터: {API_ROUTERS_LOADED}")
print(f"   집계기: {AGGREGATOR_LOADED}")
print("=" * 70)


# ============================================================
# 로깅 설정
# ============================================================

if API_ROUTERS_LOADED:
    setup_logging()
    log = logging.getLogger("main")
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    log = logging.getLogger("main")


# ============================================================
# FastAPI 라이프사이클 관리
# ============================================================

# 전역 변수로 집계기 관리
aggregator_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 서버 시작/종료시 실행되는 라이프사이클 함수
    """
    global aggregator_manager
    
    log.info("=" * 70)
    log.info("🚀 센서 모니터링 시스템 시작")
    log.info("=" * 70)
    
    # ============= 1단계: DB 스키마 초기화 =============
    if API_ROUTERS_LOADED:
        try:
            log.info("🗄️  DB 스키마 초기화 시도...")
            ensure_schema()
            log.info("✅ DB 스키마 초기화 완료")
        except Exception as e:
            log.warning(f"⚠️  DB 스키마 초기화 실패: {e}")
    elif DUMMY_COLLECTORS_LOADED:
        try:
            log.info("🗄️  더미 수집기를 통한 DB 테이블 생성...")
            dummy_modbus_collector.ensure_table()
            dummy_env_collector.ensure_table()
            dummy_solar_collector.ensure_table()
            log.info("✅ 더미 수집기 DB 테이블 생성 완료")
        except Exception as e:
            log.error(f"❌ DB 테이블 생성 실패: {e}")
    
    # ============= 2단계: 수집기 시작 (모드별 분기) =============
    mode = os.getenv("MODE", "real").lower()
    log.info(f"🎛️  운영 모드: {mode}")
    
    if mode == "real" and REAL_COLLECTORS_LOADED:
        # 🔌 실제 센서 수집기 모드
        log.info("=" * 70)
        log.info("🔌 실제 센서 수집기 시작...")
        log.info("=" * 70)
        
        def start_real_modbus():
            try:
                log.info("⚡ 실제 Modbus 수집기 시작")
                modbus_collector.main()
            except Exception as e:
                log.exception(f"❌ 실제 Modbus 수집기 실패: {e}")
        
        def start_real_env():
            try:
                log.info("🌿 실제 환경 수집기 시작")
                env_collector.main()
            except Exception as e:
                log.exception(f"❌ 실제 환경 수집기 실패: {e}")
        
        def start_real_solar():
            try:
                log.info("☀️  실제 태양광 수집기 시작")
                solar_collector.main()
            except Exception as e:
                log.exception(f"❌ 실제 태양광 수집기 실패: {e}")
        
        threading.Thread(target=start_real_modbus, daemon=True, name="real_modbus").start()
        threading.Thread(target=start_real_env, daemon=True, name="real_env").start()
        threading.Thread(target=start_real_solar, daemon=True, name="real_solar").start()
        log.info("✅ 모든 실제 센서 수집기 시작됨")
        
    elif DUMMY_COLLECTORS_LOADED:
        # 🎭 더미 센서 수집기 모드 (기본값)
        log.info("=" * 70)
        log.info("🎭 더미 센서 수집기 시작...")
        log.info("=" * 70)
        
        def start_dummy_modbus():
            try:
                log.info("🔌 더미 Modbus 수집기 시작")
                dummy_modbus_collector.run_collector()
            except Exception as e:
                log.exception(f"❌ 더미 Modbus 수집기 실패: {e}")
        
        def start_dummy_env():
            try:
                log.info("🌿 더미 환경 수집기 시작")
                dummy_env_collector.run_collector()
            except Exception as e:
                log.exception(f"❌ 더미 환경 수집기 실패: {e}")
        
        def start_dummy_solar():
            try:
                log.info("☀️  더미 태양광 수집기 시작")
                dummy_solar_collector.run_collector()
            except Exception as e:
                log.exception(f"❌ 더미 태양광 수집기 실패: {e}")
        
        threading.Thread(target=start_dummy_modbus, daemon=True, name="dummy_modbus").start()
        threading.Thread(target=start_dummy_env, daemon=True, name="dummy_env").start()
        threading.Thread(target=start_dummy_solar, daemon=True, name="dummy_solar").start()
        log.info("✅ 모든 더미 센서 수집기 시작됨")
    else:
        log.warning("🚨 사용 가능한 수집기가 없습니다!")
    
    # ============= 3단계: 집계기 시작 + 초기 집계 =============
    if AGGREGATOR_LOADED:
        try:
            log.info("")
            log.info("=" * 70)
            log.info("🔄 데이터 집계기 시작...")
            log.info("=" * 70)
            aggregator_manager = AggregatorManager()
            aggregator_manager.start()
            log.info("✅ 집계기 시작 완료 (1분/15분/1시간/1일 자동 집계)")
            
            # ✅ 추가: 시작 직후 과거 데이터 일괄 집계
            log.info("")
            log.info("=" * 70)
            log.info("📊 초기 집계 실행 중 (과거 데이터 집계)...")
            log.info("=" * 70)
            
            def run_initial_aggregation():
                """시작 시 과거 데이터 일괄 집계"""
                try:
                    from src.aggregators.aggregator import (
                        aggregate_modbus_4wire_to_1min,
                        aggregate_modbus_4wire_to_15min,
                        aggregate_modbus_4wire_to_1hour,
                        aggregate_modbus_4wire_to_1day,
                        aggregate_modbus_3wire_to_1min,
                        aggregate_modbus_3wire_to_15min,
                        aggregate_modbus_3wire_to_1hour,
                        aggregate_modbus_3wire_to_1day,
                        aggregate_env_to_1min,
                        aggregate_env_to_15min,
                        aggregate_env_to_1hour,
                        aggregate_env_to_1day,
                        aggregate_solar_to_1min,
                        aggregate_solar_to_15min,
                        aggregate_solar_to_1hour,
                        aggregate_solar_to_1day,
                    )
                    
                    log.info("🔄 1분 집계 실행...")
                    aggregate_modbus_4wire_to_1min()
                    aggregate_modbus_3wire_to_1min()
                    aggregate_env_to_1min()
                    aggregate_solar_to_1min()
                    log.info("✅ 1분 집계 완료")
                    
                    log.info("🔄 15분 집계 실행...")
                    aggregate_modbus_4wire_to_15min()
                    aggregate_modbus_3wire_to_15min()
                    aggregate_env_to_15min()
                    aggregate_solar_to_15min()
                    log.info("✅ 15분 집계 완료")
                    
                    log.info("🔄 1시간 집계 실행...")
                    aggregate_modbus_4wire_to_1hour()
                    aggregate_modbus_3wire_to_1hour()
                    aggregate_env_to_1hour()
                    aggregate_solar_to_1hour()
                    log.info("✅ 1시간 집계 완료")
                    
                    log.info("🔄 1일 집계 실행...")
                    aggregate_modbus_4wire_to_1day()
                    aggregate_modbus_3wire_to_1day()
                    aggregate_env_to_1day()
                    aggregate_solar_to_1day()
                    log.info("✅ 1일 집계 완료")
                    
                    log.info("=" * 70)
                    log.info("✅ 초기 집계 완료! 과거 데이터 모두 집계됨")
                    log.info("=" * 70)
                    
                except Exception as e:
                    log.exception(f"❌ 초기 집계 실패: {e}")
            
            # 백그라운드 스레드로 초기 집계 실행 (서버 시작 블로킹 방지)
            threading.Thread(target=run_initial_aggregation, daemon=True, name="initial_agg").start()
            
        except Exception as e:
            log.exception(f"❌ 집계기 시작 실패: {e}")
            aggregator_manager = None
    else:
        log.warning("")
        log.warning("=" * 70)
        log.warning("⚠️  집계기 모듈을 로드할 수 없어 자동 집계가 비활성화됩니다")
        log.warning("   데이터 수집은 되지만 1분/15분/... 테이블이 업데이트되지 않습니다")
        log.warning("=" * 70)
    
    log.info("")
    log.info("=" * 70)
    log.info("✅ 센서 모니터링 시스템 시작 완료")
    log.info("=" * 70)
    
    # ============= 서버 실행 중 =============
    yield
    
    # ============= 서버 종료시 정리 작업 =============
    log.info("")
    log.info("=" * 70)
    log.info("🛑 센서 모니터링 시스템 종료 중...")
    log.info("=" * 70)
    
    if aggregator_manager:
        try:
            log.info("🔄 집계기 중지...")
            aggregator_manager.stop()
            log.info("✅ 집계기 중지 완료")
        except Exception as e:
            log.error(f"❌ 집계기 중지 실패: {e}")
    
    log.info("=" * 70)
    log.info("👋 센서 모니터링 시스템 종료 완료")
    log.info("=" * 70)


# ============================================================
# FastAPI 앱 생성
# ============================================================

app = FastAPI(
    lifespan=lifespan,
    title="📊 센서 모니터링 시스템",
    description="실시간 IoT 센서 데이터 수집 및 다중 해상도 집계 시스템",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


# ============================================================
# CORS 설정
# ============================================================

if API_ROUTERS_LOADED:
    cors_origins = settings.get_cors_origins_list()
    if not cors_origins:
        cors_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    log.info(f"✅ CORS 설정: {cors_origins}")
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    log.info("✅ CORS 설정: 모든 origin 허용 (개발 모드)")


# ============================================================
# API 라우터 등록
# ============================================================

if API_ROUTERS_LOADED:
    app.include_router(health_router.router)
    app.include_router(modbus_router.router)
    app.include_router(env_router.router)
    app.include_router(solar_router.router)
    log.info("✅ API 라우터 등록 완료")
else:
    log.warning("⚠️ API 라우터를 로드할 수 없습니다")


# ============================================================
# 루트 엔드포인트
# ============================================================

@app.get("/api/info")
def get_system_info():
    """시스템 정보 조회"""
    return {
        "title": "센서 모니터링 시스템",
        "version": "2.0.0",
        "mode": os.getenv("MODE", "real"),
        "modules": {
            "real_collectors": REAL_COLLECTORS_LOADED,
            "dummy_collectors": DUMMY_COLLECTORS_LOADED,
            "api_routers": API_ROUTERS_LOADED,
            "aggregator": AGGREGATOR_LOADED,
        },
        "aggregator_status": "running" if aggregator_manager else "stopped",
    }


# ============================================================
# React 프론트엔드 서빙
# ============================================================

dist_path = get_resource_path("dist")
if os.path.exists(dist_path) and os.path.isdir(dist_path):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(dist_path, "assets")),
        name="assets"
    )
    
    @app.get("/")
    def serve_index():
        """React index.html 서빙"""
        index_path = os.path.join(dist_path, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        return {"error": "index.html not found"}
    
    log.info(f"✅ React 프론트엔드 서빙: {dist_path}")
else:
    log.warning(f"⚠️ React 빌드 결과물 없음: {dist_path}")
    log.warning("   프론트엔드 없이 API 서버만 실행됩니다")


# ============================================================
# 서버 실행 (직접 실행시)
# ============================================================

if __name__ == "__main__":
    multiprocessing.freeze_support()
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
