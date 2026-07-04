import { APIClient } from './api.js';
import { UIManager } from './ui.js';
import { Router } from './router.js';

class KippeApplication {
    constructor() {
        this.api = new APIClient();
        this.ui = new UIManager();
        this.router = new Router(this.ui, this.api);
    }

    async bootstrap() {
        console.log('[KIPPE] Inicializando KIPPE Platform Mobile...');
        
        this._registerServiceWorker();
        this.router.init();
        
        // Vincula a pesquisa operacional do botão de busca
        this.ui.bindSearchEvent(async (sku) => {
            this.ui.showLoader();
            try {
                const data = await this.api.getSku(sku);
                this.ui.hideLoader();
                this.ui.renderDashboard(data);
            } catch (error) {
                this.ui.hideLoader();
                this.ui.showError(error.message || "Erro de rede ou SKU não encontrado.");
            }
        });
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

