# ADR 001: Arquitetura de Identidade e Segurança (Programa B)

## 1. Contexto Operacional e Ameaças (Threat Model)
* **Ambiente:** Dispositivo móvel compartilhado no chão de loja (Kiosk Mode/Shared Device).
* **Vetor de Risco:** Operador A loga no sistema, esquece de deslogar, e Operador B realiza movimentações no nome de A (Falso Positivo de Auditoria).
* **Fricção:** Operadores de varejo não têm tempo para digitar senhas alfanuméricas complexas no meio de uma reposição de gôndola.

## 2. Modelo de Autenticação (AuthN)
A plataforma abandonará o modelo corporativo tradicional (E-mail/Senha) em favor de um **Modelo de Frente de Caixa (POS)**:
* **Credencial Primária:** Matrícula Numérica (Ex: 1045) ou Leitura de Crachá (Código de Barras do Operador).
* **Credencial Secundária (Fator de Conhecimento):** PIN de 4 a 6 dígitos (Ex: 123456).
* **Sessão:** Efêmera. O sistema exigirá reautenticação rápida por PIN após X minutos de inatividade para proteger o contexto compartilhado.

## 3. Modelo de Autorização (AuthZ) - RBAC
Role-Based Access Control restrito e codificado no Domínio:
* **OPERADOR:** Pode ler inventário, realizar Entradas e Saídas. NÃO pode excluir registros, modificar histórico ou cadastrar usuários.
* **GERENTE:** Acesso irrestrito. Pode anular transações (compensação reversa), extrair relatórios e redefinir PINs.
* **SISTEMA:** Ator não-humano para rotinas automatizadas (Ex: Backup, Alertas de Ruptura).

## 4. Auditoria Imutável (Audit Trail v2)
A entidade `Transaction` será refatorada. A assinatura do evento deixará de ser anônima.
* **Antes:** `(id, product_id, type, amount, timestamp)`
* **Agora:** `(id, product_id, type, amount, timestamp, operator_id)`
Nenhuma mudança de estado no Core Domain (Motor FEFO) será permitida sem um `operator_id` válido no contexto da requisição.
