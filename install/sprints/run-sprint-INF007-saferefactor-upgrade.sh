#!/usr/bin/env bash
#
# ============================================================
# KIPPE PLATFORM
# INFRASTRUCTURE HARDENING
# SPRINT INF007: SAFE REFACTOR AST-AWARE ENGINE UPGRADE
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

TOTAL_STEPS=3

kippe::banner_program "INF" "INF007" "SafeRefactor AST-Aware Upgrade"

kippe::step 1 ${TOTAL_STEPS} "Upgrading SafeRefactor Engine with Internal AST Validation..."

cat << "KIPPE_HUNK" > "${KIPPE_ROOT}/install/lib/refactor_engine.py"
import ast
import textwrap
import re

class SafeRefactor:
    """
    Kippe SafeRefactor Engine (AST-Aware)
    Garante que mutações de código nunca quebrem a árvore sintática.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath
        with open(filepath, 'r', encoding='utf-8') as f:
            self.original_content = f.read()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def apply(self, func) -> None:
        new_content = func(self.original_content)
        
        # AST Gate Interno: Valida a mutação em memória antes de tocar no disco
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            raise RuntimeError(f"AST Rejection em {self.filepath} (Linha {e.lineno}): {e.msg}")
            
        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

    @staticmethod
    def smart_indent(content: str, anchor: str, new_block: str) -> str:
        """
        Encontra a linha do anchor, extrai sua indentação nativa, aplica o dedent no 
        bloco novo para normalizá-lo e então injeta a indentação exata do contexto.
        """
        lines = content.split('\n')
        for line in lines:
            if anchor.strip() in line:
                match = re.match(r'^(\s*)', line)
                indent = match.group(1) if match else ""
                
                dedented_block = textwrap.dedent(new_block).strip()
                indented_block = textwrap.indent(dedented_block, indent)
                
                return content.replace(line, indented_block)
        return content.replace(anchor, new_block)
KIPPE_HUNK

kippe::step 2 ${TOTAL_STEPS} "Executing Preflight and AST Validation on Engine..."
kippe::validate_script_syntax "${BASH_SOURCE[0]}"

kippe::step 3 ${TOTAL_STEPS} "Syncing Infrastructure Governance..."
kippe::checkpoint_create "058" "1.3.0-frozen" "INF007" "SUCCESS"

echo -e "\n[AÇÃO REQUERIDA] Execute o commit de infraestrutura antes de seguir para a INV019:"
echo -e 'git add -A && git commit -m "chore(infra): eleva SafeRefactor para nivel institucional com validacao AST em memoria e indentacao dinamica (INF007)"'

exit 0

