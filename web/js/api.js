/**
 * Camada de Cliente HTTP Vanilla JS.
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
                // Preserva a mensagem de erro do backend (ex: NotFoundException)
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

    async getSku(sku) {
        return this._request(`/api/sku/${sku}`);
    }

    // NOVO: Metodo de Escrita (Command)
    async registerReceive(payload) {
        return this._request('/api/receive', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }
}

