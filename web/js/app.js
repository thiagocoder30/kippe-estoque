import { APIClient } from './api.js';
import { UIManager } from './ui.js';
import { Router } from './router.js';

/**
 * Classe principal de orquestração do KIPPE PWA.
 * Padrão: Facade / Bootstrapper
 */
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
        
        // Verificação de saúde da API de forma assíncrona sem bloquear a UI
        try {
            const health = await this.api.checkHealth();
            console.log('[KIPPE] Status da API:', health);
        } catch (error) {
            console.warn('[KIPPE] Trabalhando em modo Offline. API inacessível.');
        }
    }

    _registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/web/sw.js')
                    .then(reg => console.log('[KIPPE] Service Worker Isolado. Escopo:', reg.scope))
                    .catch(err => console.error('[KIPPE] Falha crítica no Service Worker:', err));
            });
        }
    }
}

// Inicialização segura após o carregamento do DOM
document.addEventListener('DOMContentLoaded', () => {
    const app = new KippeApplication();
    app.bootstrap();
});

