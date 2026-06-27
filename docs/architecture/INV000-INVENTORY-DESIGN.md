# 📦 Domain Design: PROGRAMA C (Inventory)

## 1. Linguagem Ubíqua (Ubiquitous Language)
* **Mercadoria / Produto (Product):** Elemento master do catálogo mercantil. Possui SKU único, nome descritivo, e unidade de medida padrão (un, kg, lt).
* **SKU (Stock Keeping Unit):** Identificador alfanumérico único e imutável que mapeia o código de barras físico do produto.
* **Lote (Batch/Lot):** Recipiente temporal de estoque físico. Um produto possui N lotes ativos, cada um com seu código identificador, quantidade física e data de validade estrita.
* **Vencimento (Expiration Date):** Data limiar de validade da mercadoria. O sistema proíbe a venda ou movimentação de lotes cuja validade seja menor ou igual à data corrente.
* **Algoritmo FEFO (First Expiring, First Out):** Política de escoamento automático onde as baixas de estoque priorizam o lote com a data de vencimento mais próxima, mitigando perdas financeiras por quebra sanitária.
* **Pick-List (Lista de Separação de Gôndola):** Instrução de retirada gerada sequencialmente pelo algoritmo FEFO, direcionando o repositor ao lote exato no depósito.
* **Ruptura de Estoque (Stockout):** Estado crítico onde a quantidade física total de um SKU atinge zero, impedindo a venda e disparando alertas operacionais.

## 2. Entidades e Agregados (Domain Mapping)
\`\`\`text
[ Product Aggregate Root ]
   └── id: SKU (String, Imutável)
   └── name: Nome (String)
   └── quantity: Quantidade Total Calculada (Integer)
   └── [ Batches Dictionary ]
          └── Key: Batch Code (String)
          └── Value: [ Batch Value Object ]
                 ├── expiration_date: Data (YYYY-MM-DD)
                 └── quantity: Quantidade do Lote (Integer)
\`\`\`

## 3. Invariantes de Negócio (Políticas Inegociáveis)
1. **Invariante de Quantidade Física:** O estoque de um lote ou do produto master jamais poderá ser negativo sob qualquer pretexto operacional.
2. **Invariante de Entrada (Bloqueio de Doca):** É proibida a entrada de lotes vencidos ou que vençam no dia corrente do recebimento.
3. **Invariante de Autoria Nominal:** Nenhuma movimentação de inventário (Entrada/Saída) possui existência anônima. Toda transação deve capturar implicitamente o \`operator_id\` do runtime.
