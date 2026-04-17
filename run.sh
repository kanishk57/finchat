#!/bin/bash

# FinChat Execution Script
# Updated to work with refactored modular structure (v2.6.3)

# CONFIGURATION
MODEL_PATH="models/gemma-3-1b-it-f16.gguf"
SERVER_PORT=8080
LOG_FILE="/tmp/llama_server.log"
LLM_OFFLINE=0
START_TS=$(date +%s)

# Colors for output
CYAN='\033[0;36m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_banner() {
    printf "\n${BOLD}${CYAN}╭────────────────────────────────────────────────────────╮${NC}\n"
    printf "${BOLD}${CYAN}│${NC} ${BOLD}${CYAN} ______ _       _____ _           _   ${NC}        ${BOLD}${CYAN}│${NC}\n"
    printf "${BOLD}${CYAN}│${NC} ${BOLD}${CYAN}|  ____(_)     / ____| |         | |  ${NC}        ${BOLD}${CYAN}│${NC}\n"
    printf "${BOLD}${CYAN}│${NC} ${BOLD}${CYAN}| |__   _ _ __ | |    | |__   ___ | |_ ${NC}        ${BOLD}${CYAN}│${NC}\n"
    printf "${BOLD}${CYAN}│${NC} ${BOLD}${CYAN}|  __| | | '_ \| |    | '_ \ / _ \| __|${NC}        ${BOLD}${CYAN}│${NC}\n"
    printf "${BOLD}${CYAN}│${NC} ${BOLD}${CYAN}| |    | | | | | |____| | | | (_) | |_ ${NC}        ${BOLD}${CYAN}│${NC}\n"
    printf "${BOLD}${CYAN}│${NC} ${BOLD}${CYAN}|_|    |_|_| |_|\_____|_| |_|\___/ \__|${NC}        ${BOLD}${CYAN}│${NC}\n"
    printf "${BOLD}${CYAN}│${NC} ${BOLD}FinChat Optimized RAG${NC} ${DIM}(Modular v2.6.3)${NC}%*s${BOLD}${CYAN}│${NC}\n" 16 ""
    printf "${BOLD}${CYAN}╰────────────────────────────────────────────────────────╯${NC}\n"
}

step() {
    printf "${BOLD}${BLUE}[%s]${NC} %s\n" "$1" "$2"
}

ok() {
    printf "${GREEN}  OK${NC} %s\n" "$1"
}

warn() {
    printf "${YELLOW}  !!${NC} %s\n" "$1"
}

err() {
    printf "${RED}  XX${NC} %s\n" "$1"
}

spinner_wait_for_health() {
    local url="$1"
    local timeout_seconds="$2"
    local elapsed=0
    local spinner='|/-\\'
    local i=0

    while [ "$elapsed" -lt "$timeout_seconds" ]; do
        if curl -s -o /dev/null "$url"; then
            printf "\r${GREEN}  OK${NC} LLM server is ready.                      \n"
            return 0
        fi

        i=$(( (i + 1) % 4 ))
        printf "\r${YELLOW}  ..${NC} Waiting for LLM server %s" "${spinner:$i:1}"
        sleep 1
        elapsed=$((elapsed + 1))
    done

    printf "\r${RED}  XX${NC} LLM server did not become ready in time.   \n"
    return 1
}

print_summary() {
    local elapsed=$(( $(date +%s) - START_TS ))
    local llm_state="ONLINE"
    local llm_color="$GREEN"
    local llm_note="Connected to localhost:${SERVER_PORT}"

    if [ "$LLM_OFFLINE" -eq 1 ]; then
        llm_state="OFFLINE"
        llm_color="$YELLOW"
        llm_note="Start llama-server to enable generation"
    fi

    printf "\n${BOLD}${CYAN}╭──────────────────── FinChat Session ────────────────────╮${NC}\n"
    printf "${BOLD}${CYAN}│${NC} ${DIM}Runtime${NC}      ${BOLD}%6ss${NC}%*s${BOLD}${CYAN}│${NC}\n" "$elapsed" 34 ""
    printf "${BOLD}${CYAN}│${NC} ${DIM}Web UI${NC}       ${GREEN}http://127.0.0.1:8000${NC}%*s${BOLD}${CYAN}│${NC}\n" 18 ""
    printf "${BOLD}${CYAN}│${NC} ${DIM}LLM Status${NC}   ${llm_color}${llm_state}${NC}%*s${BOLD}${CYAN}│${NC}\n" 35 ""
    printf "${BOLD}${CYAN}│${NC} ${DIM}LLM Detail${NC}   ${DIM}%s${NC}%*s${BOLD}${CYAN}│${NC}\n" "$llm_note" $(( 43 - ${#llm_note} )) ""
    printf "${BOLD}${CYAN}│${NC} ${DIM}Model${NC}        ${DIM}%s${NC}%*s${BOLD}${CYAN}│${NC}\n" "$MODEL_PATH" $(( 43 - ${#MODEL_PATH} )) ""
    printf "${BOLD}${CYAN}╰────────────────────────────────────────────────────────╯${NC}\n"
}

on_exit() {
    print_summary
}

trap on_exit EXIT

print_banner

# 0. Handle Arguments
REBUILD=0
for arg in "$@"; do
    if [ "$arg" == "--rebuild" ]; then
        REBUILD=1
    fi
done

if [ $REBUILD -eq 1 ]; then
    warn "Rebuild flag detected. Deleting current embeddings..."
    rm -f faiss.index metadata.pkl
fi

# 1. Check for Virtual Environment
if [ -d "venv" ]; then
    step "1/3" "Activating virtual environment"
    source venv/bin/activate
    ok "Virtual environment activated"
else
    err "Virtual environment (venv) not found."
    exit 1
fi

# 2. Check/Start llama.cpp server
step "2/3" "Checking LLM server"
curl -s -o /dev/null --connect-timeout 2 http://localhost:$SERVER_PORT/health
if [ $? -ne 0 ]; then
    warn "Server not detected. Starting llama-server in background..."
    if [ ! -f "$MODEL_PATH" ]; then
        err "Model not found at $MODEL_PATH"
        exit 1
    fi
    
    SERVER_BIN="./llama.cpp/build/bin/llama-server"
    if [ ! -f "$SERVER_BIN" ]; then
        SERVER_BIN="llama-server" 
    fi

    if [ ! -x "$SERVER_BIN" ] && ! command -v "$SERVER_BIN" >/dev/null 2>&1; then
        warn "llama-server binary not found. Skipping local model server startup."
        warn "The web app will still start, but chat generation needs a running LLM server on port ${SERVER_PORT}."
        LLM_OFFLINE=1
    else
        $SERVER_BIN -m $MODEL_PATH --port $SERVER_PORT > "$LOG_FILE" 2>&1 &
        SERVER_PID=$!

        spinner_wait_for_health "http://localhost:$SERVER_PORT/health" 30
        if [ $? -eq 0 ]; then
            ok "Server started successfully"
        else
            err "Server failed to start. Check $LOG_FILE"
            if kill -0 "$SERVER_PID" 2>/dev/null; then
                kill "$SERVER_PID"
            fi
            warn "Continuing without a local model server."
            LLM_OFFLINE=1
        fi
    fi
else
    ok "Server is already running"
fi

if [ "$LLM_OFFLINE" -eq 1 ]; then
    export FINCHAT_LLM_OFFLINE=1
    warn "FinChat will start in offline mode. Chat requests will show a friendly unavailable message until the LLM server is up."
fi

# 3. Run the application
step "3/3" "Launching FinChat Web Interface"
printf "${DIM}Note:${NC} Using modular server structure with separated concerns\n"
uvicorn server:app --host 0.0.0.0 --port 8000

# Deactivate virtual environment on exit
deactivate
