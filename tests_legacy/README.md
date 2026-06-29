# Legacy Tests Archive

Este diretório contém testes e scripts de validação desenvolvidos antes da estabilização da **Baseline 1.3.0 (Inventory Frozen)**.

Eles utilizam APIs descontinuadas (como `Batch 0.x` utilizando `batch_id` e `sku` em vez de `code` e `product_id`) e não utilizam o padrão corporativo do `pytest`. Foram movidos para cá visando preservação histórica sem comprometer a esteira de CI/CD e a doutrina Contract-First.
