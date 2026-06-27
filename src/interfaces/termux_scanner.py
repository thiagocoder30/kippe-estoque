import subprocess
from src.interfaces.barcode_scanner import BarcodeScanner
from src.domain.result import Result

class TermuxBarcodeScanner:
    """
    Adapter para o aplicativo Android Termux:API.
    Chama a câmera nativamente com timeout de 30 segundos.
    """
    def scan(self) -> Result[str, str]:
        try:
            # Invoca o binário do Termux API para leitura de código
            result = subprocess.run(
                ["termux-barcode-scanner"], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            output = result.stdout.strip()
            
            if result.returncode == 0 and output:
                return Result.ok(output)
            return Result.fail("Operação cancelada ou falha na leitura da câmera.")
            
        except FileNotFoundError:
            return Result.fail("Pacote 'termux-api' não encontrado no sistema.")
        except subprocess.TimeoutExpired:
            return Result.fail("Tempo limite de leitura (30s) excedido.")
        except Exception as e:
            return Result.fail(f"Erro inesperado no hardware: {str(e)}")
