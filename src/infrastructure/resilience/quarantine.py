import os
import shutil
from datetime import datetime

class QuarantineEngine:
    """
    Mecanismo de Isolamento de Arquivos (Quarentena).
    Move payloads estruturalmente corrompidos para preservação de evidências sem travar o runtime.
    """
    @staticmethod
    def isolate(file_path: str, quarantine_dir: str = "data/quarantine") -> str:
        if not os.path.exists(file_path):
            return ""
        os.makedirs(quarantine_dir, exist_ok=True)
        
        base_name = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = os.path.join(quarantine_dir, f"{timestamp}_{base_name}")
        
        try:
            shutil.move(file_path, dest_path)
            return dest_path
        except OSError:
            return ""
