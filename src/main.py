"""
FastAPI 앱 시작점
- CORS 허용
- /data/modbus 라우터 제공
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import modbus_router
from src.common.logging_config import setup_logging
from src.config.settings import settings

setup_logging()
app = FastAPI(title="Sensor Monitoring API")

# CORS (프론트 개발용)
origins = []
if settings.cors_origins:
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(modbus_router.router)

@app.get("/")
def root():
    return {"status": "ok"}
