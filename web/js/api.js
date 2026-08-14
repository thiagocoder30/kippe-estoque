/**
 * KIPPE WMS - Cliente HTTP canônico.
 *
 * Responsabilidade:
 * - centralizar contratos HTTP do frontend;
 * - evitar URLs de API espalhadas pela interface;
 * - preservar compatibilidade temporária durante a reconciliação.
 */
export class APIClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
    }

    async _request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;

        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...options.headers,
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers,
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error || `Erro HTTP: ${response.status}`
                );
            }

            return data;
        } catch (error) {
            console.error(
                `[API ERROR] ${options.method || 'GET'} ${url}`,
                error
            );

            throw error;
        }
    }

    async checkHealth() {
        return this._request('/health');
    }

    /**
     * Consulta operacional exata.
     * Aceita EAN, SKU ou identificador compatível com o backend.
     */
    async queryProduct(identifier) {
        return this._request(
            `/api/product/query?identifier=${encodeURIComponent(identifier)}`
        );
    }

    /**
     * Busca digitada / autocomplete.
     * Retorna até 10 sugestões ranqueadas pelo backend.
     */
    async suggestProducts(query) {
        return this._request(
            `/api/product/suggestions?q=${encodeURIComponent(query)}`
        );
    }

    /**
     * Recebimento canônico.
     */
    async registerReceive(payload) {
        return this._request('/api/receive', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    /**
     * Putaway canônico.
     */
    async registerPutaway(payload) {
        return this._request('/api/putaway', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    /**
     * Ajuste canônico.
     */
    async registerAdjustment(payload) {
        return this._request('/api/adjustment', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    /**
     * Transferência permanece disponível enquanto os demais
     * fluxos legados forem reconciliados.
     */
    async registerTransfer(payload) {
        return this._request('/api/transfer', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    /*
     * Compatibility aliases.
     *
     * app.js ainda usa esses nomes. Eles serão removidos quando
     * migrarmos a camada de aplicação frontend para os contratos
     * canônicos acima.
     */

    async getSku(identifier) {
        return this.queryProduct(identifier);
    }

    async searchCatalog(query) {
        return this.suggestProducts(query);
    }
}
