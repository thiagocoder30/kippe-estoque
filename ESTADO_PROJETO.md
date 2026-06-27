# 🌐 KIPPE PLATFORM: Institutional Retail Operations
## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 3 (Corporativo).
## 2. Status Executivo
* **Programa Atual:** PROGRAMA C (Inventory)
* **Gates Transpostos:**
  * [ GATE A - FOUNDATION READY ] ✅
  * [ GATE B - SECURITY READY ] ✅
  * [ GATE B.1 - ARCHITECTURE FREEZE ] ✅
* **Última Entrega:** Sprint INV002.1 (Runner Path Resolution & Categories)
## 3. Diretórios e Artefatos Essenciais
* `src/domain/category.py` -> (Entidade Hierárquica Mercantil)
* `src/use_cases/manage_categories.py` -> (Use Case de Classificação e Regras de Negócio)
* `docs/checkpoints/ARCHITECTURE_SCORECARD-INV002.1.md` -> (Métrica de Qualidade)
## 4. Próxima Ação Requerida
* **Sprint INV003 (Batch & Lot Management):** Desintegrar o dicionário interno em memória do Agregado de Produto, formalizando o Lote (`Batch/Lot`) como uma entidade independente da persistência. Essencial para garantir as invariantes de data de validade antes da ativação do motor FEFO nativo (INV004).
