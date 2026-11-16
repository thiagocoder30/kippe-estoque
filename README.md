# Kippe Estoque

Sistema de gestão de estoque com integração NF-e e PWA offline-first
para operação em armazém. Desenvolvido e operado em Termux (Android).

## Status

- Versão: v1.3.0-framework-frozen
- Branch ativo: recovery/architecture-reconciliation
- Python: 3.14 (venv local em .venv/)
- Banco: SQLite (data/estoque_producao.db - nao versionado)
- Cobertura: 78% (1144 testes)

## Como rodar

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt
    ./start.sh

O servidor sobe em background e grava o PID em .kippe.pid. Para parar:

    ./stop.sh

Logs em reports/logs/app.log (nao versionado).

## Testes

    pytest                                      # 1144 testes (~75s)
    pytest tests/domain/                        # so dominio
    pytest --cov=src --cov=app                  # com cobertura

Gate de cobertura configurado em pyproject.toml (fail_under = 75).

## Estrutura

- src/                    Clean Architecture (domain / application /
                          use_cases / infrastructure / interfaces /
                          presentation / security)
- app.py                  Entry point canonico (Flask, 33 rotas)
- tests/                  Contract-first, 1144 testes em 11 camadas
- web/                    PWA offline-first (zero dep externa em runtime)
- web/vendor/             Libs JS baixadas localmente (air-gap)
- web/css/generated/      CSS Tailwind pre-compilado
                          (build em tools/frontend-build/)
- scripts/                Automacao operacional (backup-db.sh, etc)
- docs/                   Roadmap, arquitetura, evidencias de sprint
- legacy/                 Codigo arquivado (nao executado)
- data/                   Runtime DB, logs, uploads
                          (NAO versionado, backup externo)
- install/                Bootstrap de ambiente e historico de sprints

## Governanca

- ESTADO_PROJETO.md                  Estado atual do desenvolvimento
- ROADMAP.md                         Proximas fases
- MASTER_MANIFEST.json               Manifesto de sprints
- reports/SPRINT_MANIFEST_*.json     40 manifestos de sprint
- docs/evidence/                     Evidencias por sprint
                                     (audit / red / green / certify)

## Air-gap do frontend (contrato nf-001k.5a.f)

O PWA roda offline em armazem, entao zero dependencia externa em
runtime e regra de negocio, nao preferencia. Os testes em
tests/test_nf_001k_5a_f_frontend_zero_external_dependency_contract.py
falham se qualquer src/href remoto voltar a aparecer.

Para atualizar dependencias JS:

    cd tools/frontend-build
    npm install
    npm run build     # regenera web/css/generated/tailwind.min.css

Depois baixe manualmente a versao pinada da lib em web/vendor/ e
atualize o <script src> em web/index.html.

## Backup

Bancos e documentos NAO estao no git. Backup automatico via cron:

    # Execucao manual
    ./scripts/backup-db.sh

    # Ver agendamento
    crontab -l

Destino: /sdcard/Download/kippe-backups/
- db/          DB SQLite, retencao 14 dias
- documents/   Uploads (DANFE, PDFs), retencao 30 dias

## Pendencias conhecidas

- Sem CI/CD (planejado para GitHub Actions)
- web/js/app.js monolitico (6.7k linhas - refactor planejado)
- main branch ~25 commits atras de recovery/architecture-reconciliation
- src/domain/services/negative_stock_policy.py a 0% de cobertura
- src/infrastructure/inspection/scanner.py a 0% de cobertura (critico)
