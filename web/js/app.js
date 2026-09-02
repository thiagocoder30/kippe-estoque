import { APIClient } from './api.js';
import { ScannerManager } from './scanner.js';

class KippeApplication {
    constructor() {
        this.api = new APIClient();

        this.currentOperator = null;

        this.scannerTarget = 'search';

        this.scanner = new ScannerManager((decodedText) => {
            if (this.scannerTarget === 'new-product') {
                const newProductInput =
                    document.getElementById(
                        'new-product-ean'
                    );

                const newProductModal =
                    document.getElementById(
                        'new-product-modal'
                    );

                if (newProductInput) {
                    newProductInput.value =
                        decodedText;
                }

                newProductModal?.classList.remove(
                    'hidden'
                );

                this.scannerTarget =
                    'search';

                return;
            }

            if (this.scannerTarget === 'putaway') {
                const putawayInput =
                    document.getElementById('put-ean');

                const putawayModal =
                    document.getElementById(
                        'putaway-modal'
                    );

                if (putawayInput) {
                    putawayInput.value =
                        decodedText;
                }

                putawayModal?.classList.remove(
                    'hidden'
                );

                this.scannerTarget =
                    'search';

                this.loadPutawayProduct(
                    decodedText
                );

                return;
            }

            if (this.scannerTarget === 'receive') {
                const receiveInput =
                    document.getElementById('rec-ean');

                const receiveModal =
                    document.getElementById('receive-modal');

                if (receiveInput) {
                    receiveInput.value = decodedText;
                }

                receiveModal?.classList.remove('hidden');

                this.loadReceivingProduct(
                    decodedText
                );

                this.updateReceivingSummary();

                this.scannerTarget = 'search';
                return;
            }

            const searchInput =
                document.getElementById('searchInput');

            if (searchInput) {
                searchInput.value = decodedText;
            }

            this.fetchAndRenderSku(decodedText);
        });
    }

    async bootstrap() {
        this.bindAuthentication();

        this.checkGlobalFefoAlerts();
        this.bindNavigation();
        this.bindInboundModule();
        this.bindReceivingDetailedControls();
        this.bindPutawayModule();
        this.bindScannerModule();
        this.bindReportsModule();

        await this.restoreOperatorSession();
    }

    bindAuthentication() {
        const submit =
            document.getElementById(
                'auth-submit'
            );

        const operatorId =
            document.getElementById(
                'auth-operator-id'
            );

        const pin =
            document.getElementById(
                'auth-pin'
            );

        const logout =
            document.getElementById(
                'operator-logout-btn'
            );

        const attemptLogin = async () => {
            await this.authenticateOperator();
        };

        submit?.addEventListener(
            'click',
            attemptLogin
        );

        operatorId?.addEventListener(
            'keydown',
            (event) => {
                if (event.key === 'Enter') {
                    pin?.focus();
                }
            }
        );

        pin?.addEventListener(
            'keydown',
            async (event) => {
                if (event.key === 'Enter') {
                    await attemptLogin();
                }
            }
        );

        logout?.addEventListener(
            'click',
            async () => {
                await this.logoutOperator();
            }
        );
    }

    showAuthenticationModal(message = '') {
        const modal =
            document.getElementById(
                'auth-modal'
            );

        const error =
            document.getElementById(
                'auth-error'
            );

        const operatorId =
            document.getElementById(
                'auth-operator-id'
            );

        modal?.classList.remove(
            'hidden'
        );

        if (error) {
            error.textContent =
                message;

            error.classList.toggle(
                'hidden',
                !message
            );
        }

        window.setTimeout(
            () => {
                operatorId?.focus();
            },
            50
        );
    }

    hideAuthenticationModal() {
        document.getElementById(
            'auth-modal'
        )?.classList.add(
            'hidden'
        );

        const error =
            document.getElementById(
                'auth-error'
            );

        if (error) {
            error.textContent = '';
            error.classList.add(
                'hidden'
            );
        }
    }

    renderOperatorIdentity() {
        const operator =
            this.currentOperator || {
                name: 'NÃO AUTENTICADO',
                role: 'SEM SESSÃO',
            };

        const operatorName =
            operator.name;

        const operatorRole =
            operator.role;

        const headerName =
            document.getElementById(
                'header-operator-name'
            );

        const homeName =
            document.getElementById(
                'home-operator-name'
            );

        const homeRole =
            document.getElementById(
                'home-operator-role'
            );

        if (headerName) {
            headerName.textContent =
                operatorName;
        }

        if (homeName) {
            homeName.textContent =
                operatorName;
        }

        if (homeRole) {
            homeRole.textContent =
                operatorRole;
        }
    }

    async restoreOperatorSession() {
        try {
            const session =
                await this.api.getCurrentOperator();

            if (
                session.authenticated &&
                session.operator
            ) {
                this.currentOperator =
                    session.operator;

                this.renderOperatorIdentity();
                this.hideAuthenticationModal();

                return true;
            }

            this.currentOperator = null;
            this.renderOperatorIdentity();

            this.showAuthenticationModal();

            return false;

        } catch (error) {
            console.error(
                '[AUTH SESSION]',
                error
            );

            this.currentOperator = null;
            this.renderOperatorIdentity();

            this.showAuthenticationModal(
                'Não foi possível verificar a sessão do operador.'
            );

            return false;
        }
    }

    async authenticateOperator() {
        const operatorIdInput =
            document.getElementById(
                'auth-operator-id'
            );

        const pinInput =
            document.getElementById(
                'auth-pin'
            );

        const submit =
            document.getElementById(
                'auth-submit'
            );

        const error =
            document.getElementById(
                'auth-error'
            );

        const id =
            operatorIdInput?.value.trim();

        const pin =
            pinInput?.value || '';

        if (!id || !pin) {
            if (error) {
                error.textContent =
                    'Informe operador e PIN.';

                error.classList.remove(
                    'hidden'
                );
            }

            return false;
        }

        if (submit) {
            submit.disabled = true;
            submit.textContent =
                'AUTENTICANDO...';
        }

        if (error) {
            error.textContent = '';
            error.classList.add(
                'hidden'
            );
        }

        try {
            const response =
                await this.api.login(
                    id,
                    pin
                );

            const operator =
                response.operator;

            if (!operator) {
                throw new Error(
                    'Backend não retornou o operador autenticado.'
                );
            }

            this.currentOperator =
                operator;

            this.renderOperatorIdentity();

            if (pinInput) {
                pinInput.value = '';
            }

            this.hideAuthenticationModal();

            return true;

        } catch (authError) {
            console.error(
                '[AUTH LOGIN]',
                authError
            );

            this.currentOperator = null;
            this.renderOperatorIdentity();

            if (pinInput) {
                pinInput.value = '';
                pinInput.focus();
            }

            if (error) {
                error.textContent =
                    authError.message ||
                    'Credenciais inválidas.';

                error.classList.remove(
                    'hidden'
                );
            }

            return false;

        } finally {
            if (submit) {
                submit.disabled = false;
                submit.textContent =
                    'ENTRAR NO WMS';
            }
        }
    }

    async logoutOperator() {
        try {
            await this.api.logout();
        } catch (error) {
            console.warn(
                '[AUTH LOGOUT]',
                error
            );
        }

        this.currentOperator = null;
        this.renderOperatorIdentity();

        const operatorId =
            document.getElementById(
                'auth-operator-id'
            );

        const pin =
            document.getElementById(
                'auth-pin'
            );

        if (operatorId) {
            operatorId.value = '';
        }

        if (pin) {
            pin.value = '';
        }

        this.showAuthenticationModal(
            'Sessão encerrada.'
        );
    }

    bindNavigation() {
        const searchBtn = document.getElementById('searchBtn');
        const searchInput = document.getElementById('searchInput');
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', () => {
                if (searchInput.value.trim()) this.fetchAndRenderSku(searchInput.value.trim());
            });
        }

        const hideAllViews = () => {
            ['home-module-view', 'dashboard-view', 'reports-view'].forEach(id => {
                const el = document.getElementById(id);
                if(el) el.classList.add('hidden');
            });
        };

        const showHome = () => {
            hideAllViews();
            document.getElementById('home-module-view').classList.remove('hidden');
        };

        document.getElementById('btn-back-dashboard')?.addEventListener('click', showHome);
        document.getElementById('btn-back-reports')?.addEventListener('click', showHome);
        document.getElementById('nav-home')?.addEventListener('click', showHome);

        document.getElementById(
            'btn-new-product-registration'
        )?.addEventListener(
            'click',
            async () => {
                await this.openNewProductRegistration(
                    ''
                );
            }
        );
    }

    async openNewProductRegistration(ean) {
        const modal =
            document.getElementById(
                'new-product-modal'
            );

        const form =
            document.getElementById(
                'new-product-form'
            );

        const successPanel =
            document.getElementById(
                'new-product-success-panel'
            );

        const errorPanel =
            document.getElementById(
                'new-product-error'
            );

        const eanInput =
            document.getElementById(
                'new-product-ean'
            );

        const nameInput =
            document.getElementById(
                'new-product-name'
            );

        const unitInput =
            document.getElementById(
                'new-product-unit'
            );

        const categoryInput =
            document.getElementById(
                'new-product-category'
            );

        form?.classList.remove(
            'hidden'
        );

        successPanel?.classList.add(
            'hidden'
        );

        if (errorPanel) {
            errorPanel.textContent = '';

            errorPanel.classList.add(
                'hidden'
            );
        }

        if (eanInput) {
            eanInput.value =
                ean || '';
        }

        if (nameInput) {
            nameInput.value = '';
        }

        if (unitInput) {
            unitInput.value = 'un';
        }

        if (categoryInput) {
            categoryInput.innerHTML =
                '<option value="">SEM CATEGORIA</option>';

            try {
                const categories =
                    await this.api.getCategories();

                categories.forEach(
                    (category) => {
                        const option =
                            document.createElement(
                                'option'
                            );

                        option.value =
                            category.id;

                        option.textContent =
                            category.name;

                        categoryInput.appendChild(
                            option
                        );
                    }
                );

            } catch (error) {
                console.warn(
                    '[PRODUCT REGISTRATION] Falha ao carregar categorias.',
                    error
                );
            }
        }

        modal?.classList.remove(
            'hidden'
        );

        window.setTimeout(
            () => {
                nameInput?.focus();
            },
            50
        );
    }

    async loadReceivingProduct(identifier) {
        const value = (identifier || '').trim();

        const card =
            document.getElementById(
                'receive-product-card'
            );

        const status =
            document.getElementById(
                'receive-product-status'
            );

        const descriptionInput =
            document.getElementById(
                'rec-product-description'
            );

        if (!value) {
            if (card) {
                card.classList.add('hidden');
            }

            if (status) {
                status.textContent = 'NÃO CONSULTADO';
                status.className =
                    'text-[9px] font-black px-2 py-1 rounded-full bg-gray-100 text-gray-500';
            }

            if (descriptionInput) {
                descriptionInput.value = '';
                descriptionInput.placeholder =
                    'AGUARDANDO IDENTIFICAÇÃO';
            }

            this.updateReceivingSummary();
            return;
        }

        try {
            const data =
                await this.api.queryProduct(value);

            if (card) {
                card.classList.remove('hidden');
            }

            if (status) {
                status.textContent = 'CADASTRADO';
                status.className =
                    'text-[9px] font-black px-2 py-1 rounded-full bg-green-100 text-green-700';
            }

            if (descriptionInput) {
                descriptionInput.value =
                    data.name;
            }

            const setText = (id, text) => {
                const element =
                    document.getElementById(id);

                if (element) {
                    element.textContent =
                        text || '—';
                }
            };

            setText(
                'receive-product-name',
                data.name
            );

            setText(
                'receive-product-sku',
                data.id || data.sku
            );

            setText(
                'receive-product-ean',
                data.ean
            );

            setText(
                'receive-product-unit',
                (
                    data.unit_of_measure ||
                    'un'
                ).toUpperCase()
            );

            const unit =
                document.getElementById(
                    'receive-quantity-unit'
                );

            if (unit) {
                unit.textContent =
                    (
                        data.unit_of_measure ||
                        'un'
                    ).toUpperCase();
            }

            this.updateReceivingSummary();

        } catch (error) {
            if (card) {
                card.classList.add('hidden');
            }

            if (descriptionInput) {
                descriptionInput.value = '';
                descriptionInput.placeholder =
                    'PRODUTO NÃO CADASTRADO';
            }

            if (status) {
                status.textContent =
                    error.message ===
                    'PRODUTO_NAO_CADASTRADO'
                        ? 'NÃO CADASTRADO'
                        : 'NÃO ENCONTRADO';

                status.className =
                    'text-[9px] font-black px-2 py-1 rounded-full bg-red-100 text-red-700';
            }

            this.updateReceivingSummary();
        }
    }


    formatDateBR(value, fallback = 'N/A') {
        const normalized =
            String(value ?? '').trim();

        if (!normalized) {
            return fallback;
        }

        /*
         * Datas operacionais continuam canonicamente em ISO
         * YYYY-MM-DD no domínio, API, persistência e ordenação.
         *
         * Esta conversão existe somente para apresentação.
         * Não usamos Date() para evitar qualquer interferência
         * de timezone em datas civis.
         */
        if (!/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
            return normalized;
        }

        const [
            year,
            month,
            day,
        ] = normalized.split('-');

        return `${day}/${month}/${year}`;
    }


    updateReceivingExpirationIntelligence() {
        const expirationInput =
            document.getElementById(
                'rec-expiration'
            );

        const statusElement =
            document.getElementById(
                'receive-expiration-status'
            );

        const daysElement =
            document.getElementById(
                'receive-expiration-days'
            );

        if (
            !expirationInput ||
            !statusElement ||
            !daysElement
        ) {
            return;
        }

        if (!expirationInput.value) {
            statusElement.textContent =
                'AGUARDANDO DATA';

            statusElement.className =
                'text-xs font-black text-gray-500 mt-0.5';

            daysElement.textContent = '—';
            return;
        }

        const expiration =
            new Date(
                expirationInput.value +
                'T00:00:00'
            );

        const today = new Date();

        today.setHours(
            0,
            0,
            0,
            0
        );

        const daysRemaining =
            Math.floor(
                (
                    expiration.getTime() -
                    today.getTime()
                ) /
                86400000
            );

        let status = 'NORMAL';
        let statusClass =
            'text-xs font-black text-green-600 mt-0.5';

        if (daysRemaining < 0) {
            status = 'VENCIDO';
            statusClass =
                'text-xs font-black text-red-700 mt-0.5';
        } else if (daysRemaining <= 7) {
            status = 'CRITICO';
            statusClass =
                'text-xs font-black text-red-600 mt-0.5';
        } else if (daysRemaining <= 30) {
            status = 'ATENCAO';
            statusClass =
                'text-xs font-black text-amber-600 mt-0.5';
        }

        statusElement.textContent = status;
        statusElement.className = statusClass;

        daysElement.textContent =
            daysRemaining === 1
                ? '1 DIA RESTANTE'
                : `${daysRemaining} DIAS RESTANTES`;
    }

    getReceivingEntryMode() {
        return document.getElementById(
            'rec-entry-mode-package'
        )?.checked
            ? 'PACKAGE'
            : 'UNIT';
    }

    calculateReceivingTotalUnits() {
        const mode =
            this.getReceivingEntryMode();

        const unitQuantity =
            parseInt(
                document.getElementById(
                    'rec-qty'
                )?.value,
                10
            ) || 0;

        const unitsPerPackage =
            parseInt(
                document.getElementById(
                    'rec-units-per-package'
                )?.value,
                10
            ) || 0;

        const packageQuantity =
            parseInt(
                document.getElementById(
                    'rec-package-qty'
                )?.value,
                10
            ) || 0;

        let totalUnits = unitQuantity;

        if (mode === 'PACKAGE') {
            totalUnits =
                unitsPerPackage * packageQuantity;
        }

        const totalInput =
            document.getElementById(
                'rec-total-units'
            );

        if (totalInput) {
            totalInput.value =
                Math.max(0, totalUnits);
        }

        const calculation =
            document.getElementById(
                'receive-package-calculation-text'
            );

        if (calculation) {
            calculation.textContent =
                mode === 'PACKAGE' &&
                unitsPerPackage > 0 &&
                packageQuantity > 0
                    ? `${unitsPerPackage} UN × ${packageQuantity} VOLUMES = ${totalUnits} UN`
                    : '—';
        }

        return Math.max(
            0,
            totalUnits
        );
    }

    updateReceivingQuantityMode() {
        const mode =
            this.getReceivingEntryMode();

        const unitFields =
            document.getElementById(
                'rec-unit-fields'
            );

        const packageFields =
            document.getElementById(
                'rec-package-fields'
            );

        if (unitFields) {
            unitFields.classList.toggle(
                'hidden',
                mode !== 'UNIT'
            );
        }

        if (packageFields) {
            packageFields.classList.toggle(
                'hidden',
                mode !== 'PACKAGE'
            );
        }

        this.calculateReceivingTotalUnits();
        this.updateReceivingSummary();
    }

    updateReceivingSummary() {
        const read = (id) =>
            document.getElementById(id)
                ?.value
                ?.trim() || '';

        const text = (id) =>
            document.getElementById(id)
                ?.textContent
                ?.trim() || '';

        const setText = (id, value) => {
            const element =
                document.getElementById(id);

            if (element) {
                element.textContent =
                    value || '—';
            }
        };

        const productDescription =
            read('rec-product-description');

        const productName =
            text('receive-product-name');

        const identifier =
            read('rec-ean');

        const batch =
            read('rec-batch');

        const expiration =
            read('rec-expiration');

        const supplier =
            read('rec-supplier');

        const invoice =
            read('rec-invoice');

        const mode =
            this.getReceivingEntryMode();

        const unitsPerPackage =
            parseInt(
                read('rec-units-per-package'),
                10
            ) || 0;

        const packageQuantity =
            parseInt(
                read('rec-package-qty'),
                10
            ) || 0;

        const quantity =
            this.calculateReceivingTotalUnits();

        const unit =
            text('receive-quantity-unit') ||
            'UN';

        setText(
            'receive-summary-product',
            productDescription ||
            (
                productName !== '—'
                    ? productName
                    : identifier
            )
        );

        setText(
            'receive-summary-batch',
            batch
        );

        setText(
            'receive-summary-expiration',
            this.formatDateBR(
                expiration,
                '—'
            )
        );

        setText(
            'receive-summary-supplier',
            supplier
        );

        setText(
            'receive-summary-invoice',
            invoice
        );

        setText(
            'receive-summary-packaging',
            mode === 'PACKAGE'
                ? (
                    unitsPerPackage > 0 &&
                    packageQuantity > 0
                        ? `${packageQuantity} VOLUMES × ${unitsPerPackage} UN`
                        : 'FARDO / CAIXA'
                )
                : 'UNIDADES'
        );

        setText(
            'receive-summary-quantity',
            `${quantity} ${unit}`
        );

        const button =
            document.getElementById(
                'submit-receive'
            );

        if (button) {
            button.textContent =
                `CONFIRMAR RECEBIMENTO • ${quantity} ${unit}`;
        }
    }


    resetReceivingForm() {
        const setValue = (id, value = '') => {
            const element = document.getElementById(id);

            if (element) {
                element.value = value;
            }
        };

        const setText = (id, value = '') => {
            const element = document.getElementById(id);

            if (element) {
                element.textContent = value;
            }
        };

        const hide = (id) => {
            document.getElementById(id)
                ?.classList.add('hidden');
        };

        /*
         * Estado de negócio.
         *
         * Cada nova operação de recebimento deve começar sem herdar
         * informações da operação anterior.
         */
        setValue('rec-ean');
        setValue('rec-batch');
        setValue('rec-manufacturing');
        setValue('rec-expiration');
        setValue('rec-supplier');
        setValue('rec-invoice');
        setValue('rec-qty');
        setValue('rec-units-per-package');
        setValue('rec-package-qty');

        const origin =
            document.getElementById('rec-origin');

        if (origin) {
            origin.value = 'MANUAL';
        }

        /*
         * Unidade é o modo inicial canônico.
         */
        const unitMode =
            document.getElementById('rec-entry-mode-unit');

        const packageMode =
            document.getElementById('rec-entry-mode-package');

        if (unitMode) {
            unitMode.checked = true;
        }

        if (packageMode) {
            packageMode.checked = false;
        }

        /*
         * Produto anteriormente identificado.
         */
        setValue('rec-product-description');

        setText('receive-product-name');
        setText('receive-product-sku');
        setText('receive-product-ean');
        setText('receive-product-unit');

        hide('receive-product-card');

        /*
         * Feedback da operação anterior nunca pertence à próxima entrada.
         */
        hide('receive-success-panel');

        /*
         * Recalcula todos os estados derivados a partir do formulário
         * agora vazio.
         */
        this.updateReceivingQuantityMode();
        this.updateReceivingExpirationIntelligence();
        this.updateReceivingSummary();
    }

    bindReceivingDetailedControls() {
        const watchIds = [
            'rec-ean',
            'rec-batch',
            'rec-manufacturing',
            'rec-expiration',
            'rec-supplier',
            'rec-invoice',
            'rec-origin',
            'rec-qty',
            'rec-units-per-package',
            'rec-package-qty',
        ];

        watchIds.forEach((id) => {
            const element =
                document.getElementById(id);

            element?.addEventListener(
                'input',
                () => {
                    if (
                        id ===
                        'rec-expiration'
                    ) {
                        this.updateReceivingExpirationIntelligence();
                    }

                    if (
                        id === 'rec-qty' ||
                        id === 'rec-units-per-package' ||
                        id === 'rec-package-qty'
                    ) {
                        this.calculateReceivingTotalUnits();
                    }

                    this.updateReceivingSummary();
                }
            );

            element?.addEventListener(
                'change',
                () => {
                    if (
                        id ===
                        'rec-expiration'
                    ) {
                        this.updateReceivingExpirationIntelligence();
                    }

                    if (
                        id === 'rec-qty' ||
                        id === 'rec-units-per-package' ||
                        id === 'rec-package-qty'
                    ) {
                        this.calculateReceivingTotalUnits();
                    }

                    this.updateReceivingSummary();
                }
            );
        });

        document.getElementById(
            'rec-entry-mode-unit'
        )?.addEventListener(
            'change',
            () => this.updateReceivingQuantityMode()
        );

        document.getElementById(
            'rec-entry-mode-package'
        )?.addEventListener(
            'change',
            () => this.updateReceivingQuantityMode()
        );

        document.getElementById(
            'rec-ean'
        )?.addEventListener(
            'change',
            (event) => {
                this.loadReceivingProduct(
                    event.target.value
                );
            }
        );

        document.getElementById(
            'rec-qty-minus'
        )?.addEventListener(
            'click',
            () => {
                const input =
                    document.getElementById(
                        'rec-qty'
                    );

                if (!input) {
                    return;
                }

                const current =
                    parseInt(
                        input.value,
                        10
                    ) || 1;

                input.value =
                    Math.max(
                        1,
                        current - 1
                    );

                this.calculateReceivingTotalUnits();
                this.updateReceivingSummary();
            }
        );

        document.getElementById(
            'rec-qty-plus'
        )?.addEventListener(
            'click',
            () => {
                const input =
                    document.getElementById(
                        'rec-qty'
                    );

                if (!input) {
                    return;
                }

                const current =
                    parseInt(
                        input.value,
                        10
                    ) || 0;

                input.value =
                    current + 1;

                this.calculateReceivingTotalUnits();
                this.updateReceivingSummary();
            }
        );

        document.getElementById(
            'rec-package-qty-minus'
        )?.addEventListener(
            'click',
            () => {
                const input =
                    document.getElementById(
                        'rec-package-qty'
                    );

                if (!input) {
                    return;
                }

                const current =
                    parseInt(
                        input.value,
                        10
                    ) || 1;

                input.value =
                    Math.max(
                        1,
                        current - 1
                    );

                this.calculateReceivingTotalUnits();
                this.updateReceivingSummary();
            }
        );

        document.getElementById(
            'rec-package-qty-plus'
        )?.addEventListener(
            'click',
            () => {
                const input =
                    document.getElementById(
                        'rec-package-qty'
                    );

                if (!input) {
                    return;
                }

                const current =
                    parseInt(
                        input.value,
                        10
                    ) || 0;

                input.value =
                    current + 1;

                this.calculateReceivingTotalUnits();
                this.updateReceivingSummary();
            }
        );

        this.updateReceivingQuantityMode();
    }


    bindInboundModule() {
        const methodModal = document.getElementById('inbound-method-modal');
        const modalReceive = document.getElementById('receive-modal');
        const newProductModal =
            document.getElementById('new-product-modal');

        document.getElementById(
            'close-new-product-modal'
        )?.addEventListener('click', () => {
            newProductModal?.classList.add('hidden');
        });

        document.getElementById(
            'btn-new-product-scanner'
        )?.addEventListener(
            'click',
            async () => {
                this.scannerTarget =
                    'new-product';

                newProductModal?.classList.add(
                    'hidden'
                );

                try {
                    await this.scanner.start();

                    /*
                     * ScannerManager absorve internamente falhas
                     * de inicialização e retorna para IDLE.
                     *
                     * Portanto, o sucesso operacional precisa ser
                     * confirmado pelo estado SCANNING.
                     */
                    if (
                        this.scanner.status !==
                        'SCANNING'
                    ) {
                        this.scannerTarget =
                            'search';

                        newProductModal?.classList.remove(
                            'hidden'
                        );

                        const errorPanel =
                            document.getElementById(
                                'new-product-error'
                            );

                        if (errorPanel) {
                            errorPanel.textContent =
                                'Não foi possível abrir o scanner.';

                            errorPanel.classList.remove(
                                'hidden'
                            );
                        }

                        return;
                    }

                } catch (error) {
                    this.scannerTarget =
                        'search';

                    newProductModal?.classList.remove(
                        'hidden'
                    );

                    const errorPanel =
                        document.getElementById(
                            'new-product-error'
                        );

                    if (errorPanel) {
                        errorPanel.textContent =
                            'Não foi possível abrir o scanner.';

                        errorPanel.classList.remove(
                            'hidden'
                        );
                    }

                    console.error(
                        '[NEW PRODUCT SCANNER]',
                        error
                    );
                }
            }
        );

        document.getElementById(
            'submit-new-product'
        )?.addEventListener(
            'click',
            async () => {
                const ean =
                    document.getElementById(
                        'new-product-ean'
                    )?.value.trim();

                const name =
                    document.getElementById(
                        'new-product-name'
                    )?.value.trim();

                const categoryId =
                    document.getElementById(
                        'new-product-category'
                    )?.value || null;

                const unit =
                    document.getElementById(
                        'new-product-unit'
                    )?.value || 'un';

                const errorPanel =
                    document.getElementById(
                        'new-product-error'
                    );

                const submitButton =
                    document.getElementById(
                        'submit-new-product'
                    );

                if (!ean || !name) {
                    if (errorPanel) {
                        errorPanel.textContent =
                            'Preencha EAN e descrição.';

                        errorPanel.classList.remove(
                            'hidden'
                        );
                    }

                    return;
                }

                if (errorPanel) {
                    errorPanel.textContent = '';

                    errorPanel.classList.add(
                        'hidden'
                    );
                }

                if (submitButton) {
                    submitButton.disabled = true;

                    submitButton.textContent =
                        'CADASTRANDO...';
                }

                document.getElementById(
                    'loader'
                )?.classList.remove(
                    'hidden'
                );

                try {
                    const response =
                        await this.api.createProduct({
                            name: name,
                            ean: ean,
                            unit_of_measure: unit,
                            category_id: categoryId,
                        });

                    const product =
                        response.product;

                    if (
                        !product ||
                        !product.id
                    ) {
                        throw new Error(
                            'Backend não retornou o SKU gerado.'
                        );
                    }

                    const successName =
                        document.getElementById(
                            'new-product-success-name'
                        );

                    const successSku =
                        document.getElementById(
                            'new-product-success-sku'
                        );

                    const successEan =
                        document.getElementById(
                            'new-product-success-ean'
                        );

                    if (successName) {
                        successName.textContent =
                            product.name ||
                            name;
                    }

                    if (successSku) {
                        successSku.textContent =
                            product.id;
                    }

                    if (successEan) {
                        successEan.textContent =
                            product.ean ||
                            ean;
                    }

                    document.getElementById(
                        'new-product-form'
                    )?.classList.add(
                        'hidden'
                    );

                    document.getElementById(
                        'new-product-success-panel'
                    )?.classList.remove(
                        'hidden'
                    );

                } catch (error) {
                    if (errorPanel) {
                        errorPanel.textContent =
                            'Erro ao cadastrar produto: ' +
                            (
                                error.message ||
                                'Falha no cadastro.'
                            );

                        errorPanel.classList.remove(
                            'hidden'
                        );
                    }

                } finally {
                    document.getElementById(
                        'loader'
                    )?.classList.add(
                        'hidden'
                    );

                    if (submitButton) {
                        submitButton.disabled =
                            false;

                        submitButton.textContent =
                            'CADASTRAR PRODUTO';
                    }
                }
            }
        );

        document.getElementById(
            'continue-new-product-receiving'
        )?.addEventListener(
            'click',
            async () => {
                const ean =
                    document.getElementById(
                        'new-product-ean'
                    )?.value.trim();

                if (!ean) {
                    return;
                }

                const recEan =
                    document.getElementById(
                        'rec-ean'
                    );

                if (recEan) {
                    recEan.value =
                        ean;
                }

                newProductModal?.classList.add(
                    'hidden'
                );

                modalReceive?.classList.remove(
                    'hidden'
                );

                await this.loadReceivingProduct(
                    ean
                );

                this.updateReceivingSummary();
            }
        );

        document.getElementById('btn-module-inbound')?.addEventListener('click', () => methodModal?.classList.remove('hidden'));
        document.getElementById('close-inbound-method')?.addEventListener('click', () => methodModal?.classList.add('hidden'));
        document.getElementById('close-receive-modal')?.addEventListener('click', () => modalReceive?.classList.add('hidden'));

        document.getElementById('btn-inbound-traditional')?.addEventListener('click', () => {
            this.resetReceivingForm();
            methodModal?.classList.add('hidden');
            const searchInput = document.getElementById('searchInput');
            const recEan = document.getElementById('rec-ean');
            if(recEan) recEan.value = searchInput ? searchInput.value.trim() : '';
            const recQty = document.getElementById('rec-qty');
            if(recQty) recQty.value = '';
            modalReceive?.classList.remove('hidden');
        });

        document.getElementById(
            'btn-receive-scanner'
        )?.addEventListener('click', async () => {
            this.scannerTarget = 'receive';

            modalReceive?.classList.add('hidden');

            try {
                await this.scanner.start();
            } catch (error) {
                this.scannerTarget = 'search';

                modalReceive?.classList.remove('hidden');

                alert(
                    'Erro ao abrir scanner: ' +
                    (error.message || 'Falha na câmera.')
                );
            }
        });

        /*
         * Entrada por NF/IA reservada para implementação futura.
         *
         * Não existe extrator OCR canônico conectado ao backend.
         * O botão permanece desabilitado no HTML para impedir
         * movimentações fictícias de estoque.
         */

        const submitReceive = document.getElementById('submit-receive');

        if (submitReceive) {
            submitReceive.addEventListener('click', async () => {
                const sku =
                    document.getElementById('rec-ean')?.value.trim();

                const quantity = parseInt(
                    document.getElementById(
                        'rec-total-units'
                    )?.value,
                    10
                );

                const batchCode =
                    document.getElementById('rec-batch')?.value.trim();

                const expirationDate =
                    document.getElementById('rec-expiration')?.value;

                const supplier =
                    document.getElementById('rec-supplier')?.value.trim();

                const manufacturingDate =
                    document.getElementById(
                        'rec-manufacturing'
                    )?.value || '';

                const invoiceId =
                    document.getElementById(
                        'rec-invoice'
                    )?.value.trim() || '';

                const originDocument =
                    document.getElementById(
                        'rec-origin'
                    )?.value || 'MANUAL';

                if (
                    !sku ||
                    !batchCode ||
                    !expirationDate ||
                    !supplier ||
                    Number.isNaN(quantity) ||
                    quantity <= 0
                ) {
                    alert(
                        'Preencha EAN/SKU, lote, validade, ' +
                        'fornecedor e quantidade.'
                    );
                    return;
                }

                document.getElementById('loader')?.classList.remove('hidden');

                try {
                    const response =
                        await this.api.registerReceive({
                            sku: sku,
                            quantity: quantity,
                            batch_code: batchCode,
                            manufacturing_date: manufacturingDate,
                            expiration_date: expirationDate,
                            supplier: supplier,
                            invoice_id: invoiceId,
                            origin_document: originDocument,
                        });

                    const receiving =
                        response.receiving;

                    document.getElementById(
                        'loader'
                    )?.classList.add('hidden');

                    if (receiving) {
                        const details =
                            document.getElementById(
                                'receive-success-details'
                            );

                        const putaway =
                            document.getElementById(
                                'receive-success-putaway'
                            );

                        if (details) {
                            details.textContent =
                                `${receiving.quantity} UN • ` +
                                `LOTE ${receiving.batch_code}`;
                        }

                        if (putaway) {
                            putaway.textContent =
                                receiving.putaway_status ===
                                'PENDENTE'
                                    ? 'PENDENTE DE ARMAZENAGEM'
                                    : receiving.putaway_status;
                        }

                        document.getElementById(
                            'receive-success-panel'
                        )?.classList.remove('hidden');
                    }

                    this.fetchAndRenderSku(sku);
                } catch (error) {
                    document.getElementById('loader')?.classList.add('hidden');

                    if (
                        error.message ===
                        'PRODUTO_NAO_CADASTRADO'
                    ) {
                        modalReceive?.classList.add('hidden');

                        await this.openNewProductRegistration(
                            sku
                        );

                        return;
                    }

                    alert(
                        'Erro: ' +
                        (error.message || 'Falha no recebimento.')
                    );
                }
            });
        }
    }

    bindPutawayModule() {
        const modalPutaway =
            document.getElementById('putaway-modal');

        const btnPutaway =
            document.getElementById('btn-module-putaway');

        const errorPanel =
            document.getElementById('putaway-error');

        const clearPutawayError = () => {
            if (!errorPanel) {
                return;
            }

            errorPanel.textContent = '';
            errorPanel.classList.add('hidden');
        };

        const showPutawayError = (message) => {
            if (!errorPanel) {
                return;
            }

            errorPanel.textContent = message;
            errorPanel.classList.remove('hidden');
        };

        const resetPutawayIdentification = () => {
            document.getElementById(
                'putaway-product-panel'
            )?.classList.add('hidden');

            document.getElementById(
                'putaway-batch-panel'
            )?.classList.add('hidden');

            const putBatch =
                document.getElementById('put-batch');

            if (putBatch) {
                putBatch.value = '';
            }
        };

        this.loadPutawayProduct =
            async (identifier) => {
                const normalized =
                    String(identifier || '').trim();

                clearPutawayError();
                resetPutawayIdentification();

                if (!normalized) {
                    return;
                }

                try {
                    const data =
                        await this.api.queryProduct(
                            normalized
                        );

                    const putEan =
                        document.getElementById(
                            'put-ean'
                        );

                    /*
                     * Após identificação, normalizamos o campo
                     * para o SKU canônico. O backend de Putaway
                     * trabalha com product_id/SKU.
                     */
                    if (putEan) {
                        putEan.value =
                            data.id ||
                            data.sku ||
                            normalized;
                    }

                    const productPanel =
                        document.getElementById(
                            'putaway-product-panel'
                        );

                    const productName =
                        document.getElementById(
                            'putaway-product-name'
                        );

                    const productSku =
                        document.getElementById(
                            'putaway-product-sku'
                        );

                    const productEan =
                        document.getElementById(
                            'putaway-product-ean'
                        );

                    if (productName) {
                        productName.textContent =
                            data.name ||
                            'PRODUTO SEM DESCRIÇÃO';
                    }

                    if (productSku) {
                        productSku.textContent =
                            data.id ||
                            data.sku ||
                            '—';
                    }

                    if (productEan) {
                        productEan.textContent =
                            data.ean ||
                            'NÃO INFORMADO';
                    }

                    productPanel?.classList.remove(
                        'hidden'
                    );

                    const batches =
                        Array.isArray(data.batches)
                            ? data.batches
                            : [];

                    /*
                     * Um lote é pendente de Putaway quando
                     * ainda não possui localização física.
                     *
                     * A ordenação por expiration_date coloca
                     * primeiro o lote de menor validade.
                     * Isso é prioridade operacional; ainda não
                     * é o motor completo de separação FEFO.
                     */
                    const pendingBatches =
                        batches
                            .filter(
                                (batch) =>
                                    !batch.location_id
                            )
                            .sort(
                                (left, right) =>
                                    String(
                                        left.expiration_date ||
                                        '9999-12-31'
                                    ).localeCompare(
                                        String(
                                            right.expiration_date ||
                                            '9999-12-31'
                                        )
                                    )
                            );

                    if (
                        pendingBatches.length === 0
                    ) {
                        showPutawayError(
                            'Este produto não possui lote ' +
                            'pendente de armazenagem.'
                        );

                        return;
                    }

                    const selectedBatch =
                        pendingBatches[0];

                    const putBatch =
                        document.getElementById(
                            'put-batch'
                        );

                    if (putBatch) {
                        putBatch.value =
                            selectedBatch.code || '';
                    }

                    const batchExpiration =
                        document.getElementById(
                            'putaway-batch-expiration'
                        );

                    const batchQuantity =
                        document.getElementById(
                            'putaway-batch-quantity'
                        );

                    const batchStatus =
                        document.getElementById(
                            'putaway-batch-status'
                        );

                    const pendingCount =
                        document.getElementById(
                            'putaway-pending-count'
                        );

                    if (batchExpiration) {
                        batchExpiration.textContent =
                            this.formatDateBR(
                                selectedBatch.expiration_date,
                                'N/A'
                            );
                    }

                    if (batchQuantity) {
                        batchQuantity.textContent =
                            `${
                                selectedBatch.quantity ?? 0
                            } UN`;
                    }

                    if (batchStatus) {
                        batchStatus.textContent =
                            selectedBatch
                                .expiration_status ||
                            'NORMAL';
                    }

                    if (pendingCount) {
                        pendingCount.textContent =
                            pendingBatches.length === 1
                                ? '1 LOTE PENDENTE'
                                : `${pendingBatches.length} LOTES PENDENTES`;
                    }

                    document.getElementById(
                        'putaway-batch-panel'
                    )?.classList.remove(
                        'hidden'
                    );

                } catch (error) {
                    resetPutawayIdentification();

                    showPutawayError(
                        error.message ||
                        'Produto não encontrado.'
                    );

                    console.error(
                        '[PUTAWAY PRODUCT]',
                        error
                    );
                }
            };

        if (btnPutaway) {
            btnPutaway.addEventListener(
                'click',
                async () => {
                    const searchInput =
                        document.getElementById(
                            'searchInput'
                        );

                    const putEan =
                        document.getElementById(
                            'put-ean'
                        );

                    const putLocation =
                        document.getElementById(
                            'put-location'
                        );

                    const identifier =
                        searchInput
                            ? searchInput.value.trim()
                            : '';

                    if (putEan) {
                        putEan.value =
                            identifier;
                    }

                    if (putLocation) {
                        putLocation.value = '';
                    }

                    clearPutawayError();
                    resetPutawayIdentification();

                    modalPutaway?.classList.remove(
                        'hidden'
                    );

                    if (identifier) {
                        await this.loadPutawayProduct(
                            identifier
                        );
                    }
                }
            );
        }

        document.getElementById(
            'close-putaway-modal'
        )?.addEventListener(
            'click',
            () => {
                modalPutaway?.classList.add(
                    'hidden'
                );
            }
        );

        document.getElementById(
            'put-ean'
        )?.addEventListener(
            'change',
            async (event) => {
                await this.loadPutawayProduct(
                    event.target.value
                );
            }
        );

        document.getElementById(
            'btn-putaway-scanner'
        )?.addEventListener(
            'click',
            async () => {
                clearPutawayError();

                this.scannerTarget =
                    'putaway';

                modalPutaway?.classList.add(
                    'hidden'
                );

                try {
                    await this.scanner.start();

                    /*
                     * ScannerManager absorve internamente
                     * falhas de inicialização. Por isso,
                     * confirmamos explicitamente SCANNING.
                     */
                    if (
                        this.scanner.status !==
                        'SCANNING'
                    ) {
                        this.scannerTarget =
                            'search';

                        modalPutaway?.classList.remove(
                            'hidden'
                        );

                        showPutawayError(
                            'Não foi possível abrir o scanner.'
                        );

                        return;
                    }

                } catch (error) {
                    this.scannerTarget =
                        'search';

                    modalPutaway?.classList.remove(
                        'hidden'
                    );

                    showPutawayError(
                        'Não foi possível abrir o scanner.'
                    );

                    console.error(
                        '[PUTAWAY SCANNER]',
                        error
                    );
                }
            }
        );

        document.getElementById(
            'btn-putaway-success-continue'
        )?.addEventListener(
            'click',
            () => {
                document.getElementById(
                    'putaway-success-modal'
                )?.classList.add(
                    'hidden'
                );
            }
        );

        document.getElementById(
            'submit-putaway'
        )?.addEventListener(
            'click',
            async () => {
                const sku =
                    document.getElementById(
                        'put-ean'
                    )?.value.trim();

                const batchCode =
                    document.getElementById(
                        'put-batch'
                    )?.value.trim();

                const locationId =
                    document.getElementById(
                        'put-location'
                    )?.value.trim();

                clearPutawayError();

                if (
                    !sku ||
                    !batchCode ||
                    !locationId
                ) {
                    showPutawayError(
                        'Informe o produto, o lote e ' +
                        'selecione a localização.'
                    );

                    return;
                }

                document.getElementById(
                    'loader'
                )?.classList.remove(
                    'hidden'
                );

                try {
                    await this.api.registerPutaway({
                        sku: sku,
                        batch_code: batchCode,
                        location_id: locationId,
                    });

                    document.getElementById(
                        'loader'
                    )?.classList.add(
                        'hidden'
                    );

                    modalPutaway?.classList.add(
                        'hidden'
                    );

                    const successModal =
                        document.getElementById(
                            'putaway-success-modal'
                        );

                    const successProduct =
                        document.getElementById(
                            'putaway-success-product'
                        );

                    const successBatch =
                        document.getElementById(
                            'putaway-success-batch'
                        );

                    const successLocation =
                        document.getElementById(
                            'putaway-success-location'
                        );

                    const identifiedProduct =
                        document.getElementById(
                            'putaway-product-name'
                        )?.textContent?.trim();

                    if (successProduct) {
                        successProduct.textContent =
                            identifiedProduct ||
                            sku;
                    }

                    if (successBatch) {
                        successBatch.textContent =
                            batchCode;
                    }

                    if (successLocation) {
                        successLocation.textContent =
                            locationId;
                    }

                    successModal?.classList.remove(
                        'hidden'
                    );

                    this.fetchAndRenderSku(
                        sku
                    );

                } catch (error) {
                    document.getElementById(
                        'loader'
                    )?.classList.add(
                        'hidden'
                    );

                    showPutawayError(
                        error.message ||
                        'Falha no Putaway.'
                    );
                }
            }
        );
    }

    bindReportsModule() {
        const btnReports =
            document.getElementById('btn-module-reports');

        if (btnReports) {
            btnReports.addEventListener('click', async () => {
                document.getElementById('loader')?.classList.remove('hidden');

                try {
                    const data =
                        await this.api.getExpirationReport();

                    document.getElementById('loader')?.classList.add('hidden');

                    document.getElementById(
                        'home-module-view'
                    )?.classList.add('hidden');

                    document.getElementById(
                        'dashboard-view'
                    )?.classList.add('hidden');

                    document.getElementById(
                        'reports-view'
                    )?.classList.remove('hidden');

                    const list =
                        document.getElementById('fefo-list');

                    if (!list) {
                        return;
                    }

                    if (data.length === 0) {
                        list.innerHTML = `
                            <div class="p-4 bg-green-50 text-green-700 rounded-lg text-center font-bold text-[11px] uppercase border border-green-100">
                                NENHUM LOTE ENCONTRADO.
                            </div>
                        `;

                        return;
                    }

                    list.innerHTML = data.map(item => `
                        <div class="p-3 bg-white border rounded-lg shadow-sm flex justify-between items-center">
                            <div>
                                <p class="text-[11px] font-black text-gray-800 uppercase">
                                    ${item.name || item.sku || 'PRODUTO'}
                                </p>

                                <p class="text-[9px] text-gray-500 font-bold uppercase mt-0.5">
                                    VALIDADE: ${this.formatDateBR(item.expiration, 'N/A')}
                                </p>

                                <p class="text-[9px] text-gray-500 font-bold uppercase mt-0.5">
                                    STATUS: ${item.status || 'N/A'}
                                </p>

                                <p class="text-[9px] text-gray-500 font-bold uppercase mt-0.5">
                                    LOCAL: ${item.location_id || 'NÃO ENDEREÇADO'}
                                </p>
                            </div>

                            <div class="text-right">
                                <span class="block bg-gray-50 border text-gray-700 font-black text-[10px] px-2 py-1 rounded">
                                    LOTE: ${item.batch || 'N/A'}
                                </span>

                                <span class="block mt-1 text-[10px] font-black text-[#124191]">
                                    ${item.quantity ?? 0} UN
                                </span>
                            </div>
                        </div>
                    `).join('');
                } catch (error) {
                    document.getElementById('loader')?.classList.add('hidden');

                    alert(
                        'Erro ao carregar relatório de validade: ' +
                        (error.message || 'Falha de comunicação.')
                    );
                }
            });
        }
    }

    bindScannerModule() {
        document.getElementById(
            'close-scanner-btn'
        )?.addEventListener(
            'click',
            () => {
                if (
                    this.scannerTarget ===
                    'new-product'
                ) {
                    document.getElementById(
                        'new-product-modal'
                    )?.classList.remove(
                        'hidden'
                    );

                    this.scannerTarget =
                        'search';

                    return;
                }

                if (
                    this.scannerTarget ===
                    'putaway'
                ) {
                    document.getElementById(
                        'putaway-modal'
                    )?.classList.remove(
                        'hidden'
                    );

                    this.scannerTarget =
                        'search';
                }
            }
        );

        const openScanner = () => {
            this.scannerTarget =
                'search';

            this.scanner.start();
        };

        document.getElementById('btn-module-scan')?.addEventListener(
            'click',
            openScanner
        );

        document.getElementById('nav-scan')?.addEventListener(
            'click',
            openScanner
        );
    }

    async checkGlobalFefoAlerts() {
        try {
            const data =
                await this.api.getExpirationReport();

            const critical = data.filter(item =>
                item.status === 'VENCIDO' ||
                item.status === 'CRITICO' ||
                item.status === 'ATENCAO'
            );

            if (critical.length > 0) {
                const badge =
                    document.getElementById('global-fefo-badge');

                if (badge) {
                    badge.textContent = critical.length;
                    badge.classList.remove('hidden');
                }
            }
        } catch (error) {
            console.warn(
                '[FEFO ALERTS] Não foi possível carregar alertas.',
                error
            );
        }
    }

    async fetchAndRenderSku(identifier) {
        document.getElementById('loader')?.classList.remove('hidden');

        try {
            const data = await this.api.queryProduct(identifier);

            document.getElementById('loader')?.classList.add('hidden');

            ['home-module-view', 'reports-view'].forEach(id => {
                const el = document.getElementById(id);

                if (el) {
                    el.classList.add('hidden');
                }
            });

            document.getElementById('dashboard-view')?.classList.remove('hidden');

            const prodName = document.getElementById('prodName');
            const prodSku = document.getElementById('prodSku');
            const prodEan = document.getElementById('prodEan');
            const stockTotal = document.getElementById('stockTotal');
            const batchesContainer = document.getElementById('product-batches');

            if (prodName) {
                prodName.textContent = data.name || 'PRODUTO SEM DESCRIÇÃO';
            }

            if (prodSku) {
                prodSku.textContent = data.id || identifier;
            }

            if (prodEan) {
                prodEan.textContent = data.ean || 'NÃO INFORMADO';
            }

            if (stockTotal) {
                stockTotal.textContent = data.quantity ?? 0;
            }

            if (batchesContainer) {
                batchesContainer.innerHTML = '';

                const batches = Array.isArray(data.batches)
                    ? data.batches
                    : [];

                if (batches.length === 0) {
                    batchesContainer.innerHTML = `
                        <div class="p-4 bg-gray-50 border border-gray-100 rounded-lg text-center">
                            <p class="text-[10px] font-bold text-gray-400">
                                NENHUM LOTE ATIVO
                            </p>
                        </div>
                    `;
                } else {
                    batches.forEach((batch) => {
                        const card = document.createElement('div');

                        const status = batch.expiration_status || 'NORMAL';

                        const statusClasses = {
                            NORMAL: 'bg-green-100 text-green-700 border-green-200',
                            ATENCAO: 'bg-amber-100 text-amber-800 border-amber-200',
                            CRITICO: 'bg-red-100 text-red-700 border-red-200',
                            VENCIDO: 'bg-red-600 text-white border-red-700',
                        };

                        const statusClass =
                            statusClasses[status] ||
                            statusClasses.NORMAL;

                        const location =
                            batch.location_id ||
                            'NÃO ENDEREÇADO';

                        const daysRemaining =
                            batch.days_remaining ?? 'N/A';

                        card.className =
                            'p-3 rounded-xl border border-gray-100 bg-gray-50';

                        card.innerHTML = `
                            <div class="flex justify-between items-start gap-2">
                                <div class="min-w-0">
                                    <p class="text-[9px] text-gray-400 font-bold">
                                        LOTE
                                    </p>

                                    <p class="text-sm font-black text-gray-800 font-mono">
                                        ${batch.code || 'N/A'}
                                    </p>
                                </div>

                                <span class="text-[9px] font-black px-2 py-1 rounded border ${statusClass}">
                                    ${status}
                                </span>
                            </div>

                            <div class="grid grid-cols-2 gap-2 mt-3 text-[9px]">
                                <div>
                                    <p class="text-gray-400 font-bold">
                                        QUANTIDADE
                                    </p>

                                    <p class="font-black text-gray-800">
                                        ${batch.quantity ?? 0}
                                    </p>
                                </div>

                                <div>
                                    <p class="text-gray-400 font-bold">
                                        LOCALIZAÇÃO
                                    </p>

                                    <p class="font-black text-[#124191]">
                                        ${location}
                                    </p>
                                </div>

                                <div>
                                    <p class="text-gray-400 font-bold">
                                        VALIDADE
                                    </p>

                                    <p class="font-black text-gray-800">
                                        ${this.formatDateBR(batch.expiration_date, 'N/A')}
                                    </p>
                                </div>

                                <div>
                                    <p class="text-gray-400 font-bold">
                                        DIAS RESTANTES
                                    </p>

                                    <p class="font-black text-gray-800">
                                        ${daysRemaining}
                                    </p>
                                </div>
                            </div>
                        `;

                        batchesContainer.appendChild(card);
                    });
                }
            }
        } catch (error) {
            document.getElementById('loader')?.classList.add('hidden');

            alert(
                "❌ PRODUTO NÃO ENCONTRADO.\n\n" +
                "Use o botão '1. RECEBER' para dar entrada."
            );
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new KippeApplication();
    app.bootstrap();
});
