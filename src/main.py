from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.modbus_router import router as modbus_router
from src.api.temp_router import router as temp_router
from src.api.humidity_router import router as humidity_router
from src.api.solar_router import router as solar_router
from src.common.logging_config import setup_logging
from src.config.settings import get_allowed_origins

setup_logging()
app = FastAPI(title="Sensor Data API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(modbus_router, prefix="/data")
# app.include_router(temp_router, prefix="/data")
# app.include_router(humidity_router, prefix="/data")
# app.include_router(solar_router, prefix="/data")

@app.get("/health")
def health_check():
    return {"status": "ok"}
