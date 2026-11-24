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
        const timeoutMs = Number(options.timeoutMs || 20000);
        const controller = new AbortController();
        const timerId = setTimeout(() => controller.abort(), timeoutMs);

        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            ...options.headers,
        };

        const fetchOptions = {
            ...options,
            headers,
            credentials: 'same-origin',
            signal: options.signal || controller.signal,
        };
        delete fetchOptions.timeoutMs;

        try {
            const response = await fetch(url, fetchOptions);
            const rawText = await response.text();
            let data = {};
            if (rawText) {
                try {
                    data = JSON.parse(rawText);
                } catch (_) {
                    data = { error: `Resposta inv\u00e1lida do servidor (HTTP ${response.status}).` };
                }
            }

            if (!response.ok) {
                throw new Error(
                    data.error || `Erro HTTP: ${response.status}`
                );
            }

            return data;
        } catch (error) {
            if (error && error.name === 'AbortError') {
                throw new Error('Tempo limite excedido (20s). Verifique sua conex\u00e3o e tente novamente.');
            }
            console.error(
                `[API ERROR] ${options.method || 'GET'} ${url}`,
                error
            );

            throw error;
        } finally {
            clearTimeout(timerId);
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
     * Histórico documental autenticado do produto.
     * Não representa autoridade quantitativa de estoque.
     */
    async getProductHistory(productId) {
        return this._request(
            `/api/products/${encodeURIComponent(productId)}/history`,
            {
                method: 'GET',
            }
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
     * Incorporação canônica de estoque fisicamente preexistente.
     *
     * Não representa recebimento de mercadoria.
     */
    async onboardExistingStock(payload) {
        return this._request('/api/stock/onboarding', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    /**
     * NF-001J.10
     *
     * Reconciliação documental da NF.
     * Não altera estoque.
     */
    async reconcileSupplierInvoice(payload) {
        return this._request(
            '/api/stock/onboarding',
            {
                method: 'POST',
                body: JSON.stringify(payload),
            }
        );
    }

    /**
     * NF-001J.10
     *
     * Execução certificada após conferência física explícita.
     * A autoridade de mutação permanece no backend J.9 -> J.8.
     */
    async receiveCertifiedInvoice(payload) {
        return this._request(
            '/api/invoices/receive-certified',
            {
                method: 'POST',
                body: JSON.stringify(payload),
            }
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
     * Relatório canônico de validade por lote.
     */
    async getExpirationReport() {
        return this._request('/api/relatorios/vencimentos');
    }

    /**
     * Valida e resolve o carrinho de abastecimento por FEFO.
     * Não altera estoque.
     */
    async planReplenishment(payload) {
        return this._request('/api/abastecimento/plano', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    /**
     * Gera a rota física de coleta a partir do carrinho.
     * FEFO e ordem física são decididos pelo backend.
     */
    async planReplenishmentPick(payload) {
        return this._request('/api/abastecimento/coleta/plano', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    }

    /**
     * Confirma um único passo físico da coleta.
     * Esta operação altera o estoque controlado.
     */
    async confirmReplenishmentPick(payload) {
        return this._request('/api/abastecimento/coleta/confirmar', {
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
}
