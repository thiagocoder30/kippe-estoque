import os
import sys
import re
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor

def patch_batch_test_wording(content: str) -> str:
    # Substitui a expectativa antiga pela nova mensagem canônica
    content = re.sub(
        r'match\s*=\s*["\']atrelado a um SKU["\']', 
        'match="O product_id é obrigatório"', 
        content
    )
    content = re.sub(
        r'match\s*=\s*["\'].*?não pode ser negativa.*?["\']',
        'match="Lotes físicos não podem ser negativos."',
        content
    )
    return content

try:
    with SafeRefactor("tests/test_batch_entity.py") as sr:
        sr.apply(patch_batch_test_wording)
except Exception as e:
    # Ignora graciosamente se já tiver sido aplicado ou ocorrer I/O error transitório
    pass
