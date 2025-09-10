"""
env_reader.py
- 온습도 센서에서 값을 읽어오는 모듈
- 실제 하드웨어 드라이버 호출 부분을 이 파일에서 캡슐화한다.
- 현재는 센서 장치가 없으므로 더미(random) 데이터를 반환하도록 작성.
"""

import random
import datetime

def read_env() -> dict:
    """
    온습도 센서에서 데이터를 읽는다.
    실제 장치가 연결되면 이 부분을 센서 라이브러리 호출로 교체하면 된다.
    
    Returns:
        dict: {"time_stamp": datetime, "temperature": float, "humidity": float}
    """
    return {
        "time_stamp": datetime.datetime.utcnow(),
        "temperature": round(random.uniform(20, 30), 2),  # 예: 20~30도 사이 랜덤
        "humidity": round(random.uniform(30, 70), 2),     # 예: 30~70% 사이 랜덤
    }
