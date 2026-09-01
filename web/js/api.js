/**
 * KIPPE WMS - Cliente HTTP canônico.
 *
 * Responsabilidade:
 * - centralizar contratos HTTP do frontend;
 * - preservar a sessão Flask do operador;
 * - evitar URLs de API espalhadas pela interface.
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
                credentials: 'same-origin',
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

    /**
     * Inicia sessão nominal de operador.
     */
    async login(id, pin) {
        return this._request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                id,
                pin,
            }),
        });
    }

    /**
     * Consulta a sessão Flask atualmente ativa.
     */
    async getCurrentOperator() {
        return this._request('/api/auth/me');
    }

    /**
     * Encerra a sessão Flask atualmente ativa.
     */
    async logout() {
        return this._request('/api/auth/logout', {
            method: 'POST',
        });
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
     * Cadastro canônico de produto.
     */
    async createProduct(payload) {
        return this._request('/api/produto', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    /**
     * Categorias disponíveis para cadastro.
     */
    async getCategories() {
        return this._request('/api/categorias');
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
     * Relatório canônico de validade por lote.
     */
    async getExpirationReport() {
        return this._request('/api/relatorios/vencimentos');
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
}
