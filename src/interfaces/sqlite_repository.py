import json
import sqlite3
from typing import Any, Dict, List, Optional

from src.domain.batch import Batch
from src.domain.category import Category
from src.domain.product import Product


class SQLiteProductRepository:
    PRODUCT_SKU_SEQUENCE = "product"

    DEFAULT_CATEGORIES = (
        (
            "MER",
            "Mercearia",
            10,
        ),
        (
            "BEB",
            "Bebidas",
            20,
        ),
        (
            "LAT",
            "Laticínios e Refrigerados",
            30,
        ),
        (
            "CAR",
            "Carnes e Açougue",
            40,
        ),
        (
            "FRI",
            "Frios e Embutidos",
            50,
        ),
        (
            "HOR",
            "Hortifruti",
            60,
        ),
        (
            "PAD",
            "Padaria e Confeitaria",
            70,
        ),
        (
            "CON",
            "Congelados",
            80,
        ),
        (
            "HIG",
            "Higiene Pessoal",
            90,
        ),
        (
            "LIM",
            "Limpeza",
            100,
        ),
        (
            "BAZ",
            "Bazar e Utilidades",
            110,
        ),
        (
            "PET",
            "Pet",
            120,
        ),
        (
            "INF",
            "Infantil",
            130,
        ),
        (
            "COS",
            "Perfumaria e Cosméticos",
            140,
        ),
        (
            "DES",
            "Descartáveis e Embalagens",
            150,
        ),
        (
            "OUT",
            "Outros",
            160,
        ),
    )

    def __init__(
        self,
        db_path: str = "data/estoque_producao.db",
    ):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path
        )
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    parent_id TEXT,
                    active INTEGER DEFAULT 1,
                    sort_order INTEGER DEFAULT 0,
                    classification_rules TEXT DEFAULT '{}',
                    FOREIGN KEY(parent_id) REFERENCES categories(id)
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS warehouses (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    address TEXT,
                    is_active INTEGER DEFAULT 1
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS locations (
                    id TEXT PRIMARY KEY,
                    warehouse TEXT NOT NULL,
                    zone TEXT NOT NULL,
                    aisle TEXT NOT NULL,
                    rack TEXT NOT NULL,
                    shelf TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    ean TEXT NOT NULL DEFAULT '',
                    quantity INTEGER NOT NULL,
                    unit_of_measure TEXT NOT NULL DEFAULT 'un',
                    status TEXT NOT NULL DEFAULT 'ATIVO',
                    category_id TEXT,
                    reserved_quantity INTEGER NOT NULL DEFAULT 0,
                    allow_negative_stock INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    operator_id TEXT NOT NULL DEFAULT 'SYSTEM'
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS operational_audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    batch_code TEXT DEFAULT '',
                    location_id TEXT DEFAULT '',
                    quantity_planned INTEGER,
                    quantity_actual INTEGER,
                    quantity_before INTEGER,
                    quantity_after INTEGER,
                    quantity_divergence INTEGER,
                    supplier TEXT DEFAULT '',
                    document_id TEXT DEFAULT '',
                    origin_document TEXT DEFAULT '',
                    operator_id TEXT NOT NULL,
                    occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS batches (
                    product_id TEXT NOT NULL,
                    batch_code TEXT NOT NULL,
                    expiration_date TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    manufacturing_date TEXT DEFAULT '',
                    supplier TEXT DEFAULT 'PADRAO',
                    status TEXT DEFAULT 'ATIVO',
                    traceability_id TEXT DEFAULT '',
                    location_id TEXT DEFAULT '',
                    warehouse_id TEXT DEFAULT 'WH-PADRAO',
                    cost_per_unit REAL NOT NULL DEFAULT 0.0,
                    PRIMARY KEY (product_id, batch_code)
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reservations (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    operator_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sku_sequences (
                    name TEXT PRIMARY KEY,
                    next_value INTEGER NOT NULL
                        CHECK(next_value > 0)
                )
                """
            )

            # Migrações retroativas.
            cursor = conn.execute(
                "PRAGMA table_info(products)"
            )

            product_columns = [
                info["name"]
                for info in cursor.fetchall()
            ]

            if "ean" not in product_columns:
                conn.execute(
                    """
                    ALTER TABLE products
                    ADD COLUMN ean TEXT NOT NULL DEFAULT ''
                    """
                )

            if (
                "allow_negative_stock"
                not in product_columns
            ):
                conn.execute(
                    """
                    ALTER TABLE products
                    ADD COLUMN allow_negative_stock
                    INTEGER NOT NULL DEFAULT 0
                    """
                )

            cursor = conn.execute(
                "PRAGMA table_info(batches)"
            )

            batch_columns = [
                info["name"]
                for info in cursor.fetchall()
            ]

            if (
                "cost_per_unit"
                not in batch_columns
            ):
                conn.execute(
                    """
                    ALTER TABLE batches
                    ADD COLUMN cost_per_unit
                    REAL NOT NULL DEFAULT 0.0
                    """
                )

            self._insert_default_categories(
                conn
            )

            self._ensure_product_sku_sequence(
                conn
            )

            conn.commit()

    def _insert_default_categories(
        self,
        conn: sqlite3.Connection,
    ) -> None:
        """
        Insere somente categorias canônicas ausentes.

        Categorias já existentes nunca são atualizadas pelo
        bootstrap. Isso preserva customizações operacionais,
        status, ordenação, descrições e regras locais.
        """
        rows = [
            (
                category_id,
                name,
                "",
                None,
                1,
                sort_order,
                "{}",
            )
            for (
                category_id,
                name,
                sort_order,
            )
            in self.DEFAULT_CATEGORIES
        ]

        conn.executemany(
            """
            INSERT OR IGNORE INTO categories (
                id,
                name,
                description,
                parent_id,
                active,
                sort_order,
                classification_rules
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def ensure_default_categories(
        self,
    ) -> None:
        """
        Garante idempotentemente o catálogo mercantil mínimo.

        A operação é insert-only: registros previamente
        existentes permanecem integralmente sob controle da
        operação.
        """
        with self._get_connection() as conn:
            self._insert_default_categories(
                conn
            )

            conn.commit()

    def _ensure_product_sku_sequence(
        self,
        conn: sqlite3.Connection,
    ) -> None:
        existing = conn.execute(
            """
            SELECT next_value
            FROM sku_sequences
            WHERE name = ?
            """,
            (
                self.PRODUCT_SKU_SEQUENCE,
            ),
        ).fetchone()

        if existing:
            return

        # Somente SKUs canônicos "SKU" + seis dígitos
        # participam da sequência automática.
        row = conn.execute(
            """
            SELECT MAX(
                CAST(
                    SUBSTR(id, 4)
                    AS INTEGER
                )
            ) AS max_generated
            FROM products
            WHERE id GLOB
                'SKU[0-9][0-9][0-9][0-9][0-9][0-9]'
            """
        ).fetchone()

        max_generated = (
            int(row["max_generated"])
            if (
                row
                and row["max_generated"]
                is not None
            )
            else 0
        )

        next_value = (
            max_generated + 1
        )

        conn.execute(
            """
            INSERT INTO sku_sequences (
                name,
                next_value
            )
            VALUES (?, ?)
            """,
            (
                self.PRODUCT_SKU_SEQUENCE,
                next_value,
            ),
        )

    def save_category(
        self,
        category: Category,
    ) -> None:
        with self._get_connection() as conn:
            rules_json = json.dumps(
                category.classification_rules
            )

            conn.execute(
                """
                INSERT INTO categories (
                    id,
                    name,
                    description,
                    parent_id,
                    active,
                    sort_order,
                    classification_rules
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    parent_id=excluded.parent_id,
                    active=excluded.active,
                    sort_order=excluded.sort_order,
                    classification_rules=
                        excluded.classification_rules
                """,
                (
                    category.id,
                    category.name,
                    category.description,
                    category.parent_id,
                    int(category.active),
                    category.sort_order,
                    rules_json,
                ),
            )

            conn.commit()

    def get_category_by_id(
        self,
        category_id: str,
    ) -> Optional[Category]:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM categories
                WHERE id = ?
                """,
                (
                    category_id,
                ),
            ).fetchone()

            if not row:
                return None

            return Category(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                parent_id=row["parent_id"],
                active=bool(
                    row["active"]
                ),
                sort_order=row["sort_order"],
                classification_rules=json.loads(
                    row["classification_rules"]
                ),
            )

    def get_all_categories(
        self,
    ) -> List[Category]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM categories
                ORDER BY sort_order, name
                """
            ).fetchall()

            return [
                Category(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    parent_id=row["parent_id"],
                    active=bool(
                        row["active"]
                    ),
                    sort_order=row["sort_order"],
                    classification_rules=json.loads(
                        row[
                            "classification_rules"
                        ]
                    ),
                )
                for row in rows
            ]

    def get_by_ean(
        self,
        ean: str,
    ) -> Optional[Product]:
        normalized_ean = str(
            ean or ""
        ).strip()

        if not normalized_ean:
            return None

        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM products
                WHERE ean = ?
                LIMIT 1
                """,
                (
                    normalized_ean,
                ),
            ).fetchone()

        if not row:
            return None

        return self.get_by_id(
            row["id"]
        )

    def register_new_product(
        self,
        name: str,
        ean: str,
        unit_of_measure: str = "un",
        status: str = "ATIVO",
        category_id: str = None,
    ) -> Product:
        normalized_name = str(
            name or ""
        ).strip()

        normalized_ean = str(
            ean or ""
        ).strip()

        normalized_unit = str(
            unit_of_measure or "un"
        ).strip().lower()

        normalized_status = str(
            status or "ATIVO"
        ).strip().upper()

        normalized_category = (
            str(category_id).strip()
            if category_id
            else None
        )

        if not normalized_ean:
            raise ValueError(
                "O EAN é obrigatório para o cadastro operacional."
            )

        with self._get_connection() as conn:
            # Serializa cadastros concorrentes enquanto o próximo
            # identificador é resolvido e persistido.
            conn.execute(
                "BEGIN IMMEDIATE"
            )

            duplicate = conn.execute(
                """
                SELECT id, name
                FROM products
                WHERE ean = ?
                LIMIT 1
                """,
                (
                    normalized_ean,
                ),
            ).fetchone()

            if duplicate:
                raise ValueError(
                    "EAN já cadastrado no produto "
                    f"[{duplicate['id']}] "
                    f"{duplicate['name']}."
                )

            sequence_row = conn.execute(
                """
                SELECT next_value
                FROM sku_sequences
                WHERE name = ?
                """,
                (
                    self.PRODUCT_SKU_SEQUENCE,
                ),
            ).fetchone()

            if not sequence_row:
                self._ensure_product_sku_sequence(
                    conn
                )

                sequence_row = conn.execute(
                    """
                    SELECT next_value
                    FROM sku_sequences
                    WHERE name = ?
                    """,
                    (
                        self.PRODUCT_SKU_SEQUENCE,
                    ),
                ).fetchone()

            candidate_number = int(
                sequence_row["next_value"]
            )

            while True:
                candidate_sku = (
                    f"SKU{candidate_number:06d}"
                )

                collision = conn.execute(
                    """
                    SELECT 1
                    FROM products
                    WHERE id = ?
                    LIMIT 1
                    """,
                    (
                        candidate_sku,
                    ),
                ).fetchone()

                if not collision:
                    break

                candidate_number += 1

            # Valida todas as invariantes do domínio antes
            # de consumir definitivamente a sequência.
            product = Product(
                id=candidate_sku,
                name=normalized_name,
                ean=normalized_ean,
                quantity=0,
                unit_of_measure=normalized_unit,
                status=normalized_status,
                category_id=normalized_category,
            )

            conn.execute(
                """
                INSERT INTO products (
                    id,
                    name,
                    ean,
                    quantity,
                    unit_of_measure,
                    status,
                    category_id,
                    reserved_quantity,
                    allow_negative_stock
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product.id,
                    product.name,
                    product.ean,
                    product.quantity,
                    product.unit_of_measure,
                    product.status,
                    product.category_id,
                    product.reserved_quantity,
                    int(
                        product.allow_negative_stock
                    ),
                ),
            )

            conn.execute(
                """
                UPDATE sku_sequences
                SET next_value = ?
                WHERE name = ?
                """,
                (
                    candidate_number + 1,
                    self.PRODUCT_SKU_SEQUENCE,
                ),
            )

            return product

    def _save_product_on_connection(
        self,
        conn: sqlite3.Connection,
        product: Product,
    ) -> None:
        conn.execute(
            """
            INSERT INTO products (
                id,
                name,
                ean,
                quantity,
                unit_of_measure,
                status,
                category_id,
                reserved_quantity,
                allow_negative_stock
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                ean=excluded.ean,
                quantity=excluded.quantity,
                unit_of_measure=excluded.unit_of_measure,
                status=excluded.status,
                category_id=excluded.category_id,
                reserved_quantity=
                    excluded.reserved_quantity,
                allow_negative_stock=
                    excluded.allow_negative_stock
            """,
            (
                product.id,
                product.name,
                product.ean,
                product.quantity,
                product.unit_of_measure,
                product.status,
                product.category_id,
                product.reserved_quantity,
                int(
                    product.allow_negative_stock
                ),
            ),
        )

        conn.execute(
            """
            DELETE FROM batches
            WHERE product_id = ?
            """,
            (
                product.id,
            ),
        )

        for batch in product.batches.values():
            conn.execute(
                """
                INSERT INTO batches (
                    product_id,
                    batch_code,
                    expiration_date,
                    quantity,
                    manufacturing_date,
                    supplier,
                    status,
                    traceability_id,
                    location_id,
                    warehouse_id,
                    cost_per_unit
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product.id,
                    batch.code,
                    batch.expiration_date,
                    batch.quantity,
                    batch.manufacturing_date,
                    batch.supplier,
                    batch.status,
                    batch.traceability_id,
                    batch.location_id,
                    batch.warehouse_id,
                    float(
                        getattr(
                            batch,
                            "cost_per_unit",
                            0.0,
                        )
                    ),
                ),
            )

    def save(
        self,
        product: Product,
    ) -> None:
        with self._get_connection() as conn:
            self._save_product_on_connection(
                conn,
                product,
            )

            conn.commit()

    def get_by_id(
        self,
        product_id: str,
    ) -> Optional[Product]:
        with self._get_connection() as conn:
            prod_row = conn.execute(
                """
                SELECT *
                FROM products
                WHERE id = ?
                """,
                (
                    product_id,
                ),
            ).fetchone()

            if not prod_row:
                return None

            batch_rows = conn.execute(
                """
                SELECT *
                FROM batches
                WHERE product_id = ?
                """,
                (
                    product_id,
                ),
            ).fetchall()

            batches_dict = {}

            for row in batch_rows:
                row_data = dict(
                    row
                )

                batches_dict[
                    row_data["batch_code"]
                ] = Batch(
                    code=row_data[
                        "batch_code"
                    ],
                    product_id=row_data[
                        "product_id"
                    ],
                    quantity=row_data[
                        "quantity"
                    ],
                    expiration_date=row_data[
                        "expiration_date"
                    ],
                    warehouse_id=row_data.get(
                        "warehouse_id",
                        "WH-PADRAO",
                    ),
                    location_id=row_data.get(
                        "location_id",
                        "",
                    ),
                    manufacturing_date=row_data[
                        "manufacturing_date"
                    ],
                    supplier=row_data[
                        "supplier"
                    ],
                    status=row_data[
                        "status"
                    ],
                    traceability_id=row_data[
                        "traceability_id"
                    ],
                    cost_per_unit=float(
                        row_data.get(
                            "cost_per_unit",
                            0.0,
                        )
                    ),
                )

            product = Product(
                id=prod_row["id"],
                name=prod_row["name"],
                ean=dict(
                    prod_row
                ).get(
                    "ean",
                    "",
                ),
                quantity=prod_row[
                    "quantity"
                ],
                batches=batches_dict,
                unit_of_measure=prod_row[
                    "unit_of_measure"
                ],
                status=prod_row[
                    "status"
                ],
                category_id=prod_row[
                    "category_id"
                ],
                allow_negative_stock=bool(
                    dict(
                        prod_row
                    ).get(
                        "allow_negative_stock",
                        0,
                    )
                ),
            )

            product.reserved_quantity = (
                prod_row[
                    "reserved_quantity"
                ]
            )

            return product

    def get_all(
        self,
    ) -> List[Product]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM products
                ORDER BY name
                """
            ).fetchall()

            products = []

            for row in rows:
                batch_rows = conn.execute(
                    """
                    SELECT *
                    FROM batches
                    WHERE product_id = ?
                    ORDER BY expiration_date
                    """,
                    (
                        row["id"],
                    ),
                ).fetchall()

                batches_dict = {}

                for batch_row in batch_rows:
                    batch_data = dict(
                        batch_row
                    )

                    batches_dict[
                        batch_data[
                            "batch_code"
                        ]
                    ] = Batch(
                        code=batch_data[
                            "batch_code"
                        ],
                        product_id=batch_data[
                            "product_id"
                        ],
                        quantity=batch_data[
                            "quantity"
                        ],
                        expiration_date=batch_data[
                            "expiration_date"
                        ],
                        warehouse_id=batch_data.get(
                            "warehouse_id",
                            "WH-PADRAO",
                        ),
                        location_id=batch_data.get(
                            "location_id",
                            "",
                        ),
                        manufacturing_date=batch_data[
                            "manufacturing_date"
                        ],
                        supplier=batch_data[
                            "supplier"
                        ],
                        status=batch_data[
                            "status"
                        ],
                        traceability_id=batch_data[
                            "traceability_id"
                        ],
                        cost_per_unit=float(
                            batch_data.get(
                                "cost_per_unit",
                                0.0,
                            )
                        ),
                    )

                product = Product(
                    id=row["id"],
                    name=row["name"],
                    ean=dict(
                        row
                    ).get(
                        "ean",
                        "",
                    ),
                    quantity=row[
                        "quantity"
                    ],
                    batches=batches_dict,
                    unit_of_measure=row[
                        "unit_of_measure"
                    ],
                    status=row[
                        "status"
                    ],
                    category_id=row[
                        "category_id"
                    ],
                    allow_negative_stock=bool(
                        dict(
                            row
                        ).get(
                            "allow_negative_stock",
                            0,
                        )
                    ),
                )

                product.reserved_quantity = (
                    row[
                        "reserved_quantity"
                    ]
                )

                products.append(
                    product
                )

            return products

    def log_transaction(
        self,
        product_id: str,
        trans_type: str,
        amount: int,
        operator_id: str,
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO transactions (
                    product_id,
                    type,
                    amount,
                    operator_id
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    product_id,
                    trans_type,
                    amount,
                    operator_id,
                ),
            )

            conn.commit()

    def _append_operational_audit_event_on_connection(
        self,
        conn: sqlite3.Connection,
        *,
        event_type: str,
        product_id: str,
        batch_code: str = "",
        location_id: str = "",
        quantity_planned: Optional[int] = None,
        quantity_actual: Optional[int] = None,
        quantity_before: Optional[int] = None,
        quantity_after: Optional[int] = None,
        quantity_divergence: Optional[int] = None,
        supplier: str = "",
        document_id: str = "",
        origin_document: str = "",
        operator_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        normalized_event_type = str(
            event_type or ""
        ).strip()

        normalized_product_id = str(
            product_id or ""
        ).strip()

        normalized_operator_id = str(
            operator_id or ""
        ).strip()

        if not normalized_event_type:
            raise ValueError(
                "event_type é obrigatório para auditoria operacional."
            )

        if not normalized_product_id:
            raise ValueError(
                "product_id é obrigatório para auditoria operacional."
            )

        if not normalized_operator_id:
            raise ValueError(
                "operator_id é obrigatório para auditoria operacional."
            )

        metadata_json = json.dumps(
            metadata or {},
            ensure_ascii=False,
            sort_keys=True,
        )

        cursor = conn.execute(
            """
            INSERT INTO operational_audit_events (
                event_type,
                product_id,
                batch_code,
                location_id,
                quantity_planned,
                quantity_actual,
                quantity_before,
                quantity_after,
                quantity_divergence,
                supplier,
                document_id,
                origin_document,
                operator_id,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_event_type,
                normalized_product_id,
                str(batch_code or "").strip(),
                str(location_id or "").strip(),
                quantity_planned,
                quantity_actual,
                quantity_before,
                quantity_after,
                quantity_divergence,
                str(supplier or "").strip(),
                str(document_id or "").strip(),
                str(origin_document or "").strip(),
                normalized_operator_id,
                metadata_json,
            ),
        )

        return int(
            cursor.lastrowid
        )

    def append_operational_audit_event(
        self,
        *,
        event_type: str,
        product_id: str,
        batch_code: str = "",
        location_id: str = "",
        quantity_planned: Optional[int] = None,
        quantity_actual: Optional[int] = None,
        quantity_before: Optional[int] = None,
        quantity_after: Optional[int] = None,
        quantity_divergence: Optional[int] = None,
        supplier: str = "",
        document_id: str = "",
        origin_document: str = "",
        operator_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Registra evidência documental sem alterar
        qualquer autoridade quantitativa.
        """

        with self._get_connection() as conn:
            event_id = (
                self._append_operational_audit_event_on_connection(
                    conn,
                    event_type=event_type,
                    product_id=product_id,
                    batch_code=batch_code,
                    location_id=location_id,
                    quantity_planned=quantity_planned,
                    quantity_actual=quantity_actual,
                    quantity_before=quantity_before,
                    quantity_after=quantity_after,
                    quantity_divergence=quantity_divergence,
                    supplier=supplier,
                    document_id=document_id,
                    origin_document=origin_document,
                    operator_id=operator_id,
                    metadata=metadata,
                )
            )

            conn.commit()

            return event_id

    def save_product_with_operational_audit(
        self,
        product: Product,
        *,
        event_type: str,
        product_id: str,
        batch_code: str = "",
        location_id: str = "",
        quantity_planned: Optional[int] = None,
        quantity_actual: Optional[int] = None,
        quantity_before: Optional[int] = None,
        quantity_after: Optional[int] = None,
        quantity_divergence: Optional[int] = None,
        supplier: str = "",
        document_id: str = "",
        origin_document: str = "",
        operator_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Persiste Product/Batch e sua evidência documental
        na mesma transação SQLite.

        Product/Batch continua sendo a autoridade quantitativa.
        O evento é somente evidência documental append-only.
        """

        with self._get_connection() as conn:
            try:
                conn.execute(
                    "BEGIN IMMEDIATE"
                )

                self._save_product_on_connection(
                    conn,
                    product,
                )

                event_id = (
                    self._append_operational_audit_event_on_connection(
                        conn,
                        event_type=event_type,
                        product_id=product_id,
                        batch_code=batch_code,
                        location_id=location_id,
                        quantity_planned=quantity_planned,
                        quantity_actual=quantity_actual,
                        quantity_before=quantity_before,
                        quantity_after=quantity_after,
                        quantity_divergence=quantity_divergence,
                        supplier=supplier,
                        document_id=document_id,
                        origin_document=origin_document,
                        operator_id=operator_id,
                        metadata=metadata,
                    )
                )

                conn.commit()

                return event_id

            except Exception:
                conn.rollback()
                raise

    def get_operational_audit_events_by_product(
        self,
        product_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Lê somente evidências documentais de um produto.

        A ordem é a ordem física de append do evento.
        Nenhum saldo é calculado a partir desta tabela.
        """

        normalized_product_id = str(
            product_id or ""
        ).strip()

        if not normalized_product_id:
            return []

        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    event_type,
                    product_id,
                    batch_code,
                    location_id,
                    quantity_planned,
                    quantity_actual,
                    quantity_before,
                    quantity_after,
                    quantity_divergence,
                    supplier,
                    document_id,
                    origin_document,
                    operator_id,
                    occurred_at,
                    metadata_json
                FROM operational_audit_events
                WHERE product_id = ?
                ORDER BY id ASC
                """,
                (
                    normalized_product_id,
                ),
            ).fetchall()

            return [
                dict(row)
                for row in rows
            ]

    def get_history(
        self,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    t.id,
                    t.type,
                    t.amount,
                    datetime(
                        t.timestamp,
                        'localtime'
                    ) AS data,
                    p.name,
                    t.operator_id
                FROM transactions t
                JOIN products p
                    ON t.product_id = p.id
                ORDER BY t.id DESC
                LIMIT ?
                """,
                (
                    limit,
                ),
            ).fetchall()

            return [
                dict(
                    row
                )
                for row in rows
            ]

    def get_dashboard_projection(
        self,
        sku_or_barcode: str,
    ) -> dict:
        try:
            conn = sqlite3.connect(
                "kippe.db"
            )

            conn.row_factory = (
                sqlite3.Row
            )

            cur = conn.cursor()

            cur.execute(
                """
                SELECT *
                FROM catalog
                WHERE sku = ?
                   OR barcode = ?
                """,
                (
                    sku_or_barcode,
                    sku_or_barcode,
                ),
            )

            catalog_row = (
                cur.fetchone()
            )

            if not catalog_row:
                conn.close()
                return None

            catalog_data = dict(
                catalog_row
            )

            true_sku = (
                catalog_data.get(
                    "sku",
                    sku_or_barcode,
                )
            )

            cur.execute(
                """
                SELECT *
                FROM batches
                WHERE sku = ?
                """,
                (
                    true_sku,
                ),
            )

            batches_rows = (
                cur.fetchall()
            )

            batches = []
            total_quantity = 0
            primary_supplier = "N/D"

            for row in batches_rows:
                batch_data = dict(
                    row
                )

                quantity = int(
                    batch_data.get(
                        "quantity"
                    )
                    or 0
                )

                store_quantity = int(
                    batch_data.get(
                        "quantity_store"
                    )
                    or 0
                )

                store_balance = int(
                    batch_data.get(
                        "store_balance"
                    )
                    or 0
                )

                batches.append(
                    {
                        "batch_code": (
                            batch_data.get(
                                "batch_code",
                                "N/D",
                            )
                        ),
                        "quantity": (
                            quantity
                        ),
                        "expiration_date": (
                            batch_data.get(
                                "expiration",
                                "N/D",
                            )
                        ),
                    }
                )

                total_quantity += (
                    quantity
                    + store_quantity
                    + store_balance
                )

                if (
                    batch_data.get(
                        "supplier"
                    )
                    and primary_supplier
                    == "N/D"
                ):
                    primary_supplier = (
                        batch_data.get(
                            "supplier"
                        )
                    )

            cur.execute(
                """
                SELECT *
                FROM audit_log
                WHERE sku = ?
                ORDER BY timestamp DESC
                LIMIT 10
                """,
                (
                    true_sku,
                ),
            )

            audit_rows = (
                cur.fetchall()
            )

            audit_logs = []

            for row in audit_rows:
                audit_data = dict(
                    row
                )

                audit_logs.append(
                    {
                        "date": (
                            audit_data.get(
                                "timestamp",
                                "",
                            )
                        ),
                        "op": (
                            audit_data.get(
                                "operation",
                                "",
                            )
                        ),
                        "qty": (
                            audit_data.get(
                                "quantity",
                                0,
                            )
                        ),
                        "operator": (
                            audit_data.get(
                                "operator",
                                "SISTEMA",
                            )
                        ),
                    }
                )

            conn.close()

            return {
                "sku": true_sku,
                "description": (
                    catalog_data.get(
                        "description",
                        "PRODUTO SEM NOME",
                    )
                ),
                "barcode": (
                    catalog_data.get(
                        "barcode",
                        true_sku,
                    )
                ),
                "category": (
                    catalog_data.get(
                        "category",
                        "N/D",
                    )
                ),
                "photo": (
                    catalog_data.get(
                        "photo",
                        None,
                    )
                ),
                "balances": {
                    "total": (
                        total_quantity
                    )
                },
                "primary_supplier": (
                    primary_supplier
                ),
                "physical_location": {
                    "details": (
                        catalog_data.get(
                            "box_location",
                            "NÃO ENDEREÇADO",
                        )
                    )
                },
                "traceability": {
                    "batches": batches
                },
                "audit_logs": (
                    audit_logs
                ),
            }

        except Exception as exc:
            print(
                "Erro no Read Model do "
                f"sku/ean {sku_or_barcode}: "
                f"{exc}"
            )

            return None
