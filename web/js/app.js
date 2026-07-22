import { APIClient } from './api.js';

class KippeApplication {
    constructor() {
        this.api = new APIClient();
    }

    async bootstrap() {
        // 1. Escuta o Botão de Busca Rápida
        const searchBtn = document.getElementById('searchBtn');
        const searchInput = document.getElementById('searchInput');
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', () => {
                const val = searchInput.value.trim();
                if (val) this.fetchAndRenderSku(val);
            });
        }

        // 2. Escuta o Botão "VOLTAR" na tela do produto
        const btnBackDash = document.getElementById('btn-back-dashboard');
        if (btnBackDash) {
            btnBackDash.addEventListener('click', () => {
                document.getElementById('dashboard-view').classList.add('hidden');
                document.getElementById('home-module-view').classList.remove('hidden');
                if (searchInput) searchInput.value = '';
            });
        }
    }

    async fetchAndRenderSku(sku) {
        try {
            // A MAGIA ACONTECE AQUI: Chama o Python/SQLite
            const data = await this.api.getSku(sku);
            
            // Troca de tela (Esconde a Home, Mostra o Produto)
            document.getElementById('home-module-view').classList.add('hidden');
            document.getElementById('dashboard-view').classList.remove('hidden');
            
            // Injeta os dados reais do banco de dados no Layout
            document.getElementById('prodName').textContent = data.name || data.description || "PRODUTO SEM NOME";
            document.getElementById('prodSku').textContent = data.id || data.sku;
            document.getElementById('prodEan').textContent = data.barcode || data.id || sku;
            
            const stock = data.balances ? data.balances.total : data.quantity;
            document.getElementById('stockTotal').textContent = stock !== undefined ? stock : 0;
            
        } catch (error) {
            // Se o EAN não existir no banco, alerta com segurança sem quebrar a tela
            alert("❌ ERRO DE ESTOQUE:\n\nProduto " + sku + " não foi encontrado no Banco de Dados.");
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new KippeApplication();
    app.bootstrap();
});
