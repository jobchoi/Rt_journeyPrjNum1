#!/usr/bin/env bash
set -u

# 상대 경로(DB, 템플릿, 로그)를 항상 프로젝트 루트에서 해석합니다.
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR" || exit 1
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
PID_FILE="$PROJECT_DIR/server.pid"
LOG_FILE="$PROJECT_DIR/server.log"

resolve_python() {
    if [[ -n "${VENV_DIR:-}" ]]; then
        PYTHON="$VENV_DIR/bin/python"
    elif [[ -x .venv/bin/python ]]; then
        PYTHON="$PROJECT_DIR/.venv/bin/python"
    elif [[ -x venv/bin/python ]]; then
        PYTHON="$PROJECT_DIR/venv/bin/python"
    else
        PYTHON="$(command -v python3 || command -v python || true)"
    fi
    if [[ -z "$PYTHON" || ! -x "$PYTHON" ]]; then
        echo "Python 실행 파일을 찾을 수 없습니다. VENV_DIR 또는 Python 환경을 확인하세요." >&2
        return 1
    fi
    if ! "$PYTHON" -c 'import uvicorn' >/dev/null 2>&1; then
        echo "선택한 Python에 uvicorn이 없습니다: $PYTHON" >&2
        echo "해당 환경에서 python -m pip install -r requirements.txt 를 실행하세요." >&2
        return 1
    fi
}

read_pid() {
    PID=""
    [[ -f "$PID_FILE" ]] || return 1
    read -r PID < "$PID_FILE" || return 1
    [[ "$PID" =~ ^[1-9][0-9]*$ ]] || return 1
    kill -0 "$PID" 2>/dev/null || return 1
    # 오래된 PID가 다른 프로세스에 재사용되어도 종료하지 않습니다.
    [[ "$(ps -p "$PID" -o args=)" == *"uvicorn src.main:app"* ]] || return 1
    [[ ! -d /proc/$PID || "$(readlink "/proc/$PID/cwd")" == "$PROJECT_DIR" ]] || return 1
}

start() {
    if read_pid; then
        echo "서버가 이미 실행 중입니다 (PID: $PID)."
        return 0
    fi
    resolve_python || return 1
    rm -f -- "$PID_FILE"
    echo "서버를 시작합니다 (Python: $PYTHON)..."
    nohup "$PYTHON" -m uvicorn src.main:app --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 < /dev/null &
    PID=$!
    echo "$PID" > "$PID_FILE"
    for ((attempt=0; attempt<30; attempt++)); do
        if ! kill -0 "$PID" 2>/dev/null; then
            wait "$PID" 2>/dev/null
            rm -f -- "$PID_FILE"
            echo "서버 시작에 실패했습니다. 로그: $LOG_FILE" >&2
            tail -n 20 "$LOG_FILE" >&2
            return 1
        fi
        if [[ "$(cat "$LOG_FILE")" == *"Uvicorn running on"* ]]; then
            echo "서버가 백그라운드에서 실행되었습니다. (PID: $PID, 포트: $PORT)"
            echo "로그 확인: ./manage.sh log"
            return 0
        fi
        sleep 1
    done
    echo "서버 시작 대기 시간이 초과되었습니다. 로그: $LOG_FILE" >&2
    stop
    return 1
}

stop() {
    if ! read_pid; then
        rm -f -- "$PID_FILE"
        echo "실행 중인 서버를 찾을 수 없습니다."
        return 0
    fi
    echo "서버(PID: $PID)를 종료합니다..."
    kill "$PID" || return 1
    for ((attempt=0; attempt<30; attempt++)); do
        if ! read_pid; then
            rm -f -- "$PID_FILE"
            echo "서버가 종료되었습니다."
            return 0
        fi
        sleep 1
    done
    echo "서버 종료 대기 시간이 초과되었습니다 (PID: $PID)." >&2
    return 1
}

status() {
    if read_pid; then
        echo "서버가 실행 중입니다 (PID: $PID)."
    else
        echo "서버가 실행 중이지 않습니다."
        return 1
    fi
}

log() {
    if [[ -f "$LOG_FILE" ]]; then
        tail -f "$LOG_FILE"
    else
        echo "로그 파일($LOG_FILE)이 아직 생성되지 않았습니다."
        return 1
    fi
}

case "${1:-}" in
    start) start ;;
    stop) stop ;;
    restart) resolve_python && stop && start ;;
    status) status ;;
    log) log ;;
    *) echo "사용법: ./manage.sh {start|stop|restart|status|log}"; exit 1 ;;
esac
