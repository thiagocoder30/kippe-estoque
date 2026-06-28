import os
import sys
import ast
import re
from pathlib import Path

def run_semantic_checks(root_dir: Path) -> bool:
    has_errors = False
    
    bash_leak_pattern = re.compile(r'\$\{[a-zA-Z_][a-zA-Z0-9_]*.*?\}')
    subshell_leak_pattern = re.compile(r'\$\(pwd\)|\$\(git rev-parse')
    invalid_as_pattern = re.compile(r'\[.*? as .*? for .*? in .*?\]')
    
    for filepath in root_dir.rglob("*.py"):
        if "venv" in filepath.parts or "__pycache__" in filepath.parts:
            continue
            
        try:
            content = filepath.read_text(encoding="utf-8")
            
            leaks = bash_leak_pattern.findall(content)
            if leaks:
                print(f"[SEMANTIC FATAL] Vazamento de template Bash detectado em {filepath.name}: {set(leaks)}")
                has_errors = True
                
            subshells = subshell_leak_pattern.findall(content)
            if subshells:
                print(f"[SEMANTIC FATAL] Resolução dinamica crua de terminal vazada para o Python em {filepath.name}: {set(subshells)}")
                has_errors = True
                
            invalid_comps = invalid_as_pattern.findall(content)
            if invalid_comps:
                print(f"[SEMANTIC FATAL] Uso invalido da keyword 'as' em compreensao de lista no {filepath.name}: {invalid_comps}")
                has_errors = True
                
            if 'sqlite_repository.py' in filepath.name:
                if 'row.get(' in content or 'b.get(' in content:
                    print(f"[SEMANTIC FATAL] Incompatibilidade API detectada. 'sqlite3.Row' nao suporta .get() em: {filepath.name}")
                    has_errors = True
            
        except SyntaxError as e:
            print(f"[AST ERROR] Erro Estrutural em {filepath.name} (Linha {e.lineno}): {e.msg}")
            has_errors = True
            
    return not has_errors

if __name__ == "__main__":
    if "KIPPE_ROOT" not in os.environ:
        sys.exit(1)
        
    root = Path(os.environ["KIPPE_ROOT"])
    print("  -> Executando KIPPE Semantic Repository Gate...")
    
    is_valid = run_semantic_checks(root / "src") and run_semantic_checks(root / "tests")
    if not is_valid:
        print("  -> Semantic Gate: REPROVADO.")
        sys.exit(1)
    sys.exit(0)
