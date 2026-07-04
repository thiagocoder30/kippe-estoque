from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PatchResult:
    file: str
    changed: bool
    action: str


class PatchEngine:
    """
    RL.SYS CORE - Patch Engine Institucional

    Responsabilidade:
    - mutação segura de arquivos de código
    - operações idempotentes
    - prevenção de duplicação de imports
    - estabilidade para execução de Sprints
    """

    @staticmethod
    def read(file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def write(file_path: str, content: str) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def ensure_import(file_path: str, import_line: str) -> PatchResult:
        content = PatchEngine.read(file_path)

        if import_line.strip() in content:
            return PatchResult(
                file=file_path,
                changed=False,
                action="IMPORT_ALREADY_EXISTS"
            )

        # garante import no topo respeitando shebang/docstring
        lines = content.splitlines()

        insert_index = 0

        # preserva shebang
        if lines and lines[0].startswith("#!"):
            insert_index = 1

        # preserva docstring inicial
        if len(lines) > insert_index and lines[insert_index].startswith('"""'):
            insert_index += 1
            while insert_index < len(lines) and '"""' not in lines[insert_index]:
                insert_index += 1
            insert_index += 1

        new_lines = (
            lines[:insert_index]
            + [import_line]
            + [""] 
            + lines[insert_index:]
        )

        PatchEngine.write(file_path, "\n".join(new_lines))

        return PatchResult(
            file=file_path,
            changed=True,
            action="IMPORT_INSERTED"
        )

    @staticmethod
    def replace_text(file_path: str, old: str, new: str) -> PatchResult:
        content = PatchEngine.read(file_path)

        if old not in content:
            return PatchResult(
                file=file_path,
                changed=False,
                action="TEXT_NOT_FOUND"
            )

        new_content = content.replace(old, new)

        PatchEngine.write(file_path, new_content)

        return PatchResult(
            file=file_path,
            changed=True,
            action="TEXT_REPLACED"
        )

    @staticmethod
    def safe_append(file_path: str, block: str) -> PatchResult:
        content = PatchEngine.read(file_path)

        if block.strip() in content:
            return PatchResult(
                file=file_path,
                changed=False,
                action="BLOCK_ALREADY_EXISTS"
            )

        new_content = content.rstrip() + "\n\n" + block + "\n"

        PatchEngine.write(file_path, new_content)

        return PatchResult(
            file=file_path,
            changed=True,
            action="BLOCK_APPENDED"
        )
