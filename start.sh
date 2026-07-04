#!/bin/bash

PID_FILE=".kippe.pid"
LOG_FILE="kippe_server.log"

if [ -f "$PID_FILE" ]; then
    echo -e "\033[93m[AVISO] O KIPPE Platform já está rodando (PID: $(cat $PID_FILE)).\033[0m"
    echo "Pode fechar o Termux e acessar o aplicativo."
    exit 1
fi

echo -e "\033[96m[SISTEMA] Iniciando KIPPE Platform em Background...\033[0m"

# Inicia o servidor Python desvinculado do terminal atual
nohup python3 -m src.main > "$LOG_FILE" 2>&1 &

# Salva o número do processo para podermos desligar depois
echo $! > "$PID_FILE"

echo -e "\033[92m[OK] SERVIDOR ENTERPRISE LIGADO!\033[0m"
echo -e "Você já pode sair do Termux."

