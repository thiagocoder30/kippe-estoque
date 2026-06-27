# 🌐 KIPPE PLATFORM: Institutional Retail Operations

## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 2 (Profissional).

## 2. Status Executivo
* **Programa Atual:** PROGRAMA B (Identity & Security)
* **Gate Alvo:** GATE B - Security Ready
* **Última Entrega:** Sprint SEC003.1 (Identity Propagation Layer)

## 3. Diretórios e Artefatos Essenciais
* `src/infrastructure/identity.py` - (Nominal Context Resolver / Propagation Layer)
* `src/infrastructure/container.py` - (IoC Injetando Dependência de Contexto automaticamente)
* `src/use_cases/` - (Domínio agnóstico à infraestrutura web, resolvendo autoria via interface)

## 4. Próxima Ação Requerida
* **Sprint SEC004 (RBAC Gate Control):** Com a propagação de identidade operando de forma coesa (e os testes passando limpos), vamos estender a autoridade do Domínio de Estoque. Ações destrutivas passarão a consultar não apenas *quem* é o operador, mas *qual* é o seu `operator_role` (OPERADOR vs. GERENTE).
