import { APIClient } from './api.js';

class KippeApplication {
    constructor() {
        this.api = new APIClient();
    }

    async bootstrap() {
        // LUPA BUSCA
        const searchBtn = document.getElementById('searchBtn');
        const searchInput = document.getElementById('searchInput');
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', () => {
                const val = searchInput.value.trim();
                if (val) this.fetchAndRenderSku(val);
            });
        }

        // VOLTAR
        const btnBackDash = document.getElementById('btn-back-dashboard');
        if (btnBackDash) {
            btnBackDash.addEventListener('click', () => {
                document.getElementById('dashboard-view').classList.add('hidden');
                document.getElementById('home-module-view').classList.remove('hidden');
            });
        }

        // ABRIR RECEBIMENTO
        const btnInbound = document.getElementById('btn-module-inbound');
        const modalReceive = document.getElementById('receive-modal');
        if (btnInbound && modalReceive) {
            btnInbound.addEventListener('click', () => {
                document.getElementById('rec-ean').value = searchInput ? searchInput.value.trim() : '';
                document.getElementById('rec-qty').value = '';
                modalReceive.classList.remove('hidden');
            });
        }

        // FECHAR RECEBIMENTO
        const closeReceive = document.getElementById('close-receive-modal');
        if (closeReceive) closeReceive.addEventListener('click', () => modalReceive.classList.add('hidden'));

        // CONFIRMAR RECEBIMENTO
        const submitReceive = document.getElementById('submit-receive');
        if (submitReceive) {
            submitReceive.addEventListener('click', async () => {
                const sku = document.getElementById('rec-ean').value.trim();
                const qty = parseInt(document.getElementById('rec-qty').value.trim(), 10);
                
                if (!sku || isNaN(qty) || qty <= 0) {
                    alert('Dados inválidos. Verifique o SKU e a Quantidade.');
                    return;
                }

                document.getElementById('loader').classList.remove('hidden');
                try {
                    // API Register Receive do backend oficial
                    await this.api.registerReceive({
                        id: sku,
                        barcode: sku,
                        amount: qty,
                        operator: "ADMIN"
                    });
                    
                    document.getElementById('loader').classList.add('hidden');
                    modalReceive.classList.add('hidden');
                    this.fetchAndRenderSku(sku); // Já busca e mostra o saldo atualizado!
                } catch (error) {
                    document.getElementById('loader').classList.add('hidden');
                    alert('Erro ao dar entrada: ' + (error.message || 'Falha no banco.'));
                }
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
            alert("❌ PRODUTO NÃO ENCONTRADO.\n\nClique no botão '1. RECEBER' para dar entrada nele.");
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new KippeApplication();
    app.bootstrap();
});
