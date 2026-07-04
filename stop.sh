#!/bin/bash

PID_FILE=".kippe.pid"

if [ ! -f "$PID_FILE" ]; then
    echo -e "\033[91m[ERRO] O KIPPE Platform não está rodando.\033[0m"
    exit 1
fi

PID=$(cat "$PID_FILE")

echo -e "\033[93m[SISTEMA] Encerrando o KIPPE Platform...\033[0m"

# Encerra o processo do servidor
kill $PID
rm "$PID_FILE"

echo -e "\033[92m[OK] SERVIDOR DESLIGADO COM SUCESSO.\033[0m\n"

