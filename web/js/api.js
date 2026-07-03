/**
 * Camada de Cliente HTTP.
 * Padrão: Gateway / Adapter
 */
export class APIClient {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
    }

    async _request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...options.headers
        };

        try {
            const response = await fetch(url, { ...options, headers });
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `Erro HTTP: ${response.status}`);
            }
            return data;
        } catch (error) {
            console.error(`[API ERROR] ${options.method || 'GET'} ${url}`, error);
            throw error;
        }
    }

    async checkHealth() {
        return this._request('/health');
    }

    /**
     * @param {string} sku - Código do produto
     * @returns {Promise<Object>} Payload da View de Produto
     */
    async getSku(sku) {
        return this._request(`/api/sku/${sku}`);
    }

    async registerReceive(payload) {
        return this._request('/api/receive', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }
}

