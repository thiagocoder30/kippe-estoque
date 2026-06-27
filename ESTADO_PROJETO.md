# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 2 (Profissional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA B (Identity & Security)
* **Gate Alvo:** GATE B - Security Ready
* **Última Entrega:** Sprint SEC004 (RBAC Gate Control)

## 3. Diretórios e Artefatos Essenciais
* `src/use_cases/` - (Core Domain com Gatekeepers RBAC)
* `src/infrastructure/identity.py` - (Context Resolver consciente de Role/Nível de Acesso)
* `install/lib/validation.sh` - (Runner Execution Safety Layer)

## 4. Próxima Ação Requerida
* **Sprint SEC005 (UI Access Control):** Com o núcleo lógico bloqueando transações proibidas, precisamos refletir essas restrições visualmente. O *Frontend* (UI POS) deve consumir o `operator_role` da sessão e ocultar/desabilitar botões gerenciais para os Operadores, melhorando a UX e prevenindo chamadas HTTP desnecessárias.
