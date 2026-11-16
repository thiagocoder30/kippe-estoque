# Legacy — código arquivado

## main_httpserver_DEV001.1.py.bak

**Origem**: `src/main.py` (Sprint DEV001.1, commit 40c30ec)
**Arquivado em**: 2026-11-16
**Motivo**: substituído por `app.py` (Flask) no Sprint 006

### Contexto histórico

- **Até Sprint 005**: `src/main.py` era CLI + `ThreadingHTTPServer` (stdlib, zero deps)
- **Sprint 006** (`install/sprints/archive_mvp/run-sprint-006.sh:16`): migração consciente para Flask, com comentário *"Remove o main.py antigo (CLI) pois agora usaremos app.py (Servidor Web)"*
- **Até hoje**: `src/main.py` sobreviveu como arquivo zumbi — não importado, não testado, não usado por `start.sh`
- **Entry point canônico**: `app.py` (Flask, 33 rotas, todos os testes importam `from app import app, container`)

### Se você está aqui procurando o entry point

Use `./start.sh` que invoca `python3 app.py`. **Não** invoque este arquivo.

### Por que foi arquivado em vez de deletado

- Preserva evidência histórica da migração CLI → Flask
- O `main` branch ainda pode referenciar (precisa de reconciliação de branch — ver Sessão 2)
- Removível após merge de `recovery/architecture-reconciliation` em `main`
