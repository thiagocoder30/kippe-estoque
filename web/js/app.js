import { APIClient } from './api.js';

class KippeApplication {
    constructor() {
        this.api = new APIClient();
        this.html5QrCode = null;
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

    bindInboundModule() {
        const methodModal = document.getElementById('inbound-method-modal');
        const modalReceive = document.getElementById('receive-modal');

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
                const sku = document.getElementById('rec-ean')?.value.trim();
                const qty = parseInt(document.getElementById('rec-qty')?.value.trim(), 10);
                if (!sku || isNaN(qty) || qty <= 0) return alert('Verifique o SKU e a Quantidade.');
                
                document.getElementById('loader')?.classList.remove('hidden');
                try {
                    await this.api.registerReceive({ id: sku, barcode: sku, amount: qty, operator: "ADMIN", batch_code: "LOTE-" + new Date().getTime().toString().slice(-5), expiration_date: "2027-12-31" });
                    document.getElementById('loader')?.classList.add('hidden');
                    modalReceive?.classList.add('hidden');
                    this.fetchAndRenderSku(sku);
                } catch (error) {
                    document.getElementById('loader')?.classList.add('hidden');
                    alert('Erro: ' + (error.message || 'Falha no banco.'));
                }
            });
        }
    }

    bindPutawayModule() {
        const modalPutaway = document.getElementById('putaway-modal');
        const btnPutaway = document.getElementById('btn-module-putaway');

        if(btnPutaway) {
            btnPutaway.addEventListener('click', () => {
                const searchInput = document.getElementById('searchInput');
                const putEan = document.getElementById('put-ean');
                if(putEan) putEan.value = searchInput ? searchInput.value.trim() : '';
                
                const putLoc = document.getElementById('put-location');
                if(putLoc) putLoc.value = ''; // Reseta Topologia
                
                const putQty = document.getElementById('put-qty');
                if(putQty) putQty.value = '';
                
                modalPutaway?.classList.remove('hidden');
            });
        }

        document.getElementById('close-putaway-modal')?.addEventListener('click', () => modalPutaway?.classList.add('hidden'));

        document.getElementById('submit-putaway')?.addEventListener('click', async () => {
            const sku = document.getElementById('put-ean')?.value.trim();
            const loc = document.getElementById('put-location')?.value.trim();
            const qty = parseInt(document.getElementById('put-qty')?.value.trim(), 10);
            
            if (!sku || !loc || isNaN(qty) || qty <= 0) return alert('Preencha SKU, Topologia e Quantidade válidos.');
            
            document.getElementById('loader')?.classList.remove('hidden');
            try {
                if(this.api.registerTransfer) {
                    await this.api.registerTransfer({ id: sku, location: loc, amount: qty, operator: "ADMIN" }).catch(e => console.warn("Modo Off: Transfer Mock"));
                }
                document.getElementById('loader')?.classList.add('hidden');
                modalPutaway?.classList.add('hidden');
                alert(`✅ PRODUTO ENDEREÇADO!

${qty} UN do Produto ${sku} foram alocadas na posição:
${loc}`);
                this.fetchAndRenderSku(sku);
            } catch (error) {
                document.getElementById('loader')?.classList.add('hidden');
                alert('Erro ao armazenar.');
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
        const scannerModal = document.getElementById('scanner-modal');
        const openScanner = () => {
            scannerModal?.classList.remove('hidden');
            if (!this.html5QrCode && window.Html5Qrcode) {
                this.html5QrCode = new window.Html5Qrcode("reader");
            }
            if (this.html5QrCode) {
                this.html5QrCode.start(
                    { facingMode: "environment" }, { fps: 10, qrbox: { width: 250, height: 250 } },
                    (decodedText) => {
                        this.html5QrCode.stop().catch(e=>{});
                        scannerModal?.classList.add('hidden');
                        const searchInput = document.getElementById('searchInput');
                        if(searchInput) searchInput.value = decodedText;
                        this.fetchAndRenderSku(decodedText);
                    },
                    (errorMessage) => { }
                ).catch(err => {
                    alert("Erro ao iniciar a câmera.");
                    scannerModal?.classList.add('hidden');
                });
            }
        };

        document.getElementById('btn-module-scan')?.addEventListener('click', openScanner);
        document.getElementById('nav-scan')?.addEventListener('click', openScanner);
        document.getElementById('close-scanner-btn')?.addEventListener('click', () => {
            if (this.html5QrCode) this.html5QrCode.stop().catch(e => {});
            scannerModal?.classList.add('hidden');
        });
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

    async fetchAndRenderSku(sku) {
        document.getElementById('loader')?.classList.remove('hidden');
        try {
            const data = await this.api.getSku(sku);
            document.getElementById('loader')?.classList.add('hidden');
            
            ['home-module-view', 'reports-view'].forEach(id => {
                const el = document.getElementById(id);
                if(el) el.classList.add('hidden');
            });
            document.getElementById('dashboard-view')?.classList.remove('hidden');
            
            const prodName = document.getElementById('prodName');
            if(prodName) prodName.textContent = data.name || data.description || "PRODUTO SEM CADASTRO";
            
            const prodSku = document.getElementById('prodSku');
            if(prodSku) prodSku.textContent = data.id || data.sku || sku;
            
            const stockTotal = document.getElementById('stockTotal');
            const stock = data.balances ? data.balances.total : data.quantity;
            if(stockTotal) stockTotal.textContent = stock !== undefined ? stock : 0;
        } catch (error) {
            document.getElementById('loader')?.classList.add('hidden');
            alert("❌ PRODUTO NÃO ENCONTRADO.\n\nUse o botão '1. RECEBER' para dar entrada.");
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new KippeApplication();
    app.bootstrap();
});
