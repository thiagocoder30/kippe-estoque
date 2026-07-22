import { APIClient } from './api.js';

class KippeApplication {
    constructor() {
        this.api = new APIClient();
        this.html5QrCode = null;
    }

    async bootstrap() {
        // --- BUSCA RÁPIDA ---
        const searchBtn = document.getElementById('searchBtn');
        const searchInput = document.getElementById('searchInput');
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', () => {
                if (searchInput.value.trim()) this.fetchAndRenderSku(searchInput.value.trim());
            });
        }

        // --- NAVEGAÇÃO ---
        const btnBackDash = document.getElementById('btn-back-dashboard');
        if (btnBackDash) {
            btnBackDash.addEventListener('click', () => {
                document.getElementById('dashboard-view').classList.add('hidden');
                document.getElementById('home-module-view').classList.remove('hidden');
            });
        }
        
        const navHome = document.getElementById('nav-home');
        if(navHome) navHome.addEventListener('click', () => {
             document.getElementById('dashboard-view').classList.add('hidden');
             document.getElementById('home-module-view').classList.remove('hidden');
        });

        // --- MÓDULO RECEBIMENTO ---
        const btnInbound = document.getElementById('btn-module-inbound');
        const modalReceive = document.getElementById('receive-modal');
        if (btnInbound && modalReceive) {
            btnInbound.addEventListener('click', () => {
                document.getElementById('rec-ean').value = searchInput ? searchInput.value.trim() : '';
                document.getElementById('rec-qty').value = '';
                modalReceive.classList.remove('hidden');
            });
        }

        const closeReceive = document.getElementById('close-receive-modal');
        if (closeReceive) closeReceive.addEventListener('click', () => modalReceive.classList.add('hidden'));

        const submitReceive = document.getElementById('submit-receive');
        if (submitReceive) {
            submitReceive.addEventListener('click', async () => {
                const sku = document.getElementById('rec-ean').value.trim();
                const qty = parseInt(document.getElementById('rec-qty').value.trim(), 10);
                if (!sku || isNaN(qty) || qty <= 0) return alert('Verifique o SKU e a Quantidade.');
                
                document.getElementById('loader').classList.remove('hidden');
                try {
                    await this.api.registerReceive({ id: sku, barcode: sku, amount: qty, operator: "ADMIN" });
                    document.getElementById('loader').classList.add('hidden');
                    modalReceive.classList.add('hidden');
                    this.fetchAndRenderSku(sku);
                } catch (error) {
                    document.getElementById('loader').classList.add('hidden');
                    alert('Erro: ' + (error.message || 'Falha no banco.'));
                }
            });
        }

        // --- MÓDULO SCANNER (CÂMERA) ---
        const btnScan3 = document.getElementById('btn-module-scan');
        const navScan = document.getElementById('nav-scan');
        const scannerModal = document.getElementById('scanner-modal');
        const closeScannerBtn = document.getElementById('close-scanner-btn');

        const openScanner = () => {
            scannerModal.classList.remove('hidden');
            if (!this.html5QrCode) {
                this.html5QrCode = new Html5Qrcode("reader");
            }
            this.html5QrCode.start(
                { facingMode: "environment" },
                { fps: 10, qrbox: { width: 250, height: 250 } },
                (decodedText) => {
                    this.html5QrCode.stop();
                    scannerModal.classList.add('hidden');
                    if(searchInput) searchInput.value = decodedText;
                    this.fetchAndRenderSku(decodedText);
                },
                (errorMessage) => { /* Ignora erros de frame contínuo */ }
            ).catch(err => {
                alert("Erro ao iniciar a câmera. Verifique as permissões do navegador.");
                scannerModal.classList.add('hidden');
            });
        };

        if(btnScan3) btnScan3.addEventListener('click', openScanner);
        if(navScan) navScan.addEventListener('click', openScanner);
        if(closeScannerBtn) {
            closeScannerBtn.addEventListener('click', () => {
                if (this.html5QrCode) this.html5QrCode.stop().catch(e => {});
                scannerModal.classList.add('hidden');
            });
        }
    }

    async fetchAndRenderSku(sku) {
        document.getElementById('loader').classList.remove('hidden');
        try {
            const data = await this.api.getSku(sku);
            document.getElementById('loader').classList.add('hidden');
            
            document.getElementById('home-module-view').classList.add('hidden');
            document.getElementById('dashboard-view').classList.remove('hidden');
            
            document.getElementById('prodName').textContent = data.name || data.description || "NOVO PRODUTO";
            document.getElementById('prodSku').textContent = data.id || data.sku || sku;
            const stock = data.balances ? data.balances.total : data.quantity;
            document.getElementById('stockTotal').textContent = stock !== undefined ? stock : 0;
            
        } catch (error) {
            document.getElementById('loader').classList.add('hidden');
            alert("❌ PRODUTO NÃO ENCONTRADO.\n\nUse o botão '1. RECEBER' para dar entrada.");
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new KippeApplication();
    app.bootstrap();
});
