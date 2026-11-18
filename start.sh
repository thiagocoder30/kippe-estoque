#!/bin/bash

PID_FILE=".kippe.pid"
LOG_FILE="kippe_server.log"

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo -e "\033[93m[AVISO] O KIPPE Platform já está rodando (PID: $OLD_PID).\033[0m"
        echo "Pode fechar o Termux e acessar o aplicativo."
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

echo -e "\033[96m[SISTEMA] Iniciando KIPPE Platform em Background...\033[0m"

PYTHON_BIN=".venv/bin/python"
[ ! -x "$PYTHON_BIN" ] && PYTHON_BIN="python3"

nohup "$PYTHON_BIN" app.py > "$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"

sleep 1
if kill -0 "$PID" 2>/dev/null; then
    echo -e "\033[92m[OK] SERVIDOR ENTERPRISE LIGADO! (PID: $PID)\033[0m"
    echo -e "Você já pode sair do Termux."
else
    rm -f "$PID_FILE"
    echo -e "\033[91m[ERRO] O servidor falhou ao iniciar. Veja o log:\033[0m"
    cat "$LOG_FILE"
    exit 1
fi
