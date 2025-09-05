import logging, sys

def setup_logging(level: str = "INFO") -> None:
    """콘솔 로거 기본 설정."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
