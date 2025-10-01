"""
센서 모니터링 시스템 - PyInstaller EXE 배포용 메인 파일

📁 시스템 구조:
- src/collectors/modbus_collector.py       → 실제 TAC4300 전력계 통신
- src/collectors/env_collector.py          → 실제 온습도 센서 통신  
- src/collectors/solar_collector.py        → 실제 태양광 센서 통신
- src/collectors/dummy_modbus_collector.py → 더미 전력 데이터 DB 저장
- src/collectors/dummy_env_collector.py    → 더미 환경 데이터 DB 저장
- src/collectors/dummy_solar_collector.py  → 더미 태양광 데이터 DB 저장
- src/api/*_router.py                      → DB에서 데이터 읽어서 API 응답

🎯 main.py 역할:
1. 운영 모드에 따라 실제/더미 수집기 선택 실행
2. FastAPI 서버 및 React 프론트엔드 서빙
3. PyInstaller EXE 환경 완벽 지원
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


# ============= PyInstaller 경로 처리 =============
def get_resource_path(relative_path: str) -> str:
    """
    PyInstaller EXE와 개발환경 모두 지원하는 리소스 경로 반환
    
    Args:
        relative_path: 상대 경로 ("dist", ".env" 등)
        
    Returns:
        str: 실제 파일 시스템 경로
    """
    try:
        # PyInstaller로 패키징된 EXE 실행시
        base_path = sys._MEIPASS
        print(f"🎯 PyInstaller 모드 감지: {base_path}")
    except AttributeError:
        # 일반 Python 스크립트 실행시 (개발 환경)
        if relative_path == "dist":
            # React 빌드 결과물은 프로젝트 루트/front/dist
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            resource_path = os.path.join(base_path, "front", "dist")
        else:
            # 기타 리소스는 프로젝트 루트 기준
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            resource_path = os.path.join(base_path, relative_path)
        
        print(f"📁 개발 모드: {base_path}")
        print(f"📁 리소스 경로 매핑: {relative_path} → {resource_path}")
        return resource_path
    
    # PyInstaller 환경에서는 _MEIPASS 기준 경로 사용
    resource_path = os.path.join(base_path, relative_path)
    print(f"📦 PyInstaller 리소스: {relative_path} → {resource_path}")
    return resource_path


# ============= 환경변수 로드 =============
# .env 파일을 PyInstaller EXE 번들 내부 또는 개발 환경에서 찾아서 로드
env_path = get_resource_path(".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ 환경변수 로드 완료: {env_path}")
else:
    print(f"⚠️  .env 파일 없음: {env_path}")


# ============= 모듈 임포트 (단계별 로드) =============
# 실제 센서용 모듈들 (pymodbus, pyserial 등 외부 의존성 필요)
REAL_COLLECTORS_LOADED = False
# 더미 센서용 모듈들 (외부 의존성 없음, 항상 로드 가능해야 함)  
DUMMY_COLLECTORS_LOADED = False
# API 라우터 모듈들
API_ROUTERS_LOADED = False

try:
    print("📦 실제 센서 수집기 모듈 로드 시도...")
    
    # 실제 센서 수집기들 (pymodbus 등 외부 라이브러리 필요)
    from src.collectors import modbus_collector, env_collector, solar_collector
    from src.sensors import modbus_reader, env_reader, solar_reader
    
    REAL_COLLECTORS_LOADED = True
    print("✅ 실제 센서 수집기 모듈 로드 성공")
    
except ImportError as e:
    print(f"⚠️  실제 센서 모듈 로드 실패: {e}")
    print("💡 실제 센서 사용시 필요: pip install pymodbus pyserial")
    REAL_COLLECTORS_LOADED = False

try:
    print("📦 더미 센서 수집기 모듈 로드 시도...")
    
    # 더미 센서 수집기들 (외부 의존성 없이 순수 Python으로 구현)
    from src.collectors import dummy_modbus_collector, dummy_env_collector, dummy_solar_collector
    
    DUMMY_COLLECTORS_LOADED = True
    print("✅ 더미 센서 수집기 모듈 로드 성공")
    
except ImportError as e:
    print(f"❌ 더미 센서 모듈 로드 실패: {e}")
    print("🚨 심각한 문제: 더미 수집기도 로드할 수 없음")
    DUMMY_COLLECTORS_LOADED = False

try:
    print("📦 API 라우터 모듈 로드 시도...")
    
    # API 라우터들과 공통 모듈들
    from src.api import health_router, modbus_router, env_router, solar_router
    from src.config.settings import settings
    from src.common.logging_config import setup_logging
    from src.db.bootstrap import ensure_schema
    
    API_ROUTERS_LOADED = True
    print("✅ API 라우터 모듈 로드 성공")
    
except ImportError as e:
    print(f"⚠️  API 라우터 모듈 로드 실패: {e}")
    API_ROUTERS_LOADED = False

# 로드 상태 요약
print(f"🎯 모듈 로드 상태: 실제센서={REAL_COLLECTORS_LOADED}, 더미센서={DUMMY_COLLECTORS_LOADED}, API={API_ROUTERS_LOADED}")


# ============= 로깅 설정 =============
if API_ROUTERS_LOADED:
    # 완전한 로깅 시스템 사용
    setup_logging()
    log = logging.getLogger("main")
else:
    # 기본 로깅만 사용
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    log = logging.getLogger("main")


# ============= FastAPI 라이프사이클 관리 =============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 서버 시작/종료시 실행되는 라이프사이클 함수
    
    주요 작업:
    1. DB 스키마 초기화
    2. 운영 모드에 따른 수집기 시작 (실제 vs 더미)
    3. 브라우저 자동 실행
    """
    log.info("🚀 센서 모니터링 시스템 시작")
    
    # ============= 1단계: DB 스키마 초기화 =============
    if API_ROUTERS_LOADED:
        try:
            log.info("🗄️  DB 스키마 초기화 시도...")
            ensure_schema()
            log.info("✅ DB 스키마 초기화 완료")
        except Exception as e:
            log.warning(f"⚠️  DB 스키마 초기화 실패: {e}")
            log.warning("계속 진행하지만 데이터 저장/조회에 문제가 있을 수 있음")
    
    elif DUMMY_COLLECTORS_LOADED:
        try:
            log.info("🗄️  더미 수집기를 통한 DB 테이블 생성...")
            # 각 더미 수집기의 ensure_table() 직접 호출
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
        log.info("🔌 실제 센서 수집기 시작...")
        
        def start_real_modbus():
            """실제 Modbus(TAC4300) 전력계 데이터 수집"""
            try:
                log.info("⚡ 실제 Modbus 수집기 시작")
                modbus_collector.main()  # 실제 수집기의 main() 함수 실행
            except Exception as e:
                log.exception(f"❌ 실제 Modbus 수집기 실패: {e}")
        
        def start_real_env():
            """실제 온습도 센서 데이터 수집"""
            try:
                log.info("🌿 실제 환경 수집기 시작")
                env_collector.main()
            except Exception as e:
                log.exception(f"❌ 실제 환경 수집기 실패: {e}")
        
        def start_real_solar():
            """실제 태양광 센서 데이터 수집"""
            try:
                log.info("☀️ 실제 태양광 수집기 시작")
                solar_collector.main()
            except Exception as e:
                log.exception(f"❌ 실제 태양광 수집기 실패: {e}")
        
        # 실제 센서 수집기들을 별도 쓰레드에서 실행
        threading.Thread(target=start_real_modbus, daemon=True, name="real_modbus").start()
        # threading.Thread(target=start_real_env, daemon=True, name="real_env").start()
        # threading.Thread(target=start_real_solar, daemon=True, name="real_solar").start()
        
        log.info("🔌 모든 실제 센서 수집기 시작됨")
        
    elif DUMMY_COLLECTORS_LOADED:
        # 🎭 더미 센서 수집기 모드 (기본값)
        log.info("🎭 더미 센서 수집기 시작...")
        
        def start_dummy_modbus():
            """더미 Modbus 전력 데이터 생성 및 DB 저장"""
            try:
                log.info("🔌 더미 Modbus 수집기 시작")
                # 3초마다 더미 전력 데이터 생성하여 DB에 저장
                dummy_modbus_collector.run_collector(interval=3)
            except Exception as e:
                log.exception(f"❌ 더미 Modbus 수집기 실패: {e}")
        
        def start_dummy_env():
            """더미 환경 데이터 생성 및 DB 저장"""
            try:
                log.info("🌿 더미 환경 수집기 시작") 
                # 3초마다 더미 온습도 데이터 생성하여 DB에 저장
                dummy_env_collector.run_collector(interval=3)
            except Exception as e:
                log.exception(f"❌ 더미 환경 수집기 실패: {e}")
        
        def start_dummy_solar():
            """더미 태양광 데이터 생성 및 DB 저장"""
            try:
                log.info("☀️ 더미 태양광 수집기 시작")
                # 3초마다 더미 일사량 데이터 생성하여 DB에 저장
                dummy_solar_collector.run_collector(interval=3)
            except Exception as e:
                log.exception(f"❌ 더미 태양광 수집기 실패: {e}")
        
        # 더미 센서 수집기들을 별도 쓰레드에서 실행
        modbus_thread = threading.Thread(target=start_dummy_modbus, daemon=True, name="dummy_modbus")
        env_thread = threading.Thread(target=start_dummy_env, daemon=True, name="dummy_env")
        solar_thread = threading.Thread(target=start_dummy_solar, daemon=True, name="dummy_solar")
        
        modbus_thread.start()
        env_thread.start() 
        solar_thread.start()
        
        log.info("🎭 모든 더미 센서 수집기 시작됨")
        log.info(f"📊 쓰레드 상태 확인: modbus={modbus_thread.is_alive()}, env={env_thread.is_alive()}, solar={solar_thread.is_alive()}")
        
        # 🔍 DB 저장 상태 확인 (5초 후)
        def verify_data_collection():
            """더미 수집기들이 DB에 데이터를 정상적으로 저장하고 있는지 확인"""
            import time
            time.sleep(5)  # 수집기들이 데이터를 저장할 시간 대기
            
            try:
                from src.db.client import get_cursor
                with get_cursor() as cur:
                    # 각 테이블별 데이터 개수 확인
                    cur.execute("SELECT COUNT(*) FROM modbus_data")
                    modbus_count = cur.fetchone()[0]
                    
                    cur.execute("SELECT COUNT(*) FROM env_data") 
                    env_count = cur.fetchone()[0]
                    
                    cur.execute("SELECT COUNT(*) FROM solar_data")
                    solar_count = cur.fetchone()[0]
                    
                    log.info(f"📊 DB 데이터 저장 확인: Modbus={modbus_count}개, 환경={env_count}개, 태양광={solar_count}개")
                    
                    if modbus_count > 0 or env_count > 0 or solar_count > 0:
                        log.info("🎉 더미 수집기들이 DB에 데이터를 정상적으로 저장 중!")
                    else:
                        log.warning("⚠️  아직 DB에 데이터가 없습니다. 잠시 더 기다려보세요.")
                        
            except Exception as e:
                log.error(f"❌ DB 데이터 확인 실패: {e}")
        
        # 데이터 수집 확인을 별도 쓰레드에서 실행
        threading.Thread(target=verify_data_collection, daemon=True, name="data_verify").start()
        
    else:
        log.warning("🚨 사용 가능한 수집기가 없습니다!")
        if mode == "real":
            log.warning("실제 센서 모드를 요청했지만 필요한 라이브러리가 설치되지 않았습니다.")
            log.warning("더미 모드로 .env의 MODE를 변경하거나 필요한 패키지를 설치하세요.")
    
    # ============= 3단계: 브라우저 자동 실행 =============
    def open_browser():
        """서버 시작 완료 후 기본 브라우저 자동 실행"""
        import time
        time.sleep(2)  # 서버가 완전히 시작될 때까지 대기
        try:
            port = int(os.getenv("PORT", "8000"))
            webbrowser.open(f"http://localhost:{port}")
            log.info(f"🌐 브라우저 자동 실행: http://localhost:{port}")
        except Exception as e:
            log.warning(f"⚠️  브라우저 자동 실행 실패: {e}")
    
    # 브라우저 실행을 별도 쓰레드에서 수행 (메인 서버 시작을 방해하지 않도록)
    threading.Thread(target=open_browser, daemon=True, name="browser").start()
    
    log.info("🚀 센서 모니터링 시스템 시작 완료")
    
    # ============= 서버 실행 중 =============
    yield  # FastAPI 서버가 실행되는 구간
    
    # ============= 서버 종료시 정리 작업 =============
    log.info("🛑 센서 모니터링 시스템 종료")


# ============= FastAPI 앱 생성 =============
app = FastAPI(
    lifespan=lifespan,  # 시작/종료 라이프사이클 연결
    title="📊 센서 모니터링 시스템",
    description="TAC4300 전력계 + 환경센서 + 태양광센서 통합 모니터링 (PyInstaller EXE 지원)",
    version="2.0.0",
    docs_url="/api/docs",    # Swagger UI 경로
    redoc_url="/api/redoc",  # ReDoc 경로
)


# ============= CORS 설정 =============
# 프론트엔드에서 API 호출할 수 있도록 CORS 허용
cors_origins = os.getenv("CORS_ORIGINS", "").strip()
if cors_origins:
    # 환경변수에서 허용할 도메인 목록을 읽음 (쉼표 구분)
    origins = [origin.strip() for origin in cors_origins.split(",")]
else:
    # 기본 개발 환경용 도메인들
    origins = [
        "http://localhost:5173",  # Vite 개발 서버
        "http://127.0.0.1:5173",
        "http://localhost:3000",  # React 개발 서버
        "http://127.0.0.1:3000",
        "http://localhost:8000",  # FastAPI 자체 요청
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 개발용으로 모든 도메인 허용 (운영시에는 제한 필요)
    allow_credentials=True,        # 쿠키 등 인증 정보 허용
    allow_methods=["*"],           # 모든 HTTP 메소드 허용
    allow_headers=["*"],           # 모든 헤더 허용
)


# ============= API 라우터 등록 =============
if API_ROUTERS_LOADED:
    # 🎯 완전한 API 라우터 시스템 사용 (DB에서 데이터 읽어서 응답)
    
    # 각 센서별 API 라우터 등록
    app.include_router(modbus_router.router, tags=["modbus"])    # 전력 데이터 API
    app.include_router(env_router.router, tags=["env"])          # 환경 데이터 API  
    app.include_router(solar_router.router, tags=["solar"])      # 태양광 데이터 API
    app.include_router(health_router.router, prefix="", tags=["health"])  # 시스템 상태 API
    
    log.info("✅ 완전한 API 라우터 등록 완료 (DB 연동)")
    
else:
    # 🚨 최소 기능 더미 API (모듈 로드 실패시 사용)
    
    log.warning("⚠️  API 라우터 로드 실패, 최소 기능 더미 API 사용")
    
    @app.get("/health")
    async def minimal_health_check():
        """최소 기능 헬스체크 API"""
        return {
            "status": "limited",
            "mode": "fallback",
            "message": "모듈 로드 실패로 제한된 기능만 사용 가능",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
    
    @app.get("/")
    async def minimal_info():
        """시스템 정보 페이지"""
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>센서 모니터링 시스템 - 제한 모드</title>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; margin: 40px;">
            <h1>🚨 센서 모니터링 시스템 - 제한 모드</h1>
            <p><strong>모듈 로드 상태:</strong></p>
            <ul>
                <li>실제 센서: {'✅' if REAL_COLLECTORS_LOADED else '❌'}</li>
                <li>더미 센서: {'✅' if DUMMY_COLLECTORS_LOADED else '❌'}</li>
                <li>API 라우터: {'✅' if API_ROUTERS_LOADED else '❌'}</li>
            </ul>
            <p>완전한 기능을 사용하려면 필요한 모듈을 설치하거나 설정을 확인하세요.</p>
        </body>
        </html>
        """)


# ============= React 프론트엔드 정적 파일 서빙 =============
# React 빌드 결과물(front/dist)을 정적 파일로 서빙
dist_path = get_resource_path("dist")
print(f"📁 React 빌드 파일 경로 확인: {dist_path}")

if os.path.isdir(dist_path):
    try:
        # React 앱의 모든 파일을 루트 경로에서 서빙
        app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")
        log.info(f"✅ React 프론트엔드 서빙 설정: {dist_path}")
        print("🌐 React 앱이 루트 경로(/)에서 제공됩니다")
    except Exception as e:
        log.error(f"❌ React 정적 파일 마운트 실패: {e}")
        print("⚠️  React 파일 서빙 실패, API만 사용 가능")
else:
    log.warning(f"⚠️  React 빌드 파일을 찾을 수 없음: {dist_path}")
    print("💡 npm run build로 React 앱을 빌드하거나 front/dist 폴더를 확인하세요")


# ============= 서버 실행 함수 =============
def run_server():
    """
    Uvicorn을 사용하여 FastAPI 서버 실행
    
    환경변수:
    - HOST: 서버 바인딩 주소 (기본값: 0.0.0.0)
    - PORT: 서버 포트 (기본값: 8000)
    """
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"🚀 센서 모니터링 시스템 서버 시작")
    print(f"📡 서버 주소: http://{host}:{port}")
    print(f"📊 API 문서: http://localhost:{port}/api/docs")
    print(f"🌐 React 앱: http://localhost:{port}/")
    
    # Uvicorn 서버 실행
    uvicorn.run(
        app,                    # FastAPI 앱 인스턴스
        host=host,              # 바인딩 주소
        port=port,              # 포트 번호
        log_level="info",       # 로그 레벨
        access_log=True,        # 접근 로그 활성화
    )


# ============= 메인 실행 지점 =============
if __name__ == "__main__":
    # PyInstaller 멀티프로세싱 지원
    multiprocessing.freeze_support()
    
    try:
        # 서버 시작
        run_server()
    except Exception as e:
        print(f"❌ 서버 시작 실패: {e}")
        
        # PyInstaller EXE에서 실행중인 경우 에러 표시 후 대기
        if hasattr(sys, '_MEIPASS'):
            import traceback
            traceback.print_exc()
            input("오류가 발생했습니다. Enter 키를 눌러 종료하세요...")
        else:
            # 일반 Python 환경에서는 즉시 종료
            raise
