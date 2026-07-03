/**
 * Roteador de navegação Vanilla JS.
 * Padrão: State Machine / View Switcher
 */
export class Router {
    constructor(ui, api) {
        this.ui = ui;
        this.api = api;
        this.routes = {
            '#dashboard': this._loadDashboard.bind(this),
            '#scanner': this._loadScanner.bind(this)
        };
    }

    init() {
        window.addEventListener('hashchange', () => this._handleRoute());
        
        // Dispara a rota inicial
        if (!window.location.hash) {
            window.location.hash = '#dashboard';
        } else {
            this._handleRoute();
        }
    }

    _handleRoute() {
        const hash = window.location.hash;
        const routeHandler = this.routes[hash];
        
        if (routeHandler) {
            routeHandler();
        } else {
            console.warn(`[ROUTER] Rota não encontrada: ${hash}`);
            window.location.hash = '#dashboard';
        }
    }

    async _loadDashboard() {
        console.log('[ROUTER] Navegando para Dashboard...');
        // A UI limpará a tela atual e mostrará o Dashboard vazio aguardando ação
    }

    _loadScanner() {
        console.log('[ROUTER] Inicializando Módulo de Scanner...');
        // Preparação para a Sprint F004
    }
}

