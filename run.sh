#!/bin/bash

# FinChat Execution Script

# CONFIGURATION
MODEL_PATH="models/gemma-3-1b-it-f16.gguf"
SERVER_PORT=8080
LOG_FILE="/tmp/llama_server.log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting FinChat Optimized RAG ===${NC}"

# 0. Handle Arguments
REBUILD=0
for arg in "$@"; do
    if [ "$arg" == "--rebuild" ]; then
        REBUILD=1
    fi
done

if [ $REBUILD -eq 1 ]; then
    echo -e "${YELLOW}Rebuild flag detected. Deleting current embeddings...${NC}"
    rm -f faiss.index metadata.pkl
fi

# 1. Check for Virtual Environment
if [ -d "venv" ]; then
    echo -e "${YELLOW}[1/3] Activating virtual environment...${NC}"
    source venv/bin/activate
else
    echo -e "${RED}Error: Virtual environment (venv) not found.${NC}"
    exit 1
fi

# 2. Check/Start llama.cpp server
echo -e "${YELLOW}[2/3] Checking llama-server status...${NC}"
curl -s -o /dev/null --connect-timeout 2 http://localhost:$SERVER_PORT/health
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Server not detected. Starting llama-server in background...${NC}"
    if [ ! -f "$MODEL_PATH" ]; then
        echo -e "${RED}Error: Model not found at $MODEL_PATH${NC}"
        exit 1
    fi
    
    SERVER_BIN="./llama.cpp/build/bin/llama-server"
    if [ ! -f "$SERVER_BIN" ]; then
        SERVER_BIN="llama-server" 
    fi

    $SERVER_BIN -m $MODEL_PATH --port $SERVER_PORT > "$LOG_FILE" 2>&1 &
    SERVER_PID=$!
    
    echo -e "${YELLOW}Waiting for server to initialize...${NC}"
    for i in {1..30}; do
        if curl -s -o /dev/null http://localhost:$SERVER_PORT/health; then
            echo -e "${GREEN}Server started successfully.${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}Error: Server failed to start. Check $LOG_FILE${NC}"
            kill $SERVER_PID
            exit 1
        fi
        sleep 1
    done
else
    echo -e "${GREEN}Server is already running.${NC}"
fi

# 3. Run the application
echo -e "${YELLOW}[3/3] Launching FinChat Web Interface...${NC}"
uvicorn server:app --host 0.0.0.0 --port 8000

deactivate
