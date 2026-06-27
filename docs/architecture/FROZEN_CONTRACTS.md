# 🧊 Kippe Platform: Architecture Freeze (Gate B.1)

## 1. Propósito
Este documento declara o congelamento oficial dos contratos de fundação (Program A) e segurança (Program B). Qualquer alteração nas assinaturas públicas, comportamentos esperados ou interfaces listadas abaixo está terminantemente proibida sem a abertura de uma Sprint Corretiva Estrutural, justificativa via ADR e revisão formal de Gate.

## 2. Contratos Públicos Congelados (Frozen Interfaces)

### Core Integration & DI
* \`src/infrastructure/container.py\` -> Classe \`Container\` (Propriedades públicas: \`config\`, \`logger\`, \`product_repository\`, \`operator_repository\`, \`use_case\`, \`auth_use_case\`, \`identity_provider\`).
* \`src/infrastructure/config.py\` -> Classe \`Config\` (Propriedades: \`ENV\`, \`DB_PATH\`, \`LOG_PATH\`, \`HOST\`, \`PORT\`, \`SECRET_KEY\`).

### Observabilidade & Contexto
* \`src/interfaces/logger.py\` -> Protocolo \`Logger\` (Métodos: \`info\`, \`warning\`, \`error\`).
* \`src/interfaces/identity.py\` -> Protocolo \`IdentityProvider\` (Métodos: \`get_current_operator_id\`, \`get_current_operator_role\`).

### Segurança & Persistência Base
* \`src/domain/operator.py\` -> Classe \`Operator\` e regras de criptografia de PIN via hash.
* \`src/infrastructure/identity.py\` -> Classe \`CurrentOperatorResolver\` (Garantia de Implicit Security Context).
* \`src/interfaces/sqlite_operator_repository.py\` -> Classe \`SQLiteOperatorRepository\`.

## 3. Impacto Operacional
O Domínio de Inventário (Program C) herda estes contratos de forma estritamente imutável. Nenhum caso de uso mercantil poderá exigir parâmetros manuais de contexto que violem a resolução implícita provida pelo \`IdentityProvider\`.
