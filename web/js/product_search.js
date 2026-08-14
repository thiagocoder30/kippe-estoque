import { APIClient } from './api.js';


class ProductSearchController {
    constructor() {
        this.api = new APIClient();

        this.input = document.getElementById('searchInput');
        this.button = document.getElementById('searchBtn');

        this.suggestions = null;
        this.debounceTimer = null;
    }

    init() {
        if (!this.input || !this.button) {
            return;
        }

        this.createSuggestionsContainer();
        this.bindInput();
        this.bindOutsideClick();
    }

    createSuggestionsContainer() {
        const existing = document.getElementById('search-suggestions');

        if (existing) {
            this.suggestions = existing;
            return;
        }

        const container = document.createElement('ul');

        container.id = 'search-suggestions';
        container.className =
            'hidden mt-2 bg-white border border-gray-200 rounded-xl ' +
            'shadow-lg overflow-hidden divide-y divide-gray-100';

        const searchRow = this.input.parentElement;

        if (searchRow && searchRow.parentElement) {
            searchRow.parentElement.appendChild(container);
        }

        this.suggestions = container;
    }

    bindInput() {
        this.input.addEventListener('input', () => {
            clearTimeout(this.debounceTimer);

            const term = this.input.value.trim();

            if (term.length < 3) {
                this.hideSuggestions();
                return;
            }

            this.debounceTimer = setTimeout(
                () => this.loadSuggestions(term),
                300
            );
        });

        this.input.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter') {
                return;
            }

            event.preventDefault();

            const value = this.input.value.trim();

            if (!value) {
                return;
            }

            this.hideSuggestions();
            this.button.click();
        });
    }

    bindOutsideClick() {
        document.addEventListener('click', (event) => {
            if (
                event.target === this.input ||
                this.suggestions?.contains(event.target)
            ) {
                return;
            }

            this.hideSuggestions();
        });
    }

    async loadSuggestions(term) {
        try {
            const products = await this.api.suggestProducts(term);

            if (this.input.value.trim() !== term) {
                return;
            }

            this.renderSuggestions(products);
        } catch (error) {
            console.error(
                '[PRODUCT SEARCH] Falha ao carregar sugestões.',
                error
            );

            this.renderMessage(
                'Não foi possível carregar as sugestões.'
            );
        }
    }

    renderSuggestions(products) {
        this.suggestions.innerHTML = '';

        if (!products || products.length === 0) {
            this.renderMessage('Nenhum produto encontrado.');
            return;
        }

        products.forEach((product) => {
            const item = document.createElement('li');

            item.className =
                'p-3 active:bg-blue-50 cursor-pointer flex ' +
                'justify-between items-center gap-3';

            const description = document.createElement('div');
            description.className = 'min-w-0 flex-1';

            const name = document.createElement('p');
            name.className =
                'text-sm font-black text-gray-800 truncate';
            name.textContent = product.name || 'Produto';

            const ean = document.createElement('p');
            ean.className =
                'text-[9px] text-gray-400 font-mono mt-1 truncate';
            ean.textContent = product.ean
                ? `EAN: ${product.ean}`
                : 'EAN não informado';

            description.appendChild(name);
            description.appendChild(ean);

            const sku = document.createElement('span');
            sku.className =
                'text-[9px] font-black font-mono text-[#124191] ' +
                'bg-blue-50 px-2 py-1 rounded';
            sku.textContent = product.id;

            item.appendChild(description);
            item.appendChild(sku);

            item.addEventListener('click', () => {
                this.input.value = product.id;
                this.hideSuggestions();

                /*
                 * Reutiliza o fluxo de consulta já existente
                 * em app.js. O botão chegará ao queryProduct()
                 * através do alias canônico getSku().
                 */
                this.button.click();
            });

            this.suggestions.appendChild(item);
        });

        this.suggestions.classList.remove('hidden');
    }

    renderMessage(message) {
        this.suggestions.innerHTML = '';

        const item = document.createElement('li');

        item.className =
            'p-3 text-xs text-gray-400 text-center font-bold';

        item.textContent = message;

        this.suggestions.appendChild(item);
        this.suggestions.classList.remove('hidden');
    }

    hideSuggestions() {
        if (this.suggestions) {
            this.suggestions.classList.add('hidden');
        }
    }
}


document.addEventListener('DOMContentLoaded', () => {
    const productSearch = new ProductSearchController();
    productSearch.init();
});
