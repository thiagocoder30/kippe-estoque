#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# INFRASTRUCTURE HARDENING
# SPRINT INF005.1: SEMANTIC GATE HOTFIX & SYNTAX RESOLUTION
# ============================================================

set -Eeuo pipefail

export KIPPE_ROOT="${KIPPE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "${KIPPE_ROOT}"

source install/lib/bootstrap.sh
source install/lib/testing.sh
source install/lib/validation.sh

kippe::init
kippe::init_environment

trap 'kippe::on_error ${LINENO}' ERR

TOTAL_STEPS=5

kippe::banner_program \
    "INF" \
    "INF005.1" \
    "Semantic Gate Hotfix & Syntax Resolution"

kippe::step 1 ${TOTAL_STEPS} "Applying Surgical Syntax Fix via SafeRefactor Engine..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/sprints/hotfix_sqlite_syntax.py"
import os
import sys
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor

def fix_invalid_list_comp(content: str) -> str:
    # Remove a sintaxe inválida "as data" que ficou residual no arquivo
    target = "return [dict(row) as data for row in rows]"
    replacement = "return [dict(row) for row in rows]"
    return content.replace(target, replacement)

try:
    with SafeRefactor("src/interfaces/sqlite_repository.py") as sr:
        sr.apply(fix_invalid_list_comp)
except Exception as e:
    print(f"Falha no Hotfix: {e}")
    sys.exit(1)
KIPPE_HUNK
python3 "${KIPPE_ROOT}/install/sprints/hotfix_sqlite_syntax.py"

kippe::step 2 ${TOTAL_STEPS} "Supercharging Semantic Validator (INF004) with Custom KIPPE Anti-Patterns..."
cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/lib/semantic_validator.py"
import os
import sys
import ast
import re
from pathlib import Path

def run_semantic_checks(root_dir: Path) -> bool:
    """
    KIPPE Semantic Repository Gate.
    Procura por code smells históricos antes da compilação AST.
    """
    has_errors = False
    
    # Anti-patterns mapeados historicamente
    bash_leak_pattern = re.compile(r'\$\{[a-zA-Z_][a-zA-Z0-9_]*\}')
    invalid_as_pattern = re.compile(r'\[.*? as .*? for .*? in .*?\]')
    
    for filepath in root_dir.rglob("*.py"):
        if "venv" in filepath.parts or "__pycache__" in filepath.parts:
            continue
            
        try:
            content = filepath.read_text(encoding="utf-8")
            
            # 1. Semantic Rules (Regras de Negócio de Infra)
            leaks = bash_leak_pattern.findall(content)
            if leaks:
                print(f"[SEMANTIC FATAL] Vazamento de variavel Bash \${{...}} detectado em {filepath.name}: {set(leaks)}")
                has_errors = True
                
            invalid_comps = invalid_as_pattern.findall(content)
            if invalid_comps:
                print(f"[SEMANTIC FATAL] Uso invalido da keyword 'as' em compreensao de lista no {filepath.name}: {invalid_comps}")
                has_errors = True
                
            # 2. Unreachable Code Detection (AST Walk)
            tree = ast.parse(content, filename=str(filepath))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for i, stmt in enumerate(node.body):
                        if isinstance(stmt, ast.Return) and i < len(node.body) - 1:
                            print(f"[SEMANTIC WARNING] Codigo inalcancavel apos 'return' em {filepath.name} (Linha {stmt.lineno})")
                            # Não falha o build, mas alerta o engenheiro
            
        except SyntaxError as e:
            print(f"[AST ERROR] Erro Estrutural em {filepath.name} (Linha {e.lineno}): {e.msg}")
            has_errors = True
        except Exception as e:
            print(f"[ERROR] Falha critica ao analisar {filepath.name}: {str(e)}")
            has_errors = True
            
    return not has_errors

if __name__ == "__main__":
    if "KIPPE_ROOT" not in os.environ:
        sys.exit(1)
        
    root = Path(os.environ["KIPPE_ROOT"])
    print("  -> Executando KIPPE Semantic Repository Gate...")
    
    is_valid = run_semantic_checks(root / "src") and run_semantic_checks(root / "tests")
    
    if not is_valid:
        print("  -> Semantic Gate: REPROVADO. Corrija as anomalias detectadas.")
        sys.exit(1)
    sys.exit(0)
KIPPE_HUNK

kippe::step 3 ${TOTAL_STEPS} "Executing Upgraded Preflight Pipeline..."
source "${KIPPE_ROOT}/install/lib/bootstrap.sh"
kippe::validate_script_syntax "${BASH_SOURCE[0]}"

kippe::step 4 ${TOTAL_STEPS} "Running Complete Testing Regression Matrix..."
kippe::test_execute_all

kippe::step 5 ${TOTAL_STEPS} "Sealing Governance Pipeline (Completing INF005)..."
# Limpeza
rm -f "${KIPPE_ROOT}"/install/sprints/hotfix_*.py
rm -f data/test_*.db data/test_*.log data/test_*.db-journal 2>/dev/null || true

kippe::checkpoint_create "043" "1.2.0-gov" "INF005.1" "SUCCESS"
kippe::manifest_create "INF005.1" "INF" "1.2.0-gov" "SUCCESS" "INV010"

kippe::governance_sync \
    "C" \
    "Inventory" \
    "2" \
    "Profissional" \
    "INF005.1 (Semantic Hotfix)" \
    "INV009 — Stock Transfers" \
    "9/20" \
    "49" \
    "0" \
    "STABLE"

exit 0

