from flask import Flask, jsonify, request, session, send_from_directory
from src.infrastructure.container import Container
from src.domain.services.expiration_analyzer import ExpirationAnalyzer

container = Container()
app = Flask(__name__)
app.secret_key = container.config.SECRET_KEY


def _has_valid_session():
    if (
        container.config.ENV == "testing"
        and "X-Test-Operator-Override" in request.headers
    ):
        return True

    return 'operator_id' in session


@app.route('/')
def index():
    return send_from_directory('web', 'index.html')


@app.route('/web/<path:filename>', methods=['GET'])
def web_assets(filename):
    return send_from_directory('web', filename)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'system': 'KIPPE WMS',
        'gateway': 'flask'
    }), 200


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}

    res = container.auth_use_case.authenticate(
        data.get('id'),
        data.get('pin')
    )

    if res.is_success:
        session['operator_id'] = res.value.id
        session['operator_name'] = res.value.name
        session['operator_role'] = res.value.role

        return jsonify({
            'message': 'OK',
            'operator': {
                'id': res.value.id,
                'name': res.value.name,
                'role': res.value.role
            }
        }), 200

    return jsonify({
        'error': res.error
    }), 401


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()

    return jsonify({
        'message': 'Sessão encerrada'
    }), 200


@app.route('/api/auth/me', methods=['GET'])
def me():
    if _has_valid_session():
        op_id = (
            request.headers.get(
                "X-Test-Operator-Override"
            )
            if (
                container.config.ENV == "testing"
                and "X-Test-Operator-Override"
                in request.headers
            )
            else session.get('operator_id')
        )

        return jsonify({
            'authenticated': True,
            'operator': {
                'id': op_id,
                'name': session.get(
                    'operator_name',
                    'Test Agent'
                ),
                'role': session.get(
                    'operator_role',
                    'OPERADOR'
                )
            }
        })

    return jsonify({
        'authenticated': False
    }), 200


@app.route('/api/categorias', methods=['GET'])
def get_categorias():
    return jsonify([
        {
            'id': category.id,
            'name': category.name,
            'parent_id': category.parent_id
        }
        for category
        in container.category_use_case.list_all()
    ])


@app.route('/api/categoria', methods=['POST'])
def create_categoria():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = container.category_use_case.create_category(
        data.get('id'),
        data.get('name'),
        data.get('parent_id')
    )

    if res.is_success:
        return jsonify({
            'message': 'OK'
        }), 201

    if "Autorização negada" in res.error:
        return jsonify({
            "error": res.error
        }), 403

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    return jsonify([
        {
            'id': product.id,
            'name': product.name,
            'quantity': product.quantity
        }
        for product
        in container.use_case.list_all()
    ])


@app.route('/api/produto/<sku>', methods=['GET'])
@app.route('/api/sku/<sku>', methods=['GET'])
def get_produto(sku):
    product = container.product_repository.get_by_id(
        sku
    )

    if not product:
        return jsonify({
            'error': 'Not found'
        }), 404

    return jsonify({
        'id': product.id,
        'name': product.name,
        'quantity': product.quantity
    })


@app.route('/api/reposicao/<sku>', methods=['GET'])
def get_picking_info(sku):
    res = container.use_case.get_picking_info(
        sku
    )

    if res.is_success:
        return jsonify(
            res.value
        )

    return jsonify({
        'error': res.error
    }), 404


# ========================================================
# PROTECTED ROUTES (HTTP Auth Normalization 401)
# ========================================================

@app.route('/api/produto', methods=['POST'])
def create_produto():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    explicit_product_id = data.get(
        'id'
    )

    # Compatibilidade temporária:
    # integrações e testes internos antigos ainda podem
    # cadastrar um produto usando um SKU explícito.
    if explicit_product_id:
        res = container.use_case.create_product(
            product_id=explicit_product_id,
            name=data.get('name'),
            unit_of_measure=data.get(
                'unit_of_measure',
                'un'
            ),
            status=data.get(
                'status',
                'ATIVO'
            ),
            category_id=data.get(
                'category_id'
            ),
            ean=data.get(
                'ean',
                ''
            ),
        )

        if res.is_success:
            return jsonify({
                'message': 'OK'
            }), 201

    else:
        # Contrato operacional canônico:
        # o cliente não controla o SKU.
        res = container.use_case.register_product(
            name=data.get('name'),
            ean=data.get(
                'ean',
                ''
            ),
            unit_of_measure=data.get(
                'unit_of_measure',
                'un'
            ),
            status=data.get(
                'status',
                'ATIVO'
            ),
            category_id=data.get(
                'category_id'
            ),
        )

        if res.is_success:
            return jsonify({
                'message': 'Produto cadastrado.',
                'product': res.value
            }), 201

    if (
        'Autorização negada'
        in res.error
    ):
        return jsonify({
            'error': res.error
        }), 403

    if (
        'EAN' in res.error
        and 'já' in res.error.lower()
    ):
        return jsonify({
            'error': res.error
        }), 409

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/adjustment', methods=['POST'])
def adjustment_stock():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    product_id = (
        data.get('sku')
        or data.get('id')
    )

    amount = (
        data.get('quantity')
        or data.get('amount')
    )

    reason = (
        data.get('divergence_type')
        or data.get('reason')
        or "CONTAGEM"
    )

    res = container.use_case.execute_adjustment(
        product_id,
        amount,
        reason,
        data.get('batch_code'),
        data.get(
            'warehouse_id',
            'WH-PADRAO'
        )
    )

    if res.is_success:
        return jsonify({
            'message': 'Ajuste registrado.'
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/product/suggestions', methods=['GET'])
def suggest_products():
    query = request.args.get(
        'q',
        ''
    ).strip()

    if not query:
        return jsonify([]), 200

    products = (
        container
        .product_suggestion_use_case
        .execute(
            query=query
        )
    )

    return jsonify([
        {
            'id': product.id,
            'name': product.name,
            'ean': product.ean,
        }
        for product in products
    ]), 200


@app.route('/api/product/query', methods=['GET'])
def query_product():
    identifier = request.args.get(
        'identifier',
        ''
    ).strip()

    if not identifier:
        return jsonify({
            'error': 'Identificador obrigatório.'
        }), 400

    res = (
        container
        .product_query_use_case
        .execute(
            identifier=identifier
        )
    )

    if res.is_success:
        return jsonify(
            res.value
        ), 200

    if (
        res.error
        == 'PRODUTO_NAO_CADASTRADO'
    ):
        return jsonify({
            'error': res.error
        }), 404

    return jsonify({
        'error': res.error
    }), 400


@app.route(
    '/api/products/<product_id>/history',
    methods=['GET']
)
def product_operational_history(product_id):
    if not _has_valid_session():
        return jsonify({
            'success': False,
            'error': 'Operador não autenticado.'
        }), 401

    normalized_product_id = str(
        product_id
    ).strip()

    product = (
        container
        .repository
        .get_by_id(
            normalized_product_id
        )
    )

    if product is None:
        return jsonify({
            'success': False,
            'error': 'PRODUTO_NAO_CADASTRADO',
            'product_id': normalized_product_id,
        }), 404

    events = (
        container
        .repository
        .get_operational_audit_events_by_product(
            normalized_product_id
        )
    )

    events = sorted(
        list(events or []),
        key=lambda event: (
            int(event.get('id') or 0)
        ),
    )

    receiving_events = [
        event
        for event in events
        if event.get('event_type')
        == 'RECEBIMENTO'
    ]

    latest_receiving = (
        receiving_events[-1]
        if receiving_events
        else None
    )

    return jsonify({
        'success': True,
        'product_id': normalized_product_id,
        'latest_receiving': latest_receiving,
        'events': events,
    }), 200


@app.route(
    '/api/relatorios/vencimentos',
    methods=['GET']
)
def expiration_report():
    report = []

    products = (
        container
        .product_repository
        .get_all()
    )

    for product in products:
        for batch in (
            product.batches.values()
        ):
            analysis = (
                ExpirationAnalyzer
                .analyze(
                    batch.expiration_date
                )
            )

            if not analysis.is_success:
                continue

            expiration = analysis.value

            report.append({
                'sku': product.id,
                'ean': product.ean,
                'name': product.name,
                'batch': batch.code,
                'expiration': (
                    batch.expiration_date
                ),
                'days_remaining': (
                    expiration[
                        'days_remaining'
                    ]
                ),
                'status': (
                    expiration[
                        'status'
                    ]
                ),
                'quantity': (
                    batch.quantity
                ),
                'location_id': (
                    batch.location_id
                ),
            })

    report.sort(
        key=lambda item: (
            item['expiration'],
            item['sku'],
            item['batch'],
        )
    )

    return jsonify(
        report
    ), 200


@app.route(
    '/api/abastecimento/plano',
    methods=['POST']
)
def replenishment_plan():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = (
        container
        .use_case
        .plan_replenishment(
            data.get('items')
        )
    )

    if res.is_success:
        return jsonify(
            res.value
        ), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route(
    '/api/abastecimento/coleta/plano',
    methods=['POST']
)
def replenishment_pick_plan():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = (
        container
        .use_case
        .plan_replenishment_pick(
            data.get('items')
        )
    )

    if res.is_success:
        return jsonify(
            res.value
        ), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route(
    '/api/abastecimento/coleta/confirmar',
    methods=['POST']
)
def replenishment_pick_confirm():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = (
        container
        .use_case
        .confirm_replenishment_pick(
            data.get('sku'),
            data.get('batch_code'),
            data.get('quantity'),
        )
    )

    if res.is_success:
        return jsonify(
            res.value
        ), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/putaway', methods=['POST'])
def putaway_stock():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    product_id = (
        data.get('sku')
        or data.get('id')
    )

    batch_code = data.get(
        'batch_code'
    )

    location_id = (
        data.get('location_id')
        or data.get('location')
    )

    res = container.use_case.execute_putaway(
        product_id,
        batch_code,
        location_id
    )

    if res.is_success:
        return jsonify({
            'message': 'Putaway registrado.'
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/stock/onboarding', methods=['POST'])
def onboard_existing_stock():
    """
    Incorpora ao controle do Kippe estoque que já existia
    fisicamente antes de sua entrada no sistema.

    Esta rota é semanticamente distinta de o fluxo de recebimento físico:
    ela nunca representa chegada física ocorrendo agora.
    """

    if not _has_valid_session():
        return jsonify({
            'error': (
                'Operador não autenticado.'
            )
        }), 401

    data = request.json or {}

    product_id = (
        data.get('sku')
        or data.get('id')
    )

    result = (
        container
        .existing_stock_onboarding_use_case
        .execute(
            product_id=product_id,
            quantity=data.get(
                'quantity'
            ),
            batch_code=data.get(
                'batch_code',
                '',
            ),
            expiration_date=data.get(
                'expiration_date',
                '',
            ),
            manufacturing_date=data.get(
                'manufacturing_date',
                '',
            ),
            supplier=data.get(
                'supplier',
                '',
            ),
            location_id=(
                data.get(
                    'location_id'
                )
                or data.get(
                    'location'
                )
                or ''
            ),
            historical_receipt_date=(
                data.get(
                    'historical_receipt_date'
                )
            ),
            historical_date_basis=(
                data.get(
                    'historical_date_basis'
                )
            ),
            document_id=data.get(
                'document_id',
                '',
            ),
        )
    )

    if result.is_success:
        onboarded = result.value

        return jsonify({
            'message': (
                'Estoque existente incorporado.'
            ),
            'onboarding': {
                'status': onboarded[
                    'status'
                ],
                'event_type': onboarded[
                    'event_type'
                ],
                'sku': onboarded[
                    'product_id'
                ],
                'batch_code': onboarded[
                    'batch_code'
                ],
                'quantity': onboarded[
                    'quantity'
                ],
                'quantity_before': onboarded[
                    'quantity_before'
                ],
                'quantity_after': onboarded[
                    'quantity_after'
                ],
                'location_id': onboarded[
                    'location_id'
                ],
                'supplier': onboarded[
                    'supplier'
                ],
                'document_id': onboarded[
                    'document_id'
                ],
                'historical_receipt_date': (
                    onboarded[
                        'historical_receipt_date'
                    ]
                ),
                'historical_date_basis': (
                    onboarded[
                        'historical_date_basis'
                    ]
                ),
            }
        }), 200

    error = str(
        result.error
        or 'Falha ao implantar estoque existente.'
    )

    normalized_error = (
        error.lower()
    )

    if (
        'sem privilégio'
        in normalized_error
        or 'sem privilegio'
        in normalized_error
        or 'autorização negada'
        in normalized_error
        or 'autorizacao negada'
        in normalized_error
    ):
        return jsonify({
            'error': error
        }), 403

    return jsonify({
        'error': error
    }), 400


@app.route('/api/receive', methods=['POST'])
def receive_stock():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    product_id = (
        data.get('sku')
        or data.get('id')
    )

    amount = (
        data.get('quantity')
        or data.get('amount')
    )

    manufacturing_date = data.get(
        'manufacturing_date',
        ''
    )

    invoice_id = data.get(
        'invoice_id',
        ''
    )

    origin_document = data.get(
        'origin_document',
        'MANUAL'
    )

    operator_id = (
        request.headers.get(
            'X-Test-Operator-Override'
        )
        if (
            container.config.ENV == 'testing'
            and 'X-Test-Operator-Override'
            in request.headers
        )
        else session.get(
            'operator_id'
        )
    )

    res = container.receive_use_case.execute(
        identifier=product_id,
        quantity=amount,
        batch_code=data.get(
            'batch_code',
            ''
        ),
        expiration_date=data.get(
            'expiration_date',
            ''
        ),
        supplier=data.get(
            'supplier',
            'PADRAO'
        ),
        manufacturing_date=(
            manufacturing_date
        ),
        invoice_id=invoice_id,
        origin_document=origin_document,
        operator_id=operator_id,
    )

    if res.is_success:
        received = res.value

        return jsonify({
            'message': 'Entrada registrada.',
            'receiving': {
                'sku': (
                    received[
                        'product_id'
                    ]
                ),
                'batch_code': (
                    received[
                        'batch_code'
                    ]
                ),
                'quantity': (
                    received[
                        'quantity'
                    ]
                ),
                'supplier': (
                    received[
                        'supplier'
                    ]
                ),
                'manufacturing_date': (
                    received[
                        'manufacturing_date'
                    ]
                ),
                'expiration_date': (
                    received[
                        'expiration_date'
                    ]
                ),
                'invoice_id': (
                    invoice_id
                ),
                'origin_document': (
                    origin_document
                ),
                'putaway_status': (
                    'PENDENTE'
                ),
            }
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/entrada', methods=['POST'])
def add_stock():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = container.use_case.execute_add(
        data.get('id'),
        data.get('amount'),
        data.get(
            'expiration_date',
            ''
        ),
        data.get(
            'batch_code',
            ''
        ),
        data.get(
            'manufacturing_date',
            ''
        ),
        data.get(
            'supplier',
            'PADRAO'
        )
    )

    if res.is_success:
        return jsonify({
            'message': 'OK'
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/saida', methods=['POST'])
def remove_stock():
    if not _has_valid_session():
        return jsonify({
            'error': 'Operador não autenticado.'
        }), 401

    data = request.json or {}

    res = container.use_case.execute_remove(
        data.get('id'),
        data.get('amount')
    )

    if res.is_success:
        return jsonify({
            'message': 'OK'
        }), 200

    return jsonify({
        'error': res.error
    }), 400


@app.route('/api/historico', methods=['GET'])
def get_historico():
    return jsonify(
        container.use_case.get_recent_history()
    )


if __name__ == '__main__':
    is_dev = (
        container.config.ENV
        == 'development'
    )

    app.run(
        host=container.config.HOST,
        port=container.config.PORT,
        debug=is_dev
    )
