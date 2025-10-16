# ⚡ IoT 에너지 모니터링 시스템 - 백엔드

FastAPI 기반 실시간 센서 데이터 수집 및 시계열 데이터 관리 시스템

---

## 📋 프로젝트 개요

산업용 IoT 센서(전력량계, 온습도, 일사량)로부터 데이터를 수집하고 TimescaleDB에 저장하여 RESTful API로 제공합니다.

***

## 🛠 기술 스택

- **언어**: Python 3.10+
- **프레임워크**: FastAPI
- **데이터베이스**: PostgreSQL 16 + TimescaleDB 2.x
- **센서 통신**: Modbus RTU (minimalmodbus)
- **서버**: Uvicorn (ASGI)

***

## ✨ 주요 기능

- 실시간 센서 데이터 수집 (5초 주기)
- 시계열 데이터 자동 집계 (1분 → 15분 → 1시간 → 1일)
- RESTful API (실시간/히스토리 조회)
- 더미 모드 지원 (실제 센서 없이 테스트 가능)
- 전력 데이터 분석 (유효/무효/피상전력, 역률)

***

## 🚀 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone https://github.com/your-username/energy-monitoring-backend.git
cd energy-monitoring-backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 데이터베이스 설정

```bash
# PostgreSQL + TimescaleDB 설치 필요
createdb energydb
psql -d energydb -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

# 테이블 생성
python -m src.db.bootstrap
```

### 3. 환경 변수 설정

`.env` 파일 생성:

```bash
MODE=dummy  # real: 실제 센서, dummy: 테스트
PG_DSN=postgresql://postgres:password@localhost:5432/energydb
CORS_ORIGINS=http://localhost:5173

# Modbus 설정 (실제 센서 사용 시)
MODBUS_PORT=COM7
MODBUS_BAUDRATE=9600
MODBUS_4W_IDS=11,12,13
MODBUS_3W_IDS=14,15
```

### 4. 서버 실행

```bash
# 개발 모드
uvicorn src.main:app --reload

# API 문서: http://localhost:8000/docs
```

***

## 📡 API 엔드포인트

### Modbus (전력량계)

```http
GET /api/modbus/{device_id}/realtime          # 실시간 데이터
GET /api/modbus/{device_id}/query             # 히스토리 데이터
GET /api/modbus/{device_id}/today-energy      # 오늘 누적 전력량
```

**쿼리 파라미터**:
- `preset`: `1day` | `1week` | `1month` | `1year`
- `start`, `end`: ISO 8601 형식 (커스텀 범위)

### 환경센서 / 일사량센서

```http
GET /api/env/{device_id}/realtime
GET /api/env/{device_id}/query
GET /api/solar/{device_id}/realtime
GET /api/solar/{device_id}/query
```

***

## 📁 프로젝트 구조

```
backend/
├── src/
│   ├── main.py              # FastAPI 앱
│   ├── config/settings.py   # 환경 변수
│   ├── db/
│   │   ├── client.py        # DB 연결
│   │   └── bootstrap.py     # 테이블 생성
│   ├── routers/             # API 엔드포인트
│   ├── services/            # 비즈니스 로직
│   └── sensors/             # 센서 통신 및 수집
├── .env
├── requirements.txt
└── README.md
```

***

## 🔧 주요 의존성

```txt
fastapi==0.118.0
uvicorn==0.37.0
psycopg2-binary==2.9.8
minimalmodbus==2.0.1
pyserial==3.5
python-dotenv==1.0.0
pydantic==2.11.9
```

***

## 📝 라이센스

MIT License

***