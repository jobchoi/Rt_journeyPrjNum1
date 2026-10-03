#!/bin/bash

# 설정 변수
PORT=8000
VENV_DIR="venv"
PID_FILE="server.pid"
LOG_FILE="server.log"

start() {
    if [ -f "$PID_FILE" ]; then
        echo "서버가 이미 실행 중인 것 같습니다 (PID: $(cat $PID_FILE))."
        return
    fi
    
    echo "가상환경을 활성화하고 서버를 시작합니다..."
    source $VENV_DIR/bin/activate
    
    # 백그라운드에서 실행하고 로그 저장
    nohup uvicorn src.main:app --host 0.0.0.0 --port $PORT > $LOG_FILE 2>&1 &
    
    # 프로세스 ID 저장
    echo $! > $PID_FILE
    echo "서버가 백그라운드에서 실행되었습니다. (포트: $PORT)"
    echo "로그 확인: ./manage.sh log"
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        echo "서버(PID: $PID)를 종료합니다..."
        kill $PID
        rm $PID_FILE
        echo "서버가 종료되었습니다."
    else
        echo "실행 중인 서버(PID 파일)를 찾을 수 없습니다."
    fi
}

status() {
    if [ -f "$PID_FILE" ]; then
        echo "서버가 실행 중입니다 (PID: $(cat $PID_FILE))."
    else
        echo "서버가 실행 중이지 않습니다."
    fi
}

log() {
    if [ -f "$LOG_FILE" ]; then
        echo "실시간 로그를 출력합니다. (종료하려면 Ctrl+C를 누르세요)"
        tail -f $LOG_FILE
    else
        echo "로그 파일($LOG_FILE)이 아직 생성되지 않았습니다."
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    status)
        status
        ;;
    log)
        log
        ;;
    *)
        echo "사용법: ./manage.sh {start|stop|restart|status|log}"
        exit 1
esac
