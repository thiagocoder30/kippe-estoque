from typing import Dict, Any, Callable

class MigrationEngine:
    """
    Motor de Migração (Upcasting) para a Camada de Infraestrutura.
    Intercepta dados desserializados brutos e aplica transformações sequenciais.
    Implementa proteção DAG (Grafo Direcionado Acíclico) contra loops infinitos.
    """
    def __init__(self):
        self._upcasters: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register_upcaster(self, from_version: str, upcaster_func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._upcasters[from_version] = upcaster_func

    def migrate(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        current_version = raw_data.get("schema_version", "1.0")
        migrated_data = raw_data.copy()
        visited = set()
        
        while current_version in self._upcasters:
            # Proteção contra Estagnação de Estado e Ciclos (Infinite Loop)
            if current_version in visited:
                raise RuntimeError(f"Ciclo de migração detectado na versão {current_version}.")
            visited.add(current_version)
            
            upcaster = self._upcasters[current_version]
            migrated_data = upcaster(migrated_data)
            current_version = migrated_data.get("schema_version")
            
            if not current_version:
                raise RuntimeError("Falha no Upcaster: schema_version não atualizado na transformação.")
                
        return migrated_data
