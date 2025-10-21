# src/collectors/serial_manager.py
"""
RS485 시리얼 포트 관리자
여러 collector가 안전하게 같은 COM 포트를 공유
"""

import threading
import logging
from typing import Dict, Optional, Callable, Any

log = logging.getLogger("serial_manager")

class SerialPortManager:
    """
    Thread-safe 시리얼 포트 관리
    싱글톤 패턴으로 같은 포트는 하나의 인스턴스만 생성
    """
    _instances: Dict[str, 'SerialPortManager'] = {}
    _locks: Dict[str, threading.Lock] = {}
    
    def __init__(self, port: str):
        self.port = port
        self._lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, port: str) -> 'SerialPortManager':
        """싱글톤: 같은 포트는 하나의 인스턴스"""
        if port not in cls._instances:
            cls._instances[port] = cls(port)
            cls._locks[port] = threading.Lock()
            log.info(f"✅ SerialPortManager 생성: {port}")
        return cls._instances[port]
    
    def execute(self, func: Callable[[], Any]) -> Optional[Any]:
        """
        Thread-safe 실행
        
        Args:
            func: 실행할 함수 (시리얼 포트 사용)
        
        Returns:
            함수 실행 결과 또는 None
        """
        with self._lock:
            try:
                return func()
            except Exception as e:
                log.debug(f"⚠️ Serial operation failed on {self.port}: {e}")
                raise
