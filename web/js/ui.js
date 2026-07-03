/**
 * Gerenciador de Interface de Usuário.
 * Responsabilidade: Mutações no DOM e feedback visual.
 */
export class UIManager {
    constructor() {
        // Cache de elementos vitais para performance
        this.elements = {
            dashboard: document.getElementById('dashboard-view'),
            loader: document.getElementById('global-loader'),
            errorToast: document.getElementById('error-toast')
        };
    }

    showLoader() {
        if (this.elements.loader) this.elements.loader.classList.remove('hidden');
    }

    hideLoader() {
        if (this.elements.loader) this.elements.loader.classList.add('hidden');
    }

    showError(message) {
        console.error('[UI ERROR]', message);
        // Implementação futura do Toast F006
    }

    /**
     * @param {Object} data - Objeto InventoryProductView mapeado da API
     */
    renderDashboard(data) {
        if (!this.elements.dashboard) return;
        
        // Exemplo de preenchimento seguro via textContent
        this._safeSetText('prodName', data.description);
        this._safeSetText('prodSku', data.sku);
        this._safeSetText('stockTotal', data.balances.total);
        
        this.elements.dashboard.classList.remove('hidden');
    }

    _safeSetText(elementId, text) {
        const el = document.getElementById(elementId);
        if (el) el.textContent = text ?? 'N/A';
    }
}

