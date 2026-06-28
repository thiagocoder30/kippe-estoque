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
                
            
            row_get_pattern = re.compile(r'row\.get\(')
            b_get_pattern = re.compile(r'b\.get\(')
            
            # Bloqueia chamadas .get() diretas se a var parecer ser sqlite3.Row em contextos de repositório
            if 'sqlite_repository.py' in filepath.name:
                row_gets = row_get_pattern.findall(content)
                b_gets = b_get_pattern.findall(content)
                if row_gets or b_gets:
                    print(f"[SEMANTIC FATAL] Incompatibilidade API detectada. 'sqlite3.Row' nao suporta .get(). Converta para dict() antes em: {filepath.name}")
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
