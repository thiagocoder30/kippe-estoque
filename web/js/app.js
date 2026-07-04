import { APIClient } from './api.js';
import { UIManager } from './ui.js';
import { Router } from './router.js';
import { ScannerManager } from './scanner.js';

class KippeApplication {
    constructor() {
        this.api = new APIClient();
        this.ui = new UIManager();
        this.router = new Router(this.ui, this.api);
        
        // Inicializa o Scanner passando a função de Callback para quando a leitura for concluída
        this.scanner = new ScannerManager((scannedCode) => {
            this.handleScanSuccess(scannedCode);
        });
    }

    async bootstrap() {
        console.log('[KIPPE] Inicializando KIPPE Platform Mobile...');
        
        this._registerServiceWorker();
        this.router.init();
        
        // 1. Vincula a busca por digitação (Lupa)
        this.ui.bindSearchEvent((sku) => this.fetchAndRenderSku(sku));

        // 2. Vincula o botão físico de Scan na navegação inferior
        const scanBtn = document.getElementById('btn-scan');
        if (scanBtn) {
            scanBtn.addEventListener('click', () => {
                this.scanner.start();
            });
        }
    }

    // Fluxo acionado automaticamente após a câmera ler o código de barras com sucesso
    handleScanSuccess(scannedCode) {
        console.log("[KIPPE] Código capturado pelo Scanner:", scannedCode);
        // Atualiza a barra de pesquisa visualmente para o operador ver o que foi lido
        this.ui.setInputValue(scannedCode);
        // Desencadeia a busca no Ledger automaticamente
        this.fetchAndRenderSku(scannedCode);
    }

    // Fluxo principal de busca no banco de dados e atualização da tela
    async fetchAndRenderSku(sku) {
        this.ui.showLoader();
        try {
            const data = await this.api.getSku(sku);
            this.ui.hideLoader();
            this.ui.renderDashboard(data);
        } catch (error) {
            this.ui.hideLoader();
            this.ui.showError(error.message || "Erro de rede ou SKU não encontrado.");
        }
    }

    _registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/web/sw.js')
                    .catch(err => console.error('[KIPPE] Service Worker falhou:', err));
            });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new KippeApplication();
    app.bootstrap();
});

