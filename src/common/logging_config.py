import logging, sys

def setup_logging(level: int = logging.INFO):
    """콘솔 로거 간단 설정"""
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(fmt)
    root.addHandler(handler)
    root.setLevel(level)
