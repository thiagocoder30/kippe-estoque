import os
import sys
import shutil
import py_compile
from pathlib import Path
from typing import Callable
class SafeRefactor:
    """
    KIPPE PLATFORM - NATIVE REFACTORING ENGINE
    Garante mutações determinísticas em código-fonte com Rollback automático
    e validação nativa de Abstract Syntax Tree (AST).
    """
    def __init__(self, filepath: str | Path):
        if "KIPPE_ROOT" not in os.environ:
            raise EnvironmentError("Variável KIPPE_ROOT não encontrada no ambiente.")
            
        self.root = Path(os.environ["KIPPE_ROOT"])
        self.target_path = self.root / filepath
        self.backup_path = self.target_path.with_suffix('.py.bak')
        
        if not self.target_path.exists():
            raise FileNotFoundError(f"Arquivo alvo não encontrado: {self.target_path}")
    def __enter__(self):
        # 1. Snapshot de Segurança
        shutil.copy2(self.target_path, self.backup_path)
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback(f"Exceção durante refatoração: {exc_val}")
            return False
        # 2. Validação AST pós-mutação
        try:
            py_compile.compile(str(self.target_path), doraise=True)
            # 3. Limpeza do Snapshot em caso de sucesso
            if self.backup_path.exists():
                self.backup_path.unlink()
        except py_compile.PyCompileError as e:
            self.rollback(f"Falha no AST Compiler Gate. Código quebrado detectado:\n{e}")
            sys.exit(1)
    def rollback(self, reason: str):
        print(f"\n[CRITICAL] {reason}")
        if self.backup_path.exists():
            shutil.copy2(self.backup_path, self.target_path)
            self.backup_path.unlink()
            print(f"[ROLLBACK] Arquivo {self.target_path.name} restaurado para o estado original seguro.")
    def apply(self, mutator: Callable[[str], str]) -> None:
        """Aplica a função mutadora ao conteúdo do arquivo."""
        content = self.target_path.read_text(encoding="utf-8")
        new_content = mutator(content)
        
        if content != new_content:
            self.target_path.write_text(new_content, encoding="utf-8")
            print(f"  -> Mutação aplicada com sucesso em: {self.target_path.name}")
        else:
            print(f"  -> Nenhuma alteração necessária em: {self.target_path.name}")
