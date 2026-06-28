import os
import sys
import re
sys.path.insert(0, os.environ["KIPPE_ROOT"])
from install.lib.refactor_engine import SafeRefactor
def patch_repo_strict_mapping(content: str) -> str:
    # Assegura que o mapeamento SQLite -> Domain (Leitura) é explícito e tipado
    pattern_read = re.compile(r'batches_dict\[b_dict\[\'batch_code\'\]\] = Batch\(.*?cost_per_unit=.*?\)', re.DOTALL)
    strict_read = '''batches_dict[b_dict['batch_code']] = Batch(
                        code=str(b_dict['batch_code']), 
                        product_id=str(b_dict['product_id']), 
                        quantity=int(b_dict['quantity']),
                        expiration_date=str(b_dict['expiration_date']), 
                        warehouse_id=str(b_dict.get('warehouse_id', 'WH-PADRAO')),
                        location_id=str(b_dict.get('location_id', '')), 
                        manufacturing_date=str(b_dict.get('manufacturing_date', '')),
                        supplier=str(b_dict.get('supplier', 'PADRAO')), 
                        status=str(b_dict.get('status', 'ATIVO')), 
                        traceability_id=str(b_dict.get('traceability_id', '')),
                        cost_per_unit=float(b_dict.get('cost_per_unit', 0.0))
                    )'''
    content = pattern_read.sub(strict_read, content)
    
    # Assegura o mapeamento em get_by_id (Duplicidade histórica do repo)
    pattern_read_id = re.compile(r'batches_dict\[r_dict\[\'batch_code\'\]\] = Batch\(.*?cost_per_unit=.*?\)', re.DOTALL)
    strict_read_id = '''batches_dict[r_dict['batch_code']] = Batch(
                    code=str(r_dict['batch_code']), 
                    product_id=str(r_dict['product_id']), 
                    quantity=int(r_dict['quantity']),
                    expiration_date=str(r_dict['expiration_date']), 
                    warehouse_id=str(r_dict.get('warehouse_id', 'WH-PADRAO')),
                    location_id=str(r_dict.get('location_id', '')), 
                    manufacturing_date=str(r_dict.get('manufacturing_date', '')),
                    supplier=str(r_dict.get('supplier', 'PADRAO')), 
                    status=str(r_dict.get('status', 'ATIVO')), 
                    traceability_id=str(r_dict.get('traceability_id', '')),
                    cost_per_unit=float(r_dict.get('cost_per_unit', 0.0))
                )'''
    content = pattern_read_id.sub(strict_read_id, content)
    # Assegura que o mapeamento Domain -> SQLite (Escrita) é explícito e tipado
    pattern_write = re.compile(r'VALUES \(\?, \?, \?, \?, \?, \?, \?, \?, \?, \?, \?\).*?\)', re.DOTALL)
    strict_write = '''VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(product.id), str(batch.code), str(batch.expiration_date), int(batch.quantity), 
                    str(batch.manufacturing_date), str(batch.supplier), str(batch.status), 
                    str(batch.traceability_id), str(batch.location_id), str(batch.warehouse_id), 
                    float(batch.cost_per_unit)
                ))'''
    
    if "float(batch.cost_per_unit)" not in content:
        content = pattern_write.sub(strict_write, content)
    return content
try:
    with SafeRefactor("src/interfaces/sqlite_repository.py") as sr:
        sr.apply(patch_repo_strict_mapping)
except Exception as e:
    sys.exit(1)
