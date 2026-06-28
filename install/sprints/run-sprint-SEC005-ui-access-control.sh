#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# PROGRAM B: IDENTITY & SECURITY
# SPRINT SEC005
# UI ACCESS CONTROL (Sincronização de UX/RBAC)
# ============================================================

set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${ROOT}"

export KIPPE_ROOT="${ROOT}"
export KIPPE_LOG_DIR="${ROOT}/reports/logs"

source install/lib/bootstrap.sh
source install/lib/testing.sh

kippe::init
kippe::init_environment

trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=5

kippe::banner_program \
    "B" \
    "SEC005" \
    "UI Access Control"

kippe::step 1 ${TOTAL_STEPS} "Refactoring Frontend Template with Client-Side RBAC Enforcement..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/templates/index.html"
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Kippe Platform | POS Terminal</title>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #eef2f5; margin: 0; padding: 15px; color: #333; }
        .card { background: white; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .btn { width: 100%; padding: 14px; border: none; border-radius: 8px; font-weight: 700; font-size: 16px; margin-bottom: 10px; cursor: pointer; color: white; transition: 0.2s; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-blue { background: #007bff; }
        .btn-green { background: #28a745; }
        .btn-red { background: #dc3545; }
        .btn-gray { background: #6c757d; }
        input { width: 100%; padding: 12px; margin: 5px 0 15px; border: 1px solid #dcdcdc; border-radius: 8px; box-sizing: border-box; font-size:16px; background: #f9f9f9;}
        #reader { width: 100%; border-radius: 12px; overflow: hidden; margin-bottom: 10px; }
        .tabs { display: flex; border-bottom: 2px solid #ddd; margin-bottom: 15px; }
        .tab { flex: 1; text-align: center; padding: 10px; cursor: pointer; font-weight: bold; color: #888; }
        .tab.active { border-bottom: 3px solid #007bff; color: #007bff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .list-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; font-size: 14px; }
        .badge { background: #007bff; color: white; padding: 4px 8px; border-radius: 12px; font-weight: bold; }
        .badge-gerente { background: #fd7e14; }
        .alert-box { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin-bottom: 10px; font-size: 14px; }
        .rbac-blocked { display: none !important; }
        #auth-overlay { position: fixed; top:0; left:0; width:100%; height:100%; background: #eef2f5; z-index:9999; display: flex; align-items: center; justify-content: center; }
        .login-box { width: 90%; max-width: 360px; background: white; padding: 25px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); text-align: center; }
    </style>
</head>
<body>

    <div id="auth-overlay">
        <div class="login-box">
            <h2 style="margin:0 0 5px 0; color:#1a1a1a;">Kippe Platform</h2>
            <p style="color:#666; font-size:14px; margin:0 0 20px 0;">Identificação do Operador</p>
            <input type="number" id="auth-matricula" placeholder="Nº da Matrícula" pattern="\d*">
            <input type="password" id="auth-pin" placeholder="PIN Numérico" inputmode="numeric" pattern="\d*">
            <button class="btn btn-blue" onclick="executarLogin()">🔓 Acessar Terminal</button>
        </div>
    </div>

    <div id="app-context" style="display:none;">
        <div class="list-item" style="background: white; padding: 10px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
            <span>Identidade: <b id="user-display">---</b> <span class="badge" id="role-display">---</span></span>
            <a href="#" onclick="executarLogout()" style="color:#dc3545; font-weight:bold; text-decoration:none; font-size:14px;">Logoff</a>
        </div>

        <div class="card">
            <button class="btn btn-blue" onclick="startScanner()">📷 Iniciar Leitor</button>
            <div id="reader"></div>
        </div>

        <div class="card">
            <div class="tabs">
                <div class="tab active" onclick="switchTab('caixa')">Movimentação</div>
                <div class="tab" onclick="switchTab('reposicao')">Reposição</div>
                <div class="tab" onclick="switchTab('estoque')">Inventário</div>
            </div>

            <div id="caixa-tab" class="tab-content active">
                <input type="text" id="sku" placeholder="SKU LIDO" readonly>
                
                <div id="wrapper-nome-produto" class="rbac-blocked">
                    <label style="font-size: 11px; font-weight: bold; color: #fd7e14;">⚠️ NOVO SKU DETECTADO (Requer Perfil Gerencial):</label>
                    <input type="text" id="nome" placeholder="Nome do Novo Produto">
                </div>

                <input type="number" id="qtd" placeholder="Quantidade" value="1">
                <div style="display:flex; gap:10px;">
                    <div style="flex:1;">
                        <input type="text" id="lote" placeholder="Lote" oninput="validarCampos()">
                    </div>
                    <div style="flex:1;">
                        <input type="date" id="validade" onchange="validarCampos()">
                    </div>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-green" id="btn-entrada" onclick="processarTransacao('+')" disabled>+ Entrada</button>
                    <button class="btn btn-red" onclick="processarTransacao('-')">- Saída (FEFO)</button>
                </div>
            </div>

            <div id="reposicao-tab" class="tab-content">
                <div id="instrucoes-reposicao">
                    <p style="text-align:center; color:#666; font-size: 14px;">Aguardando leitura de gôndola...</p>
                </div>
            </div>

            <div id="estoque-tab" class="tab-content">
                <button class="btn btn-gray" onclick="carregarEstoque()">🔄 Atualizar</button>
                <div id="lista-estoque" style="margin-top: 10px;"></div>
            </div>
        </div>
    </div>

    <script>
        let html5QrcodeScanner;
        let currentTab = 'caixa';
        let operatorRole = 'OPERADOR';

        function playBeep() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                osc.type = 'sine'; osc.frequency.setValueAtTime(880, ctx.currentTime);
                osc.connect(ctx.destination); osc.start(); osc.stop(ctx.currentTime + 0.1);
            } catch (e) {}
        }

        async function checarSessao() {
            const res = await fetch('/api/auth/me');
            const data = await res.json();
            if (data.authenticated) {
                operatorRole = data.operator.role;
                document.getElementById('auth-overlay').style.display = 'none';
                document.getElementById('app-context').style.display = 'block';
                document.getElementById('user-display').innerText = data.operator.name;
                
                const roleBadge = document.getElementById('role-display');
                roleBadge.innerText = operatorRole;
                if(operatorRole === 'GERENTE') {
                    roleBadge.classList.add('badge-gerente');
                } else {
                    roleBadge.classList.remove('badge-gerente');
                }
                
                carregarEstoque();
            } else {
                document.getElementById('auth-overlay').style.display = 'flex';
                document.getElementById('app-context').style.display = 'none';
            }
        }

        async function executarLogin() {
            const matricula = document.getElementById('auth-matricula').value;
            const pin = document.getElementById('auth-pin').value;
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: matricula, pin: pin})
            });
            if(res.ok) {
                document.getElementById('auth-matricula').value = '';
                document.getElementById('auth-pin').value = '';
                checarSessao();
            } else {
                const err = await res.json();
                alert("Bloqueio de Segurança: " + err.error);
            }
        }

        async function executarLogout() {
            await fetch('/api/auth/logout', {method: 'POST'});
            checarSessao();
        }

        function switchTab(t) {
            currentTab = t;
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(t + '-tab').classList.add('active');
            if(t === 'estoque') carregarEstoque();
        }

        function startScanner() {
            if(html5QrcodeScanner) return;
            html5QrcodeScanner = new Html5Qrcode("reader");
            html5QrcodeScanner.start({ facingMode: "environment" }, { fps: 15, qrbox: {width: 250, height: 150} }, 
            (decodedText) => {
                playBeep();
                if (navigator.vibrate) navigator.vibrate(100);
                html5QrcodeScanner.stop(); html5QrcodeScanner = null;
                
                if(currentTab === 'reposicao') gerarPickList(decodedText);
                else {
                    document.getElementById('sku').value = decodedText;
                    verificarCadastro(decodedText);
                }
            }, (err) => {}).catch(err => alert(err));
        }

        async function verificarCadastro(sku) {
            const res = await fetch(`/api/produto/${sku}`);
            const inputNomeWrapper = document.getElementById('wrapper-nome-produto');
            
            if(res.status === 404) {
                // Caso seja novo SKU, valida a capacidade RBAC do usuário logado antes de exibir o formulário
                if(operatorRole !== 'GERENTE') {
                    alert("🛑 OPERAÇÃO BLOQUEADA\nO SKU lido não está cadastrado. Apenas gerentes podem realizar a catalogação de novos produtos.");
                    document.getElementById('sku').value = '';
                    inputNomeWrapper.classList.add('rbac-blocked');
                } else {
                    inputNomeWrapper.classList.remove('rbac-blocked');
                    document.getElementById('nome').focus();
                }
            } else {
                inputNomeWrapper.classList.add('rbac-blocked');
                const data = await res.json();
                document.getElementById('nome').value = data.name;
                document.getElementById('qtd').focus();
            }
            validarCampos();
        }

        function validarCampos() {
            const skuVal = document.getElementById('sku').value;
            const loteVal = document.getElementById('lote').value;
            const dateVal = document.getElementById('validade').value;
            document.getElementById('btn-entrada').disabled = !(skuVal && loteVal && dateVal);
        }

        async function processarTransacao(operacao) {
            const sku = document.getElementById('sku').value;
            const nome = document.getElementById('nome').value;
            const qtd = parseInt(document.getElementById('qtd').value) || 0;
            const lote = document.getElementById('lote').value;
            const validade = document.getElementById('validade').value;

            // Bloqueio preventivo na UI para novos cadastros por operadores
            let resCheck = await fetch(`/api/produto/${sku}`);
            if(resCheck.status === 404) {
                if(operatorRole !== 'GERENTE') {
                    return alert("Erro: Operação negada por política de segurança.");
                }
                if(!nome) return alert("Nome do produto obrigatório para cadastro.");
                
                await fetch('/api/produto', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: sku, name: nome})
                });
            }

            const endpoint = operacao === '+' ? '/api/entrada' : '/api/saida';
            const payload = { id: sku, amount: qtd };
            if (operacao === '+') {
                payload.expiration_date = validade;
                payload.batch_code = lote;
            }

            const resMov = await fetch(endpoint, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            if(resMov.ok) {
                document.getElementById('sku').value = '';
                document.getElementById('nome').value = '';
                document.getElementById('qtd').value = '1';
                document.getElementById('lote').value = '';
                document.getElementById('validade').value = '';
                document.getElementById('wrapper-nome-produto').classList.add('rbac-blocked');
                validarCampos();
                alert("Movimentação processada com sucesso.");
            } else {
                const data = await resMov.json();
                alert("🛑 REJEIÇÃO DA PLATAFORMA:\n" + data.error);
                if(resMov.status === 401 || resMov.status === 403) checarSessao();
            }
        }

        async function carregarEstoque() {
            const res = await fetch('/api/produtos');
            const produtos = await res.json();
            let html = '';
            produtos.forEach(p => {
                html += `<div class="list-item">
                            <span><b>${p.name}</b> <br><small style="color:#888">${p.id}</small></span>
                            <span class="badge">${p.quantity} un</span>
                         </div>`;
            });
            document.getElementById('lista-estoque').innerHTML = html;
        }

        checarSessao();
    </script>
</body>
</html>
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Verifying Code Integrity with Automated Regression Testing Suite..."
# O Hardened Runner faz o linting e a suite valida se os controllers continuam operacionais
kippe::validate_script_syntax "${BASH_SOURCE[0]}"
kippe::test_execute_all

kippe::step 3 ${TOTAL_STEPS} "Updating System Master State Ledger..."
cat << "KIPPE_HUNK" > ESTADO_PROJETO.md
# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 3 (Corporativo) - Domínio SEC Concluído.

## 2. Status Executivo
* **Programa Atual:** PROGRAMA B (Identity & Security)
* **Gate Concluído:** [ GATE B - SECURITY READY ] ✅
* **Última Entrega:** Sprint SEC005 (UI Access Control / UX-RBAC Synchronization)

## 3. Diretórios e Artefatos Essenciais
* `templates/index.html` - (UI POS Inteligente c/ Context-Aware Capability Blocks)
* `src/infrastructure/identity.py` - (Context Resolution Router)
* `src/use_cases/manage_stock.py` - (Core Domain com RBAC Nativo)

## 4. Próxima Ação Requerida
* **GATE B APPROVED.** Com a fundação estável (Program A) e a segurança nominal baseada em políticas concluída no frontend e backend (Program B), a plataforma está pronta para receber o seu primeiro grande domínio de negócios de alto volume: o **PROGRAMA C (Inventory)**. A próxima ação será a **Sprint INV001 (Produtos & Categorias)**, expandindo o domínio para suportar árvores de classificação mercantil complexas.
KIPPE_HUNK

kippe::checkpoint_create "016" "1.0.0" "SEC005" "SUCCESS"
kippe::manifest_create "SEC005" "B" "1.0.0" "SUCCESS" "INV001"

kippe::step 4 ${TOTAL_STEPS} "Purging Untracked Test Relics from Filesystem..."
# Garante que nenhum arquivo de banco temporário suba no commit
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true

kippe::step 5 ${TOTAL_STEPS} "Committing UX Synchronization Layer..."
git add templates/index.html ESTADO_PROJETO.md docs/checkpoints/ reports/SPRINT_MANIFEST_SEC005.json
git commit -m "feat(security): sincroniza UX do terminal POS com as regras de policy do RBAC (SEC005)" || true

kippe::banner_finish
kippe::success "UI Access Control successfully deployed. PROGRAM B OFFICIALLY CONCLUDED."
echo -e "\n============================================="
echo -e "     [ GATE B - SECURITY READY ] APPROVED"
echo -e "============================================="
echo -e "\nNext Program: C (Inventory)"
echo -e "Next Sprint: INV001 (Product Catalog Extension)\n"
exit 0

