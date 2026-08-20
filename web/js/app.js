import { APIClient } from './api.js';
import { ScannerManager } from './scanner.js';

class KippeApplication {
    constructor() {
        this.api = new APIClient();

        this.scanner = new ScannerManager((decodedText) => {
            const searchInput = document.getElementById('searchInput');

            if (searchInput) {
                searchInput.value = decodedText;
            }

            this.fetchAndRenderSku(decodedText);
        });
    }

    async bootstrap() {
        this.checkGlobalFefoAlerts();
        this.bindNavigation();
        this.bindInboundModule();
        this.bindPutawayModule();
        this.bindScannerModule();
        this.bindReportsModule();
    }

    bindNavigation() {
        const searchBtn = document.getElementById('searchBtn');
        const searchInput = document.getElementById('searchInput');
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', () => {
                if (searchInput.value.trim()) this.fetchAndRenderSku(searchInput.value.trim());
            });
        }

        const hideAllViews = () => {
            ['home-module-view', 'dashboard-view', 'reports-view'].forEach(id => {
                const el = document.getElementById(id);
                if(el) el.classList.add('hidden');
            });
        };

        const showHome = () => {
            hideAllViews();
            document.getElementById('home-module-view').classList.remove('hidden');
        };

        document.getElementById('btn-back-dashboard')?.addEventListener('click', showHome);
        document.getElementById('btn-back-reports')?.addEventListener('click', showHome);
        document.getElementById('nav-home')?.addEventListener('click', showHome);
    }

    async openNewProductRegistration(ean) {
        const modal =
            document.getElementById('new-product-modal');

        const eanInput =
            document.getElementById('new-product-ean');

        const skuInput =
            document.getElementById('new-product-sku');

        const nameInput =
            document.getElementById('new-product-name');

        const unitInput =
            document.getElementById('new-product-unit');

        const categoryInput =
            document.getElementById('new-product-category');

        if (eanInput) {
            eanInput.value = ean;
        }

        if (skuInput) {
            skuInput.value = '';
        }

        if (nameInput) {
            nameInput.value = '';
        }

        if (unitInput) {
            unitInput.value = 'un';
        }

        if (categoryInput) {
            categoryInput.innerHTML =
                '<option value="">SEM CATEGORIA</option>';

            try {
                const categories =
                    await this.api.getCategories();

                categories.forEach((category) => {
                    const option =
                        document.createElement('option');

                    option.value = category.id;
                    option.textContent = category.name;

                    categoryInput.appendChild(option);
                });
            } catch (error) {
                console.warn(
                    '[PRODUCT REGISTRATION] Falha ao carregar categorias.',
                    error
                );
            }
        }

        modal?.classList.remove('hidden');
    }

    bindInboundModule() {
        const methodModal = document.getElementById('inbound-method-modal');
        const modalReceive = document.getElementById('receive-modal');
        const newProductModal =
            document.getElementById('new-product-modal');

        document.getElementById(
            'close-new-product-modal'
        )?.addEventListener('click', () => {
            newProductModal?.classList.add('hidden');
        });

        document.getElementById(
            'submit-new-product'
        )?.addEventListener('click', async () => {
            const ean =
                document.getElementById('new-product-ean')?.value.trim();

            const sku =
                document.getElementById('new-product-sku')?.value.trim();

            const name =
                document.getElementById('new-product-name')?.value.trim();

            const categoryId =
                document.getElementById('new-product-category')?.value || null;

            const unit =
                document.getElementById('new-product-unit')?.value || 'un';

            if (!ean || !sku || !name) {
                alert(
                    'Preencha EAN, SKU interno e descrição.'
                );
                return;
            }

            document.getElementById('loader')?.classList.remove('hidden');

            try {
                await this.api.createProduct({
                    id: sku,
                    name: name,
                    ean: ean,
                    unit_of_measure: unit,
                    category_id: categoryId,
                });

                document.getElementById('loader')?.classList.add('hidden');

                newProductModal?.classList.add('hidden');

                const recEan =
                    document.getElementById('rec-ean');

                if (recEan) {
                    recEan.value = ean;
                }

                modalReceive?.classList.remove('hidden');

                alert(
                    '✅ PRODUTO CADASTRADO.\n\n' +
                    'Continue o recebimento informando lote, validade, ' +
                    'fornecedor e quantidade.'
                );
            } catch (error) {
                document.getElementById('loader')?.classList.add('hidden');

                alert(
                    'Erro ao cadastrar produto: ' +
                    (error.message || 'Falha no cadastro.')
                );
            }
        });

        document.getElementById('btn-module-inbound')?.addEventListener('click', () => methodModal?.classList.remove('hidden'));
        document.getElementById('close-inbound-method')?.addEventListener('click', () => methodModal?.classList.add('hidden'));
        document.getElementById('close-smart-modal')?.addEventListener('click', () => document.getElementById('smart-receipt-modal')?.classList.add('hidden'));
        document.getElementById('close-receive-modal')?.addEventListener('click', () => modalReceive?.classList.add('hidden'));

        document.getElementById('btn-inbound-traditional')?.addEventListener('click', () => {
            methodModal?.classList.add('hidden');
            const searchInput = document.getElementById('searchInput');
            const recEan = document.getElementById('rec-ean');
            if(recEan) recEan.value = searchInput ? searchInput.value.trim() : '';
            const recQty = document.getElementById('rec-qty');
            if(recQty) recQty.value = '';
            modalReceive?.classList.remove('hidden');
        });

        // IA OCR Lógica
        const btnAi = document.getElementById('btn-inbound-ai');
        const photoInput = document.getElementById('ia-photo-input');
        if (btnAi && photoInput) {
            btnAi.addEventListener('click', () => photoInput.click());
            photoInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    methodModal?.classList.add('hidden');
                    document.getElementById('loader')?.classList.remove('hidden');
                    setTimeout(() => {
                        document.getElementById('loader')?.classList.add('hidden');
                        document.getElementById('smart-receipt-modal')?.classList.remove('hidden');
                    }, 1800);
                }
            });
        }

        document.getElementById('btn-confirm-ai-batch')?.addEventListener('click', async () => {
            const sku = "7891242151567"; const qty = 120;
            document.getElementById('loader')?.classList.remove('hidden');
            try {
                await this.api.registerReceive({ id: sku, barcode: sku, amount: qty, operator: "ADMIN (IA)", batch_code: "NF-004992831", expiration_date: "2027-12-31", supplier: "DISTRIBUIDORA KIPPE" });
                document.getElementById('loader')?.classList.add('hidden');
                document.getElementById('smart-receipt-modal')?.classList.add('hidden');
                this.fetchAndRenderSku(sku);
            } catch (error) {
                document.getElementById('loader')?.classList.add('hidden');
                alert('Erro na IA: ' + (error.message || 'Falha de comunicação.'));
            }
        });

        const submitReceive = document.getElementById('submit-receive');

        if (submitReceive) {
            submitReceive.addEventListener('click', async () => {
                const sku =
                    document.getElementById('rec-ean')?.value.trim();

                const quantity = parseInt(
                    document.getElementById('rec-qty')?.value.trim(),
                    10
                );

                const batchCode =
                    document.getElementById('rec-batch')?.value.trim();

                const expirationDate =
                    document.getElementById('rec-expiration')?.value;

                const supplier =
                    document.getElementById('rec-supplier')?.value.trim();

                if (
                    !sku ||
                    !batchCode ||
                    !expirationDate ||
                    !supplier ||
                    Number.isNaN(quantity) ||
                    quantity <= 0
                ) {
                    alert(
                        'Preencha EAN/SKU, lote, validade, ' +
                        'fornecedor e quantidade.'
                    );
                    return;
                }

                document.getElementById('loader')?.classList.remove('hidden');

                try {
                    await this.api.registerReceive({
                        sku: sku,
                        quantity: quantity,
                        batch_code: batchCode,
                        expiration_date: expirationDate,
                        supplier: supplier,
                    });

                    document.getElementById('loader')?.classList.add('hidden');
                    modalReceive?.classList.add('hidden');

                    this.fetchAndRenderSku(sku);
                } catch (error) {
                    document.getElementById('loader')?.classList.add('hidden');

                    if (
                        error.message ===
                        'PRODUTO_NAO_CADASTRADO'
                    ) {
                        modalReceive?.classList.add('hidden');

                        await this.openNewProductRegistration(
                            sku
                        );

                        return;
                    }

                    alert(
                        'Erro: ' +
                        (error.message || 'Falha no recebimento.')
                    );
                }
            });
        }
    }

    bindPutawayModule() {
        const modalPutaway =
            document.getElementById('putaway-modal');

        const btnPutaway =
            document.getElementById('btn-module-putaway');

        if (btnPutaway) {
            btnPutaway.addEventListener('click', () => {
                const searchInput =
                    document.getElementById('searchInput');

                const putEan =
                    document.getElementById('put-ean');

                const putBatch =
                    document.getElementById('put-batch');

                const putLocation =
                    document.getElementById('put-location');

                if (putEan) {
                    putEan.value =
                        searchInput
                            ? searchInput.value.trim()
                            : '';
                }

                if (putBatch) {
                    putBatch.value = '';
                }

                if (putLocation) {
                    putLocation.value = '';
                }

                modalPutaway?.classList.remove('hidden');
            });
        }

        document.getElementById(
            'close-putaway-modal'
        )?.addEventListener('click', () => {
            modalPutaway?.classList.add('hidden');
        });

        document.getElementById(
            'submit-putaway'
        )?.addEventListener('click', async () => {
            const sku =
                document.getElementById('put-ean')?.value.trim();

            const batchCode =
                document.getElementById('put-batch')?.value.trim();

            const locationId =
                document.getElementById('put-location')?.value.trim();

            if (
                !sku ||
                !batchCode ||
                !locationId
            ) {
                alert(
                    'Preencha EAN/SKU, lote e localização.'
                );
                return;
            }

            document.getElementById('loader')?.classList.remove('hidden');

            try {
                await this.api.registerPutaway({
                    sku: sku,
                    batch_code: batchCode,
                    location_id: locationId,
                });

                document.getElementById('loader')?.classList.add('hidden');

                modalPutaway?.classList.add('hidden');

                alert(
                    '✅ LOTE ENDEREÇADO.\n\n' +
                    `Produto: ${sku}\n` +
                    `Lote: ${batchCode}\n` +
                    `Local: ${locationId}`
                );

                this.fetchAndRenderSku(sku);
            } catch (error) {
                document.getElementById('loader')?.classList.add('hidden');

                alert(
                    'Erro ao armazenar: ' +
                    (error.message || 'Falha no Putaway.')
                );
            }
        });
    }

    bindReportsModule() {
        const btnReports = document.getElementById('btn-module-reports');
        if(btnReports) {
            btnReports.addEventListener('click', async () => {
                document.getElementById('loader')?.classList.remove('hidden');
                try {
                    const res = await fetch('/api/relatorios/vencimentos?_t=' + Date.now(), { method: 'GET', headers: {'Cache-Control': 'no-cache, no-store, must-revalidate'}, cache: 'no-store' });
                    let data = [];
                    if (res.ok) {
                        data = await res.json();
                    } else {
                        data = [{sku: "HTTP " + res.status, name: "ERRO 500: SERVIDOR PYTHON CAIU", expiration: "FALHA DE COMUNICAÇÃO INTERNA", batch: "CRASH FRONTEND"}];
                    }
                    
                    document.getElementById('loader')?.classList.add('hidden');
                    document.getElementById('home-module-view')?.classList.add('hidden');
                    document.getElementById('dashboard-view')?.classList.add('hidden');
                    document.getElementById('reports-view')?.classList.remove('hidden');
                    
                    const list = document.getElementById('fefo-list');
                    if(list) {
                        if(data.length === 0) {
                            list.innerHTML = `<div class="p-4 bg-green-50 text-green-700 rounded-lg text-center font-bold text-[11px] uppercase border border-green-100">NENHUM PRODUTO PRÓXIMO AO VENCIMENTO! OPERAÇÃO SEGURA.</div>`;
                        } else {
                            list.innerHTML = data.map(item => `
                                <div class="p-3 bg-red-50 border-l-4 border-l-kippe-red rounded-lg shadow-sm flex justify-between items-center">
                                    <div>
                                        <p class="text-[11px] font-black text-gray-800 uppercase">${item.name || item.sku || 'PRODUTO'}</p>
                                        <p class="text-[9px] text-red-600 font-bold uppercase mt-0.5">VENCE EM: ${item.expiration || 'CRÍTICO'}</p>
                                    </div>
                                    <span class="bg-white border border-red-200 text-kippe-red font-black text-[10px] px-2 py-1 rounded">LOTE: ${item.batch || 'ND'}</span>
                                </div>
                            `).join('');
                        }
                    }
                } catch(e) {
                    document.getElementById('loader')?.classList.add('hidden');
                    alert("Erro ao gerar relatório FEFO.");
                }
            });
        }
    }

    bindScannerModule() {
        const openScanner = () => {
            this.scanner.start();
        };

        document.getElementById('btn-module-scan')?.addEventListener(
            'click',
            openScanner
        );

        document.getElementById('nav-scan')?.addEventListener(
            'click',
            openScanner
        );
    }

    async checkGlobalFefoAlerts() {
        try {
            const res = await fetch('/api/relatorios/vencimentos?_t=' + Date.now(), { method: 'GET', headers: {'Cache-Control': 'no-cache, no-store, must-revalidate'}, cache: 'no-store' });
            if (res.ok) {
                const data = await res.json();
                if (data && data.length > 0) {
                    const badge = document.getElementById('global-fefo-badge');
                    if (badge) {
                        badge.textContent = data.length;
                        badge.classList.remove('hidden');
                    }
                }
            }
        } catch(e) {}
    }

    async fetchAndRenderSku(identifier) {
        document.getElementById('loader')?.classList.remove('hidden');

        try {
            const data = await this.api.queryProduct(identifier);

            document.getElementById('loader')?.classList.add('hidden');

            ['home-module-view', 'reports-view'].forEach(id => {
                const el = document.getElementById(id);

                if (el) {
                    el.classList.add('hidden');
                }
            });

            document.getElementById('dashboard-view')?.classList.remove('hidden');

            const prodName = document.getElementById('prodName');
            const prodSku = document.getElementById('prodSku');
            const prodEan = document.getElementById('prodEan');
            const stockTotal = document.getElementById('stockTotal');
            const batchesContainer = document.getElementById('product-batches');

            if (prodName) {
                prodName.textContent = data.name || 'PRODUTO SEM DESCRIÇÃO';
            }

            if (prodSku) {
                prodSku.textContent = data.id || identifier;
            }

            if (prodEan) {
                prodEan.textContent = data.ean || 'NÃO INFORMADO';
            }

            if (stockTotal) {
                stockTotal.textContent = data.quantity ?? 0;
            }

            if (batchesContainer) {
                batchesContainer.innerHTML = '';

                const batches = Array.isArray(data.batches)
                    ? data.batches
                    : [];

                if (batches.length === 0) {
                    batchesContainer.innerHTML = `
                        <div class="p-4 bg-gray-50 border border-gray-100 rounded-lg text-center">
                            <p class="text-[10px] font-bold text-gray-400">
                                NENHUM LOTE ATIVO
                            </p>
                        </div>
                    `;
                } else {
                    batches.forEach((batch) => {
                        const card = document.createElement('div');

                        const status = batch.expiration_status || 'NORMAL';

                        const statusClasses = {
                            NORMAL: 'bg-green-100 text-green-700 border-green-200',
                            ATENCAO: 'bg-amber-100 text-amber-800 border-amber-200',
                            CRITICO: 'bg-red-100 text-red-700 border-red-200',
                            VENCIDO: 'bg-red-600 text-white border-red-700',
                        };

                        const statusClass =
                            statusClasses[status] ||
                            statusClasses.NORMAL;

                        const location =
                            batch.location_id ||
                            'NÃO ENDEREÇADO';

                        const daysRemaining =
                            batch.days_remaining ?? 'N/A';

                        card.className =
                            'p-3 rounded-xl border border-gray-100 bg-gray-50';

                        card.innerHTML = `
                            <div class="flex justify-between items-start gap-2">
                                <div class="min-w-0">
                                    <p class="text-[9px] text-gray-400 font-bold">
                                        LOTE
                                    </p>

                                    <p class="text-sm font-black text-gray-800 font-mono">
                                        ${batch.code || 'N/A'}
                                    </p>
                                </div>

                                <span class="text-[9px] font-black px-2 py-1 rounded border ${statusClass}">
                                    ${status}
                                </span>
                            </div>

                            <div class="grid grid-cols-2 gap-2 mt-3 text-[9px]">
                                <div>
                                    <p class="text-gray-400 font-bold">
                                        QUANTIDADE
                                    </p>

                                    <p class="font-black text-gray-800">
                                        ${batch.quantity ?? 0}
                                    </p>
                                </div>

                                <div>
                                    <p class="text-gray-400 font-bold">
                                        LOCALIZAÇÃO
                                    </p>

                                    <p class="font-black text-[#124191]">
                                        ${location}
                                    </p>
                                </div>

                                <div>
                                    <p class="text-gray-400 font-bold">
                                        VALIDADE
                                    </p>

                                    <p class="font-black text-gray-800">
                                        ${batch.expiration_date || 'N/A'}
                                    </p>
                                </div>

                                <div>
                                    <p class="text-gray-400 font-bold">
                                        DIAS RESTANTES
                                    </p>

                                    <p class="font-black text-gray-800">
                                        ${daysRemaining}
                                    </p>
                                </div>
                            </div>
                        `;

                        batchesContainer.appendChild(card);
                    });
                }
            }
        } catch (error) {
            document.getElementById('loader')?.classList.add('hidden');

            alert(
                "❌ PRODUTO NÃO ENCONTRADO.\n\n" +
                "Use o botão '1. RECEBER' para dar entrada."
            );
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new KippeApplication();
    app.bootstrap();
});
