# 🌐 KIPPE PLATFORM: Institutional Retail Operations
## 1. Visão Estratégica Global
* **Propósito:** Plataforma institucional de operações para o varejo de alto giro.
* **Governança:** Planejamento orientado a Programas, Domínios, Sprints e Gates.
* **Maturidade Atual do Sistema:** Nível 3 (Corporativo).
## 2. Status Executivo
* **Programa Atual:** PROGRAMA C (Inventory)
* **Gates Transpostos:**
  * [ GATE A / B / B.1 ] ✅
  * [ GATE INFRA - SAFE REFACTOR ] ✅
* **Última Entrega:** Sprint INV006 (Stock Reservation Lifecycle)
## 3. Diretórios e Artefatos Essenciais
* `src/domain/reservation.py` -> (Lifecycle gerencial com Time-To-Live / TTL)
* `src/interfaces/sqlite_reservation_repository.py` -> (Separação de Persistência via SRP)
* `install/lib/refactor_engine.py` -> (Motor responsável pela evolução cirúrgica da plataforma)
## 4. Próxima Ação Requerida
* **Sprint INV007 (Warehouse Locations):** Com os estoques protegidos logicamente e com validade de bloqueio estrita, passamos para a dimensão espacial: mapeamento do endereço físico (Rua, Corredor, Prateleira), fundamental para a rota de Picking baseada em FEFO.
