"""
collector(1분 주기 DB 저장) + realtime_monitor(5초 주기 실시간 전력계산)
두 개를 병렬로 실행
"""
import multiprocessing
from src.ingest.collector import main as collector_main
from src.ingest.realtime_monitor import main as monitor_main

def run_collector():
    collector_main()

def run_monitor():
    monitor_main()

if __name__ == "__main__":
    p1 = multiprocessing.Process(target=run_collector)
    p2 = multiprocessing.Process(target=run_monitor)

    p1.start()
    p2.start()

    p1.join()
    p2.join()
