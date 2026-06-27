# 📦 Kippe-Estoque Core: Master Roadmap Institucional

## 1. Visão Geral
* **Objetivo:** Sistema de alta performance para controle logístico de alto volume e prevenção de perdas em supermercados.
* **Arquitetura:** Clean Architecture, O(1) Core Domain, RESTful API (Flask), SQLite ACID.
* **Ambiente:** Termux Server (Galaxy A50) + Client HTML5 Mobile-First.

---

## 2. Roadmap de Engenharia (Sprints)

### FASE 1: Fundação & Domínio Core (Concluída)
* [x] **Sprint 001:** Clean Architecture & Entidade Core (`Product`).
* [x] **Sprint 002:** Casos de Uso Isolados & CI Pipeline Local.

### FASE 2: Persistência & Adaptadores (Concluída)
* [x] **Sprint 003:** SQLite Repository & Operações de Upsert Idempotentes.
* [x] **Sprint 004:** Injeção de Dependência & CLI Interativa.

### FASE 3: Transição Web & Usabilidade de Chão de Loja (Concluída)
* [x] **Sprint 005:** (Hotfix) Rollback do Scanner CLI.
* [x] **Sprint 006:** Servidor Web Flask, API RESTful & Scanner HTML5-QRCode.
* [x] **Sprint 007:** Audit Trail (Histórico Imutável ACID) & UX Sonora (Beep).

### FASE 4: Governança & Segurança (A Fazer)
* [ ] **Sprint 008:** Autenticação de Operador (Sistema de PIN numérico para registrar *quem* fez a movimentação no Audit Trail).
* [ ] **Sprint 009:** Níveis de Acesso (Gerente vs. Repositor/Caixa - bloqueio de exclusão de produtos).

### FASE 5: Inteligência de Negócio & Relatórios (A Fazer)
* [ ] **Sprint 010:** Dashboard Analítico (Alerta de estoque baixo).
* [ ] **Sprint 011:** Exportação de Dados (Gerar arquivo CSV das movimentações do dia e salvar no `/sdcard/Download`).

### FASE 6: Resiliência & Deploy de Produção (A Fazer)
* [ ] **Sprint 012:** Backup Automático do Banco de Dados (`.db`) agendado.
* [ ] **Sprint 013:** Configuração de autostart do servidor Flask ao ligar o Termux.

---

## 3. Protocolo de Recuperação de Contexto
Em caso de falha de comunicação ou alucinação da IA, o desenvolvedor deve copiar o conteúdo integral deste arquivo e enviar no novo chat com o comando:
> *"Retomando Kippe-Estoque Core. O estado atual é este. Vamos iniciar a próxima Sprint pendente."*

