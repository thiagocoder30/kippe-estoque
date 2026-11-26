window.formatBrtDateTime = function(iso) {
    if (!iso) return '-';
    const raw = String(iso).trim();
    if (!raw) return '-';
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
        const [y, m, d] = raw.split('-');
        return `${d}/${m}/${y}`;
    }
    let normalized = raw.replace(' ', 'T');
    if (!/(Z|[+-]\d{2}:?\d{2})$/i.test(normalized)) {
        normalized += 'Z';
    }
    const dt = new Date(normalized);
    if (Number.isNaN(dt.getTime())) {
        return raw.replace('T', ' ').slice(0, 16);
    }
    return new Intl.DateTimeFormat('pt-BR', {
        timeZone: 'America/Sao_Paulo',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    }).format(dt).replace(',', '');
};

import { APIClient } from './api.js';
import { ScannerManager } from './scanner.js';

(function initKippeDialogs() {
    if (window.kippeModalAlert && window.kippeModalConfirm) return;

    function detectTheme(msg) {
        const text = String(msg || '').trim();
        if (text.startsWith('❌') || /erro|falha|inválid|negad|não encontrado/i.test(text.slice(0, 40))) {
            return { bg: '#D9232E', badge: 'ALERTA DO SISTEMA', icon: '✕' };
        }
        if (text.startsWith('✅') || /sucesso|concluíd|atualizado|aprovad/i.test(text.slice(0, 45))) {
            return { bg: '#15803D', badge: 'OPERAÇÃO CONCLUÍDA', icon: '✓' };
        }
        if (text.startsWith('⚠️') || text.startsWith('🚩') || /atenção|duplicidade|diverg/i.test(text.slice(0, 45))) {
            return { bg: '#D97706', badge: 'ATENÇÃO OPERACIONAL', icon: '!' };
        }
        return { bg: '#124191', badge: 'KIPPE WMS', icon: 'i' };
    }

    function stripLeadingEmoji(msg) {
        return String(msg || '').replace(/^(?:❌|✅|⚠️|🚩)\s*/u, '').trim();
    }

    function buildDialog({ message, title, confirmMode = false, confirmLabel = 'CONFIRMAR', cancelLabel = 'CANCELAR' }) {
        return new Promise((resolve) => {
            document.getElementById('kippe-system-dialog')?.remove();
            const theme = detectTheme(message);
            const cleanBody = stripLeadingEmoji(message);

            const overlay = document.createElement('div');
            overlay.id = 'kippe-system-dialog';
            overlay.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(15,23,42,0.72);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:16px;';

            const card = document.createElement('div');
            card.style.cssText = 'width:100%;max-width:360px;background:#FFFFFF;border-radius:16px;overflow:hidden;box-shadow:0 20px 40px rgba(15,23,42,0.35);border:1px solid #E2E8F0;animation:fadeIn .14s ease-out;';

            const header = document.createElement('div');
            header.style.cssText = `background:${theme.bg};color:#FFFFFF;padding:12px 16px;display:flex;align-items:center;gap:10px;`;
            header.innerHTML = `
                <span style="width:24px;height:24px;border-radius:999px;background:rgba(255,255,255,0.2);display:inline-flex;align-items:center;justify-content:center;font-weight:900;font-size:12px;flex-shrink:0;">${theme.icon}</span>
                <span style="font-size:11px;font-weight:900;letter-spacing:0.06em;text-transform:uppercase;">${title || theme.badge}</span>
            `;

            const body = document.createElement('div');
            body.style.cssText = 'padding:18px 16px;color:#1E293B;font-size:13px;font-weight:700;line-height:1.45;white-space:pre-line;word-break:break-word;';
            body.textContent = cleanBody;

            const footer = document.createElement('div');
            footer.style.cssText = 'padding:12px 16px;background:#F8FAFC;border-top:1px solid #E2E8F0;display:flex;gap:8px;';

            const closeWith = (val) => {
                overlay.remove();
                resolve(val);
            };

            if (confirmMode) {
                const cancelBtn = document.createElement('button');
                cancelBtn.type = 'button';
                cancelBtn.textContent = cancelLabel;
                cancelBtn.style.cssText = 'flex:1;padding:11px 12px;border-radius:10px;border:1px solid #CBD5E1;background:#FFFFFF;color:#475569;font-size:11px;font-weight:900;letter-spacing:0.04em;text-transform:uppercase;cursor:pointer;';
                cancelBtn.addEventListener('click', () => closeWith(false));
                footer.appendChild(cancelBtn);
            }

            const okBtn = document.createElement('button');
            okBtn.type = 'button';
            okBtn.textContent = confirmMode ? confirmLabel : 'ENTENDI';
            okBtn.style.cssText = `flex:1;padding:11px 12px;border-radius:10px;border:none;background:${theme.bg};color:#FFFFFF;font-size:11px;font-weight:900;letter-spacing:0.04em;text-transform:uppercase;box-shadow:0 2px 6px rgba(15,23,42,0.18);cursor:pointer;`;
            okBtn.addEventListener('click', () => closeWith(true));
            footer.appendChild(okBtn);

            card.appendChild(header);
            card.appendChild(body);
            card.appendChild(footer);
            overlay.appendChild(card);
            document.body.appendChild(overlay);
            okBtn.focus();
        });
    }

    window.kippeModalAlert = (message, title) => buildDialog({ message, title, confirmMode: false });
    window.kippeModalConfirm = (message, title, confirmLabel = 'CONFIRMAR', cancelLabel = 'CANCELAR') =>
        buildDialog({ message, title, confirmMode: true, confirmLabel, cancelLabel });
})();

class KippeApplication {
    constructor() {
        this.api = new APIClient();

        this.currentOperator = null;

        /*
         * STOCK-ONBOARDING-001C
         *
         * Produto-alvo da implantação física e
         * último produto carregado no cartão operacional.
         */
        this.existingStockProduct = null;
        this.currentCatalogProduct = null;

        /*
         * RECEIVING-UX-002
         *
         * Mantém somente o resultado do recebimento corrente
         * enquanto o operador decide entre endereçar agora
         * ou deixar o lote pendente.
         */
        this.lastReceivingResult = null;
        this.assistedPutaway = false;
        this.preferredBatchCode = null;

        /*
         * NF-001J.10
         *
         * Estado efêmero da conferência fiscal.
         * Nenhum destes objetos possui autoridade de estoque.
         */
        this.certifiedInvoicePayload = null;
        this.certifiedInvoicePreview = null;
        this.certifiedConferenceCounts = {};
        this.certifiedPhysicalData = {};
        this.certifiedReceivingSubmitting = false;

        /*
         * REPLENISHMENT-UX-001
         *
         * Carrinho = intenção.
         * Plano de coleta = recomendação.
         * Confirmação física = mutação.
         */
        this.replenishmentCart = [];
        this.replenishmentProduct = null;
        this.replenishmentPickSteps = [];
        this.replenishmentPickIndex = 0;
        this.replenishmentCompletion = [];

        this.scannerTarget = 'search';

        this.scanner = new ScannerManager((decodedText) => {
            if (this.scannerTarget === 'conference') {
                this.scannerTarget = 'search';
                if (window.ConferenceFeature && typeof window.ConferenceFeature.scan === 'function') {
                    window.ConferenceFeature.scan(decodedText);
                }
                return;
            }

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

            if (this.scannerTarget === 'replenishment') {
                const replenishmentInput =
                    document.getElementById(
                        'replenishment-product-input'
                    );

                if (replenishmentInput) {
                    replenishmentInput.value =
                        decodedText;
                }

                document.getElementById(
                    'replenishment-view'
                )?.classList.remove(
                    'hidden'
                );

                this.scannerTarget =
                    'search';

                this.loadReplenishmentProduct(
                    decodedText
                );

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
        this.bindExistingStockOnboarding();
        this.bindInboundModule();
        this.bindCertifiedInvoiceReceiving();
        this.bindReceivingDetailedControls();
        this.bindPutawayModule();
        this.bindReplenishmentModule();
        this.bindScannerModule();
        this.initReceivingAuditModule();
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

        if (modal) {
            modal.style.zIndex = '9995';
            modal.classList.remove('hidden');
        }

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
                this.updateExistingStockActionVisibility();

                this.renderOperatorIdentity();
                this.hideAuthenticationModal();

                return true;
            }

            this.currentOperator = null;
            this.updateExistingStockActionVisibility();
            this.renderOperatorIdentity();

            this.showAuthenticationModal();

            return false;

        } catch (error) {
            console.error(
                '[AUTH SESSION]',
                error
            );

            this.currentOperator = null;
            this.updateExistingStockActionVisibility();
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
            this.updateExistingStockActionVisibility();

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
            this.updateExistingStockActionVisibility();
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
        this.updateExistingStockActionVisibility();
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
            document.querySelectorAll('main > section[id$="-view"]').forEach(el => el.classList.add('hidden'));
            [
                'home-module-view',
                'dashboard-view',
                'reports-view',
                'replenishment-view',
                'conference-view',
                'validity-view',
            ].forEach(id => {
                const el = document.getElementById(id);
                if(el) el.classList.add('hidden');
            });
        };

        const showHome = () => {
            hideAllViews();
            document.getElementById('home-module-view')?.classList.remove('hidden');
            window.scrollTo(0, 0);
            if (this.currentOperator?.id && typeof this.refreshEstoquistaPendingQueue === 'function') {
                this.refreshEstoquistaPendingQueue();
            }
        };
        window.showHome = showHome;

        document.getElementById('btn-back-dashboard')?.addEventListener('click', showHome);
        document.getElementById('btn-back-reports')?.addEventListener('click', showHome);
        document.getElementById('btn-back-replenishment')?.addEventListener('click', showHome);
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

    async refreshEstoquistaPendingQueue() {
        const isEstoquista = this.canManageCatalog();
        try {
            const [res, divRes] = await Promise.all([
                isEstoquista
                    ? fetch('/api/receiving/pending', { credentials: 'same-origin' })
                    : Promise.resolve(null),
                fetch('/api/receiving/divergences/pending', { credentials: 'same-origin' }).catch(() => null),
            ]);
            if (isEstoquista && (!res || !res.ok)) return;
            const data = (isEstoquista && res)
                ? await res.json()
                : { pending_conferences_count: 0, pending_products_count: 0, conferences: [], product_requests: [] };
            const divData = (divRes && divRes.ok) ? await divRes.json().catch(() => ({})) : {};
            const canhotoGroups = Array.isArray(divData.pending) ? divData.pending : [];
            const pendingCanhotosCount = Number(divData.total_nfs || canhotoGroups.length || 0);
            data.canhotos_retidos = canhotoGroups;
            data.pending_canhotos_count = pendingCanhotosCount;

            const totalPending = isEstoquista
                ? ((data.pending_conferences_count || 0) + (data.pending_products_count || 0) + pendingCanhotosCount)
                : pendingCanhotosCount;

            let card = document.getElementById('estoquista-pending-card');
            const homeView = document.getElementById('home-module-view');
            if (!homeView) return;

            if (totalPending === 0) {
                card?.remove();
                return;
            }

            if (!card) {
                card = document.createElement('div');
                card.id = 'estoquista-pending-card';
                card.style.cssText = isEstoquista
                    ? 'background:#FFFBEB;border:2px solid #F59E0B;border-radius:14px;padding:12px 14px;box-shadow:0 2px 6px rgba(245,158,11,0.15);display:flex;align-items:center;justify-content:space-between;gap:10px;'
                    : 'background:#FFF7ED;border:2px solid #F97316;border-radius:14px;padding:12px 14px;box-shadow:0 2px 6px rgba(234,88,12,0.15);display:flex;align-items:center;justify-content:space-between;gap:10px;';
                homeView.insertBefore(card, homeView.children[1] || null);
            }

            if (isEstoquista) {
                const canhotoTag = pendingCanhotosCount > 0 ? ` · ${pendingCanhotosCount} canhoto(s) retido(s)` : '';
                card.innerHTML = `
                    <div>
                        <span class="inline-block bg-amber-500 text-white text-[9px] font-black px-2 py-0.5 rounded uppercase tracking-wider">
                            PENDÊNCIAS DO ESTOQUISTA
                        </span>
                        <p class="text-xs font-black text-gray-800 mt-1">
                            ${data.pending_conferences_count || 0} conferência(s) · ${data.pending_products_count || 0} produto(s) novo(s)${canhotoTag}
                        </p>
                        <p class="text-[10px] text-gray-600">Aguardando cadastro, armazenagem ou complemento</p>
                    </div>
                    <button type="button" id="btn-open-estoquista-queue"
                        class="bg-[#124191] text-white text-[10px] font-black uppercase px-3 py-2.5 rounded-lg shadow active:scale-95 shrink-0">
                        REVISAR
                    </button>
                `;
            } else {
                card.innerHTML = `
                    <div>
                        <span style="display:inline-block;background:#EA580C;color:#FFFFFF;font-size:9px;font-weight:900;padding:2px 7px;border-radius:5px;text-transform:uppercase;letter-spacing:0.04em;">
                            📌 CANHOTOS RETIDOS NA DOCA
                        </span>
                        <p class="text-xs font-black text-gray-800 mt-1">
                            ${pendingCanhotosCount} canhoto(s) retido(s) aguardando complemento
                        </p>
                        <p class="text-[10px] text-gray-600">Conferir entrega faltante e liberar canhoto</p>
                    </div>
                    <button type="button" id="btn-open-estoquista-queue"
                        style="background:#EA580C;color:#FFFFFF;font-size:10px;font-weight:900;text-transform:uppercase;padding:10px 12px;border-radius:9px;border:none;flex-shrink:0;cursor:pointer;">
                        CONFERIR
                    </button>
                `;
            }

            document.getElementById('btn-open-estoquista-queue')?.addEventListener('click', () => {
                this.openEstoquistaQueueModal(data);
            });
        } catch { /* ignora falha silenciosa */ }
    }

    openEstoquistaQueueModal(data) {
        document.getElementById('estoquista-queue-modal')?.remove();
        const modal = document.createElement('div');
        modal.id = 'estoquista-queue-modal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:9990;background:rgba(15,23,42,0.78);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:12px;box-sizing:border-box;';

        const reqList = data.product_requests || [];
        const confList = data.conferences || [];
        const canhotoList = data.canhotos_retidos || [];

        const escSafe = (s) => String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');

        const canhotoHtml = canhotoList.map(grp => `
            <div style="border:1.5px solid #FDBA74;background:#FFF7ED;border-radius:12px;padding:11px;display:flex;flex-direction:column;gap:8px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;padding-bottom:6px;border-bottom:1px solid #FED7AA;">
                    <div style="min-width:0;flex:1;">
                        <span style="display:inline-block;background:#EA580C;color:#FFFFFF;font-size:8.5px;font-weight:900;padding:2px 7px;border-radius:5px;text-transform:uppercase;">
                            CANHOTO RETIDO · NF ${escSafe(grp.invoice_number || 'S/N')}
                        </span>
                        <p style="font-size:11px;font-weight:900;color:#0F172A;text-transform:uppercase;margin:4px 0 0;line-height:1.3;word-break:break-word;">
                            ${escSafe(grp.supplier || 'FORNECEDOR')}
                        </p>
                    </div>
                    <span style="font-size:9px;font-weight:900;color:#9A3412;background:#FFEDD5;border:1px solid #FDBA74;padding:3px 7px;border-radius:6px;white-space:nowrap;flex-shrink:0;">
                        FALTA: ${Number(grp.total_pending || 0)}
                    </span>
                </div>
                <div style="display:flex;flex-direction:column;gap:6px;">
                    ${(grp.items || []).map(it => `
                        <div style="background:#FFFFFF;border:1px solid #FED7AA;border-radius:9px;padding:9px;display:flex;flex-direction:column;gap:6px;">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px;">
                                <div style="min-width:0;flex:1;">
                                    <p style="font-size:11px;font-weight:900;color:#1E293B;margin:0;line-height:1.25;text-transform:uppercase;word-break:break-word;">
                                        ${escSafe(it.product_name || it.sku)}
                                    </p>
                                    <p style="font-size:9.5px;font-weight:700;color:#64748B;margin:2px 0 0;">
                                        SKU: <strong>${escSafe(it.sku)}</strong> · NF: ${Number(it.expected_qty || 0)} · Rec: ${Number(it.counted_qty || 0)} · <span style="color:#C2410C;font-weight:900;">Falta: ${Number(it.pending_qty || 0)}</span>
                                    </p>
                                </div>
                            </div>
                            <button type="button"
                                data-comp-open="${it.divergence_id}"
                                data-comp-sku="${escSafe(it.sku)}"
                                data-comp-name="${escSafe(it.product_name || it.sku)}"
                                data-comp-nf="${escSafe(grp.invoice_number || 'S/N')}"
                                data-comp-supplier="${escSafe(grp.supplier || '')}"
                                data-comp-pending="${Number(it.pending_qty || 0)}"
                                style="width:100%;background:#EA580C;color:#FFFFFF;border:none;border-radius:8px;padding:9px 10px;font-size:10px;font-weight:900;text-transform:uppercase;cursor:pointer;">
                                📦 RECEBER COMPLEMENTO (SALDO: ${Number(it.pending_qty || 0)})
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('') || '<div style="background:#F8FAFC;border:1px dashed #CBD5E1;border-radius:10px;padding:12px;text-align:center;font-size:11px;font-weight:700;color:#64748B;">Nenhum canhoto retido pendente.</div>';

        const prodHtml = reqList.map(pr => `
            <div style="border:1px solid #FDE68A;background:#FFFBEB;border-radius:12px;padding:11px;display:flex;flex-direction:column;gap:8px;">
                <div>
                    <span style="display:inline-block;background:#FEF3C7;color:#92400E;border:1px solid #FCD34D;font-size:8.5px;font-weight:900;text-transform:uppercase;padding:2px 6px;border-radius:5px;">
                        SOLICITADO POR ${pr.requested_by_name}
                    </span>
                    <p style="font-size:12px;font-weight:900;color:#0F172A;text-transform:uppercase;margin:5px 0 2px;line-height:1.3;word-break:break-word;">
                        ${pr.raw_description}
                    </p>
                    <p style="font-size:10px;font-weight:700;color:#475569;margin:0;line-height:1.35;">
                        NF: <strong>${pr.invoice_number || '-'}</strong> · ${pr.supplier || '-'} · Qtd: <strong>${pr.nf_qty} × ${pr.pack_factor} UN</strong>
                    </p>
                </div>
                <div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;">
                    <button type="button" data-pr-register="${pr.id}" data-pr-ean="${pr.suggested_ean || ''}" data-pr-desc="${pr.raw_description}"
                        style="background:#124191;color:#FFFFFF;border:none;border-radius:8px;padding:9px 10px;font-size:10px;font-weight:900;text-transform:uppercase;cursor:pointer;">
                        + CADASTRAR PRODUTO
                    </button>
                    <button type="button" data-pr-discard="${pr.id}"
                        style="background:#FFFFFF;color:#475569;border:1px solid #CBD5E1;border-radius:8px;padding:9px 12px;font-size:10px;font-weight:800;text-transform:uppercase;cursor:pointer;">
                        DESCARTAR
                    </button>
                </div>
            </div>
        `).join('') || '<div style="background:#F8FAFC;border:1px dashed #CBD5E1;border-radius:10px;padding:12px;text-align:center;font-size:11px;font-weight:700;color:#64748B;">Nenhum produto novo pendente.</div>';

        const confHtml = confList.map(cf => `
            <div style="border:1.5px solid #93C5FD;background:#EFF6FF;border-radius:12px;padding:11px;display:flex;flex-direction:column;gap:10px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;padding-bottom:8px;border-bottom:1px solid #DBEAFE;">
                    <div style="min-width:0;flex:1;">
                        <span style="display:inline-block;background:#124191;color:#FFFFFF;font-size:9px;font-weight:900;padding:2px 7px;border-radius:5px;text-transform:uppercase;">
                            NF ${cf.invoice_number || 'S/N'}
                        </span>
                        <p style="font-size:11px;font-weight:900;color:#0F172A;text-transform:uppercase;margin:4px 0 0;line-height:1.3;word-break:break-word;">
                            ${cf.supplier}
                        </p>
                    </div>
                    <span style="font-size:9px;font-weight:800;color:#334155;background:#FFFFFF;border:1px solid #CBD5E1;padding:3px 7px;border-radius:6px;white-space:nowrap;flex-shrink:0;">
                        Por ${cf.submitted_by_name}
                    </span>
                </div>

                <div style="display:flex;flex-direction:column;gap:8px;">
                    ${(cf.items || []).map((it, idx) => {
                        const curSku = String(it.sku || '').trim().toUpperCase();
                        const hasValidSku = Boolean(curSku && !curSku.startsWith('TEMP-'));
                        const safeDescAttr = String(it.name || it.sku || '').replace(/"/g, '&quot;');
                        const safeEanAttr = String(it.ean || '').replace(/"/g, '&quot;');
                        const badgeBg = hasValidSku ? '#DCFCE7' : '#FEF3C7';
                        const badgeColor = hasValidSku ? '#166534' : '#92400E';
                        const badgeBorder = hasValidSku ? '#86EFAC' : '#FCD34D';
                        const badgeText = hasValidSku ? ('\u2713 SKU: ' + curSku) : '\u26a0 SEM V\u00cdNCULO NO CAT\u00c1LOGO';
                        const linkBtnBg = hasValidSku ? '#F1F5F9' : '#059669';
                        const linkBtnColor = hasValidSku ? '#334155' : '#FFFFFF';
                        const linkBtnBorder = hasValidSku ? '1px solid #CBD5E1' : 'none';
                        const linkBtnLabel = hasValidSku ? 'TROCAR SKU' : 'VINCULAR PRODUTO';
                        return `
                        <div style="background:#FFFFFF;border:1px solid #DBEAFE;border-radius:10px;padding:10px;display:flex;flex-direction:column;gap:8px;">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
                                <p style="font-size:11px;font-weight:900;color:#1E293B;margin:0;line-height:1.3;flex:1;min-width:0;word-break:break-word;text-transform:uppercase;">
                                    ${it.name || it.sku}
                                </p>
                                <span style="flex-shrink:0;background:#DBEAFE;color:#124191;font-size:10px;font-weight:900;padding:2px 7px;border-radius:6px;white-space:nowrap;">
                                    ${it.quantity || it.scanned || 0} UN
                                </span>
                            </div>
                            <div data-cf-sku-bar="${cf.id}:${idx}" style="display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap;">
                                <span data-cf-sku-badge style="display:inline-block;background:${badgeBg};color:${badgeColor};border:1px solid ${badgeBorder};font-size:9px;font-weight:900;padding:3px 7px;border-radius:6px;text-transform:uppercase;line-height:1.25;">
                                    ${badgeText}
                                </span>
                                <button type="button" data-cf-link-sku="${cf.id}:${idx}" data-cf-item-desc="${safeDescAttr}" data-cf-item-ean="${safeEanAttr}"
                                    style="background:${linkBtnBg};color:${linkBtnColor};border:${linkBtnBorder};border-radius:6px;padding:4px 8px;font-size:9px;font-weight:900;text-transform:uppercase;cursor:pointer;white-space:nowrap;">
                                    ${linkBtnLabel}
                                </button>
                            </div>
                            <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:8px;">
                                <div style="min-width:0;">
                                    <label style="display:block;font-size:8.5px;font-weight:900;color:#64748B;text-transform:uppercase;margin-bottom:3px;">LOTE (OPC.)</label>
                                    <input type="text" data-cf-batch="${cf.id}:${idx}" value="${it.batch_code || ''}" placeholder="EX: L123"
                                        style="width:100%;height:36px;box-sizing:border-box;background:#F8FAFC;border:1px solid #CBD5E1;border-radius:7px;padding:0 9px;font-size:11px;font-weight:800;text-transform:uppercase;color:#0F172A;outline:none;">
                                </div>
                                <div style="min-width:0;">
                                    <label style="display:block;font-size:8.5px;font-weight:900;color:#64748B;text-transform:uppercase;margin-bottom:3px;">VALIDADE</label>
                                    <input type="date" data-cf-exp="${cf.id}:${idx}" value="${it.expiration_date || ''}"
                                        style="width:100%;height:36px;box-sizing:border-box;background:#F8FAFC;border:1px solid #CBD5E1;border-radius:7px;padding:0 8px;font-size:11px;font-weight:800;color:#0F172A;outline:none;">
                                </div>
                            </div>
                        </div>
                    `;
                    }).join('')}
                </div>

                <div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;padding-top:2px;">
                    <button type="button" data-cf-approve="${cf.id}"
                        style="background:#16A34A;color:#FFFFFF;border:none;border-radius:9px;padding:11px 12px;font-size:10px;font-weight:900;text-transform:uppercase;box-shadow:0 2px 4px rgba(22,163,74,0.25);cursor:pointer;">
                        ✅ APROVAR & ARMAZENAR
                    </button>
                    <button type="button" data-cf-reject="${cf.id}"
                        style="background:#FFFFFF;color:#DC2626;border:1px solid #FECACA;border-radius:9px;padding:11px 12px;font-size:10px;font-weight:900;text-transform:uppercase;cursor:pointer;">
                        REJEITAR
                    </button>
                </div>
            </div>
        `).join('') || '<div style="background:#F8FAFC;border:1px dashed #CBD5E1;border-radius:10px;padding:12px;text-align:center;font-size:11px;font-weight:700;color:#64748B;">Nenhuma conferência aguardando armazenagem.</div>';

        const isEstoquistaModal = this.canManageCatalog();
        const modalHeaderBg = isEstoquistaModal ? '#124191' : '#EA580C';
        const modalTitleText = isEstoquistaModal ? 'Fila do Estoquista / Armazenagem' : 'Canhotos Retidos / Complementos';
        const modalSubText = isEstoquistaModal ? 'Cadastros solicitados e entradas conferidas' : 'Conferência de saldo faltante na doca';
        const sectionTitleCanhoto = isEstoquistaModal
            ? `3. Canhotos Retidos / Complementos (${canhotoList.length})`
            : `Canhotos Retidos Aguardando Entrega (${canhotoList.length})`;

        modal.innerHTML = `
            <div style="background:#FFFFFF;border-radius:16px;box-shadow:0 24px 48px rgba(15,23,42,0.4);width:100%;max-width:440px;max-height:88dvh;display:flex;flex-direction:column;overflow:hidden;border:1px solid #E2E8F0;">
                <div style="background:${modalHeaderBg};color:#FFFFFF;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-shrink:0;">
                    <div style="min-width:0;">
                        <h3 style="font-size:13px;font-weight:900;text-transform:uppercase;margin:0;letter-spacing:0.03em;">${modalTitleText}</h3>
                        <p style="font-size:10px;color:rgba(255,255,255,0.85);margin:2px 0 0;">${modalSubText}</p>
                    </div>
                    <button type="button" id="close-estoquista-queue"
                        style="width:32px;height:32px;border-radius:8px;border:1px solid rgba(255,255,255,0.25);background:rgba(255,255,255,0.12);color:#FFFFFF;font-size:15px;font-weight:900;display:flex;align-items:center;justify-content:center;flex-shrink:0;cursor:pointer;">
                        ✕
                    </button>
                </div>

                <div style="padding:14px;overflow-y:auto;flex:1;min-height:0;display:flex;flex-direction:column;gap:16px;-webkit-overflow-scrolling:touch;">
                    ${isEstoquistaModal ? `
                    <div style="display:flex;flex-direction:column;gap:8px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <h4 style="font-size:10px;font-weight:900;text-transform:uppercase;color:#475569;margin:0;letter-spacing:0.04em;">
                                1. Produtos Novos Solicitados (${reqList.length})
                            </h4>
                        </div>
                        <div style="display:flex;flex-direction:column;gap:8px;">${prodHtml}</div>
                    </div>

                    <div style="display:flex;flex-direction:column;gap:8px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <h4 style="font-size:10px;font-weight:900;text-transform:uppercase;color:#475569;margin:0;letter-spacing:0.04em;">
                                2. Conferências para Dar Entrada (${confList.length})
                            </h4>
                        </div>
                        <div style="display:flex;flex-direction:column;gap:10px;">${confHtml}</div>
                    </div>
                    ` : ''}

                    <div style="display:flex;flex-direction:column;gap:8px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <h4 style="font-size:10px;font-weight:900;text-transform:uppercase;color:#9A3412;margin:0;letter-spacing:0.04em;">
                                ${sectionTitleCanhoto}
                            </h4>
                        </div>
                        <div style="display:flex;flex-direction:column;gap:10px;">${canhotoHtml}</div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        document.getElementById('close-estoquista-queue')?.addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        const openLinkExistingModal = (reqId, sugEan, rawDesc, onPickedCallback = null) => {
            document.getElementById('kippe-link-existing-modal')?.remove();

            const escHtml = (str) => String(str || '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');

            const overlay = document.createElement('div');
            overlay.id = 'kippe-link-existing-modal';
            overlay.style.cssText = [
                'position:fixed;inset:0;background:rgba(15,23,42,0.72);',
                'backdrop-filter:blur(2px);z-index:10050;display:flex;',
                'align-items:center;justify-content:center;padding:16px;'
            ].join('');

            const cardStyle = [
                'width:100%;max-width:420px;background:#FFFFFF;border-radius:18px;',
                'overflow:hidden;box-shadow:0 20px 40px rgba(15,23,42,0.35);',
                'border:1px solid #E2E8F0;display:flex;flex-direction:column;',
                'max-height:85vh;text-transform:uppercase;'
            ].join('');

            const hdrStyle = [
                'background:#124191;color:#FFFFFF;padding:14px 16px;display:flex;',
                'align-items:center;justify-content:space-between;gap:10px;'
            ].join('');

            const closeBtnStyle = [
                'width:32px;height:32px;border-radius:8px;',
                'border:1px solid rgba(255,255,255,0.25);',
                'background:rgba(255,255,255,0.12);color:#FFFFFF;',
                'font-size:15px;font-weight:900;display:flex;',
                'align-items:center;justify-content:center;flex-shrink:0;cursor:pointer;'
            ].join('');

            const bodyStyle = [
                'padding:14px;display:flex;flex-direction:column;gap:12px;',
                'overflow-y:auto;-webkit-overflow-scrolling:touch;'
            ].join('');

            const inpStyle = [
                'width:100%;box-sizing:border-box;background:#F8FAFC;',
                'border:1.5px solid #CBD5E1;border-radius:10px;padding:10px 12px;',
                'font-size:13px;font-weight:900;color:#0F172A;',
                'text-transform:uppercase;outline:none;'
            ].join('');

            const cancelBtnStyle = [
                'height:40px;background:#F1F5F9;color:#475569;',
                'border:1px solid #CBD5E1;border-radius:10px;',
                'font-size:11px;font-weight:900;text-transform:uppercase;cursor:pointer;'
            ].join('');

            const confirmBtnStyle = [
                'height:40px;background:#059669;color:#FFFFFF;border:none;',
                'border-radius:10px;font-size:11px;font-weight:900;',
                'text-transform:uppercase;letter-spacing:0.03em;',
                'box-shadow:0 2px 6px rgba(5,150,105,0.25);cursor:pointer;'
            ].join('');

            const initVal = escHtml(String(sugEan || '').toUpperCase());
            const itemTitle = escHtml(String(rawDesc || '').toUpperCase());

            overlay.innerHTML = `
                <div style="${cardStyle}">
                    <div style="${hdrStyle}">
                        <div style="min-width:0;">
                            <h3 style="font-size:13px;font-weight:900;margin:0;letter-spacing:0.03em;">
                                VINCULAR PRODUTO EXISTENTE
                            </h3>
                            <p style="font-size:10px;color:#BFDBFE;margin:2px 0 0;">
                                DE-PARA NO CAT\u00c1LOGO SEM DUPLICAR SKU
                            </p>
                        </div>
                        <button type="button" id="close-link-existing-modal" style="${closeBtnStyle}">
                            \u2715
                        </button>
                    </div>

                    <div style="${bodyStyle}">
                        <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:12px;padding:10px 12px;">
                            <span style="display:inline-block;background:#F59E0B;color:#FFFFFF;font-size:9px;font-weight:900;padding:2px 6px;border-radius:4px;">
                                ITEM SOLICITADO NA NF
                            </span>
                            <p style="font-size:12px;font-weight:900;color:#1E293B;margin:5px 0 0;line-height:1.3;">
                                ${itemTitle}
                            </p>
                        </div>

                        <div>
                            <label for="kippe-link-existing-input"
                                style="display:block;font-size:10px;font-weight:900;color:#475569;margin-bottom:5px;">
                                BUSCAR POR SKU, EAN OU NOME NO CAT\u00c1LOGO
                            </label>
                            <input type="text" id="kippe-link-existing-input"
                                value="${initVal}"
                                placeholder="EX: SKU000041, EAN OU NOME DO PRODUTO..."
                                autocomplete="off"
                                style="${inpStyle}" />
                        </div>

                        <div id="kippe-link-existing-suggestions"
                            style="display:flex;flex-direction:column;gap:6px;max-height:190px;overflow-y:auto;">
                            <div style="font-size:11px;font-weight:800;color:#64748B;text-align:center;padding:10px;">
                                CARREGANDO CAT\u00c1LOGO...
                            </div>
                        </div>

                        <div id="kippe-link-existing-error"
                            style="display:none;background:#FEF2F2;border:1px solid #FECACA;color:#B91C1C;border-radius:10px;padding:9px 11px;font-size:11px;font-weight:800;">
                        </div>

                        <div style="display:grid;grid-template-columns:1fr 1.4fr;gap:8px;margin-top:2px;">
                            <button type="button" id="cancel-link-existing-modal" style="${cancelBtnStyle}">
                                CANCELAR
                            </button>
                            <button type="button" id="confirm-link-existing-modal" style="${confirmBtnStyle}">
                                CONFIRMAR V\u00cdNCULO
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(overlay);

            const inputEl = document.getElementById('kippe-link-existing-input');
            const sugBox = document.getElementById('kippe-link-existing-suggestions');
            const errBox = document.getElementById('kippe-link-existing-error');
            const confirmBtn = document.getElementById('confirm-link-existing-modal');

            let catalogCache = [];
            let selectedProduct = null;

            const showModalError = (msg) => {
                if (!errBox) return;
                errBox.textContent = String(msg || '').toUpperCase();
                errBox.style.display = 'block';
            };
            const clearModalError = () => {
                if (!errBox) return;
                errBox.textContent = '';
                errBox.style.display = 'none';
            };

            const closeOverlay = () => overlay.remove();
            document.getElementById('close-link-existing-modal')?.addEventListener('click', closeOverlay);
            document.getElementById('cancel-link-existing-modal')?.addEventListener('click', closeOverlay);
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) closeOverlay();
            });

            const renderSuggestions = (queryText) => {
                if (!sugBox) return;
                const q = String(queryText || '').trim().toUpperCase();
                let matches = catalogCache;
                if (q) {
                    matches = catalogCache.filter(p =>
                        String(p.id || '').toUpperCase().includes(q) ||
                        String(p.ean || '').trim().includes(q) ||
                        String(p.name || '').toUpperCase().includes(q)
                    );
                } else {
                    const tokens = String(rawDesc || '').toUpperCase()
                        .split(/[^A-Z0-9]+/)
                        .filter(t => t.length >= 3);
                    if (tokens.length) {
                        const byTokens = catalogCache.filter(p => {
                            const nm = String(p.name || '').toUpperCase();
                            return tokens.some(tk => nm.includes(tk));
                        });
                        if (byTokens.length) matches = byTokens;
                    }
                }

                const slice = matches.slice(0, 12);
                if (!slice.length) {
                    sugBox.innerHTML = [
                        '<div style="font-size:11px;font-weight:800;color:#64748B;text-align:center;',
                        'padding:10px;background:#F8FAFC;border-radius:10px;border:1px dashed #CBD5E1;">',
                        'NENHUM PRODUTO ENCONTRADO PARA O FILTRO INFORMADO.</div>'
                    ].join('');
                    return;
                }

                sugBox.innerHTML = slice.map(p => {
                    const isSel = selectedProduct && String(selectedProduct.id) === String(p.id);
                    const bColor = isSel ? '#124191' : '#E2E8F0';
                    const bgColor = isSel ? '#EFF6FF' : '#F8FAFC';
                    const pName = escHtml(String(p.name || '').toUpperCase());
                    const pSku = escHtml(String(p.id || '').toUpperCase());
                    const pEan = p.ean ? `<span>EAN: ${escHtml(p.ean)}</span>` : '';
                    return `
                        <button type="button" data-pick-sku="${pSku}"
                            style="text-align:left;width:100%;padding:9px 11px;border-radius:10px;border:1.5px solid ${bColor};background:${bgColor};cursor:pointer;display:flex;flex-direction:column;gap:3px;text-transform:uppercase;">
                            <div style="font-size:11px;font-weight:900;color:#0F172A;line-height:1.25;">${pName}</div>
                            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:10px;font-weight:800;color:#475569;">
                                <span style="background:#DBEAFE;color:#124191;padding:1px 6px;border-radius:4px;font-weight:900;">${pSku}</span>
                                ${pEan}
                                <span>\u2022 SALDO: ${Number(p.quantity || 0)} UN</span>
                            </div>
                        </button>
                    `;
                }).join('');

                sugBox.querySelectorAll('[data-pick-sku]').forEach(cardBtn => {
                    cardBtn.addEventListener('click', () => {
                        const pickedId = cardBtn.getAttribute('data-pick-sku');
                        const found = catalogCache.find(item => String(item.id) === String(pickedId));
                        if (found) {
                            selectedProduct = found;
                            if (inputEl) inputEl.value = String(found.id || '').toUpperCase();
                            clearModalError();
                            renderSuggestions(found.id);
                        }
                    });
                });
            };

            const submitLink = async () => {
                clearModalError();
                const rawVal = (inputEl?.value || '').trim();
                const q = rawVal.toUpperCase();
                if (!q && !selectedProduct) {
                    showModalError('INFORME O SKU, EAN OU SELECIONE UM PRODUTO DA LISTA.');
                    inputEl?.focus();
                    return;
                }

                let prod = selectedProduct && (
                    String(selectedProduct.id || '').toUpperCase() === q ||
                    String(selectedProduct.ean || '').trim() === q
                ) ? selectedProduct : null;

                if (!prod && catalogCache.length) {
                    prod = catalogCache.find(p =>
                        String(p.id || '').toUpperCase() === q ||
                        String(p.ean || '').trim() === q
                    ) || null;
                }

                if (!prod) {
                    const rDirect = await fetch('/api/produto/' + encodeURIComponent(q), {
                        credentials: 'same-origin'
                    }).catch(() => null);
                    if (rDirect && rDirect.ok) {
                        const d = await rDirect.json();
                        prod = d.product || d;
                    }
                }

                if (!prod || !prod.id) {
                    showModalError('PRODUTO N\u00c3O ENCONTRADO NO CAT\u00c1LOGO PARA: ' + q);
                    return;
                }

                if (confirmBtn) {
                    confirmBtn.disabled = true;
                    confirmBtn.textContent = 'VINCULANDO...';
                }

                try {
                    if (typeof onPickedCallback === 'function') {
                        await onPickedCallback(prod);
                        closeOverlay();
                        return;
                    }
                    const rRes = await fetch(`/api/receiving/pending/${reqId}/resolve-product`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'same-origin',
                        body: JSON.stringify({
                            action: 'CADASTRADO',
                            sku: prod.id,
                            ean: prod.ean || sugEan,
                            name: prod.name || rawDesc
                        })
                    });
                    if (!rRes.ok) {
                        const errOut = await rRes.json().catch(() => ({}));
                        showModalError(errOut.error || 'FALHA AO VINCULAR PRODUTO EXISTENTE.');
                        if (confirmBtn) {
                            confirmBtn.disabled = false;
                            confirmBtn.textContent = 'CONFIRMAR V\u00cdNCULO';
                        }
                        return;
                    }
                    closeOverlay();
                    modal.remove();
                    await this.refreshEstoquistaPendingQueue();
                    document.getElementById('btn-open-estoquista-queue')?.click();
                } catch (e) {
                    showModalError('ERRO DE REDE AO VINCULAR: ' + (e.message || e));
                    if (confirmBtn) {
                        confirmBtn.disabled = false;
                        confirmBtn.textContent = 'CONFIRMAR V\u00cdNCULO';
                    }
                }
            };

            confirmBtn?.addEventListener('click', submitLink);
            inputEl?.addEventListener('input', () => {
                const start = inputEl.selectionStart;
                const end = inputEl.selectionEnd;
                inputEl.value = inputEl.value.toUpperCase();
                if (typeof start === 'number' && typeof end === 'number') {
                    inputEl.setSelectionRange(start, end);
                }
                clearModalError();
                selectedProduct = null;
                renderSuggestions(inputEl.value);
            });
            inputEl?.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    submitLink();
                } else if (e.key === 'Escape') {
                    closeOverlay();
                }
            });

            fetch('/api/produtos', { credentials: 'same-origin' })
                .then(r => r.ok ? r.json() : [])
                .then(data => {
                    catalogCache = Array.isArray(data) ? data : (data.products || []);
                    renderSuggestions(inputEl?.value || '');
                })
                .catch(() => {
                    if (sugBox) sugBox.innerHTML = '';
                });

            setTimeout(() => {
                inputEl?.focus();
                inputEl?.select();
            }, 40);
        };

        modal.querySelectorAll('[data-pr-register]').forEach(regBtn => {
            const reqId = regBtn.getAttribute('data-pr-register');
            const sugEan = regBtn.getAttribute('data-pr-ean') || '';
            const rawDesc = regBtn.getAttribute('data-pr-desc') || '';
            const parentRow = regBtn.parentElement;
            if (parentRow && !parentRow.querySelector('[data-pr-link-existing]')) {
                parentRow.style.cssText += ';display:flex;flex-wrap:wrap;gap:8px;';
                regBtn.style.cssText += ';flex:1 1 100%;height:38px;';

                const discardBtn = parentRow.querySelector('[data-pr-discard]');
                if (discardBtn) {
                    discardBtn.style.cssText += ';flex:1 1 calc(50% - 4px);height:36px;display:inline-flex;align-items:center;justify-content:center;';
                }

                const linkBtn = document.createElement('button');
                linkBtn.type = 'button';
                linkBtn.setAttribute('data-pr-link-existing', reqId);
                linkBtn.className = 'bg-emerald-600 text-white text-[10px] font-black uppercase py-2.5 px-2.5 rounded-lg shadow active:scale-95';
                linkBtn.style.cssText = 'flex:1 1 calc(50% - 4px);height:36px;background:#059669;color:#FFFFFF;font-size:10px;font-weight:900;padding:0 8px;border-radius:8px;white-space:nowrap;display:inline-flex;align-items:center;justify-content:center;';
                linkBtn.textContent = 'VINCULAR EXISTENTE';
                linkBtn.addEventListener('click', () => openLinkExistingModal(reqId, sugEan, rawDesc));
                parentRow.insertBefore(linkBtn, discardBtn || regBtn.nextSibling);
            }
        });

        modal.querySelectorAll('[data-pr-register]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const reqId = btn.getAttribute('data-pr-register');
                const ean = btn.getAttribute('data-pr-ean') || '';
                const desc = btn.getAttribute('data-pr-desc') || '';
                const prObj = reqList.find(x => String(x.id) === String(reqId)) || {};
                const ctx = {
                    reqId,
                    desc,
                    supplier: prObj.supplier || '',
                    invoice_number: prObj.invoice_number || '',
                    nf_qty: Number(prObj.nf_qty || 1),
                    pack_factor: Number(prObj.pack_factor || 1),
                    batch_code: prObj.batch_code || '',
                    expiration_date: prObj.expiration_date || '',
                };
                this._pendingProductRequest = ctx;
                this._lastReceivingContext = { ...ctx };
                this._returnToEstoquistaQueueAfterPutaway = true;
                modal.remove();
                await this.openNewProductRegistration(ean);
                const nameInput = document.getElementById('new-product-name');
                if (nameInput && !nameInput.value) nameInput.value = desc;
            });
        });

        modal.querySelectorAll('[data-pr-discard]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const reqId = btn.getAttribute('data-pr-discard');
                await fetch(`/api/receiving/pending/${reqId}/resolve-product`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ action: 'DESCARTADO' })
                });
                modal.remove();
                this.refreshEstoquistaPendingQueue();
            });
        });

        const skuOverridesByConf = {};
        modal.querySelectorAll('[data-cf-link-sku]').forEach(linkBtn => {
            linkBtn.addEventListener('click', () => {
                const pair = linkBtn.getAttribute('data-cf-link-sku') || '';
                const [cfId, idxStr] = pair.split(':');
                const itemDesc = linkBtn.getAttribute('data-cf-item-desc') || '';
                const itemEan = linkBtn.getAttribute('data-cf-item-ean') || '';
                openLinkExistingModal(null, itemEan, itemDesc, async (prod) => {
                    skuOverridesByConf[cfId] = skuOverridesByConf[cfId] || {};
                    skuOverridesByConf[cfId][String(idxStr)] = prod.id;
                    const bar = modal.querySelector(`[data-cf-sku-bar="${cfId}:${idxStr}"]`);
                    const badge = bar?.querySelector('[data-cf-sku-badge]');
                    if (badge) {
                        badge.style.background = '#DCFCE7';
                        badge.style.color = '#166534';
                        badge.style.borderColor = '#86EFAC';
                        badge.textContent = '\u2713 VINCULADO: ' + prod.id + ' - ' + String(prod.name || '').toUpperCase();
                    }
                    linkBtn.style.background = '#F1F5F9';
                    linkBtn.style.color = '#334155';
                    linkBtn.style.border = '1px solid #CBD5E1';
                    linkBtn.textContent = 'TROCAR SKU';
                });
            });
        });

        modal.querySelectorAll('[data-cf-approve]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const cfId = btn.getAttribute('data-cf-approve');
                const itemOverrides = {};
                const skuOverrides = skuOverridesByConf[cfId] || {};
                modal.querySelectorAll(`[data-cf-batch^="${cfId}:"]`).forEach(inp => {
                    const idx = inp.getAttribute('data-cf-batch').split(':')[1];
                    itemOverrides[idx] = itemOverrides[idx] || {};
                    itemOverrides[idx].batch_code = inp.value.trim().toUpperCase();
                });
                modal.querySelectorAll(`[data-cf-exp^="${cfId}:"]`).forEach(inp => {
                    const idx = inp.getAttribute('data-cf-exp').split(':')[1];
                    itemOverrides[idx] = itemOverrides[idx] || {};
                    itemOverrides[idx].expiration_date = inp.value;
                });
                btn.disabled = true;
                const res = await fetch(`/api/receiving/pending/${cfId}/approve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ item_overrides: itemOverrides, sku_overrides: skuOverrides })
                });
                const out = await res.json();
                if (!res.ok) {
                    await window.kippeModalAlert('❌ ' + (out.error || 'Falha ao aprovar conferência.'), 'VALIDAÇÃO PENDENTE');
                    btn.disabled = false;
                    return;
                }
                alert(`✅ Armazenagem confirmada! ${out.approved} item(ns) lançados no estoque.`);
                modal.remove();
                this.refreshEstoquistaPendingQueue();
            });
        });

        modal.querySelectorAll('[data-cf-reject]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const cfId = btn.getAttribute('data-cf-reject');
                if (!confirm('Rejeitar esta conferência pendente?')) return;
                await fetch(`/api/receiving/pending/${cfId}/reject`, {
                    method: 'POST',
                    credentials: 'same-origin'
                });
                modal.remove();
                this.refreshEstoquistaPendingQueue();
            });
        });

        modal.querySelectorAll('[data-comp-open]').forEach(btn => {
            btn.addEventListener('click', () => {
                const divId = btn.getAttribute('data-comp-open');
                const sku = btn.getAttribute('data-comp-sku') || '';
                const prodName = btn.getAttribute('data-comp-name') || sku;
                const nfNum = btn.getAttribute('data-comp-nf') || 'S/N';
                const supplier = btn.getAttribute('data-comp-supplier') || '';
                const pendingMax = Number(btn.getAttribute('data-comp-pending') || 0);

                document.getElementById('kippe-complement-modal')?.remove();
                const compOverlay = document.createElement('div');
                compOverlay.id = 'kippe-complement-modal';
                compOverlay.style.cssText = 'position:fixed;inset:0;z-index:10060;background:rgba(15,23,42,0.78);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:16px;';

                const defExp = new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 10);
                compOverlay.innerHTML = `
                    <div style="background:#FFFFFF;border-radius:16px;width:100%;max-width:390px;overflow:hidden;box-shadow:0 24px 48px rgba(15,23,42,0.45);border:1px solid #E2E8F0;">
                        <div style="background:#EA580C;color:#FFFFFF;padding:13px 16px;display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <div style="font-size:9px;font-weight:900;text-transform:uppercase;color:#FFEDD5;">CANHOTO RETIDO · NF ${escSafe(nfNum)}</div>
                                <h3 style="font-size:13px;font-weight:900;margin:2px 0 0;text-transform:uppercase;">RECEBER COMPLEMENTO</h3>
                            </div>
                            <button type="button" id="close-comp-modal" style="background:rgba(255,255,255,0.2);border:none;color:#FFFFFF;width:30px;height:30px;border-radius:8px;font-weight:900;cursor:pointer;">✕</button>
                        </div>
                        <div style="padding:14px;display:flex;flex-direction:column;gap:10px;">
                            <div style="background:#FFF7ED;border:1px solid #FDBA74;border-radius:10px;padding:10px;">
                                <p style="font-size:11px;font-weight:900;color:#0F172A;margin:0;text-transform:uppercase;">${escSafe(prodName)}</p>
                                <p style="font-size:10px;font-weight:700;color:#64748B;margin:3px 0 0;">SKU: <strong>${escSafe(sku)}</strong> · ${escSafe(supplier)}</p>
                                <p style="font-size:10px;font-weight:900;color:#C2410C;margin:4px 0 0;">SALDO PENDENTE DO CANHOTO: ${pendingMax}</p>
                            </div>
                            <div>
                                <label style="display:block;font-size:9.5px;font-weight:900;color:#334155;text-transform:uppercase;margin-bottom:4px;">Quantidade Recebida Agora</label>
                                <input type="number" id="comp-qty-input" value="${pendingMax}" min="0.001" max="${pendingMax}" step="any"
                                    style="width:100%;height:38px;border:1.5px solid #CBD5E1;border-radius:9px;padding:0 10px;font-size:14px;font-weight:900;color:#0F172A;box-sizing:border-box;">
                            </div>
                            ${isEstoquistaModal ? `
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                                <div>
                                    <label style="display:block;font-size:9px;font-weight:900;color:#475569;text-transform:uppercase;margin-bottom:4px;">Lote (Opcional)</label>
                                    <input type="text" id="comp-batch-input" placeholder="AUTO"
                                        style="width:100%;height:36px;border:1px solid #CBD5E1;border-radius:8px;padding:0 8px;font-size:11px;font-weight:800;text-transform:uppercase;box-sizing:border-box;">
                                </div>
                                <div>
                                    <label style="display:block;font-size:9px;font-weight:900;color:#475569;text-transform:uppercase;margin-bottom:4px;">Validade</label>
                                    <input type="date" id="comp-exp-input" value="${defExp}"
                                        style="width:100%;height:36px;border:1px solid #CBD5E1;border-radius:8px;padding:0 8px;font-size:11px;font-weight:800;box-sizing:border-box;">
                                </div>
                            </div>
                            ` : `
                            <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:8px 10px;font-size:10px;font-weight:700;color:#1E40AF;line-height:1.35;">
                                Ao confirmar, o saldo do canhoto será abatido e o item seguirá para a fila de armazenagem do Estoquista.
                            </div>
                            `}
                            <div id="comp-err-box" style="display:none;background:#FEF2F2;border:1px solid #FECACA;color:#B91C1C;font-size:10px;font-weight:800;padding:8px;border-radius:8px;"></div>
                            <button type="button" id="confirm-comp-submit"
                                style="width:100%;background:#16A34A;color:#FFFFFF;border:none;border-radius:10px;padding:12px;font-size:11px;font-weight:900;text-transform:uppercase;cursor:pointer;margin-top:2px;">
                                ${isEstoquistaModal ? '✅ CONFIRMAR ENTRADA & ABATER SALDO' : '✅ REGISTRAR COMPLEMENTO & ENVIAR P/ ESTOQUISTA'}
                            </button>
                        </div>
                    </div>
                `;
                document.body.appendChild(compOverlay);

                const closeComp = () => compOverlay.remove();
                document.getElementById('close-comp-modal')?.addEventListener('click', closeComp);
                compOverlay.addEventListener('click', (e) => { if (e.target === compOverlay) closeComp(); });

                document.getElementById('confirm-comp-submit')?.addEventListener('click', async (ev) => {
                    const submitBtn = ev.currentTarget;
                    const errBox = document.getElementById('comp-err-box');
                    const qtyVal = Number(document.getElementById('comp-qty-input')?.value || 0);
                    const batchVal = (document.getElementById('comp-batch-input')?.value || '').trim().toUpperCase();
                    const expVal = (document.getElementById('comp-exp-input')?.value || '').trim();

                    if (qtyVal <= 0 || qtyVal > pendingMax) {
                        if (errBox) {
                            errBox.textContent = `Informe uma quantidade entre 1 e ${pendingMax}.`;
                            errBox.style.display = 'block';
                        }
                        return;
                    }
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'PROCESSANDO...';
                    try {
                        const r = await fetch(`/api/receiving/divergences/${divId}/complement`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'same-origin',
                            body: JSON.stringify({
                                sku,
                                quantity: qtyVal,
                                batch_code: batchVal,
                                expiration_date: expVal,
                            }),
                        });
                        const out = await r.json().catch(() => ({}));
                        if (!r.ok) {
                            if (errBox) {
                                errBox.textContent = out.error || 'Falha ao registrar complemento.';
                                errBox.style.display = 'block';
                            }
                            submitBtn.disabled = false;
                            submitBtn.textContent = '✅ CONFIRMAR ENTRADA & ABATER SALDO';
                            return;
                        }
                        closeComp();
                        modal.remove();
                        const statusMsg = out.queued_for_storage
                            ? (out.canhoto_liberado
                                ? `✅ Canhoto liberado! Saldo pendente da NF ${nfNum} zerado e +${qtyVal} enviado para a fila de armazenagem do Estoquista.`
                                : `✅ Complemento de +${qtyVal} enviado para a fila do Estoquista! Saldo restante no canhoto: ${out.pending_after}.`)
                            : (out.canhoto_liberado
                                ? `✅ Canhoto liberado! Saldo pendente da NF ${nfNum} zerado e +${qtyVal} lançado no estoque.`
                                : `✅ Complemento de +${qtyVal} lançado! Saldo restante no canhoto: ${out.pending_after}.`);
                        if (window.kippeModalAlert) {
                            await window.kippeModalAlert(statusMsg, 'COMPLEMENTO RECEBIDO');
                        } else {
                            alert(statusMsg);
                        }
                        await this.refreshEstoquistaPendingQueue();
                    } catch (err) {
                        if (errBox) {
                            errBox.textContent = 'Erro de rede: ' + (err.message || err);
                            errBox.style.display = 'block';
                        }
                        submitBtn.disabled = false;
                        submitBtn.textContent = '✅ CONFIRMAR ENTRADA & ABATER SALDO';
                    }
                });
            });
        });
    }

    isSystemAdmin() {
        const role = String(this.currentOperator?.role || '').trim().toUpperCase();
        return role === 'ADMIN_SISTEMA';
    }

    syncSelfPinButton() {
        const homeView = document.getElementById('home-module-view');
        if (!homeView) return;

        let selfCard = document.getElementById('operator-self-security-card');
        if (!this.currentOperator?.id) {
            selfCard?.remove();
            return;
        }

        if (!selfCard) {
            selfCard = document.createElement('div');
            selfCard.id = 'operator-self-security-card';
            selfCard.style.cssText = 'background:#FFFFFF;border:1px solid #E2E8F0;border-radius:14px;padding:12px 16px;box-shadow:0 1px 2px rgba(15,23,42,0.04);display:flex;align-items:center;justify-content:space-between;gap:12px;';
            selfCard.innerHTML = `
                <div style="min-width:0;">
                    <p style="font-size:11px;font-weight:900;color:#1E293B;margin:0;text-transform:uppercase;letter-spacing:0.02em;">
                        Credencial de Acesso
                    </p>
                    <p style="font-size:10px;color:#64748B;margin:2px 0 0;">
                        Alterar seu PIN pessoal de autenticação
                    </p>
                </div>
                <button type="button" id="btn-open-change-own-pin"
                    style="background:#F8FAFC;color:#124191;border:1.5px solid #CBD5E1;border-radius:10px;padding:8px 12px;font-size:10px;font-weight:900;letter-spacing:0.04em;text-transform:uppercase;cursor:pointer;flex-shrink:0;">
                    🔑 MEU PIN
                </button>
            `;
            homeView.appendChild(selfCard);
            document.getElementById('btn-open-change-own-pin')?.addEventListener('click', () => {
                this.openChangeOwnPinModal();
            });
        }
    }

    openChangeOwnPinModal() {
        document.getElementById('change-own-pin-modal')?.remove();
        const modal = document.createElement('div');
        modal.id = 'change-own-pin-modal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(15,23,42,0.78);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:16px;';

        const inputStyle = 'width:100%;box-sizing:border-box;background:#F8FAFC;border:1.5px solid #CBD5E1;border-radius:10px;padding:11px 12px;font-size:13px;font-weight:800;color:#0F172A;outline:none;';
        const labelStyle = 'display:block;font-size:9px;font-weight:900;color:#64748B;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:6px;';

        modal.innerHTML = `
            <div style="background:#FFFFFF;border-radius:18px;box-shadow:0 20px 45px rgba(15,23,42,0.35);width:100%;max-width:400px;overflow:hidden;">
                <div style="background:#124191;color:#FFFFFF;padding:18px 20px;border-bottom:4px solid #D32F2F;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                    <div>
                        <p style="font-size:9px;font-weight:900;letter-spacing:0.1em;color:#93C5FD;text-transform:uppercase;margin:0 0 4px;">
                            SEGURANÇA DO OPERADOR
                        </p>
                        <h3 style="font-size:15px;font-weight:900;text-transform:uppercase;margin:0;">
                            Alterar Meu PIN
                        </h3>
                    </div>
                    <button type="button" id="close-own-pin-modal"
                        style="background:rgba(255,255,255,0.14);border:1px solid rgba(255,255,255,0.22);color:#FFFFFF;width:32px;height:32px;border-radius:8px;font-size:14px;font-weight:900;cursor:pointer;">
                        ✕
                    </button>
                </div>
                <form id="form-change-own-pin" style="padding:20px;display:flex;flex-direction:column;gap:14px;">
                    <div>
                        <label style="${labelStyle}">PIN Atual</label>
                        <input type="password" inputmode="numeric" id="own-pin-current" placeholder="••••" required style="${inputStyle}">
                    </div>
                    <div>
                        <label style="${labelStyle}">Novo PIN (Mínimo 4 dígitos)</label>
                        <input type="password" inputmode="numeric" id="own-pin-new" placeholder="••••" required style="${inputStyle}">
                    </div>
                    <div>
                        <label style="${labelStyle}">Confirmar Novo PIN</label>
                        <input type="password" inputmode="numeric" id="own-pin-confirm" placeholder="••••" required style="${inputStyle}">
                    </div>
                    <button type="submit" id="btn-save-own-pin"
                        style="width:100%;margin-top:4px;background:#124191;color:#FFFFFF;border:none;border-radius:12px;padding:13px 16px;font-size:11px;font-weight:900;letter-spacing:0.06em;text-transform:uppercase;box-shadow:0 4px 12px rgba(18,65,145,0.28);cursor:pointer;">
                        ATUALIZAR MEU PIN
                    </button>
                </form>
            </div>
        `;

        document.body.appendChild(modal);
        document.getElementById('close-own-pin-modal')?.addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (ev) => {
            if (ev.target === modal) modal.remove();
        });

        document.getElementById('form-change-own-pin')?.addEventListener('submit', async (ev) => {
            ev.preventDefault();
            const current_pin = document.getElementById('own-pin-current')?.value || '';
            const new_pin = document.getElementById('own-pin-new')?.value || '';
            const confirm_pin = document.getElementById('own-pin-confirm')?.value || '';

            if (new_pin !== confirm_pin) {
                alert('❌ A confirmação do novo PIN não confere.');
                return;
            }

            const btn = document.getElementById('btn-save-own-pin');
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'SALVANDO...';
            }

            try {
                const res = await fetch('/api/auth/change-pin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ current_pin, new_pin }),
                });
                const out = await res.json();
                if (!res.ok) {
                    alert('❌ ' + (out.error || 'Não foi possível alterar o PIN.'));
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = 'ATUALIZAR MEU PIN';
                    }
                    return;
                }
                alert('✅ PIN alterado com sucesso!');
                modal.remove();
            } catch (err) {
                alert('❌ ' + err.message);
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'ATUALIZAR MEU PIN';
                }
            }
        });
    }

    syncAdminTeamButton() {
        const homeView = document.getElementById('home-module-view');
        if (!homeView) return;

        let btnCard = document.getElementById('admin-team-profiles-card');
        if (!this.isSystemAdmin()) {
            btnCard?.remove();
            return;
        }

        if (!btnCard) {
            btnCard = document.createElement('div');
            btnCard.id = 'admin-team-profiles-card';
            btnCard.style.cssText = 'background:#FFFFFF;border:1px solid #E2E8F0;border-left:4px solid #124191;border-radius:14px;padding:14px 16px;box-shadow:0 1px 3px rgba(15,23,42,0.06);display:flex;flex-direction:column;gap:12px;';
            btnCard.innerHTML = `
                <div>
                    <span style="display:inline-block;background:#EFF6FF;color:#124191;border:1px solid #DBEAFE;font-size:9px;font-weight:900;padding:2px 8px;border-radius:6px;letter-spacing:0.06em;text-transform:uppercase;">
                        ADMINISTRAÇÃO &amp; GOVERNANÇA
                    </span>
                    <p style="font-size:12px;font-weight:900;color:#1E293B;margin:6px 0 2px;text-transform:uppercase;letter-spacing:0.02em;">
                        Controle Institucional WMS
                    </p>
                    <p style="font-size:10px;color:#64748B;margin:0;line-height:1.35;">
                        Gerencie perfis, redefina senhas e consulte a trilha de auditoria
                    </p>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;">
                    <button type="button" id="btn-open-team-profiles"
                        style="background:#124191;color:#FFFFFF;border:none;border-radius:10px;padding:10px 8px;font-size:9.5px;font-weight:900;letter-spacing:0.04em;text-transform:uppercase;box-shadow:0 2px 6px rgba(18,65,145,0.24);cursor:pointer;display:flex;align-items:center;justify-content:center;gap:4px;">
                        <span>👥 PERFIS</span>
                    </button>
                    <button type="button" id="btn-open-audit-logs"
                        style="background:#0F172A;color:#FFFFFF;border:none;border-radius:10px;padding:10px 8px;font-size:9.5px;font-weight:900;letter-spacing:0.04em;text-transform:uppercase;box-shadow:0 2px 6px rgba(15,23,42,0.22);cursor:pointer;display:flex;align-items:center;justify-content:center;gap:4px;">
                        <span>📋 AUDITORIA</span>
                    </button>
                    <button type="button" id="btn-open-backup-export"
                        style="background:#065F46;color:#FFFFFF;border:none;border-radius:10px;padding:10px 8px;font-size:9.5px;font-weight:900;letter-spacing:0.04em;text-transform:uppercase;box-shadow:0 2px 6px rgba(6,95,70,0.24);cursor:pointer;display:flex;align-items:center;justify-content:center;gap:4px;">
                        <span>💾 BACKUP</span>
                    </button>
                </div>
            `;
            homeView.appendChild(btnCard);
            document.getElementById('btn-open-team-profiles')?.addEventListener('click', () => {
                this.openTeamProfilesModal();
            });
            document.getElementById('btn-open-audit-logs')?.addEventListener('click', () => {
                this.openAuditLogsModal();
            });
            document.getElementById('btn-open-backup-export')?.addEventListener('click', () => {
                this.openBackupAndExportModal();
            });
        }
    }

    openBackupAndExportModal() {
        if (!this.isSystemAdmin()) return;

        document.getElementById('backup-export-modal')?.remove();
        const modal = document.createElement('div');
        modal.id = 'backup-export-modal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(15,23,42,0.78);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:16px;';

        const reportCard = (slug, title, desc, badge) => `
            <div style="padding:12px 14px;border-radius:12px;border:1px solid #E2E8F0;background:#F8FAFC;display:flex;align-items:center;justify-content:space-between;gap:12px;">
                <div style="min-width:0;">
                    <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                        <span style="font-size:11px;font-weight:900;color:#0F172A;text-transform:uppercase;">${title}</span>
                        <span style="font-size:8.5px;font-weight:900;padding:2px 6px;border-radius:5px;background:#EFF6FF;color:#124191;border:1px solid #BFDBFE;">${badge}</span>
                    </div>
                    <p style="font-size:10px;color:#64748B;margin:4px 0 0;line-height:1.3;">${desc}</p>
                </div>
                <a href="/api/reports/export/${slug}.csv" download
                    style="background:#124191;color:#FFFFFF;text-decoration:none;border-radius:9px;padding:8px 11px;font-size:9.5px;font-weight:900;letter-spacing:0.04em;text-transform:uppercase;flex-shrink:0;box-shadow:0 2px 5px rgba(18,65,145,0.2);">
                    ⬇️ CSV
                </a>
            </div>
        `;

        modal.innerHTML = `
            <div style="background:#FFFFFF;border-radius:18px;box-shadow:0 20px 45px rgba(15,23,42,0.35);width:100%;max-width:450px;max-height:88vh;display:flex;flex-direction:column;overflow:hidden;">
                <div style="background:#124191;color:#FFFFFF;padding:18px 20px;border-bottom:4px solid #D32F2F;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                    <div>
                        <p style="font-size:9px;font-weight:900;letter-spacing:0.1em;color:#93C5FD;text-transform:uppercase;margin:0 0 4px;">
                            KIPPE SUPERMERCADO · CONTINUIDADE
                        </p>
                        <h3 style="font-size:16px;font-weight:900;letter-spacing:0.02em;text-transform:uppercase;margin:0;">
                            Backup &amp; Relatórios CSV
                        </h3>
                        <p style="font-size:10px;color:#DBEAFE;margin:4px 0 0;">
                            Cópia íntegra SQLite e planilhas gerenciais WMS
                        </p>
                    </div>
                    <button type="button" id="close-backup-modal"
                        style="background:rgba(255,255,255,0.14);border:1px solid rgba(255,255,255,0.22);color:#FFFFFF;width:32px;height:32px;border-radius:8px;font-size:14px;font-weight:900;cursor:pointer;flex-shrink:0;">
                        ✕
                    </button>
                </div>

                <div style="overflow-y:auto;flex:1;padding:18px 20px;display:flex;flex-direction:column;gap:16px;">
                    <div style="padding:14px;border-radius:14px;border:1.5px solid #A7F3D0;background:#ECFDF5;display:flex;flex-direction:column;gap:10px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
                            <span style="font-size:10px;font-weight:900;letter-spacing:0.06em;text-transform:uppercase;color:#065F46;">
                                🛡️ Backup Banco de Dados SQLite
                            </span>
                            <span style="font-size:8.5px;font-weight:900;background:#065F46;color:#FFFFFF;padding:2px 7px;border-radius:5px;">
                                INTEGRITY CHECK
                            </span>
                        </div>
                        <p style="font-size:10.5px;color:#047857;margin:0;line-height:1.35;">
                            Gera snapshot atômico validado via <strong>PRAGMA integrity_check</strong> e salva automaticamente na pasta <strong>Download</strong> do aparelho.
                        </p>
                        <button type="button" id="btn-run-sqlite-backup"
                            style="width:100%;background:#065F46;color:#FFFFFF;border:none;border-radius:11px;padding:12px 14px;font-size:11px;font-weight:900;letter-spacing:0.05em;text-transform:uppercase;box-shadow:0 4px 10px rgba(6,95,70,0.25);cursor:pointer;">
                            GERAR BACKUP VALIDADO (.DB)
                        </button>
                        <div id="sqlite-backup-result" style="display:none;padding:10px 12px;border-radius:10px;background:#FFFFFF;border:1px solid #A7F3D0;font-size:10px;color:#0F172A;"></div>
                    </div>

                    <div style="display:flex;flex-direction:column;gap:10px;">
                        <p style="font-size:10px;font-weight:900;letter-spacing:0.07em;text-transform:uppercase;color:#64748B;margin:0;">
                            Exportação Gerencial (Excel / Sheets)
                        </p>
                        ${reportCard('inventario', 'Posição de Inventário', 'Saldos totais, reservas, disponível e categorias', 'CSV')}
                        ${reportCard('fefo', 'Validades & Lotes (FEFO)', 'Lotes ativos ordenados por vencimento e faixa de risco', 'FEFO')}
                        ${reportCard('recebimentos', 'Recebimentos & Divergências', 'Entradas por NF, fornecedor, divergências e operador', 'AUDITORIA')}
                        ${reportCard('divergencias', 'Ocorrências de Divergência', 'Faltas, sobras, avarias e motivos formalizados na doca', 'DIVERGÊNCIAS')}
                    </div>
                </div>

                <div style="padding:10px 16px;background:#F1F5F9;border-top:1px solid #E2E8F0;text-align:center;">
                    <span style="font-size:9px;font-weight:800;letter-spacing:0.06em;color:#64748B;text-transform:uppercase;">
                        Exportações registradas na trilha de auditoria
                    </span>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        document.getElementById('close-backup-modal')?.addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (ev) => {
            if (ev.target === modal) modal.remove();
        });

        document.getElementById('btn-run-sqlite-backup')?.addEventListener('click', async () => {
            const btn = document.getElementById('btn-run-sqlite-backup');
            const box = document.getElementById('sqlite-backup-result');
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'VALIDANDO INTEGRIDADE SQLITE...';
            }
            try {
                const res = await fetch('/api/admin/backup', {
                    method: 'POST',
                    credentials: 'same-origin',
                });
                const out = await res.json();
                if (!res.ok) {
                    alert('❌ ' + (out.error || 'Falha ao gerar backup.'));
                    return;
                }
                const kb = Math.max(1, Math.round((out.size_bytes || 0) / 1024));
                if (box) {
                    box.style.display = 'block';
                    box.innerHTML = `
                        <p style="font-weight:900;color:#065F46;margin:0 0 4px;">✅ INTEGRITY CHECK: OK (${kb} KB)</p>
                        <p style="margin:0 0 4px;word-break:break-all;"><strong>Arquivo:</strong> ${out.filename}</p>
                        <p style="margin:0 0 8px;font-family:monospace;font-size:9px;color:#475569;">SHA-256: ${(out.sha256 || '').slice(0, 24)}...</p>
                        ${out.download_folder_saved ? '<p style="margin:0 0 8px;color:#047857;font-weight:800;">📂 Cópia salva em /sdcard/Download</p>' : ''}
                        <a href="${out.download_url}" download="${out.filename}"
                            style="display:block;text-align:center;background:#124191;color:#FFFFFF;text-decoration:none;border-radius:8px;padding:8px 10px;font-size:9.5px;font-weight:900;text-transform:uppercase;">
                            ⬇️ BAIXAR CÓPIA NO NAVEGADOR
                        </a>
                    `;
                }
            } catch (err) {
                alert('❌ ' + err.message);
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'GERAR BACKUP VALIDADO (.DB)';
                }
            }
        });
    }

    async openAuditLogsModal() {
        if (!this.isSystemAdmin()) return;

        document.getElementById('institutional-audit-modal')?.remove();
        const modal = document.createElement('div');
        modal.id = 'institutional-audit-modal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(15,23,42,0.78);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:16px;';

        let activeCategory = 'ALL';
        let searchQuery = '';

        const catBadgeStyle = (cat) => {
            if (cat === 'ESTOQUE') return 'background:#ECFDF5;color:#065F46;border:1px solid #A7F3D0;';
            if (cat === 'RECEBIMENTO') return 'background:#FFFBEB;color:#92400E;border:1px solid #FDE68A;';
            if (cat === 'CATALOGO') return 'background:#EFF6FF;color:#124191;border:1px solid #BFDBFE;';
            if (cat === 'GOVERNANCA') return 'background:#FEF2F2;color:#B91C1C;border:1px solid #FECACA;';
            return 'background:#F1F5F9;color:#334155;border:1px solid #CBD5E1;';
        };

        const loadAndRender = async () => {
            const params = new URLSearchParams({
                category: activeCategory,
                q: searchQuery,
                limit: '100',
            });
            let logs = [];
            try {
                const res = await fetch(`/api/audit/logs?${params.toString()}`, { credentials: 'same-origin' });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Falha ao carregar auditoria.');
                logs = data.logs || [];
            } catch (err) {
                alert('❌ ' + err.message);
                modal.remove();
                return;
            }

            const categories = ['ALL', 'ESTOQUE', 'RECEBIMENTO', 'CATALOGO', 'GOVERNANCA', 'ACESSO'];
            const pillsHtml = categories.map(cat => {
                const isSelected = cat === activeCategory;
                const label = cat === 'ALL' ? 'TODOS' : cat;
                return `<button type="button" data-audit-cat="${cat}"
                    style="padding:6px 10px;border-radius:8px;font-size:9px;font-weight:900;letter-spacing:0.05em;text-transform:uppercase;cursor:pointer;border:1px solid ${isSelected ? '#124191' : '#CBD5E1'};background:${isSelected ? '#124191' : '#FFFFFF'};color:${isSelected ? '#FFFFFF' : '#475569'};flex-shrink:0;">
                    ${label}
                </button>`;
            }).join('');

            const rowsHtml = logs.map(item => `
                <div style="padding:12px 14px;border-radius:12px;border:1px solid #E2E8F0;background:#FFFFFF;display:flex;flex-direction:column;gap:6px;">
                    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;">
                        <span style="font-size:9px;font-weight:900;padding:2px 8px;border-radius:6px;letter-spacing:0.05em;${catBadgeStyle(item.category)}">
                            ${item.category}
                        </span>
                        <span style="font-size:9px;font-weight:700;color:#64748B;font-variant-numeric:tabular-nums;">
                            ${window.formatBrtDateTime(item.created_at)}
                        </span>
                    </div>
                    <p style="font-size:11px;font-weight:800;color:#0F172A;margin:0;line-height:1.35;">
                        ${item.summary}
                    </p>
                    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:9px;font-weight:800;color:#64748B;text-transform:uppercase;">
                        <span>POR: <strong style="color:#1E293B;">${item.actor_name}</strong> (${item.actor_role})</span>
                        ${item.target_ref ? `<span style="background:#F1F5F9;color:#334155;padding:2px 6px;border-radius:4px;">${item.target_ref}</span>` : ''}
                    </div>
                </div>
            `).join('') || '<p style="font-size:11px;color:#94A3B8;text-align:center;padding:24px 0;margin:0;">Nenhum registro encontrado para este filtro.</p>';

            modal.innerHTML = `
                <div style="background:#FFFFFF;border-radius:18px;box-shadow:0 20px 45px rgba(15,23,42,0.35);width:100%;max-width:460px;max-height:88vh;display:flex;flex-direction:column;overflow:hidden;">
                    <div style="background:#124191;color:#FFFFFF;padding:18px 20px;border-bottom:4px solid #D32F2F;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                        <div>
                            <p style="font-size:9px;font-weight:900;letter-spacing:0.1em;color:#93C5FD;text-transform:uppercase;margin:0 0 4px;">
                                KIPPE SUPERMERCADO · RASTREABILIDADE
                            </p>
                            <h3 style="font-size:16px;font-weight:900;letter-spacing:0.02em;text-transform:uppercase;margin:0;">
                                Auditoria Operacional
                            </h3>
                            <p style="font-size:10px;color:#DBEAFE;margin:4px 0 0;">
                                Histórico imutável de ações, acessos e movimentações
                            </p>
                        </div>
                        <button type="button" id="close-audit-modal"
                            style="background:rgba(255,255,255,0.14);border:1px solid rgba(255,255,255,0.22);color:#FFFFFF;width:32px;height:32px;border-radius:8px;font-size:14px;font-weight:900;cursor:pointer;flex-shrink:0;">
                            ✕
                        </button>
                    </div>

                    <div style="padding:14px 16px;background:#F8FAFC;border-bottom:1px solid #E2E8F0;display:flex;flex-direction:column;gap:10px;">
                        <div style="display:flex;gap:6px;overflow-x:auto;padding-bottom:2px;">
                            ${pillsHtml}
                        </div>
                        <div style="display:flex;gap:8px;">
                            <input type="text" id="audit-search-input" value="${searchQuery}" placeholder="Filtrar por NF, fornecedor, operador, SKU..."
                                style="flex:1;box-sizing:border-box;background:#FFFFFF;border:1.5px solid #CBD5E1;border-radius:10px;padding:9px 12px;font-size:11px;font-weight:700;color:#0F172A;outline:none;">
                            <button type="button" id="audit-search-btn"
                                style="background:#124191;color:#FFFFFF;border:none;border-radius:10px;padding:0 14px;font-size:10px;font-weight:900;text-transform:uppercase;cursor:pointer;">
                                BUSCAR
                            </button>
                        </div>
                    </div>

                    <div style="padding:14px 16px;overflow-y:auto;flex:1;background:#F1F5F9;display:flex;flex-direction:column;gap:8px;">
                        ${rowsHtml}
                    </div>

                    <div style="padding:10px 16px;background:#FFFFFF;border-top:1px solid #E2E8F0;text-align:center;">
                        <span style="font-size:9px;font-weight:800;letter-spacing:0.06em;color:#64748B;text-transform:uppercase;">
                            Exibindo ${logs.length} evento(s) auditados
                        </span>
                    </div>
                </div>
            `;

            document.getElementById('close-audit-modal')?.addEventListener('click', () => modal.remove());
            modal.querySelectorAll('[data-audit-cat]').forEach(btn => {
                btn.addEventListener('click', () => {
                    activeCategory = btn.getAttribute('data-audit-cat') || 'ALL';
                    loadAndRender();
                });
            });
            const triggerSearch = () => {
                searchQuery = document.getElementById('audit-search-input')?.value || '';
                loadAndRender();
            };
            document.getElementById('audit-search-btn')?.addEventListener('click', triggerSearch);
            document.getElementById('audit-search-input')?.addEventListener('keydown', (ev) => {
                if (ev.key === 'Enter') {
                    ev.preventDefault();
                    triggerSearch();
                }
            });
        };

        modal.addEventListener('click', (ev) => {
            if (ev.target === modal) modal.remove();
        });
        document.body.appendChild(modal);
        await loadAndRender();
    }

    async openTeamProfilesModal() {
        if (!this.isSystemAdmin()) return;

        const fetchOperators = async () => {
            const res = await fetch('/api/operators', { credentials: 'same-origin' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Erro ao carregar equipe.');
            return data.operators || [];
        };

        let operators = [];
        try {
            operators = await fetchOperators();
        } catch (err) {
            alert('❌ ' + err.message);
            return;
        }

        document.getElementById('team-profiles-modal')?.remove();
        const modal = document.createElement('div');
        modal.id = 'team-profiles-modal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:9999;background:rgba(15,23,42,0.78);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:16px;';

        const roleBadgeStyle = (role) => {
            if (role === 'ADMIN_SISTEMA') return 'background:#FEF2F2;color:#B91C1C;border:1px solid #FECACA;';
            if (role === 'ESTOQUISTA') return 'background:#EFF6FF;color:#124191;border:1px solid #BFDBFE;';
            if (role === 'CONFERENTE') return 'background:#FFFBEB;color:#92400E;border:1px solid #FDE68A;';
            return 'background:#F1F5F9;color:#334155;border:1px solid #CBD5E1;';
        };

        const inputStyle = 'width:100%;box-sizing:border-box;background:#F8FAFC;border:1.5px solid #CBD5E1;border-radius:10px;padding:10px 12px;font-size:12px;font-weight:700;color:#0F172A;outline:none;';
        const labelStyle = 'display:block;font-size:9px;font-weight:900;color:#64748B;letter-spacing:0.07em;text-transform:uppercase;margin-bottom:6px;';

        const renderBody = (list) => {
            const currentId = String(this.currentOperator?.id || '').trim();
            const listHtml = list.map(op => {
                const isSelf = op.id === currentId;
                return `
                    <div style="display:flex;flex-direction:column;gap:8px;padding:12px 14px;border-radius:12px;border:1px solid #E2E8F0;background:#F8FAFC;">
                        <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
                            <div style="min-width:0;">
                                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                                    <span style="font-size:12px;font-weight:900;color:#0F172A;text-transform:uppercase;">${op.name}</span>
                                    <span style="font-size:9px;font-weight:900;padding:2px 8px;border-radius:6px;letter-spacing:0.04em;${roleBadgeStyle(op.role)}">${op.role}</span>
                                </div>
                                <p style="font-size:10px;font-weight:700;color:#64748B;margin:5px 0 0;">
                                    ID / LOGIN: <span style="color:#1E293B;font-weight:900;">${op.id}</span>
                                </p>
                            </div>
                            <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
                                <button type="button" data-toggle-reset-pin="${op.id}"
                                    style="background:#EFF6FF;border:1.5px solid #BFDBFE;color:#124191;font-size:9px;font-weight:900;letter-spacing:0.04em;text-transform:uppercase;padding:7px 9px;border-radius:8px;cursor:pointer;">
                                    🔑 PIN
                                </button>
                                ${
                                    isSelf
                                        ? '<span style="font-size:9px;font-weight:900;color:#94A3B8;letter-spacing:0.06em;text-transform:uppercase;padding:6px 8px;background:#F1F5F9;border-radius:6px;">VOCÊ</span>'
                                        : `<button type="button" data-del-op="${op.id}" data-del-name="${op.name}"
                                             style="background:#FFFFFF;border:1.5px solid #FECACA;color:#DC2626;font-size:9px;font-weight:900;letter-spacing:0.04em;text-transform:uppercase;padding:7px 9px;border-radius:8px;cursor:pointer;">
                                             EXCLUIR
                                           </button>`
                                }
                            </div>
                        </div>
                        <div id="reset-pin-box-${op.id}" style="display:none;padding-top:8px;border-top:1px dashed #CBD5E1;gap:8px;align-items:center;">
                            <input type="password" inputmode="numeric" id="reset-pin-input-${op.id}" placeholder="Novo PIN (4+ dígitos)"
                                style="flex:1;box-sizing:border-box;background:#FFFFFF;border:1.5px solid #CBD5E1;border-radius:8px;padding:7px 10px;font-size:11px;font-weight:800;color:#0F172A;outline:none;">
                            <button type="button" data-confirm-reset-pin="${op.id}" data-confirm-reset-name="${op.name}"
                                style="background:#124191;color:#FFFFFF;border:none;border-radius:8px;padding:8px 12px;font-size:9px;font-weight:900;text-transform:uppercase;cursor:pointer;">
                                SALVAR PIN
                            </button>
                        </div>
                    </div>
                `;
            }).join('') || '<p style="font-size:11px;color:#94A3B8;text-align:center;padding:14px 0;margin:0;">Nenhum perfil cadastrado.</p>';

            modal.innerHTML = `
                <div style="background:#FFFFFF;border-radius:18px;box-shadow:0 20px 45px rgba(15,23,42,0.35);width:100%;max-width:440px;max-height:88vh;display:flex;flex-direction:column;overflow:hidden;">
                    <div style="background:#124191;color:#FFFFFF;padding:18px 20px;border-bottom:4px solid #D32F2F;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
                        <div>
                            <p style="font-size:9px;font-weight:900;letter-spacing:0.1em;color:#93C5FD;text-transform:uppercase;margin:0 0 4px;">
                                KIPPE SUPERMERCADO · GOVERNANÇA
                            </p>
                            <h3 style="font-size:16px;font-weight:900;letter-spacing:0.02em;text-transform:uppercase;margin:0;">
                                Equipe &amp; Perfis
                            </h3>
                            <p style="font-size:10px;color:#DBEAFE;margin:4px 0 0;">
                                Cadastro, redefinição de PIN e exclusão de acessos
                            </p>
                        </div>
                        <button type="button" id="close-team-profiles"
                            style="background:rgba(255,255,255,0.14);border:1px solid rgba(255,255,255,0.22);color:#FFFFFF;width:32px;height:32px;border-radius:8px;font-size:14px;font-weight:900;cursor:pointer;flex-shrink:0;">
                            ✕
                        </button>
                    </div>

                    <div style="overflow-y:auto;flex:1;">
                        <form id="form-create-operator" style="padding:20px;background:#FFFFFF;border-bottom:1px solid #E2E8F0;display:flex;flex-direction:column;gap:14px;">
                            <div style="display:flex;align-items:center;gap:8px;padding-bottom:6px;border-bottom:1px dashed #E2E8F0;">
                                <span style="width:8px;height:8px;border-radius:999px;background:#124191;display:inline-block;"></span>
                                <p style="font-size:10px;font-weight:900;letter-spacing:0.07em;text-transform:uppercase;color:#124191;margin:0;">
                                    Novo Perfil de Acesso
                                </p>
                            </div>

                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                                <div>
                                    <label style="${labelStyle}">ID / Login</label>
                                    <input type="text" id="new-op-id" placeholder="EX: 2001" required
                                        style="${inputStyle}text-transform:uppercase;">
                                </div>
                                <div>
                                    <label style="${labelStyle}">PIN (4+ Dígitos)</label>
                                    <input type="password" inputmode="numeric" id="new-op-pin" placeholder="EX: 1234" required
                                        style="${inputStyle}">
                                </div>
                            </div>

                            <div>
                                <label style="${labelStyle}">Nome do Colaborador</label>
                                <input type="text" id="new-op-name" placeholder="EX: CARLOS CONFERENTE" required
                                    style="${inputStyle}text-transform:uppercase;">
                            </div>

                            <div>
                                <label style="${labelStyle}">Função / Perfil Operacional</label>
                                <select id="new-op-role" style="${inputStyle}font-weight:800;">
                                    <option value="CONFERENTE" selected>CONFERENTE (Doca / Conferência NF)</option>
                                    <option value="ESTOQUISTA">ESTOQUISTA (Cadastro / Armazenagem)</option>
                                    <option value="GERENTE">GERENTE (Gestão Operacional)</option>
                                    <option value="ADMIN_SISTEMA">ADMIN_SISTEMA (Acesso Total)</option>
                                </select>
                            </div>

                            <button type="submit" id="btn-submit-new-op"
                                style="width:100%;margin-top:4px;background:#124191;color:#FFFFFF;border:none;border-radius:12px;padding:13px 16px;font-size:11px;font-weight:900;letter-spacing:0.06em;text-transform:uppercase;box-shadow:0 4px 12px rgba(18,65,145,0.28);cursor:pointer;">
                                CADASTRAR PERFIL
                            </button>
                        </form>

                        <div style="padding:18px 20px 20px;background:#F8FAFC;display:flex;flex-direction:column;gap:10px;">
                            <p style="font-size:10px;font-weight:900;letter-spacing:0.07em;text-transform:uppercase;color:#64748B;margin:0 0 2px;">
                                Perfis Cadastrados (${list.length})
                            </p>
                            ${listHtml}
                        </div>
                    </div>

                    <div style="padding:10px 16px;background:#F1F5F9;border-top:1px solid #E2E8F0;text-align:center;">
                        <span style="font-size:9px;font-weight:800;letter-spacing:0.06em;color:#64748B;text-transform:uppercase;">
                            Acessos vinculados à auditoria operacional WMS
                        </span>
                    </div>
                </div>
            `;

            document.getElementById('close-team-profiles')?.addEventListener('click', () => modal.remove());
            modal.addEventListener('click', (ev) => {
                if (ev.target === modal) modal.remove();
            });

            modal.querySelectorAll('[data-toggle-reset-pin]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const opId = btn.getAttribute('data-toggle-reset-pin');
                    const box = document.getElementById(`reset-pin-box-${opId}`);
                    if (box) {
                        const isHidden = box.style.display === 'none';
                        box.style.display = isHidden ? 'flex' : 'none';
                        if (isHidden) {
                            document.getElementById(`reset-pin-input-${opId}`)?.focus();
                        }
                    }
                });
            });

            modal.querySelectorAll('[data-confirm-reset-pin]').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const opId = btn.getAttribute('data-confirm-reset-pin');
                    const opName = btn.getAttribute('data-confirm-reset-name');
                    const inp = document.getElementById(`reset-pin-input-${opId}`);
                    const newPin = inp?.value || '';
                    btn.disabled = true;
                    btn.textContent = '...';
                    try {
                        const res = await fetch(`/api/operators/${encodeURIComponent(opId)}/pin`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'same-origin',
                            body: JSON.stringify({ pin: newPin }),
                        });
                        const out = await res.json();
                        if (!res.ok) {
                            alert('❌ ' + (out.error || 'Erro ao redefinir PIN.'));
                            btn.disabled = false;
                            btn.textContent = 'SALVAR PIN';
                            return;
                        }
                        alert(`✅ PIN de ${opName} (${opId}) atualizado com sucesso!`);
                        if (inp) inp.value = '';
                        const box = document.getElementById(`reset-pin-box-${opId}`);
                        if (box) box.style.display = 'none';
                    } catch (err) {
                        alert('❌ ' + err.message);
                    } finally {
                        btn.disabled = false;
                        btn.textContent = 'SALVAR PIN';
                    }
                });
            });

            document.getElementById('form-create-operator')?.addEventListener('submit', async (ev) => {
                ev.preventDefault();
                const btn = document.getElementById('btn-submit-new-op');
                const payload = {
                    id: document.getElementById('new-op-id')?.value || '',
                    name: document.getElementById('new-op-name')?.value || '',
                    pin: document.getElementById('new-op-pin')?.value || '',
                    role: document.getElementById('new-op-role')?.value || 'CONFERENTE',
                };
                if (btn) {
                    btn.disabled = true;
                    btn.textContent = 'SALVANDO PERFIL...';
                }
                try {
                    const res = await fetch('/api/operators', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'same-origin',
                        body: JSON.stringify(payload),
                    });
                    const out = await res.json();
                    if (!res.ok) {
                        alert('❌ ' + (out.error || 'Erro ao criar perfil.'));
                        if (btn) {
                            btn.disabled = false;
                            btn.textContent = 'CADASTRAR PERFIL';
                        }
                        return;
                    }
                    const refreshed = await fetchOperators();
                    renderBody(refreshed);
                } catch (err) {
                    alert('❌ ' + err.message);
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = 'CADASTRAR PERFIL';
                    }
                }
            });

            modal.querySelectorAll('[data-del-op]').forEach(delBtn => {
                delBtn.addEventListener('click', async () => {
                    const opId = delBtn.getAttribute('data-del-op');
                    const opName = delBtn.getAttribute('data-del-name');
                    if (!confirm(`Excluir permanentemente o perfil ${opName} (${opId})?`)) return;
                    delBtn.disabled = true;
                    delBtn.textContent = '...';
                    try {
                        const res = await fetch(`/api/operators/${encodeURIComponent(opId)}`, {
                            method: 'DELETE',
                            credentials: 'same-origin',
                        });
                        const out = await res.json();
                        if (!res.ok) {
                            alert('❌ ' + (out.error || 'Falha ao excluir perfil.'));
                            delBtn.disabled = false;
                            delBtn.textContent = 'EXCLUIR';
                            return;
                        }
                        const refreshed = await fetchOperators();
                        renderBody(refreshed);
                    } catch (err) {
                        alert('❌ ' + err.message);
                        delBtn.disabled = false;
                        delBtn.textContent = 'EXCLUIR';
                    }
                });
            });
        };

        document.body.appendChild(modal);
        renderBody(operators);
    }

    canManageCatalog() {
        const role = String(
            this.currentOperator?.role || ''
        ).trim().toUpperCase();

        return (
            role === 'ESTOQUISTA'
            || role === 'GERENTE'
            || role === 'ADMIN_SISTEMA'
            || role === 'SYSTEM'
        );
    }

    canManageExistingStock() {
        return this.canManageCatalog();
    }

    updateExistingStockActionVisibility() {
        const allowed =
            this.canManageExistingStock();

        const catalogButton =
            document.getElementById(
                'btn-existing-stock-onboarding'
            );

        window.kippeCanManageCatalog = () => this.canManageCatalog();
        window.kippeCurrentOperator = () => this.currentOperator;
        const confFinBtn = document.getElementById('btn-conference-finalize');
        if (confFinBtn) {
            confFinBtn.textContent = allowed ? 'FINALIZAR CONFERÊNCIA' : '✅ CONCLUIR E ENVIAR P/ ESTOQUISTA';
        }

        const homeNewProdBtn = document.getElementById('btn-new-product-registration');
        if (homeNewProdBtn) {
            homeNewProdBtn.classList.toggle('hidden', !allowed);
        }

        const roleUpper = String(this.currentOperator?.role || '').trim().toUpperCase();
        const isConferente = roleUpper === 'CONFERENTE';
        [
            'btn-module-putaway',
            'btn-module-reports',
        ].forEach((modId) => {
            document.getElementById(modId)?.classList.toggle('hidden', isConferente);
        });
        document.getElementById('btn-module-replenishment')?.classList.remove('hidden');
        document.getElementById('btn-module-validity')?.classList.remove('hidden');
        document.getElementById('btn-module-receiving-audit')?.classList.remove('hidden');

        const inboundLabel = document.querySelector('#btn-module-inbound h3');
        if (inboundLabel) {
            inboundLabel.textContent = isConferente ? '1. CONFERÊNCIA NF' : '1. RECEBER';
        }
        const repLabel = document.querySelector('#btn-module-replenishment h3');
        if (repLabel) {
            repLabel.textContent = isConferente ? '2. ABASTECER' : '3. ABASTECER';
        }
        const scanLabel = document.querySelector('#btn-module-scan h3');
        if (scanLabel) {
            scanLabel.textContent = isConferente ? '3. CONSULTA EAN' : '4. CONSULTA';
        }
        const validityLabel = document.querySelector('#btn-module-validity h3');
        if (validityLabel) {
            validityLabel.textContent = isConferente ? '4. VALIDADE' : '6. VALIDADE';
        }
        const auditLabel = document.querySelector('#btn-module-receiving-audit h3');
        if (auditLabel) {
            auditLabel.textContent = isConferente ? '5. RECEBIMENTOS' : '7. RECEBIMENTOS';
        }

        if (this.currentOperator?.id && typeof this.refreshEstoquistaPendingQueue === 'function') {
            this.refreshEstoquistaPendingQueue();
        } else {
            document.getElementById('estoquista-pending-card')?.remove();
        }
        if (typeof this.syncAdminTeamButton === 'function') {
            this.syncAdminTeamButton();
        }
        if (typeof this.syncSelfPinButton === 'function') {
            this.syncSelfPinButton();
        }

        if (catalogButton) {
            catalogButton.classList.toggle(
                'hidden',
                !(
                    allowed
                    && this.currentCatalogProduct
                )
            );
        }

        const newProductButton =
            document.getElementById(
                'continue-new-product-existing-stock'
            );

        if (newProductButton) {
            newProductButton.classList.toggle(
                'hidden',
                !allowed
            );
        }
    }

    resetExistingStockForm() {
        const fields = [
            'existing-stock-quantity',
            'existing-stock-batch',
            'existing-stock-expiration',
            'existing-stock-manufacturing',
            'existing-stock-location',
            'existing-stock-supplier',
            'existing-stock-document',
            'existing-stock-historical-date',
            'existing-stock-historical-basis',
        ];

        fields.forEach(
            (id) => {
                const element =
                    document.getElementById(id);

                if (element) {
                    element.value = '';
                }
            }
        );

        const errorPanel =
            document.getElementById(
                'existing-stock-error'
            );

        if (errorPanel) {
            errorPanel.textContent = '';
            errorPanel.classList.add(
                'hidden'
            );
        }
    }

    closeExistingStockOnboarding() {
        document.getElementById(
            'existing-stock-modal'
        )?.classList.add(
            'hidden'
        );

        this.resetExistingStockForm();

        this.existingStockProduct = null;
    }

    async openExistingStockOnboarding(
        product
    ) {
        if (!this.canManageExistingStock()) {
            return;
        }

        let target = product;

        if (
            typeof target === 'string'
        ) {
            try {
                target =
                    await this.api.queryProduct(
                        target
                    );
            } catch (error) {
                alert(
                    'Não foi possível identificar o produto.'
                );

                return;
            }
        }

        if (
            !target
            || !(
                target.id
                || target.sku
            )
        ) {
            return;
        }

        this.existingStockProduct =
            target;

        this.resetExistingStockForm();

        const sku =
            target.id
            || target.sku
            || '';

        const ean =
            target.ean
            || target.barcode
            || '';

        const name =
            target.name
            || target.description
            || 'PRODUTO';

        const setText = (
            id,
            value
        ) => {
            const element =
                document.getElementById(
                    id
                );

            if (element) {
                element.textContent =
                    value || '—';
            }
        };

        setText(
            'existing-stock-product-name',
            name
        );

        setText(
            'existing-stock-product-sku',
            sku
        );

        setText(
            'existing-stock-product-ean',
            ean
        );

        document.getElementById(
            'new-product-success-modal'
        )?.classList.add(
            'hidden'
        );

        document.getElementById(
            'existing-stock-success-modal'
        )?.classList.add(
            'hidden'
        );

        document.getElementById(
            'existing-stock-modal'
        )?.classList.remove(
            'hidden'
        );

        window.setTimeout(
            () => {
                document.getElementById(
                    'existing-stock-quantity'
                )?.focus();
            },
            50
        );
    }

    showExistingStockError(
        message
    ) {
        const panel =
            document.getElementById(
                'existing-stock-error'
            );

        if (!panel) {
            return;
        }

        panel.textContent =
            message
            || 'Não foi possível incorporar o estoque existente.';

        panel.classList.remove(
            'hidden'
        );
    }

    bindExistingStockOnboarding() {
        document.getElementById(
            'continue-new-product-existing-stock'
        )?.addEventListener(
            'click',
            async () => {
                let product =
                    this.existingStockProduct;

                if (!product) {
                    const sku =
                        document.getElementById(
                            'new-product-success-sku'
                        )?.textContent?.trim();

                    const ean =
                        document.getElementById(
                            'new-product-success-ean'
                        )?.textContent?.trim();

                    const name =
                        document.getElementById(
                            'new-product-success-name'
                        )?.textContent?.trim();

                    if (
                        !sku
                        || sku === '—'
                    ) {
                        return;
                    }

                    product = {
                        sku,
                        ean:
                            ean === '—'
                                ? ''
                                : ean,
                        name:
                            name === '—'
                                ? ''
                                : name,
                    };

                    this.existingStockProduct =
                        product;
                }

                await this.openExistingStockOnboarding(
                    product
                );
            }
        );

        document.getElementById(
            'btn-existing-stock-onboarding'
        )?.addEventListener(
            'click',
            async () => {
                if (
                    !this.currentCatalogProduct
                ) {
                    return;
                }

                await this.openExistingStockOnboarding(
                    this.currentCatalogProduct
                );
            }
        );

        document.getElementById(
            'close-existing-stock-modal'
        )?.addEventListener(
            'click',
            () => {
                this.closeExistingStockOnboarding();
            }
        );

        document.getElementById(
            'cancel-existing-stock'
        )?.addEventListener(
            'click',
            () => {
                this.closeExistingStockOnboarding();
            }
        );

        document.getElementById(
            'finish-existing-stock'
        )?.addEventListener(
            'click',
            () => {
                document.getElementById(
                    'existing-stock-success-modal'
                )?.classList.add(
                    'hidden'
                );

                this.existingStockProduct = null;
            }
        );

        document.getElementById(
            'submit-existing-stock'
        )?.addEventListener(
            'click',
            async () => {
                const product =
                    this.existingStockProduct;

                if (!product) {
                    this.showExistingStockError(
                        'Produto não identificado.'
                    );

                    return;
                }

                const read = (
                    id
                ) => {
                    return (
                        document.getElementById(
                            id
                        )?.value?.trim()
                        || ''
                    );
                };

                const quantity =
                    Number(
                        read(
                            'existing-stock-quantity'
                        )
                    );

                const batchCode =
                    read(
                        'existing-stock-batch'
                    );

                const expirationDate =
                    read(
                        'existing-stock-expiration'
                    );

                const manufacturingDate =
                    read(
                        'existing-stock-manufacturing'
                    );

                const locationId =
                    read(
                        'existing-stock-location'
                    );

                const supplier =
                    read(
                        'existing-stock-supplier'
                    );

                const documentId =
                    read(
                        'existing-stock-document'
                    );

                const historicalReceiptDate =
                    read(
                        'existing-stock-historical-date'
                    );

                const historicalDateBasis =
                    read(
                        'existing-stock-historical-basis'
                    );

                if (
                    !Number.isInteger(
                        quantity
                    )
                    || quantity <= 0
                ) {
                    this.showExistingStockError(
                        'Informe uma quantidade física válida, maior que zero.'
                    );

                    return;
                }

                if (
                    !batchCode
                    || !expirationDate
                ) {
                    this.showExistingStockError(
                        'Informe lote e validade.'
                    );

                    return;
                }

                /*
                 * Historical evidence is optional.
                 *
                 * Nunca inferimos uma data histórica.
                 * Se houver data histórica, a fonte da
                 * evidência também precisa ser declarada.
                 */
                if (
                    historicalReceiptDate
                    && !historicalDateBasis
                ) {
                    this.showExistingStockError(
                        'Selecione a base da informação histórica.'
                    );

                    return;
                }

                if (
                    historicalDateBasis
                    && !historicalReceiptDate
                ) {
                    this.showExistingStockError(
                        'Informe a data histórica correspondente.'
                    );

                    return;
                }

                if (
                    historicalDateBasis === 'DOCUMENT'
                    && !documentId
                ) {
                    this.showExistingStockError(
                        'Uma informação histórica baseada em DOCUMENT exige NF ou documento.'
                    );

                    return;
                }

                const errorPanel =
                    document.getElementById(
                        'existing-stock-error'
                    );

                errorPanel?.classList.add(
                    'hidden'
                );

                const submitButton =
                    document.getElementById(
                        'submit-existing-stock'
                    );

                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.textContent =
                        'INCORPORANDO...';
                }

                try {
                    const sku =
                        product.id
                        || product.sku;

                    const payload = {
                        sku,
                        quantity,
                        batch_code:
                            batchCode,
                        expiration_date:
                            expirationDate,
                        manufacturing_date:
                            manufacturingDate || null,
                        location_id:
                            locationId || null,
                        supplier:
                            supplier || null,
                        document_id:
                            documentId || null,
                        historical_receipt_date:
                            historicalReceiptDate || null,
                        historical_date_basis:
                            historicalDateBasis || null,
                    };

                    const response =
                        await this.api.onboardExistingStock(
                            payload
                        );

                    const onboarding =
                        response.onboarding
                        || response.stock_onboarding
                        || response;

                    const details =
                        document.getElementById(
                            'existing-stock-success-details'
                        );

                    if (details) {
                        details.textContent =
                            `${
                                onboarding.quantity
                                ?? quantity
                            } UN • LOTE ${
                                onboarding.batch_code
                                || batchCode
                            }`;
                    }

                    document.getElementById(
                        'existing-stock-modal'
                    )?.classList.add(
                        'hidden'
                    );

                    document.getElementById(
                        'existing-stock-success-modal'
                    )?.classList.remove(
                        'hidden'
                    );

                    await this.fetchAndRenderSku(
                        sku
                    );

                } catch (error) {
                    this.showExistingStockError(
                        error.message
                        || 'Falha ao incorporar estoque existente.'
                    );

                } finally {
                    if (submitButton) {
                        submitButton.disabled =
                            false;

                        submitButton.textContent =
                            'INCORPORAR ESTOQUE EXISTENTE';
                    }
                }
            }
        );

        this.updateExistingStockActionVisibility();
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
                'new-product-success-modal'
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

        if (eanInput) {
            eanInput.removeAttribute('readonly');
            eanInput.disabled = false;
            eanInput.setAttribute('inputmode', 'numeric');
            eanInput.setAttribute('pattern', '[0-9]*');
            eanInput.setAttribute('enterkeyhint', 'done');
            eanInput.placeholder = 'Digite ou bipe o EAN (0-9)';
            const eanRow = eanInput.parentElement;
            if (eanRow && !eanRow.querySelector('#btn-new-product-keypad')) {
                const keyBtn = document.createElement('button');
                keyBtn.type = 'button';
                keyBtn.id = 'btn-new-product-keypad';
                keyBtn.className = 'bg-slate-700 text-white px-3 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-wider active:scale-95 shrink-0';
                keyBtn.style.cssText = 'background:#334155;color:#FFFFFF;padding:10px 10px;border-radius:12px;font-size:10px;font-weight:900;white-space:nowrap;';
                keyBtn.textContent = 'TECLADO';
                keyBtn.addEventListener('click', () => {
                    eanInput.removeAttribute('readonly');
                    eanInput.setAttribute('inputmode', 'numeric');
                    eanInput.focus();
                    eanInput.select();
                });
                eanRow.appendChild(keyBtn);
            }
        }

        const goToStockEntryForSku = async (targetSku, targetEan, targetName) => {
            if (this._pendingProductRequest?.reqId) {
                const reqId = this._pendingProductRequest.reqId;
                this._pendingProductRequest = null;
                await fetch(`/api/receiving/pending/${reqId}/resolve-product`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        action: 'CADASTRADO',
                        sku: targetSku,
                        ean: targetEan || '',
                        name: targetName || ''
                    })
                }).catch(() => null);
                modal?.classList.add('hidden');
                await this.refreshEstoquistaPendingQueue();
                document.getElementById('btn-open-estoquista-queue')?.click();
                return;
            }
            modal?.classList.add('hidden');
            if (typeof this.fetchAndRenderSku === 'function') {
                await this.fetchAndRenderSku(targetSku);
            }
            const receiveTrigger =
                document.getElementById('btn-open-receive') ||
                document.querySelector('[data-action="receive"], #btn-receive-product');
            if (receiveTrigger) {
                receiveTrigger.click();
            } else {
                const recModal = document.getElementById('receive-modal');
                const recSku = document.getElementById('receive-sku');
                if (recSku) recSku.value = targetSku;
                recModal?.classList.remove('hidden');
            }
        };

        if (errorPanel && !errorPanel.dataset.existingSkuObserver) {
            errorPanel.dataset.existingSkuObserver = '1';
            const obs = new MutationObserver(() => {
                const txt = errorPanel.textContent || '';
                const m = txt.match(/\[([A-Z0-9-]+)\]\s*([^.\n]+)/i);
                let actionBtn = errorPanel.querySelector('#btn-link-existing-and-receive');
                if (!m) {
                    actionBtn?.remove();
                    return;
                }
                const foundSku = m[1].trim().toUpperCase();
                const foundName = m[2].trim();
                if (!actionBtn) {
                    actionBtn = document.createElement('button');
                    actionBtn.type = 'button';
                    actionBtn.id = 'btn-link-existing-and-receive';
                    actionBtn.style.cssText = 'margin-top:10px;width:100%;background:#124191;color:#FFFFFF;padding:10px 12px;border-radius:10px;font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:0.03em;cursor:pointer;display:block;';
                    errorPanel.appendChild(actionBtn);
                }
                actionBtn.textContent = 'VINCULAR AO ' + foundSku + ' E DAR ENTRADA';
                actionBtn.onclick = async () => {
                    actionBtn.disabled = true;
                    actionBtn.textContent = 'ABRINDO ENTRADA...';
                    await goToStockEntryForSku(foundSku, eanInput?.value.trim() || '', foundName);
                };
            });
            obs.observe(errorPanel, { childList: true, subtree: true, characterData: true });
        }

        if (!this._pendingProductRequest) {
            const prevSup = document.getElementById('rec-supplier')?.value.trim() || '';
            const prevInv = document.getElementById('rec-invoice')?.value.trim() || '';
            if (prevSup || prevInv) {
                this._lastReceivingContext = {
                    supplier: prevSup,
                    invoice_number: prevInv,
                    nf_qty: 1,
                    pack_factor: 1,
                    batch_code: '',
                    expiration_date: '',
                };
            } else {
                this._lastReceivingContext = null;
            }
        }

        const successCard = successPanel?.firstElementChild || successPanel;
        if (successCard) {
            successCard.querySelector('#btn-new-prod-direct-receive')?.remove();

            if (!successCard.querySelector('#btn-new-prod-back-queue')) {
                const queueBtnStyle = [
                    'margin-top:12px;width:100%;background:#059669;color:#FFFFFF;',
                    'padding:12px 14px;border-radius:12px;font-size:11px;font-weight:900;',
                    'text-transform:uppercase;letter-spacing:0.03em;cursor:pointer;',
                    'display:block;border:none;box-shadow:0 2px 6px rgba(5,150,105,0.25);'
                ].join('');
                const backQueueBtn = document.createElement('button');
                backQueueBtn.type = 'button';
                backQueueBtn.id = 'btn-new-prod-back-queue';
                backQueueBtn.style.cssText = queueBtnStyle;
                backQueueBtn.textContent = 'VOLTAR PARA FILA DA NF';
                backQueueBtn.addEventListener('click', async () => {
                    modal?.classList.add('hidden');
                    await this.refreshEstoquistaPendingQueue();
                    document.getElementById('btn-open-estoquista-queue')?.click();
                });
                successCard.appendChild(backQueueBtn);
            }
            const backQueueEl = successCard.querySelector('#btn-new-prod-back-queue');
            if (backQueueEl) {
                backQueueEl.style.display = this._lastReceivingContext?.reqId ? 'block' : 'none';
            }

            if (!successCard.querySelector('#btn-new-prod-success-close')) {
                const closeStyle = [
                    'margin-top:8px;width:100%;background:#FFFFFF;color:#475569;',
                    'padding:11px 14px;border-radius:12px;font-size:11px;font-weight:900;',
                    'text-transform:uppercase;letter-spacing:0.03em;cursor:pointer;',
                    'display:block;border:1.5px solid #CBD5E1;'
                ].join('');
                const closeSuccessBtn = document.createElement('button');
                closeSuccessBtn.type = 'button';
                closeSuccessBtn.id = 'btn-new-prod-success-close';
                closeSuccessBtn.style.cssText = closeStyle;
                closeSuccessBtn.textContent = 'FECHAR';
                closeSuccessBtn.addEventListener('click', () => {
                    modal?.classList.add('hidden');
                });
                successCard.appendChild(closeSuccessBtn);
            }
        }

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
        this.lastReceivingResult = null;

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
        hide('receive-success-modal');

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


    resetCertifiedInvoiceReceiving() {
        this.certifiedInvoicePayload = null;
        this.certifiedInvoicePreview = null;
        this.certifiedConferenceCounts = {};
        this.certifiedPhysicalData = {};
        this.certifiedReceivingSubmitting = false;

        const jsonInput =
            document.getElementById(
                'certified-invoice-json'
            );

        if (jsonInput) {
            jsonInput.value = '';
        }

        document.getElementById(
            'certified-invoice-conference'
        )?.classList.add(
            'hidden'
        );

        document.getElementById(
            'certified-invoice-execution-result'
        )?.classList.add(
            'hidden'
        );

        document.getElementById(
            'certified-invoice-divergence'
        )?.classList.add(
            'hidden'
        );

        const lines =
            document.getElementById(
                'certified-invoice-lines'
            );

        if (lines) {
            lines.innerHTML = '';
        }

        this.showCertifiedInvoiceError('');
    }

    showCertifiedInvoiceError(message) {
        const panel =
            document.getElementById(
                'certified-invoice-error'
            );

        if (!panel) {
            return;
        }

        panel.textContent =
            message || '';

        panel.classList.toggle(
            'hidden',
            !message
        );
    }

    getCertifiedLineNumber(line, index) {
        const candidate =
            Number(
                line?.line_number
                ?? line?.line
                ?? line?.number
                ?? index + 1
            );

        return Number.isInteger(candidate)
            ? candidate
            : index + 1;
    }

    getCertifiedFiscalQuantity(line) {
        const candidate =
            Number(
                line?.fiscal_quantity
                ?? line?.quantity
                ?? line?.document_quantity
                ?? line?.expected_quantity
                ?? 0
            );

        return Number.isFinite(candidate)
            ? candidate
            : 0;
    }

    isCertifiedLineBlocked(line) {
        const status =
            String(
                line?.status
                ?? line?.reconciliation_status
                ?? ''
            ).toUpperCase();

        return (
            status === 'NEEDS_REGISTRATION'
            || status === 'PENDING_REGISTRATION'
            || status === 'UNRESOLVED'
        );
    }

    renderCertifiedInvoicePreview(preview) {
        const lines =
            Array.isArray(preview?.lines)
                ? preview.lines
                : [];

        const setText = (
            id,
            value
        ) => {
            const element =
                document.getElementById(id);

            if (element) {
                element.textContent =
                    value ?? '—';
            }
        };

        setText(
            'certified-invoice-number',
            preview?.invoice_number
            ?? this.certifiedInvoicePayload?.invoice_number
            ?? this.certifiedInvoicePayload?.number
            ?? '—'
        );

        setText(
            'certified-invoice-supplier',
            preview?.supplier_id
            ?? preview?.supplier
            ?? this.certifiedInvoicePayload?.supplier_id
            ?? this.certifiedInvoicePayload?.supplier
            ?? '—'
        );

        const container =
            document.getElementById(
                'certified-invoice-lines'
            );

        if (!container) {
            return;
        }

        container.innerHTML = '';

        this.certifiedConferenceCounts = {};
        this.certifiedPhysicalData = {};

        lines.forEach(
            (line, index) => {
                const lineNumber =
                    this.getCertifiedLineNumber(
                        line,
                        index
                    );

                const fiscalQuantity =
                    this.getCertifiedFiscalQuantity(
                        line
                    );

                const blocked =
                    this.isCertifiedLineBlocked(
                        line
                    );

                const status =
                    String(
                        line?.status
                        ?? line?.reconciliation_status
                        ?? 'UNKNOWN'
                    );

                const product =
                    line?.product_name
                    ?? line?.name
                    ?? line?.description
                    ?? line?.fiscal_description
                    ?? line?.product_id
                    ?? line?.sku
                    ?? 'PRODUTO';

                const productId =
                    line?.product_id
                    ?? line?.sku
                    ?? '—';

                const card =
                    document.createElement(
                        'section'
                    );

                card.className =
                    blocked
                        ? 'bg-red-50 border-2 border-red-200 rounded-xl p-3'
                        : 'bg-white border border-gray-200 rounded-xl p-3 shadow-sm';

                const heading =
                    document.createElement(
                        'div'
                    );

                heading.className =
                    'flex justify-between items-start gap-2';

                const info =
                    document.createElement(
                        'div'
                    );

                const title =
                    document.createElement(
                        'p'
                    );

                title.className =
                    'text-[11px] font-black text-gray-900';

                title.textContent =
                    `${lineNumber}. ${product}`;

                const sku =
                    document.createElement(
                        'p'
                    );

                sku.className =
                    'text-[8px] font-mono font-bold text-gray-500 mt-1';

                sku.textContent =
                    `SKU: ${productId}`;

                info.appendChild(title);
                info.appendChild(sku);

                const badge =
                    document.createElement(
                        'span'
                    );

                badge.className =
                    blocked
                        ? 'shrink-0 text-[8px] font-black bg-red-100 text-red-700 rounded px-2 py-1'
                        : 'shrink-0 text-[8px] font-black bg-green-100 text-green-700 rounded px-2 py-1';

                badge.textContent =
                    status;

                heading.appendChild(info);
                heading.appendChild(badge);
                card.appendChild(heading);

                const fiscal =
                    document.createElement(
                        'p'
                    );

                fiscal.className =
                    'text-[9px] font-bold text-gray-600 mt-3';

                fiscal.textContent =
                    `QUANTIDADE FISCAL: ${fiscalQuantity}`;

                card.appendChild(fiscal);

                if (blocked) {
                    const warning =
                        document.createElement(
                            'p'
                        );

                    warning.className =
                        'text-[9px] font-black text-red-700 mt-3';

                    warning.textContent =
                        'PRODUTO EXIGE CADASTRO. RECEBIMENTO BLOQUEADO PARA ESTA LINHA.';

                    card.appendChild(
                        warning
                    );

                    container.appendChild(
                        card
                    );

                    return;
                }

                const countLabel =
                    document.createElement(
                        'label'
                    );

                countLabel.className =
                    'block text-[9px] font-black text-[#124191] mt-3';

                countLabel.textContent =
                    'QUANTIDADE FÍSICA CONTADA';

                const count =
                    document.createElement(
                        'input'
                    );

                count.type = 'number';
                count.min = '0';
                count.step = '1';
                count.inputMode = 'numeric';
                count.value =
                    String(
                        Math.max(
                            0,
                            fiscalQuantity
                        )
                    );

                count.dataset.certifiedLine =
                    String(lineNumber);

                count.className =
                    'certified-line-count w-full mt-1 border-2 border-[#124191] rounded-xl px-3 py-3 text-2xl text-center font-black text-[#124191]';

                this.certifiedConferenceCounts[
                    lineNumber
                ] = Number(count.value);

                count.addEventListener(
                    'input',
                    () => {
                        const value =
                            Number(count.value);

                        this.certifiedConferenceCounts[
                            lineNumber
                        ] =
                            Number.isFinite(value)
                                ? value
                                : 0;

                        this.updateCertifiedInvoiceDivergence();
                    }
                );

                card.appendChild(
                    countLabel
                );

                card.appendChild(
                    count
                );

                const traceGrid =
                    document.createElement(
                        'div'
                    );

                traceGrid.className =
                    'grid grid-cols-2 gap-2 mt-3';

                const makeField = (
                    labelText,
                    type,
                    fieldName,
                    required
                ) => {
                    const wrapper =
                        document.createElement(
                            'div'
                        );

                    const label =
                        document.createElement(
                            'label'
                        );

                    label.className =
                        'block text-[8px] font-black text-gray-500';

                    label.textContent =
                        labelText;

                    const input =
                        document.createElement(
                            'input'
                        );

                    input.type = type;

                    input.className =
                        'w-full mt-1 border border-gray-300 rounded-lg p-2 text-[10px] font-bold';

                    input.dataset.certifiedLine =
                        String(lineNumber);

                    input.dataset.certifiedField =
                        fieldName;

                    if (required) {
                        input.required = true;
                    }

                    input.addEventListener(
                        'input',
                        () => {
                            const physical =
                                this.certifiedPhysicalData[
                                    lineNumber
                                ] || {};

                            physical[
                                fieldName
                            ] =
                                input.value;

                            this.certifiedPhysicalData[
                                lineNumber
                            ] =
                                physical;
                        }
                    );

                    wrapper.appendChild(
                        label
                    );

                    wrapper.appendChild(
                        input
                    );

                    return wrapper;
                };

                traceGrid.appendChild(
                    makeField(
                        'LOTE',
                        'text',
                        'batch_code',
                        true
                    )
                );

                traceGrid.appendChild(
                    makeField(
                        'VALIDADE',
                        'date',
                        'expiration_date',
                        true
                    )
                );

                traceGrid.appendChild(
                    makeField(
                        'FABRICAÇÃO (OPCIONAL)',
                        'date',
                        'manufacturing_date',
                        false
                    )
                );

                card.appendChild(
                    traceGrid
                );

                this.certifiedPhysicalData[
                    lineNumber
                ] = {
                    batch_code: '',
                    expiration_date: '',
                    manufacturing_date: '',
                };

                container.appendChild(
                    card
                );
            }
        );

        document.getElementById(
            'certified-invoice-conference'
        )?.classList.remove(
            'hidden'
        );

        document.getElementById(
            'certified-invoice-execution-result'
        )?.classList.add(
            'hidden'
        );

        this.updateCertifiedInvoiceDivergence();
    }

    updateCertifiedInvoiceDivergence() {
        const lines =
            Array.isArray(
                this.certifiedInvoicePreview?.lines
            )
                ? this.certifiedInvoicePreview.lines
                : [];

        let divergent = 0;

        lines.forEach(
            (line, index) => {
                if (
                    this.isCertifiedLineBlocked(
                        line
                    )
                ) {
                    return;
                }

                const lineNumber =
                    this.getCertifiedLineNumber(
                        line,
                        index
                    );

                const fiscal =
                    this.getCertifiedFiscalQuantity(
                        line
                    );

                const physical =
                    Number(
                        this.certifiedConferenceCounts[
                            lineNumber
                        ]
                    );

                if (
                    Number.isFinite(physical)
                    && physical !== fiscal
                ) {
                    divergent += 1;
                }
            }
        );

        const panel =
            document.getElementById(
                'certified-invoice-divergence'
            );

        const text =
            document.getElementById(
                'certified-invoice-divergence-text'
            );

        if (text) {
            text.textContent =
                divergent === 0
                    ? ''
                    : (
                        divergent === 1
                            ? '1 linha possui quantidade física diferente da quantidade fiscal.'
                            : `${divergent} linhas possuem quantidade física diferente da quantidade fiscal.`
                    );
        }

        panel?.classList.toggle(
            'hidden',
            divergent === 0
        );
    }

    validateCertifiedPhysicalData() {
        const lines =
            Array.isArray(
                this.certifiedInvoicePreview?.lines
            )
                ? this.certifiedInvoicePreview.lines
                : [];

        for (
            let index = 0;
            index < lines.length;
            index += 1
        ) {
            const line =
                lines[index];

            if (
                this.isCertifiedLineBlocked(
                    line
                )
            ) {
                continue;
            }

            const lineNumber =
                this.getCertifiedLineNumber(
                    line,
                    index
                );

            const quantity =
                Number(
                    this.certifiedConferenceCounts[
                        lineNumber
                    ]
                );

            if (
                !Number.isInteger(quantity)
                || quantity < 0
            ) {
                throw new Error(
                    `Linha ${lineNumber}: informe a quantidade física contada.`
                );
            }

            /*
             * Quantidade zero não produz mutação.
             * O J.9 reporta skipped_zero_quantity_lines.
             */
            if (quantity === 0) {
                continue;
            }

            const physical =
                this.certifiedPhysicalData[
                    lineNumber
                ] || {};

            if (
                !String(
                    physical.batch_code || ''
                ).trim()
                || !String(
                    physical.expiration_date || ''
                ).trim()
            ) {
                throw new Error(
                    `Linha ${lineNumber}: informe lote e validade.`
                );
            }
        }
    }

    async reconcileCertifiedInvoice() {
        const raw =
            document.getElementById(
                'certified-invoice-json'
            )?.value?.trim();

        if (!raw) {
            this.showCertifiedInvoiceError(
                'Informe o documento fiscal JSON.'
            );

            return;
        }

        let invoice;

        try {
            invoice =
                JSON.parse(raw);
        } catch (error) {
            this.showCertifiedInvoiceError(
                'JSON fiscal inválido.'
            );

            return;
        }

        if (
            !invoice
            || typeof invoice !== 'object'
            || Array.isArray(invoice)
        ) {
            this.showCertifiedInvoiceError(
                'O documento fiscal deve ser um objeto JSON.'
            );

            return;
        }

        this.showCertifiedInvoiceError('');

        const button =
            document.getElementById(
                'btn-certified-invoice-reconcile'
            );

        if (button) {
            button.disabled = true;
            button.textContent =
                'RECONCILIANDO...';
        }

        document.getElementById(
            'loader'
        )?.classList.remove(
            'hidden'
        );

        try {
            const preview =
                await this.api.reconcileSupplierInvoice(
                    invoice
                );

            this.certifiedInvoicePayload =
                invoice;

            this.certifiedInvoicePreview =
                preview;

            this.renderCertifiedInvoicePreview(
                preview
            );

        } catch (error) {
            this.certifiedInvoicePayload =
                null;

            this.certifiedInvoicePreview =
                null;

            this.showCertifiedInvoiceError(
                error.message
                || 'Falha ao reconciliar a nota fiscal.'
            );

        } finally {
            document.getElementById(
                'loader'
            )?.classList.add(
                'hidden'
            );

            if (button) {
                button.disabled = false;
                button.textContent =
                    'ANALISAR E RECONCILIAR NF';
            }
        }
    }

    renderCertifiedExecutionResult(result) {
        const resultPanel =
            document.getElementById(
                'certified-invoice-execution-result'
            );

        const summary =
            document.getElementById(
                'certified-invoice-execution-summary'
            );

        const lineContainer =
            document.getElementById(
                'certified-invoice-execution-lines'
            );

        if (summary) {
            summary.innerHTML = '';

            const values = [
                [
                    'LINHAS',
                    result?.total_lines ?? 0
                ],
                [
                    'EXECUTADAS',
                    result?.executed_lines ?? 0
                ],
                [
                    'REPLAY',
                    result?.replay_lines ?? 0
                ],
                [
                    'DIVERGENTES',
                    result?.divergent_lines ?? 0
                ],
                [
                    'QUANTIDADE ZERO',
                    result?.skipped_zero_quantity_lines ?? 0
                ],
            ];

            values.forEach(
                ([label, value]) => {
                    const row =
                        document.createElement(
                            'p'
                        );

                    row.className =
                        'font-bold';

                    row.textContent =
                        `${label}: ${value}`;

                    summary.appendChild(
                        row
                    );
                }
            );
        }

        if (lineContainer) {
            lineContainer.innerHTML = '';

            const resultLines =
                Array.isArray(result?.lines)
                    ? result.lines
                    : [];

            resultLines.forEach(
                (line) => {
                    const row =
                        document.createElement(
                            'div'
                        );

                    row.className =
                        'bg-white border border-green-200 rounded-lg p-2';

                    const status =
                        String(
                            line?.operation_status
                            ?? line?.status
                            ?? 'UNKNOWN'
                        );

                    row.textContent =
                        `LINHA ${line?.line_number ?? '—'} • ${status}`;

                    lineContainer.appendChild(
                        row
                    );
                }
            );
        }

        resultPanel?.classList.remove(
            'hidden'
        );
    }

    async executeCertifiedInvoiceReceiving() {
        if (
            this.certifiedReceivingSubmitting
        ) {
            return;
        }

        if (
            !this.certifiedInvoicePayload
            || !this.certifiedInvoicePreview
        ) {
            this.showCertifiedInvoiceError(
                'Reconcilie a nota fiscal antes de executar.'
            );

            return;
        }

        try {
            this.validateCertifiedPhysicalData();
        } catch (error) {
            this.showCertifiedInvoiceError(
                error.message
            );

            return;
        }

        this.showCertifiedInvoiceError('');
        this.updateCertifiedInvoiceDivergence();

        const button =
            document.getElementById(
                'btn-certified-invoice-execute'
            );

        this.certifiedReceivingSubmitting =
            true;

        if (button) {
            button.disabled = true;
            button.textContent =
                'PROCESSANDO RECEBIMENTO...';
        }

        document.getElementById(
            'loader'
        )?.classList.remove(
            'hidden'
        );

        try {
            const result =
                await this.api.receiveCertifiedInvoice({
                    invoice:
                        this.certifiedInvoicePayload,
                    conference: {
                        counts:
                            this.certifiedConferenceCounts,
                        physical_data:
                            this.certifiedPhysicalData,
                    },
                });

            this.renderCertifiedExecutionResult(
                result
            );

            /*
             * Mantém o botão bloqueado após sucesso.
             * Replay é responsabilidade do backend, mas a UI também
             * impede duplo clique e reenvio acidental.
             */
            if (button) {
                button.disabled = true;
                button.textContent =
                    'RECEBIMENTO PROCESSADO';
            }

        } catch (error) {
            this.certifiedReceivingSubmitting =
                false;

            this.showCertifiedInvoiceError(
                error.message
                || 'Falha no recebimento certificado.'
            );

            if (button) {
                button.disabled = false;
                button.textContent =
                    'CONFIRMAR RECEBIMENTO CERTIFICADO';
            }

        } finally {
            document.getElementById(
                'loader'
            )?.classList.add(
                'hidden'
            );
        }
    }

    bindCertifiedInvoiceReceiving() {
        const modal =
            document.getElementById(
                'certified-invoice-modal'
            );

        const methodModal =
            document.getElementById(
                'inbound-method-modal'
            );

        document.getElementById(
            'btn-inbound-certified-invoice'
        )?.addEventListener(
            'click',
            () => {
                this.resetCertifiedInvoiceReceiving();

                methodModal?.classList.add(
                    'hidden'
                );

                modal?.classList.remove(
                    'hidden'
                );
            }
        );

        document.getElementById(
            'close-certified-invoice'
        )?.addEventListener(
            'click',
            () => {
                modal?.classList.add(
                    'hidden'
                );

                this.resetCertifiedInvoiceReceiving();
            }
        );

        document.getElementById(
            'btn-certified-invoice-reconcile'
        )?.addEventListener(
            'click',
            async () => {
                await this.reconcileCertifiedInvoice();
            }
        );

        document.getElementById(
            'btn-certified-invoice-execute'
        )?.addEventListener(
            'click',
            async () => {
                await this.executeCertifiedInvoiceReceiving();
            }
        );
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

                    this.existingStockProduct = product;

                    if (
                        !product ||
                        !product.id
                    ) {
                        throw new Error(
                            'Backend não retornou o SKU gerado.'
                        );
                    }

                    if (this._pendingProductRequest) {
                        const pendingReq = this._pendingProductRequest;
                        this._pendingProductRequest = null;
                        const resCtrl = new AbortController();
                        const resTimer = setTimeout(() => resCtrl.abort(), 10000);
                        await fetch(`/api/receiving/pending/${pendingReq.reqId}/resolve-product`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'same-origin',
                            signal: resCtrl.signal,
                            body: JSON.stringify({
                                action: 'CADASTRADO',
                                sku: product.id,
                                created_sku: product.id,
                                name: String(product.name || name).toUpperCase(),
                                ean: product.ean || ean
                            })
                        }).catch(() => {}).finally(() => clearTimeout(resTimer));
                        this.refreshEstoquistaPendingQueue();
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
                        'new-product-success-modal'
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

                const ctx = this._lastReceivingContext;
                if (ctx) {
                    const supEl = document.getElementById('rec-supplier');
                    const invEl = document.getElementById('rec-invoice');
                    const origEl = document.getElementById('rec-origin');
                    if (supEl && ctx.supplier) supEl.value = String(ctx.supplier).toUpperCase();
                    if (invEl && ctx.invoice_number) invEl.value = String(ctx.invoice_number).toUpperCase();
                    if (origEl && ctx.invoice_number) {
                        const hasNfOpt = Array.from(origEl.options).some(o => o.value === 'NF');
                        if (!hasNfOpt) {
                            const opt = document.createElement('option');
                            opt.value = 'NF';
                            opt.textContent = 'NF';
                            origEl.appendChild(opt);
                        }
                        origEl.value = 'NF';
                    }

                    const traceSec = document.getElementById('receive-traceability-section');
                    const batchEl = document.getElementById('rec-batch') || traceSec?.querySelector('input[type="text"]');
                    const expEl = document.getElementById('rec-expiration') || traceSec?.querySelector('input[type="date"]');
                    if (batchEl && ctx.batch_code) batchEl.value = String(ctx.batch_code).toUpperCase();
                    if (expEl && ctx.expiration_date) expEl.value = ctx.expiration_date;

                    const totalUnits = Math.max(1, Number(ctx.nf_qty || 1) * Number(ctx.pack_factor || 1));
                    const qtyEl = document.getElementById('rec-qty')
                        || document.getElementById('rec-quantity')
                        || modalReceive?.querySelector('input[type="number"]');
                    if (qtyEl && totalUnits > 0) qtyEl.value = String(totalUnits);
                }

                this.updateReceivingSummary();
            }
        );

        document.getElementById('btn-module-inbound')?.addEventListener('click', () => {
            methodModal?.classList.add('hidden');
            document.querySelectorAll('main > section[id$="-view"]').forEach(el => el.classList.add('hidden'));
            document.getElementById('conference-view')?.classList.remove('hidden');
            window.scrollTo(0, 0);
            if (window.ConferenceFeature && typeof window.ConferenceFeature.mount === 'function') {
                window.ConferenceFeature.mount();
            }
        });
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

        document.getElementById(
            'btn-receive-putaway-now'
        )?.addEventListener(
            'click',
            async () => {
                const receiving =
                    this.lastReceivingResult;

                if (
                    !receiving ||
                    !receiving.sku ||
                    !receiving.batch_code
                ) {
                    alert(
                        'Não foi possível identificar o lote recém-recebido.'
                    );
                    return;
                }

                await this.openAssistedPutaway(
                    receiving
                );
            }
        );

        document.getElementById(
            'btn-receive-putaway-later'
        )?.addEventListener(
            'click',
            () => {
                /*
                 * O recebimento já está persistido.
                 * Nenhuma mutação de Putaway ocorre neste caminho.
                 */
                modalReceive?.classList.add(
                    'hidden'
                );

                document.getElementById(
                    'receive-success-modal'
                )?.classList.add(
                    'hidden'
                );

                this.lastReceivingResult =
                    null;

                this.resetReceivingForm();

                [
                    'dashboard-view',
                    'reports-view',
                    'replenishment-view',
                ].forEach(
                    (id) => {
                        document.getElementById(
                            id
                        )?.classList.add(
                            'hidden'
                        );
                    }
                );

                document.getElementById(
                    'home-module-view'
                )?.classList.remove(
                    'hidden'
                );
            }
        );

        /*
         * NF-001J.10:
         *
         * A entrada fiscal certificada possui fluxo próprio.
         * O recebimento manual abaixo permanece disponível e
         * continua usando /api/receive.
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

                    if (receiving) {
                        /*
                         * A resposta do backend é a fonte do lote
                         * recém-recebido. Não recalculamos isso
                         * pelo histórico nem por FEFO.
                         */
                        receiving.sku =
                            receiving.sku ||
                            sku;

                        this.lastReceivingResult =
                            receiving;
                    }

                    if (this._lastReceivingContext) {
                        if (this._lastReceivingContext.reqId) {
                            this._returnToEstoquistaQueueAfterPutaway = true;
                        }
                        try {
                            await fetch('/api/receiving/pending/sync-item-meta', {
                                method: 'POST',
                                credentials: 'same-origin',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    sku: sku,
                                    desc: this._lastReceivingContext.desc || '',
                                    supplier: supplier || this._lastReceivingContext.supplier || '',
                                    invoice_number: invoiceId || this._lastReceivingContext.invoice_number || '',
                                    batch_code: batchCode || '',
                                    expiration_date: expirationDate || '',
                                }),
                            });
                        } catch (_syncErr) {}
                    }

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
                            'receive-success-modal'
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

    resetReplenishmentFlow() {
        this.replenishmentCart = [];
        this.replenishmentProduct = null;
        this.replenishmentPickSteps = [];
        this.replenishmentPickIndex = 0;
        this.replenishmentCompletion = [];

        const input =
            document.getElementById(
                'replenishment-product-input'
            );

        const quantity =
            document.getElementById(
                'replenishment-quantity'
            );

        const productPanel =
            document.getElementById(
                'replenishment-product-panel'
            );

        const error =
            document.getElementById(
                'replenishment-error'
            );

        const pickError =
            document.getElementById(
                'replenishment-pick-error'
            );

        if (input) {
            input.value = '';
        }

        if (quantity) {
            quantity.value = '1';
        }

        productPanel?.classList.add(
            'hidden'
        );

        document.getElementById(
            'replenishment-unknown-product-panel'
        )?.classList.add(
            'hidden'
        );

        document.getElementById(
            'replenishment-zero-stock-panel'
        )?.classList.add(
            'hidden'
        );

        document.getElementById(
            'replenishment-route-error-panel'
        )?.classList.add(
            'hidden'
        );

        if (error) {
            error.textContent = '';
            error.classList.add(
                'hidden'
            );
        }

        if (pickError) {
            pickError.textContent = '';
            pickError.classList.add(
                'hidden'
            );
        }

        document.getElementById(
            'replenishment-cart-view'
        )?.classList.remove(
            'hidden'
        );

        document.getElementById(
            'replenishment-pick-view'
        )?.classList.add(
            'hidden'
        );

        document.getElementById(
            'replenishment-success-panel'
        )?.classList.add(
            'hidden'
        );

        this.renderReplenishmentCart();
    }

    showReplenishmentError(
        message
    ) {
        const error =
            document.getElementById(
                'replenishment-error'
            );

        if (!error) {
            return;
        }

        error.textContent =
            message || '';

        error.classList.toggle(
            'hidden',
            !message
        );
    }

    showReplenishmentRouteError(
        message
    ) {
        const panel =
            document.getElementById(
                'replenishment-route-error-panel'
            );

        panel?.classList.add(
            'hidden'
        );

        const normalized =
            String(
                message || ''
            );

        if (
            !normalized.startsWith(
                'LOTE_FEFO_SEM_ENDERECAMENTO|'
            )
        ) {
            return false;
        }

        const parts =
            normalized.split(
                '|'
            );

        const sku =
            parts[1] || '';

        const name =
            parts[2] || sku;

        const batch =
            parts[3] || '';

        const productElement =
            document.getElementById(
                'replenishment-route-error-product'
            );

        const batchElement =
            document.getElementById(
                'replenishment-route-error-batch'
            );

        if (productElement) {
            productElement.textContent =
                name || sku || 'PRODUTO';
        }

        if (batchElement) {
            batchElement.textContent =
                batch || '—';
        }

        panel?.classList.remove(
            'hidden'
        );

        return true;
    }

    showReplenishmentPickError(
        message
    ) {
        const error =
            document.getElementById(
                'replenishment-pick-error'
            );

        if (!error) {
            return;
        }

        error.textContent =
            message || '';

        error.classList.toggle(
            'hidden',
            !message
        );
    }

    async loadReplenishmentProduct(
        identifier
    ) {
        const normalized =
            String(
                identifier || ''
            ).trim();

        this.replenishmentProduct =
            null;

        this.showReplenishmentError(
            ''
        );

        const panel =
            document.getElementById(
                'replenishment-product-panel'
            );

        panel?.classList.add(
            'hidden'
        );

        document.getElementById(
            'replenishment-unknown-product-panel'
        )?.classList.add(
            'hidden'
        );

        document.getElementById(
            'replenishment-zero-stock-panel'
        )?.classList.add(
            'hidden'
        );

        if (!normalized) {
            return;
        }

        document.getElementById(
            'loader'
        )?.classList.remove(
            'hidden'
        );

        try {
            const data =
                await this.api.queryProduct(
                    normalized
                );

            const sku =
                data.id ||
                data.sku ||
                '';

            if (!sku) {
                throw new Error(
                    'Produto sem SKU canônico.'
                );
            }

            const controlledQuantity =
                Number(data.quantity || 0);

            if (
                !Number.isFinite(controlledQuantity) ||
                controlledQuantity <= 0
            ) {
                this.replenishmentProduct =
                    null;

                const zeroPanel =
                    document.getElementById(
                        'replenishment-zero-stock-panel'
                    );

                const zeroProduct =
                    document.getElementById(
                        'replenishment-zero-stock-product'
                    );

                const zeroSku =
                    document.getElementById(
                        'replenishment-zero-stock-sku'
                    );

                if (zeroProduct) {
                    zeroProduct.textContent =
                        data.name ||
                        'PRODUTO SEM DESCRIÇÃO';
                }

                if (zeroSku) {
                    zeroSku.textContent =
                        sku;
                }

                zeroPanel?.classList.remove(
                    'hidden'
                );

                return;
            }

            this.replenishmentProduct = {
                sku: sku,
                name:
                    data.name ||
                    'PRODUTO SEM DESCRIÇÃO',
                ean:
                    data.ean ||
                    '',
            };

            const input =
                document.getElementById(
                    'replenishment-product-input'
                );

            if (input) {
                /*
                 * A partir daqui o estado do carrinho usa
                 * exclusivamente o SKU canônico.
                 */
                input.value =
                    sku;
            }

            const setText = (
                id,
                value
            ) => {
                const element =
                    document.getElementById(
                        id
                    );

                if (element) {
                    element.textContent =
                        value || '—';
                }
            };

            setText(
                'replenishment-product-name',
                this.replenishmentProduct.name
            );

            setText(
                'replenishment-product-sku',
                this.replenishmentProduct.sku
            );

            setText(
                'replenishment-product-ean',
                this.replenishmentProduct.ean ||
                    'NÃO INFORMADO'
            );

            panel?.classList.remove(
                'hidden'
            );

            const quantity =
                document.getElementById(
                    'replenishment-quantity'
                );

            if (quantity) {
                quantity.value = '1';

                window.setTimeout(
                    () => {
                        quantity.focus();
                        quantity.select();
                    },
                    50
                );
            }

        } catch (error) {
            if (
                error.message ===
                'PRODUTO_NAO_CADASTRADO'
            ) {
                this.replenishmentProduct =
                    null;

                const unknownPanel =
                    document.getElementById(
                        'replenishment-unknown-product-panel'
                    );

                const unknownEan =
                    document.getElementById(
                        'replenishment-unknown-product-ean'
                    );

                if (unknownEan) {
                    unknownEan.textContent =
                        normalized;
                }

                unknownPanel?.classList.remove(
                    'hidden'
                );

                this.showReplenishmentError(
                    ''
                );

                return;
            }

            this.showReplenishmentError(
                error.message ||
                'Produto não encontrado.'
            );

        } finally {
            document.getElementById(
                'loader'
            )?.classList.add(
                'hidden'
            );
        }
    }

    renderReplenishmentCart() {
        const items =
            document.getElementById(
                'replenishment-cart-items'
            );

        const empty =
            document.getElementById(
                'replenishment-cart-empty'
            );

        const count =
            document.getElementById(
                'replenishment-cart-count'
            );

        const start =
            document.getElementById(
                'btn-replenishment-start-pick'
            );

        const total =
            this.replenishmentCart.length;

        if (count) {
            count.textContent =
                `${total} ${
                    total === 1
                        ? 'ITEM'
                        : 'ITENS'
                }`;
        }

        if (!items) {
            return;
        }

        if (total === 0) {
            items.innerHTML = '';
            items.classList.add(
                'hidden'
            );

            empty?.classList.remove(
                'hidden'
            );

            if (start) {
                start.disabled = true;
                start.className =
                    'w-full mt-3 bg-gray-300 text-gray-500 rounded-xl py-3.5 font-black text-xs cursor-not-allowed';
            }

            return;
        }

        empty?.classList.add(
            'hidden'
        );

        items.classList.remove(
            'hidden'
        );

        items.innerHTML =
            '';

        this.replenishmentCart.forEach(
            (item, index) => {
                const card =
                    document.createElement(
                        'div'
                    );

                card.className =
                    'border border-gray-200 rounded-xl p-3 flex justify-between items-center gap-3';

                const info =
                    document.createElement(
                        'div'
                    );

                info.className =
                    'min-w-0';

                const name =
                    document.createElement(
                        'p'
                    );

                name.className =
                    'text-[11px] font-black text-gray-800 truncate';

                name.textContent =
                    item.name ||
                    item.sku;

                const sku =
                    document.createElement(
                        'p'
                    );

                sku.className =
                    'text-[8px] font-mono font-bold text-gray-400 mt-1';

                sku.textContent =
                    item.sku;

                info.appendChild(
                    name
                );

                info.appendChild(
                    sku
                );

                const controls =
                    document.createElement(
                        'div'
                    );

                controls.className =
                    'shrink-0 flex items-center gap-2';

                const quantity =
                    document.createElement(
                        'span'
                    );

                quantity.className =
                    'bg-blue-50 text-[#124191] border border-blue-100 rounded-lg px-2 py-1 text-[10px] font-black';

                quantity.textContent =
                    `${item.quantity} UN`;

                const remove =
                    document.createElement(
                        'button'
                    );

                remove.type =
                    'button';

                remove.className =
                    'text-red-600 border border-red-200 bg-red-50 rounded-lg px-2 py-1 text-[9px] font-black';

                remove.textContent =
                    'REMOVER';

                remove.addEventListener(
                    'click',
                    () => {
                        this.replenishmentCart.splice(
                            index,
                            1
                        );

                        this.renderReplenishmentCart();
                    }
                );

                controls.appendChild(
                    quantity
                );

                controls.appendChild(
                    remove
                );

                card.appendChild(
                    info
                );

                card.appendChild(
                    controls
                );

                items.appendChild(
                    card
                );
            }
        );

        if (start) {
            start.disabled = false;
            start.className =
                'w-full mt-3 bg-[#124191] text-white rounded-xl py-3.5 font-black text-xs active:scale-95 shadow-md';
        }
    }

    async addReplenishmentProduct() {
        const product =
            this.replenishmentProduct;

        const quantityInput =
            document.getElementById(
                'replenishment-quantity'
            );

        const quantity =
            Number.parseInt(
                quantityInput?.value,
                10
            );

        if (!product) {
            this.showReplenishmentError(
                'Identifique um produto antes de adicionar.'
            );

            return;
        }

        if (
            !Number.isInteger(quantity) ||
            quantity <= 0
        ) {
            this.showReplenishmentError(
                'Informe uma quantidade maior que zero.'
            );

            return;
        }

        const candidate =
            this.replenishmentCart.map(
                (item) => ({
                    sku: item.sku,
                    quantity: item.quantity,
                })
            );

        candidate.push({
            sku: product.sku,
            quantity: quantity,
        });

        document.getElementById(
            'loader'
        )?.classList.remove(
            'hidden'
        );

        try {
            /*
             * O backend consolida SKUs repetidos e valida
             * a disponibilidade FEFO. O frontend não
             * recalcula lotes.
             */
            const plan =
                await this.api.planReplenishment({
                    items: candidate,
                });

            const plannedItems =
                Array.isArray(
                    plan.items
                )
                    ? plan.items
                    : [];

            this.replenishmentCart =
                plannedItems.map(
                    (item) => ({
                        sku: item.sku,
                        name:
                            item.name ||
                            item.sku,
                        quantity:
                            item.requested_quantity,
                    })
                );

            this.replenishmentProduct =
                null;

            const input =
                document.getElementById(
                    'replenishment-product-input'
                );

            if (input) {
                input.value = '';
            }

            if (quantityInput) {
                quantityInput.value =
                    '1';
            }

            document.getElementById(
                'replenishment-product-panel'
            )?.classList.add(
                'hidden'
            );

            this.showReplenishmentError(
                ''
            );

            this.renderReplenishmentCart();

            input?.focus();

        } catch (error) {
            this.showReplenishmentError(
                error.message ||
                'Não foi possível adicionar o produto.'
            );

        } finally {
            document.getElementById(
                'loader'
            )?.classList.add(
                'hidden'
            );
        }
    }

    async startReplenishmentPick() {
        if (
            this.replenishmentCart.length ===
            0
        ) {
            this.showReplenishmentError(
                'Adicione produtos ao carrinho.'
            );

            return;
        }

        const items =
            this.replenishmentCart.map(
                (item) => ({
                    sku: item.sku,
                    quantity: item.quantity,
                })
            );

        document.getElementById(
            'replenishment-route-error-panel'
        )?.classList.add(
            'hidden'
        );

        document.getElementById(
            'loader'
        )?.classList.remove(
            'hidden'
        );

        try {
            /*
             * FEFO + rota física pertencem ao backend.
             * Aqui apenas conservamos a sequência recebida.
             */
            const plan =
                await this.api.planReplenishmentPick({
                    items: items,
                });

            this.replenishmentPickSteps =
                Array.isArray(
                    plan.steps
                )
                    ? plan.steps
                    : [];

            if (
                this.replenishmentPickSteps.length ===
                0
            ) {
                throw new Error(
                    'Plano de coleta vazio.'
                );
            }

            this.replenishmentPickIndex =
                0;

            document.getElementById(
                'replenishment-cart-view'
            )?.classList.add(
                'hidden'
            );

            document.getElementById(
                'replenishment-success-panel'
            )?.classList.add(
                'hidden'
            );

            document.getElementById(
                'replenishment-pick-view'
            )?.classList.remove(
                'hidden'
            );

            this.renderReplenishmentPickStep();

        } catch (error) {
            const routeErrorMessage =
                String(
                    error.message || ''
                );

            if (
                routeErrorMessage.startsWith(
                    'LOTE_FEFO_SEM_ENDERECAMENTO|'
                ) &&
                this.showReplenishmentRouteError(
                    routeErrorMessage
                )
            ) {
                this.showReplenishmentError(
                    ''
                );

                return;
            }

            this.showReplenishmentError(
                error.message ||
                'Não foi possível gerar a coleta.'
            );

        } finally {
            document.getElementById(
                'loader'
            )?.classList.add(
                'hidden'
            );
        }
    }

    renderReplenishmentPickStep() {
        const step =
            this.replenishmentPickSteps[
                this.replenishmentPickIndex
            ];

        if (!step) {
            this.finishReplenishmentPick();
            return;
        }

        this.showReplenishmentPickError(
            ''
        );

        const setText = (
            id,
            value
        ) => {
            const element =
                document.getElementById(
                    id
                );

            if (element) {
                element.textContent =
                    value ?? '—';
            }
        };

        setText(
            'replenishment-pick-progress',
            `${this.replenishmentPickIndex + 1} / ${this.replenishmentPickSteps.length}`
        );

        setText(
            'replenishment-pick-location',
            step.location_id
        );

        setText(
            'replenishment-pick-product',
            step.name
        );

        setText(
            'replenishment-pick-sku',
            step.sku
        );

        setText(
            'replenishment-pick-batch',
            step.batch_code
        );

        setText(
            'replenishment-pick-expiration',
            this.formatDateBR(
                step.expiration_date,
                'N/A'
            )
        );

        setText(
            'replenishment-pick-planned-quantity',
            `${step.quantity} UN`
        );

        const confirmed =
            document.getElementById(
                'replenishment-pick-confirmed-quantity'
            );

        if (confirmed) {
            confirmed.value =
                String(
                    step.quantity
                );

            confirmed.max =
                String(
                    step.quantity
                );

            window.setTimeout(
                () => {
                    confirmed.focus();
                    confirmed.select();
                },
                50
            );
        }
    }

    async confirmReplenishmentPickStep() {
        const step =
            this.replenishmentPickSteps[
                this.replenishmentPickIndex
            ];

        if (!step) {
            return;
        }

        const plannedQuantity =
            Number(step.quantity);

        const quantity =
            Number.parseInt(
                document.getElementById(
                    'replenishment-pick-confirmed-quantity'
                )?.value,
                10
            );

        const actualQuantity =
            quantity;

        if (
            !Number.isInteger(quantity) ||
            quantity <= 0
        ) {
            this.showReplenishmentPickError(
                'Informe a quantidade realmente coletada.'
            );

            return;
        }

        if (
            quantity >
            step.quantity
        ) {
            this.showReplenishmentPickError(
                'A quantidade confirmada não pode superar a quantidade planejada.'
            );

            return;
        }

        document.getElementById(
            'loader'
        )?.classList.remove(
            'hidden'
        );

        try {
            /*
             * Confirma exatamente o lote físico apresentado.
             * Não há nova resolução FEFO nesta etapa.
             */
            await this.api.confirmReplenishmentPick({
                sku: step.sku,
                batch_code:
                    step.batch_code,
                quantity: quantity,
            });

            const missingQuantity =
                Math.max(
                    0,
                    plannedQuantity - actualQuantity
                );

            this.replenishmentCompletion.push({
                sku: step.sku,
                name:
                    step.name ||
                    step.sku,
                batch_code:
                    step.batch_code,
                location_id:
                    step.location_id ||
                    '',
                planned_quantity:
                    plannedQuantity,
                confirmed_quantity:
                    actualQuantity,
                missing_quantity:
                    missingQuantity,
                has_divergence:
                    actualQuantity !== plannedQuantity,
            });

            this.replenishmentPickIndex +=
                1;

            if (
                this.replenishmentPickIndex >=
                this.replenishmentPickSteps.length
            ) {
                this.finishReplenishmentPick();
                return;
            }

            this.renderReplenishmentPickStep();

        } catch (error) {
            this.showReplenishmentPickError(
                error.message ||
                'Não foi possível confirmar a coleta.'
            );

        } finally {
            document.getElementById(
                'loader'
            )?.classList.add(
                'hidden'
            );
        }
    }

    finishReplenishmentPick() {
        document.getElementById(
            'replenishment-pick-view'
        )?.classList.add(
            'hidden'
        );

        document.getElementById(
            'replenishment-cart-view'
        )?.classList.add(
            'hidden'
        );

        const successPanel =
            document.getElementById(
                'replenishment-success-panel'
            );

        const normalCompletion =
            document.getElementById(
                'replenishment-completion-normal'
            );

        const divergenceCompletion =
            document.getElementById(
                'replenishment-completion-divergence'
            );

        const divergence =
            this.replenishmentCompletion.find(
                (item) =>
                    item.has_divergence
            );

        if (divergence) {
            normalCompletion?.classList.add(
                'hidden'
            );

            divergenceCompletion?.classList.remove(
                'hidden'
            );

            const planned =
                document.getElementById(
                    'replenishment-completion-planned'
                );

            const confirmed =
                document.getElementById(
                    'replenishment-completion-confirmed'
                );

            const missing =
                document.getElementById(
                    'replenishment-completion-missing'
                );

            const product =
                document.getElementById(
                    'replenishment-completion-product'
                );

            const batch =
                document.getElementById(
                    'replenishment-completion-batch'
                );

            const location =
                document.getElementById(
                    'replenishment-completion-location'
                );

            const deductedText =
                document.getElementById(
                    'replenishment-completion-deducted-text'
                );

            const missingText =
                document.getElementById(
                    'replenishment-completion-missing-text'
                );

            if (planned) {
                planned.textContent =
                    `${divergence.planned_quantity} UN`;
            }

            if (confirmed) {
                confirmed.textContent =
                    `${divergence.confirmed_quantity} UN`;
            }

            if (missing) {
                missing.textContent =
                    `${divergence.missing_quantity} UN`;
            }

            if (product) {
                product.textContent =
                    divergence.name;
            }

            if (batch) {
                batch.textContent =
                    divergence.batch_code ||
                    '—';
            }

            if (location) {
                location.textContent =
                    divergence.location_id ||
                    '—';
            }

            if (deductedText) {
                deductedText.textContent =
                    `${divergence.confirmed_quantity} UN FORAM BAIXADAS DO ESTOQUE CONTROLADO.`;
            }

            if (missingText) {
                missingText.textContent =
                    `${divergence.missing_quantity} UN NÃO FORAM LOCALIZADAS.`;
            }

        } else {
            divergenceCompletion?.classList.add(
                'hidden'
            );

            normalCompletion?.classList.remove(
                'hidden'
            );
        }

        successPanel?.classList.remove(
            'hidden'
        );
    }

    bindReplenishmentModule() {
        const moduleButton =
            document.getElementById(
                'btn-module-replenishment'
            );

        const view =
            document.getElementById(
                'replenishment-view'
            );

        const input =
            document.getElementById(
                'replenishment-product-input'
            );

        moduleButton?.addEventListener(
            'click',
            () => {
                [
                    'home-module-view',
                    'dashboard-view',
                    'reports-view',
                ].forEach(
                    (id) => {
                        document.getElementById(
                            id
                        )?.classList.add(
                            'hidden'
                        );
                    }
                );

                this.resetReplenishmentFlow();

                view?.classList.remove(
                    'hidden'
                );

                window.setTimeout(
                    () => input?.focus(),
                    50
                );
            }
        );

        document.getElementById(
            'btn-replenishment-scanner'
        )?.addEventListener(
            'click',
            async () => {
                this.scannerTarget = 'replenishment';

                view?.classList.add(
                    'hidden'
                );

                try {
                    await this.scanner.start();

                    if (
                        this.scanner.status !==
                        'SCANNING'
                    ) {
                        this.scannerTarget =
                            'search';

                        view?.classList.remove(
                            'hidden'
                        );
                    }

                } catch (error) {
                    this.scannerTarget =
                        'search';

                    view?.classList.remove(
                        'hidden'
                    );

                    this.showReplenishmentError(
                        error.message ||
                        'Não foi possível abrir o scanner.'
                    );
                }
            }
        );

        input?.addEventListener(
            'change',
            async () => {
                await this.loadReplenishmentProduct(
                    input.value
                );
            }
        );

        input?.addEventListener(
            'keydown',
            async (event) => {
                if (
                    event.key ===
                    'Enter'
                ) {
                    event.preventDefault();

                    await this.loadReplenishmentProduct(
                        input.value
                    );
                }
            }
        );

        document.getElementById(
            'btn-replenishment-register-product'
        )?.addEventListener(
            'click',
            async () => {
                const identifier =
                    document.getElementById(
                        'replenishment-product-input'
                    )?.value.trim() || '';

                document.getElementById(
                    'replenishment-view'
                )?.classList.add(
                    'hidden'
                );

                await this.openNewProductRegistration(
                    identifier
                );
            }
        );

        document.getElementById(
            'btn-replenishment-add'
        )?.addEventListener(
            'click',
            async () => {
                await this.addReplenishmentProduct();
            }
        );

        document.getElementById(
            'replenishment-quantity'
        )?.addEventListener(
            'keydown',
            async (event) => {
                if (
                    event.key ===
                    'Enter'
                ) {
                    event.preventDefault();

                    await this.addReplenishmentProduct();
                }
            }
        );

        document.getElementById(
            'btn-replenishment-start-pick'
        )?.addEventListener(
            'click',
            async () => {
                await this.startReplenishmentPick();
            }
        );

        document.getElementById(
            'btn-replenishment-confirm-pick'
        )?.addEventListener(
            'click',
            async () => {
                await this.confirmReplenishmentPickStep();
            }
        );

        document.getElementById(
            'btn-replenishment-new-cart'
        )?.addEventListener(
            'click',
            () => {
                this.resetReplenishmentFlow();

                input?.focus();
            }
        );
    }

    /*
     * assisted-putaway
     *
     * O recebimento já determinou o SKU e o lote físico.
     * Nesta etapa o operador deve selecionar somente o endereço.
     */
    async openAssistedPutaway(receiving) {
        if (
            !receiving ||
            !receiving.sku ||
            !receiving.batch_code
        ) {
            return;
        }

        this.assistedPutaway = true;
        this.preferredBatchCode =
            receiving.batch_code;

        document.getElementById(
            'receive-modal'
        )?.classList.add(
            'hidden'
        );

        document.getElementById(
            'receive-success-modal'
        )?.classList.add(
            'hidden'
        );

        const modal =
            document.getElementById(
                'putaway-modal'
            );

        const putEan =
            document.getElementById(
                'put-ean'
            );

        const putLocation =
            document.getElementById(
                'put-location'
            );

        const scannerButton =
            document.getElementById(
                'btn-putaway-scanner'
            );

        if (putEan) {
            putEan.value =
                receiving.sku;

            putEan.setAttribute('readonly', 'readonly');
        }

        if (scannerButton) {
            scannerButton.classList.add(
                'hidden'
            );
        }

        if (putLocation) {
            putLocation.value = '';
        }

        modal?.classList.remove(
            'hidden'
        );

        await this.loadPutawayProduct(
            receiving.sku,
            this.preferredBatchCode
        );
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
            async (
                identifier,
                preferredBatchCode = null
            ) => {
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

                    const batchHeading =
                        document.getElementById(
                            'putaway-batch-heading'
                        );

                    const batchDescription =
                        document.getElementById(
                            'putaway-batch-description'
                        );

                    /*
                     * A semântica visual acompanha a origem
                     * desta operação:
                     *
                     * - Putaway assistido:
                     *   o lote é exatamente o que acabou de
                     *   ser recebido.
                     *
                     * - Putaway manual:
                     *   preservamos a orientação operacional
                     *   pela menor validade pendente.
                     */
                    if (preferredBatchCode) {
                        if (batchHeading) {
                            batchHeading.textContent =
                                'LOTE DESTE RECEBIMENTO';
                        }

                        if (batchDescription) {
                            batchDescription.textContent =
                                'Lote recém-recebido aguardando endereçamento.';
                        }
                    } else {
                        if (batchHeading) {
                            batchHeading.textContent =
                                'LOTE PRIORITÁRIO PENDENTE';
                        }

                        if (batchDescription) {
                            batchDescription.textContent =
                                'Menor validade entre os lotes ainda não endereçados.';
                        }
                    }

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

                    const preferredBatch =
                        preferredBatchCode
                            ? pendingBatches.find(
                                (batch) =>
                                    batch.code ===
                                    preferredBatchCode
                            )
                            : null;

                    if (
                        preferredBatchCode &&
                        !preferredBatch
                    ) {
                        showPutawayError(
                            'O lote recém-recebido não está mais pendente de armazenagem.'
                        );

                        return;
                    }

                    const selectedBatch =
                        preferredBatch ||
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
                    this.assistedPutaway =
                        false;

                    this.preferredBatchCode =
                        null;

                    const manualPutEan =
                        document.getElementById(
                            'put-ean'
                        );

                    const manualScanner =
                        document.getElementById(
                            'btn-putaway-scanner'
                        );

                    manualPutEan?.removeAttribute(
                        'readonly'
                    );

                    manualScanner?.classList.remove(
                        'hidden'
                    );

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

                if (
                    this.assistedPutaway &&
                    this.lastReceivingResult
                ) {
                    document.getElementById(
                        'receive-modal'
                    )?.classList.remove(
                        'hidden'
                    );

                    document.getElementById(
                        'receive-success-modal'
                    )?.classList.remove(
                        'hidden'
                    );
                }
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
            'btn-putaway-success-finalize'
        )?.addEventListener(
            'click',
            async () => {
                document.getElementById(
                    'putaway-success-modal'
                )?.classList.add(
                    'hidden'
                );

                const shouldReturnQueue = Boolean(
                    this._returnToEstoquistaQueueAfterPutaway || this._lastReceivingContext?.reqId
                );
                this._returnToEstoquistaQueueAfterPutaway = false;
                this._lastReceivingContext = null;

                this.assistedPutaway =
                    false;

                this.preferredBatchCode =
                    null;

                this.lastReceivingResult =
                    null;

                const putEan =
                    document.getElementById(
                        'put-ean'
                    );

                putEan?.removeAttribute(
                    'readonly'
                );

                document.getElementById(
                    'btn-putaway-scanner'
                )?.classList.remove(
                    'hidden'
                );

                this.resetReceivingForm();

                [
                    'dashboard-view',
                    'reports-view',
                    'replenishment-view',
                ].forEach(
                    (id) => {
                        document.getElementById(
                            id
                        )?.classList.add(
                            'hidden'
                        );
                    }
                );

                document.getElementById(
                    'home-module-view'
                )?.classList.remove(
                    'hidden'
                );

                if (shouldReturnQueue) {
                    await this.refreshEstoquistaPendingQueue();
                    document.getElementById('btn-open-estoquista-queue')?.click();
                }
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
            const confView = document.getElementById('conference-view');
            const isConfOpen = confView && !confView.classList.contains('hidden');
            this.scannerTarget = isConfOpen ? 'conference' : 'search';

            this.scanner.start();
        };
        window.kippeOpenConferenceScanner = () => {
            this.scannerTarget = 'conference';
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

    escapeProductAuditText(value, fallback = 'N/A') {
        const normalized =
            value === null ||
            value === undefined ||
            value === ''
                ? fallback
                : String(value);

        return normalized
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    formatProductAuditDate(value) {
        if (!value) {
            return 'N/A';
        }

        const normalized =
            String(value).includes('T')
                ? String(value)
                : String(value).replace(
                    ' ',
                    'T'
                ) + 'Z';

        const date =
            new Date(normalized);

        if (
            Number.isNaN(
                date.getTime()
            )
        ) {
            return String(value);
        }

        return date.toLocaleString(
            'pt-BR',
            {
                dateStyle: 'short',
                timeStyle: 'short',
            }
        );
    }

    resetProductAuditSummary() {
        const values = {
            'product-audit-latest-receiving-date': '—',
            'product-audit-latest-receiving-supplier': '—',
            'product-audit-latest-receiving-document': '—',
            'product-audit-latest-receiving-batch': '—',
            'product-audit-latest-receiving-quantity': '—',
        };

        Object.entries(
            values
        ).forEach(
            ([id, value]) => {
                const element =
                    document.getElementById(
                        id
                    );

                if (element) {
                    element.textContent =
                        value;
                }
            }
        );

        const status =
            document.getElementById(
                'product-audit-summary-status'
            );

        if (status) {
            status.textContent =
                'SEM REGISTRO';

            status.className =
                'text-[8px] font-black bg-gray-100 text-gray-500 px-2 py-1 rounded';
        }
    }

    renderLatestReceivingSummary(
        latest_receiving
    ) {
        this.resetProductAuditSummary();

        if (!latest_receiving) {
            return;
        }

        const setText = (
            id,
            value,
            fallback = 'N/A'
        ) => {
            const element =
                document.getElementById(
                    id
                );

            if (element) {
                element.textContent =
                    value === null ||
                    value === undefined ||
                    value === ''
                        ? fallback
                        : String(value);
            }
        };

        setText(
            'product-audit-latest-receiving-date',
            this.formatProductAuditDate(
                latest_receiving.occurred_at
            )
        );

        setText(
            'product-audit-latest-receiving-supplier',
            latest_receiving.supplier,
            'NÃO INFORMADO'
        );

        setText(
            'product-audit-latest-receiving-document',
            latest_receiving.document_id,
            'NÃO INFORMADO'
        );

        setText(
            'product-audit-latest-receiving-batch',
            latest_receiving.batch_code,
            'N/A'
        );

        setText(
            'product-audit-latest-receiving-quantity',
            latest_receiving.quantity_actual,
            'N/A'
        );

        const status =
            document.getElementById(
                'product-audit-summary-status'
            );

        if (status) {
            status.textContent =
                'LOCALIZADO';

            status.className =
                'text-[8px] font-black bg-green-100 text-green-700 px-2 py-1 rounded';
        }
    }

    async loadProductAuditHistory(
        productId
    ) {
        this.currentProductAuditHistory =
            null;

        this.currentProductAuditId =
            productId;

        this.resetProductAuditSummary();

        const historyButton =
            document.getElementById(
                'btn-product-audit-history'
            );

        if (historyButton) {
            historyButton.onclick =
                () => {
                    this.openProductAuditHistory();
                };
        }

        try {
            const data =
                await this.api.getProductHistory(
                    productId
                );

            this.currentProductAuditHistory =
                data;

            this.renderLatestReceivingSummary(
                data.latest_receiving
            );
        } catch (error) {
            console.warn(
                '[PRODUCT AUDIT] Não foi possível carregar histórico.',
                error
            );

            this.showProductAuditHistoryError(
                'Não foi possível carregar o histórico documental.'
            );
        }
    }

    showProductAuditHistoryError(
        message
    ) {
        const error =
            document.getElementById(
                'product-audit-history-error'
            );

        if (!error) {
            return;
        }

        error.textContent =
            message ||
            'Não foi possível carregar o histórico.';

        error.classList.remove(
            'hidden'
        );
    }

    closeProductAuditHistory() {
        const modal =
            document.getElementById(
                'product-audit-history-modal'
            );

        modal?.classList.add(
            'hidden'
        );
    }

    openProductAuditHistory() {
        const modal =
            document.getElementById(
                'product-audit-history-modal'
            );

        const closeButton =
            document.getElementById(
                'btn-close-product-audit-history'
            );

        const title =
            document.getElementById(
                'product-audit-history-title'
            );

        if (closeButton) {
            closeButton.onclick =
                () => {
                    this.closeProductAuditHistory();
                };
        }

        if (title) {
            const sku =
                this.currentProductAuditId
                || '';

            title.textContent =
                sku
                    ? `HISTÓRICO • ${sku}`
                    : 'HISTÓRICO DO PRODUTO';
        }

        modal?.classList.remove(
            'hidden'
        );

        this.renderProductAuditHistory();
    }

    renderProductAuditHistory() {
        const timeline =
            document.getElementById(
                'product-audit-history-timeline'
            );

        const empty =
            document.getElementById(
                'product-audit-history-empty'
            );

        const error =
            document.getElementById(
                'product-audit-history-error'
            );

        if (!timeline) {
            return;
        }

        timeline.innerHTML = '';

        empty?.classList.add(
            'hidden'
        );

        error?.classList.add(
            'hidden'
        );

        const events =
            Array.isArray(
                this.currentProductAuditHistory
                    ?.events
            )
                ? this.currentProductAuditHistory.events
                : [];

        if (events.length === 0) {
            empty?.classList.remove(
                'hidden'
            );

            return;
        }

        events.forEach(
            (event) => {
                timeline.appendChild(
                    this.createProductAuditEventCard(
                        event
                    )
                );
            }
        );
    }

    createProductAuditEventCard(
        event
    ) {
        const card =
            document.createElement(
                'article'
            );

        const eventType =
            String(
                event.event_type
                || 'EVENTO'
            );

        const typeConfig = {
            RECEBIMENTO: {
                label: 'RECEBIMENTO',
                badge:
                    'bg-green-100 text-green-700 border-green-200',
            },
            PUTAWAY: {
                label: 'ENDEREÇAMENTO',
                badge:
                    'bg-blue-100 text-blue-700 border-blue-200',
            },
            ABASTECIMENTO_LOJA: {
                label: 'ABASTECIMENTO DA LOJA',
                badge:
                    'bg-amber-100 text-amber-800 border-amber-200',
            },
        };

        const config =
            typeConfig[eventType]
            || {
                label: eventType,
                badge:
                    'bg-gray-100 text-gray-700 border-gray-200',
            };

        const safe = (
            value,
            fallback = 'N/A'
        ) => this.escapeProductAuditText(
            value,
            fallback
        );

        const date =
            safe(
                this.formatProductAuditDate(
                    event.occurred_at
                )
            );

        const common = `
            <div class="grid grid-cols-2 gap-2 mt-3 text-[9px]">
                <div>
                    <p class="font-black text-gray-400">
                        LOTE
                    </p>
                    <p class="font-black font-mono text-gray-800 break-all">
                        ${safe(event.batch_code)}
                    </p>
                </div>

                <div>
                    <p class="font-black text-gray-400">
                        OPERADOR
                    </p>
                    <p class="font-black text-gray-800 break-all">
                        ${safe(event.operator_id)}
                    </p>
                </div>
            </div>
        `;

        let specific = '';

        if (
            eventType
            === 'RECEBIMENTO'
        ) {
            specific = `
                <div class="grid grid-cols-2 gap-2 mt-3 text-[9px]">
                    <div class="col-span-2">
                        <p class="font-black text-gray-400">
                            FORNECEDOR
                        </p>
                        <p class="font-black text-gray-800 break-words">
                            ${safe(
                                event.supplier,
                                'NÃO INFORMADO'
                            )}
                        </p>
                    </div>

                    <div>
                        <p class="font-black text-gray-400">
                            NF / DOCUMENTO
                        </p>
                        <p class="font-black text-gray-800 break-all">
                            ${safe(
                                event.document_id,
                                'NÃO INFORMADO'
                            )}
                        </p>
                    </div>

                    <div>
                        <p class="font-black text-gray-400">
                            ORIGEM
                        </p>
                        <p class="font-black text-gray-800 break-words">
                            ${safe(
                                event.origin_document,
                                'NÃO INFORMADO'
                            )}
                        </p>
                    </div>

                    <div>
                        <p class="font-black text-gray-400">
                            QTD. RECEBIDA
                        </p>
                        <p class="font-black text-gray-800">
                            ${safe(
                                event.quantity_actual
                            )}
                        </p>
                    </div>
                </div>
            `;
        }

        if (
            eventType
            === 'PUTAWAY'
        ) {
            specific = `
                <div class="mt-3 text-[9px]">
                    <p class="font-black text-gray-400">
                        ENDEREÇO
                    </p>
                    <p class="font-black text-gray-800 break-all">
                        ${safe(
                            event.location_id,
                            'NÃO INFORMADO'
                        )}
                    </p>
                </div>
            `;
        }

        if (
            eventType
            === 'ABASTECIMENTO_LOJA'
        ) {
            specific = `
                <div class="grid grid-cols-2 gap-2 mt-3 text-[9px]">
                    <div>
                        <p class="font-black text-gray-400">
                            QTD. PLANEJADA
                        </p>
                        <p class="font-black text-gray-800">
                            ${safe(
                                event.quantity_planned
                            )}
                        </p>
                    </div>

                    <div>
                        <p class="font-black text-gray-400">
                            QTD. CONFIRMADA
                        </p>
                        <p class="font-black text-gray-800">
                            ${safe(
                                event.quantity_actual
                            )}
                        </p>
                    </div>

                    <div>
                        <p class="font-black text-gray-400">
                            DIVERGÊNCIA
                        </p>
                        <p class="font-black text-gray-800">
                            ${safe(
                                event.quantity_divergence,
                                'SEM REGISTRO'
                            )}
                        </p>
                    </div>

                    <div>
                        <p class="font-black text-gray-400">
                            ENDEREÇO DE ORIGEM
                        </p>
                        <p class="font-black text-gray-800 break-all">
                            ${safe(
                                event.location_id,
                                'NÃO INFORMADO'
                            )}
                        </p>
                    </div>
                </div>
            `;
        }

        card.className =
            'bg-white rounded-xl border border-gray-200 p-3 shadow-sm';

        card.innerHTML = `
            <div class="flex items-start justify-between gap-2">
                <span class="text-[8px] font-black border px-2 py-1 rounded ${config.badge}">
                    ${safe(config.label)}
                </span>

                <span class="text-[8px] font-bold text-gray-400 text-right">
                    ${date}
                </span>
            </div>

            ${common}
            ${specific}
        `;

        return card;
    }

    async fetchAndRenderSku(identifier) {
        document.getElementById('loader')?.classList.remove('hidden');

        try {
            const data = await this.api.queryProduct(identifier);

            this.currentCatalogProduct = data;
            this.updateExistingStockActionVisibility();

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

            await this.loadProductAuditHistory(
                data.id || identifier
            );

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

            const roleUpper = String(this.currentOperator?.role || '').trim().toUpperCase();
            const notFoundMsg = roleUpper === 'CONFERENTE'
                ? "❌ PRODUTO NÃO CADASTRADO.\n\nSe este item veio na nota fiscal, abra '1. CONFERÊNCIA NF' e solicite o cadastro ao Estoquista."
                : "❌ PRODUTO NÃO ENCONTRADO.\n\nUse '1. RECEBER' ou '+ NOVO PRODUTO' para cadastrar no catálogo.";
            await window.kippeModalAlert(notFoundMsg, 'CONSULTA DE PRODUTO');
        }
    }

    initReceivingAuditModule() {
        if (this._receivingAuditWired) return;
        this._receivingAuditWired = true;
        this._receivingAuditStatus = 'ALL';

        const syncAuditTabsUI = (targetStatus) => {
            this._receivingAuditStatus = targetStatus || 'ALL';
            document.querySelectorAll('#receiving-audit-status-tabs [data-audit-status]').forEach(b => {
                const st = b.getAttribute('data-audit-status');
                const active = st === this._receivingAuditStatus;
                if (active) {
                    b.style.background = st === 'DIVERGENCIA' ? '#DC2626' : '#124191';
                    b.style.color = '#FFFFFF';
                } else {
                    b.style.background = st === 'DIVERGENCIA' ? '#FEF2F2' : '#F1F5F9';
                    b.style.color = st === 'DIVERGENCIA' ? '#B91C1C' : '#475569';
                }
            });
        };

        const openAuditView = async (initialStatus = 'ALL') => {
            syncAuditTabsUI(initialStatus);
            document.querySelectorAll('main > section[id$="-view"]').forEach(el => el.classList.add('hidden'));
            document.getElementById('receiving-audit-view')?.classList.remove('hidden');
            const resetBtn = document.getElementById('btn-reset-receiving-audit');
            if (resetBtn) {
                resetBtn.classList.toggle('hidden', !this.isSystemAdmin());
            }
            window.scrollTo(0, 0);
            await this.loadReceivingAudit();
        };

        document.getElementById('btn-module-receiving-audit')?.addEventListener('click', () => openAuditView('ALL'));
        document.getElementById('btn-module-divergences-history')?.addEventListener('click', () => openAuditView('DIVERGENCIA'));
        document.getElementById('btn-back-receiving-audit')?.addEventListener('click', () => {
            if (typeof window.showHome === 'function') {
                window.showHome();
            } else {
                document.getElementById('receiving-audit-view')?.classList.add('hidden');
                document.getElementById('home-module-view')?.classList.remove('hidden');
            }
        });
        document.getElementById('btn-refresh-receiving-audit')?.addEventListener('click', () => this.loadReceivingAudit());
        document.getElementById('btn-search-receiving-audit')?.addEventListener('click', () => this.loadReceivingAudit());
        document.getElementById('receiving-audit-search')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.loadReceivingAudit();
            }
        });

        document.getElementById('btn-reset-receiving-audit')?.addEventListener('click', async () => {
            const ok = await window.kippeModalConfirm(
                'Deseja apagar todos os registros antigos de recebimentos, divergências e solicitações de teste?\n\nSeus operadores e produtos cadastrados serão mantidos.',
                'ZERAR HISTÓRICO DE TESTES',
                'ZERAR AGORA'
            );
            if (!ok) return;
            try {
                const res = await fetch('/api/receiving/audit/reset', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                });
                const out = await res.json();
                if (!res.ok) throw new Error(out.error || 'Falha ao zerar histórico.');
                await window.kippeModalAlert('✅ Histórico zerado com sucesso! A auditoria está limpa para começar do zero.', 'HISTÓRICO LIMPO');
                this.refreshEstoquistaPendingQueue();
                await this.loadReceivingAudit();
            } catch (err) {
                await window.kippeModalAlert('❌ ' + err.message, 'ERRO AO ZERAR');
            }
        });

        document.querySelectorAll('#receiving-audit-status-tabs [data-audit-status]').forEach(btn => {
            btn.addEventListener('click', () => {
                syncAuditTabsUI(btn.getAttribute('data-audit-status') || 'ALL');
                this.loadReceivingAudit();
            });
        });
    }

    async loadReceivingAudit() {
        const listEl = document.getElementById('receiving-audit-list');
        const summaryEl = document.getElementById('receiving-audit-summary');
        const q = (document.getElementById('receiving-audit-search')?.value || '').trim();
        const status = this._receivingAuditStatus || 'ALL';

        if (listEl) {
            listEl.innerHTML = '<div style="background:#FFFFFF;border-radius:12px;padding:24px;text-align:center;font-size:12px;font-weight:800;color:#64748B;">Carregando registros de recebimento...</div>';
        }

        try {
            const params = new URLSearchParams({ q, status, limit: '80' });
            const res = await fetch(`/api/receiving/audit?${params.toString()}`, { credentials: 'same-origin' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Falha ao consultar recebimentos.');

            const s = data.summary || { total: 0, pendente: 0, aprovado: 0, com_divergencia: 0 };
            if (summaryEl) {
                summaryEl.innerHTML = `
                    <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:8px 4px;">
                        <p style="font-size:14px;font-weight:900;color:#1E293B;margin:0;">${s.total}</p>
                        <p style="font-size:8px;font-weight:900;color:#64748B;margin:2px 0 0;text-transform:uppercase;">TOTAL</p>
                    </div>
                    <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:8px 4px;">
                        <p style="font-size:14px;font-weight:900;color:#B45309;margin:0;">${s.pendente}</p>
                        <p style="font-size:8px;font-weight:900;color:#B45309;margin:2px 0 0;text-transform:uppercase;">PENDENTE</p>
                    </div>
                    <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;padding:8px 4px;">
                        <p style="font-size:14px;font-weight:900;color:#15803D;margin:0;">${s.aprovado}</p>
                        <p style="font-size:8px;font-weight:900;color:#15803D;margin:2px 0 0;text-transform:uppercase;">APROVADO</p>
                    </div>
                    <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:8px 4px;">
                        <p style="font-size:14px;font-weight:900;color:#B91C1C;margin:0;">${s.com_divergencia}</p>
                        <p style="font-size:8px;font-weight:900;color:#B91C1C;margin:2px 0 0;text-transform:uppercase;">DIVERG.</p>
                    </div>
                `;
            }

            const records = data.records || [];
            if (!listEl) return;
            if (records.length === 0) {
                listEl.innerHTML = '<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:24px;text-align:center;font-size:12px;font-weight:800;color:#64748B;">Nenhum recebimento encontrado para este filtro.</div>';
                return;
            }

            const statusBadge = (st) => {
                if (st === 'APROVADO') {
                    return '<span style="padding:3px 8px;border-radius:6px;background:#DCFCE7;color:#166534;border:1px solid #86EFAC;font-size:9px;font-weight:900;text-transform:uppercase;white-space:nowrap;">✅ APROVADO</span>';
                }
                if (st === 'REJEITADO') {
                    return '<span style="padding:3px 8px;border-radius:6px;background:#FEE2E2;color:#991B1B;border:1px solid #FCA5A5;font-size:9px;font-weight:900;text-transform:uppercase;white-space:nowrap;">✕ REJEITADO</span>';
                }
                return '<span style="padding:3px 8px;border-radius:6px;background:#FEF3C7;color:#92400E;border:1px solid #FCD34D;font-size:9px;font-weight:900;text-transform:uppercase;white-space:nowrap;">⏳ AGUARDANDO</span>';
            };

            const fmtDate = (iso) => window.formatBrtDateTime(iso);

            window.openQuickComplementFromAudit = (divId, sku, prodName, nfNum, supplier, pendingMax) => {
                const isEstoquistaModal = this.canManageCatalog();
                document.getElementById('kippe-complement-modal')?.remove();
                const compOverlay = document.createElement('div');
                compOverlay.id = 'kippe-complement-modal';
                compOverlay.style.cssText = 'position:fixed;inset:0;z-index:10075;background:rgba(15,23,42,0.8);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:16px;';
                const defExp = new Date(Date.now() + 365 * 86400000).toISOString().slice(0, 10);
                const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

                compOverlay.innerHTML = `
                    <div style="background:#FFFFFF;border-radius:16px;width:100%;max-width:390px;overflow:hidden;box-shadow:0 24px 48px rgba(15,23,42,0.45);border:1px solid #E2E8F0;">
                        <div style="background:#EA580C;color:#FFFFFF;padding:13px 16px;display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <div style="font-size:9px;font-weight:900;text-transform:uppercase;color:#FFEDD5;">CANHOTO RETIDO · NF ${esc(nfNum)}</div>
                                <h3 style="font-size:13px;font-weight:900;margin:2px 0 0;text-transform:uppercase;">RECEBER COMPLEMENTO</h3>
                            </div>
                            <button type="button" id="close-audit-comp-modal" style="background:rgba(255,255,255,0.2);border:none;color:#FFFFFF;width:30px;height:30px;border-radius:8px;font-weight:900;cursor:pointer;">✕</button>
                        </div>
                        <div style="padding:14px;display:flex;flex-direction:column;gap:10px;">
                            <div style="background:#FFF7ED;border:1px solid #FDBA74;border-radius:10px;padding:10px;">
                                <p style="font-size:11px;font-weight:900;color:#0F172A;margin:0;text-transform:uppercase;">${esc(prodName)}</p>
                                <p style="font-size:10px;font-weight:700;color:#64748B;margin:3px 0 0;">${esc(supplier)}</p>
                                <p style="font-size:10px;font-weight:900;color:#C2410C;margin:4px 0 0;">SALDO PENDENTE DO CANHOTO: ${pendingMax}</p>
                            </div>
                            <div>
                                <label style="display:block;font-size:9.5px;font-weight:900;color:#334155;text-transform:uppercase;margin-bottom:4px;">Quantidade Recebida Agora</label>
                                <input type="number" id="audit-comp-qty" value="${pendingMax}" min="1" max="${pendingMax}"
                                    style="width:100%;height:38px;border:1.5px solid #CBD5E1;border-radius:9px;padding:0 10px;font-size:14px;font-weight:900;color:#0F172A;box-sizing:border-box;">
                            </div>
                            ${isEstoquistaModal ? `
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                                <div>
                                    <label style="display:block;font-size:9px;font-weight:900;color:#475569;text-transform:uppercase;margin-bottom:4px;">Lote (Opcional)</label>
                                    <input type="text" id="audit-comp-batch" placeholder="AUTO"
                                        style="width:100%;height:36px;border:1px solid #CBD5E1;border-radius:8px;padding:0 8px;font-size:11px;font-weight:800;text-transform:uppercase;box-sizing:border-box;">
                                </div>
                                <div>
                                    <label style="display:block;font-size:9px;font-weight:900;color:#475569;text-transform:uppercase;margin-bottom:4px;">Validade</label>
                                    <input type="date" id="audit-comp-exp" value="${defExp}"
                                        style="width:100%;height:36px;border:1px solid #CBD5E1;border-radius:8px;padding:0 8px;font-size:11px;font-weight:800;box-sizing:border-box;">
                                </div>
                            </div>
                            ` : `
                            <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:8px 10px;font-size:10px;font-weight:700;color:#1E40AF;line-height:1.35;">
                                Ao confirmar, o saldo do canhoto será abatido e o item seguirá para a fila de armazenagem do Estoquista.
                            </div>
                            `}
                            <div id="audit-comp-err" style="display:none;background:#FEF2F2;border:1px solid #FECACA;color:#B91C1C;font-size:10px;font-weight:800;padding:8px;border-radius:8px;"></div>
                            <button type="button" id="confirm-audit-comp-btn"
                                style="width:100%;background:#16A34A;color:#FFFFFF;border:none;border-radius:10px;padding:12px;font-size:11px;font-weight:900;text-transform:uppercase;cursor:pointer;">
                                ${isEstoquistaModal ? '✅ CONFIRMAR ENTRADA & ABATER SALDO' : '✅ REGISTRAR COMPLEMENTO & ENVIAR P/ ESTOQUISTA'}
                            </button>
                        </div>
                    </div>
                `;
                document.body.appendChild(compOverlay);

                const closeOv = () => compOverlay.remove();
                document.getElementById('close-audit-comp-modal')?.addEventListener('click', closeOv);
                compOverlay.addEventListener('click', (e) => { if (e.target === compOverlay) closeOv(); });

                document.getElementById('confirm-audit-comp-btn')?.addEventListener('click', async (ev) => {
                    const submitBtn = ev.currentTarget;
                    const errBox = document.getElementById('audit-comp-err');
                    const qtyVal = Number(document.getElementById('audit-comp-qty')?.value || 0);
                    const batchVal = (document.getElementById('audit-comp-batch')?.value || '').trim();
                    const expVal = (document.getElementById('audit-comp-exp')?.value || '').trim();

                    if (qtyVal <= 0 || qtyVal > pendingMax) {
                        if (errBox) {
                            errBox.textContent = `Informe uma quantidade entre 1 e ${pendingMax}.`;
                            errBox.style.display = 'block';
                        }
                        return;
                    }
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'PROCESSANDO...';
                    try {
                        const r = await fetch(`/api/receiving/divergences/${divId}/complement`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'same-origin',
                            body: JSON.stringify({
                                sku,
                                quantity: qtyVal,
                                batch_code: batchVal,
                                expiration_date: expVal,
                            }),
                        });
                        const out = await r.json().catch(() => ({}));
                        if (!r.ok) {
                            if (errBox) {
                                errBox.textContent = out.error || 'Falha ao registrar complemento.';
                                errBox.style.display = 'block';
                            }
                            submitBtn.disabled = false;
                            submitBtn.textContent = isEstoquistaModal ? '✅ CONFIRMAR ENTRADA & ABATER SALDO' : '✅ REGISTRAR COMPLEMENTO & ENVIAR P/ ESTOQUISTA';
                            return;
                        }
                        closeOv();
                        await this.loadReceivingAudit();
                        await this.refreshEstoquistaPendingQueue();
                    } catch (err) {
                        if (errBox) {
                            errBox.textContent = 'Erro de rede: ' + (err.message || err);
                            errBox.style.display = 'block';
                        }
                        submitBtn.disabled = false;
                        submitBtn.textContent = isEstoquistaModal ? '✅ CONFIRMAR ENTRADA & ABATER SALDO' : '✅ REGISTRAR COMPLEMENTO & ENVIAR P/ ESTOQUISTA';
                    }
                });
            };

            window.openReclassifyDivergenceModal = (btn) => {
                const divId = btn.getAttribute('data-div-id');
                const prodName = btn.getAttribute('data-div-name') || '';
                const nfNum = btn.getAttribute('data-div-nf') || 'S/N';
                const currentSt = btn.getAttribute('data-div-current') || 'CANHOTO_RETIDO';
                const currentAmt = Number(btn.getAttribute('data-div-amount') || 0);
                const diffVal = Number(btn.getAttribute('data-div-diff') || 0);

                document.getElementById('kippe-reclassify-div-modal')?.remove();
                const overlay = document.createElement('div');
                overlay.id = 'kippe-reclassify-div-modal';
                overlay.style.cssText = 'position:fixed;inset:0;z-index:10070;background:rgba(15,23,42,0.8);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:14px;';

                const options = diffVal > 0 ? [
                    { id: 'SOBRA_DEVOLVIDA', label: '↩️ Sobra Devolvida ao Entregador' },
                    { id: 'BONIFICACAO_ACEITA', label: '🎁 Aceita como Bonificação' },
                    { id: 'REFATURAMENTO_NF', label: '🔄 NF Será Refaturada / Complementada' },
                ] : [
                    { id: 'REFATURAMENTO_NF', label: '🔄 NF Será Refaturada (Retirar Item da NF)' },
                    { id: 'ABATIMENTO_BOLETO', label: '🧾 Abatimento no Boleto / Nota de Crédito' },
                    { id: 'RESSARCIDO_NO_ATO', label: '💵 Ressarcido no Ato pelo Entregador' },
                    { id: 'CANHOTO_RETIDO', label: '📌 Reter Canhoto (Entrega Complementar)' },
                ];

                const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

                overlay.innerHTML = `
                    <div style="background:#FFFFFF;border-radius:16px;width:100%;max-width:400px;overflow:hidden;box-shadow:0 24px 48px rgba(15,23,42,0.45);border:1px solid #E2E8F0;">
                        <div style="background:#124191;color:#FFFFFF;padding:13px 16px;display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <div style="font-size:9px;font-weight:900;text-transform:uppercase;color:#BFDBFE;">AUDITORIA DE DIVERGÊNCIA · NF ${esc(nfNum)}</div>
                                <h3 style="font-size:13px;font-weight:900;margin:2px 0 0;text-transform:uppercase;">ALTERAR DESFECHO</h3>
                            </div>
                            <button type="button" id="close-reclassify-modal" style="background:rgba(255,255,255,0.2);border:none;color:#FFFFFF;width:30px;height:30px;border-radius:8px;font-weight:900;cursor:pointer;">✕</button>
                        </div>
                        <div style="padding:14px;display:flex;flex-direction:column;gap:10px;">
                            <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:10px;">
                                <p style="font-size:11px;font-weight:900;color:#0F172A;margin:0;text-transform:uppercase;">${esc(prodName)}</p>
                                <p style="font-size:9.5px;font-weight:700;color:#64748B;margin:3px 0 0;">Status atual: <strong>${esc(currentSt)}</strong></p>
                            </div>
                            <div>
                                <label style="display:block;font-size:9.5px;font-weight:900;color:#334155;text-transform:uppercase;margin-bottom:4px;">Novo Desfecho</label>
                                <select id="reclassify-settlement-sel" style="width:100%;height:38px;border:1.5px solid #CBD5E1;border-radius:9px;padding:0 8px;font-size:11px;font-weight:900;color:#0F172A;background:#FFFFFF;">
                                    ${options.map(o => `<option value="${o.id}" ${o.id === currentSt ? 'selected' : ''}>${o.label}</option>`).join('')}
                                </select>
                            </div>
                            <div>
                                <label style="display:block;font-size:9.5px;font-weight:900;color:#334155;text-transform:uppercase;margin-bottom:4px;">Valor Ressarcido / Abatido (R$, Opcional)</label>
                                <input type="number" step="0.01" min="0" id="reclassify-amount-inp" value="${currentAmt > 0 ? currentAmt : ''}" placeholder="0,00"
                                    style="width:100%;height:36px;border:1px solid #CBD5E1;border-radius:8px;padding:0 10px;font-size:12px;font-weight:900;box-sizing:border-box;">
                            </div>
                            <div>
                                <label style="display:block;font-size:9.5px;font-weight:900;color:#334155;text-transform:uppercase;margin-bottom:4px;">Observação / Motivo da Alteração</label>
                                <input type="text" id="reclassify-note-inp" placeholder="Ex: Fornecedor irá refaturar a NF"
                                    style="width:100%;height:36px;border:1px solid #CBD5E1;border-radius:8px;padding:0 10px;font-size:11px;box-sizing:border-box;">
                            </div>
                            <div id="reclassify-err-box" style="display:none;background:#FEF2F2;border:1px solid #FECACA;color:#B91C1C;font-size:10px;font-weight:800;padding:8px;border-radius:8px;"></div>
                            <button type="button" id="confirm-reclassify-btn" style="width:100%;background:#16A34A;color:#FFFFFF;border:none;border-radius:10px;padding:12px;font-size:11px;font-weight:900;text-transform:uppercase;cursor:pointer;">
                                ✅ SALVAR NOVO DESFECHO
                            </button>
                        </div>
                    </div>
                `;
                document.body.appendChild(overlay);

                const closeOverlay = () => overlay.remove();
                document.getElementById('close-reclassify-modal')?.addEventListener('click', closeOverlay);
                overlay.addEventListener('click', (e) => { if (e.target === overlay) closeOverlay(); });

                document.getElementById('confirm-reclassify-btn')?.addEventListener('click', async (ev) => {
                    const submitBtn = ev.currentTarget;
                    const errBox = document.getElementById('reclassify-err-box');
                    const settlementType = document.getElementById('reclassify-settlement-sel')?.value || '';
                    const settlementAmount = Number(document.getElementById('reclassify-amount-inp')?.value || 0);
                    const notes = (document.getElementById('reclassify-note-inp')?.value || '').trim();

                    submitBtn.disabled = true;
                    submitBtn.textContent = 'SALVANDO...';
                    try {
                        const r = await fetch(`/api/receiving/divergences/${divId}/settlement`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'same-origin',
                            body: JSON.stringify({
                                settlement_type: settlementType,
                                settlement_amount: settlementAmount,
                                notes,
                            }),
                        });
                        const out = await r.json().catch(() => ({}));
                        if (!r.ok) {
                            if (errBox) {
                                errBox.textContent = out.error || 'Falha ao atualizar desfecho.';
                                errBox.style.display = 'block';
                            }
                            submitBtn.disabled = false;
                            submitBtn.textContent = '✅ SALVAR NOVO DESFECHO';
                            return;
                        }
                        closeOverlay();
                        await this.loadReceivingAudit();
                        await this.refreshEstoquistaPendingQueue();
                    } catch (err) {
                        if (errBox) {
                            errBox.textContent = 'Erro de rede: ' + (err.message || err);
                            errBox.style.display = 'block';
                        }
                        submitBtn.disabled = false;
                        submitBtn.textContent = '✅ SALVAR NOVO DESFECHO';
                    }
                });
            };

            window.openAdjustQueueItemModal = (btn) => {
                const queueId = btn.getAttribute('data-queue-id');
                const itemIdx = Number(btn.getAttribute('data-item-idx') || 0);
                const itemName = btn.getAttribute('data-item-name') || '';
                const currentQty = Number(btn.getAttribute('data-item-qty') || 0);
                const nfNum = btn.getAttribute('data-rec-nf') || 'S/N';
                const defaultNewQty = Math.max(0, currentQty - 1);

                document.getElementById('kippe-adjust-qitem-modal')?.remove();
                const overlay = document.createElement('div');
                overlay.id = 'kippe-adjust-qitem-modal';
                overlay.style.cssText = 'position:fixed;inset:0;z-index:10075;background:rgba(15,23,42,0.82);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:14px;';

                const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

                overlay.innerHTML = `
                    <div style="background:#FFFFFF;border-radius:16px;width:100%;max-width:410px;overflow:hidden;box-shadow:0 24px 48px rgba(15,23,42,0.45);border:1px solid #E2E8F0;">
                        <div style="background:#124191;color:#FFFFFF;padding:13px 16px;display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <div style="font-size:9px;font-weight:900;text-transform:uppercase;color:#BFDBFE;">AJUSTE PRÉ-ESTOQUE · NF ${esc(nfNum)}</div>
                                <h3 style="font-size:13px;font-weight:900;margin:2px 0 0;text-transform:uppercase;">CORRIGIR QUANTIDADE FÍSICA</h3>
                            </div>
                            <button type="button" id="close-adj-qitem-modal" style="background:rgba(255,255,255,0.2);border:none;color:#FFFFFF;width:30px;height:30px;border-radius:8px;font-weight:900;cursor:pointer;">✕</button>
                        </div>
                        <div style="padding:14px;display:flex;flex-direction:column;gap:10px;">
                            <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:10px;">
                                <p style="font-size:11px;font-weight:900;color:#0F172A;margin:0;text-transform:uppercase;">${esc(itemName)}</p>
                                <p style="font-size:9.5px;font-weight:700;color:#64748B;margin:3px 0 0;">Lançado inicialmente na conferência: <strong>${currentQty} UN</strong></p>
                            </div>
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                                <div>
                                    <label style="display:block;font-size:9px;font-weight:900;color:#334155;text-transform:uppercase;margin-bottom:4px;">Qtd na Nota (NF)</label>
                                    <input type="number" min="0" id="adj-qitem-expected" value="${currentQty}"
                                        style="width:100%;height:38px;border:1.5px solid #CBD5E1;border-radius:8px;padding:0 10px;font-size:13px;font-weight:900;box-sizing:border-box;">
                                </div>
                                <div>
                                    <label style="display:block;font-size:9px;font-weight:900;color:#166534;text-transform:uppercase;margin-bottom:4px;">Qtd Física Real</label>
                                    <input type="number" min="0" id="adj-qitem-real" value="${defaultNewQty}"
                                        style="width:100%;height:38px;border:1.5px solid #86EFAC;background:#F0FDF4;border-radius:8px;padding:0 10px;font-size:13px;font-weight:900;color:#14532D;box-sizing:border-box;">
                                </div>
                            </div>
                            <div>
                                <label style="display:block;font-size:9.5px;font-weight:900;color:#334155;text-transform:uppercase;margin-bottom:4px;">Desfecho da Diferença</label>
                                <select id="adj-qitem-settlement" style="width:100%;height:38px;border:1.5px solid #86EFAC;background:#DCFCE7;border-radius:9px;padding:0 8px;font-size:11px;font-weight:900;color:#166534;">
                                    <option value="RESSARCIDO_NO_ATO" selected>💵 Ressarcido no Ato (Pago pelo Entregador)</option>
                                    <option value="ABATIMENTO_BOLETO">🧾 Abatimento no Boleto / Nota de Crédito</option>
                                    <option value="REFATURAMENTO_NF">🔄 NF Será Refaturada (Retirar Item da NF)</option>
                                    <option value="CANHOTO_RETIDO">📌 Reter Canhoto (Entrega Complementar)</option>
                                </select>
                            </div>
                            <div>
                                <label style="display:block;font-size:9px;font-weight:900;color:#334155;text-transform:uppercase;margin-bottom:4px;">Valor Pago / Abatido (R$, Opcional)</label>
                                <div style="display:flex;gap:6px;">
                                    <input type="number" step="0.01" min="0" id="adj-qitem-amount" placeholder="0,00"
                                        style="flex:1;height:36px;border:1px solid #CBD5E1;border-radius:8px;padding:0 10px;font-size:12px;font-weight:900;box-sizing:border-box;">
                                    <button type="button" id="adj-tag-dinheiro" style="height:36px;padding:0 8px;background:#F1F5F9;border:1px solid #CBD5E1;border-radius:7px;font-size:9px;font-weight:900;cursor:pointer;">DINHEIRO</button>
                                    <button type="button" id="adj-tag-pix" style="height:36px;padding:0 8px;background:#F1F5F9;border:1px solid #CBD5E1;border-radius:7px;font-size:9px;font-weight:900;cursor:pointer;">PIX</button>
                                </div>
                            </div>
                            <div>
                                <label style="display:block;font-size:9px;font-weight:900;color:#334155;text-transform:uppercase;margin-bottom:4px;">Observação</label>
                                <input type="text" id="adj-qitem-notes" placeholder="Ex: 1un faltando paga pelo entregador"
                                    style="width:100%;height:36px;border:1px solid #CBD5E1;border-radius:8px;padding:0 10px;font-size:11px;box-sizing:border-box;">
                            </div>
                            <div id="adj-qitem-err" style="display:none;background:#FEF2F2;border:1px solid #FECACA;color:#B91C1C;font-size:10px;font-weight:800;padding:8px;border-radius:8px;"></div>
                            <button type="button" id="confirm-adj-qitem-btn" style="width:100%;background:#16A34A;color:#FFFFFF;border:none;border-radius:10px;padding:12px;font-size:11px;font-weight:900;text-transform:uppercase;cursor:pointer;">
                                ✅ SALVAR QTD FÍSICA & REGISTRAR DIVERGÊNCIA
                            </button>
                        </div>
                    </div>
                `;
                document.body.appendChild(overlay);

                const closeOv = () => overlay.remove();
                document.getElementById('close-adj-qitem-modal')?.addEventListener('click', closeOv);
                overlay.addEventListener('click', (e) => { if (e.target === overlay) closeOv(); });

                const appendNoteTag = (tag) => {
                    const inp = document.getElementById('adj-qitem-notes');
                    if (!inp) return;
                    const cur = (inp.value || '').trim();
                    inp.value = cur ? `${cur} · ${tag}` : tag;
                };
                document.getElementById('adj-tag-dinheiro')?.addEventListener('click', () => appendNoteTag('PAGO EM DINHEIRO'));
                document.getElementById('adj-tag-pix')?.addEventListener('click', () => appendNoteTag('PAGO VIA PIX'));

                document.getElementById('confirm-adj-qitem-btn')?.addEventListener('click', async (ev) => {
                    const submitBtn = ev.currentTarget;
                    const errBox = document.getElementById('adj-qitem-err');
                    const expectedQty = Number(document.getElementById('adj-qitem-expected')?.value || 0);
                    const newQty = Number(document.getElementById('adj-qitem-real')?.value || 0);
                    const settlementType = document.getElementById('adj-qitem-settlement')?.value || 'RESSARCIDO_NO_ATO';
                    const settlementAmount = Number(document.getElementById('adj-qitem-amount')?.value || 0);
                    const notes = (document.getElementById('adj-qitem-notes')?.value || '').trim();

                    submitBtn.disabled = true;
                    submitBtn.textContent = 'SALVANDO...';
                    try {
                        const r = await fetch(`/api/receiving/pending/${queueId}/adjust-item`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'same-origin',
                            body: JSON.stringify({
                                item_index: itemIdx,
                                expected_quantity: expectedQty,
                                new_quantity: newQty,
                                settlement_type: settlementType,
                                settlement_amount: settlementAmount,
                                notes,
                            }),
                        });
                        const out = await r.json().catch(() => ({}));
                        if (!r.ok) {
                            if (errBox) {
                                errBox.textContent = out.error || 'Falha ao ajustar item.';
                                errBox.style.display = 'block';
                            }
                            submitBtn.disabled = false;
                            submitBtn.textContent = '✅ SALVAR QTD FÍSICA & REGISTRAR DIVERGÊNCIA';
                            return;
                        }
                        closeOv();
                        await this.loadReceivingAudit();
                        await this.refreshEstoquistaPendingQueue();
                    } catch (err) {
                        if (errBox) {
                            errBox.textContent = 'Erro de rede: ' + (err.message || err);
                            errBox.style.display = 'block';
                        }
                        submitBtn.disabled = false;
                        submitBtn.textContent = '✅ SALVAR QTD FÍSICA & REGISTRAR DIVERGÊNCIA';
                    }
                });
            };

            listEl.innerHTML = records.map(rec => {
                const borderLeftColor = rec.status === 'APROVADO' ? '#16A34A' : rec.status === 'REJEITADO' ? '#DC2626' : '#D97706';
                const canAdjustPending = rec.source === 'QUEUE' && rec.status === 'PENDENTE' && Boolean(rec.queue_id);
                const itemsHtml = (rec.items || []).map((it, itemIdx) => {
                    const meta = [
                        it.sku && !it.is_unlinked ? `SKU: ${it.sku}` : 'SEM CADASTRO PRÉVIO',
                        it.batch_code ? `Lote: ${it.batch_code}` : '',
                        it.expiration_date ? `Val: ${it.expiration_date}` : '',
                    ].filter(Boolean).join(' · ');
                    const safeNameAttr = String(it.name || it.sku || '').replace(/"/g, '&quot;');
                    const safeNfAttr = String(rec.invoice_number || '').replace(/"/g, '&quot;');
                    return `
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid #F1F5F9;">
                            <div style="min-width:0;flex:1;">
                                <p style="font-size:11px;font-weight:900;color:#1E293B;margin:0;line-height:1.3;word-break:break-word;">${it.name}</p>
                                <p style="font-size:9px;font-weight:700;color:#64748B;margin:2px 0 0;">${meta}</p>
                            </div>
                            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex-shrink:0;">
                                <span style="background:#EFF6FF;color:#124191;border:1px solid #BFDBFE;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:900;">
                                    ${it.quantity} UN
                                </span>
                                ${canAdjustPending ? `
                                    <button type="button"
                                        data-queue-id="${rec.queue_id}"
                                        data-item-idx="${itemIdx}"
                                        data-item-name="${safeNameAttr}"
                                        data-item-qty="${Number(it.quantity || 0)}"
                                        data-rec-nf="${safeNfAttr}"
                                        onclick="window.openAdjustQueueItemModal(this)"
                                        style="background:#FFFBEB;color:#B45309;border:1px solid #FDE68A;border-radius:5px;padding:2px 6px;font-size:8px;font-weight:900;text-transform:uppercase;cursor:pointer;">
                                        ✏️ AJUSTAR QTD
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `;
                }).join('');

                const divHtml = (rec.divergences || []).length > 0 ? `
                    <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:6px;">
                        <p style="font-size:9px;font-weight:900;color:#991B1B;margin:0;text-transform:uppercase;">⚠️ Divergências Formalizadas (${rec.divergences.length})</p>
                        ${rec.divergences.map(d => {
                            const st = String(d.settlement_type || d.status || 'REGISTRADA').toUpperCase();
                            const amtNum = Number(d.settlement_amount || 0);
                            const amtTag = amtNum > 0 ? ` · R$ ${amtNum.toFixed(2).replace('.', ',')}` : '';
                            const badgeMap = {
                                'CANHOTO_RETIDO': `<span style="display:inline-block;padding:2px 6px;border-radius:5px;background:#FEF3C7;color:#92400E;border:1px solid #FCD34D;font-size:8px;font-weight:900;">📌 CANHOTO RETIDO · SALDO: ${d.pending_qty}</span>`,
                                'COMPLEMENTO_RECEBIDO': `<span style="display:inline-block;padding:2px 6px;border-radius:5px;background:#DCFCE7;color:#166534;border:1px solid #86EFAC;font-size:8px;font-weight:900;">✅ COMPLEMENTO RECEBIDO</span>`,
                                'RESOLVIDA': `<span style="display:inline-block;padding:2px 6px;border-radius:5px;background:#DCFCE7;color:#166534;border:1px solid #86EFAC;font-size:8px;font-weight:900;">✅ CANHOTO LIBERADO</span>`,
                                'RESSARCIDO_NO_ATO': `<span style="display:inline-block;padding:2px 6px;border-radius:5px;background:#DCFCE7;color:#166534;border:1px solid #86EFAC;font-size:8px;font-weight:900;">💵 RESSARCIDO NO ATO${amtTag}</span>`,
                                'ABATIMENTO_BOLETO': `<span style="display:inline-block;padding:2px 6px;border-radius:5px;background:#DBEAFE;color:#1E40AF;border:1px solid #93C5FD;font-size:8px;font-weight:900;">🧾 ABATIMENTO NO BOLETO${amtTag}</span>`,
                                'REFATURAMENTO_NF': `<span style="display:inline-block;padding:2px 6px;border-radius:5px;background:#F3E8FF;color:#6B21A8;border:1px solid #D8B4FE;font-size:8px;font-weight:900;">🔄 NF REFATURADA / SUBSTITUÍDA</span>`,
                                'SOBRA_DEVOLVIDA': `<span style="display:inline-block;padding:2px 6px;border-radius:5px;background:#F1F5F9;color:#334155;border:1px solid #CBD5E1;font-size:8px;font-weight:900;">↩️ SOBRA DEVOLVIDA</span>`,
                                'BONIFICACAO_ACEITA': `<span style="display:inline-block;padding:2px 6px;border-radius:5px;background:#CCFBF1;color:#115E59;border:1px solid #5EEAD4;font-size:8px;font-weight:900;">🎁 BONIFICAÇÃO ACEITA</span>`,
                            };
                            const badge = badgeMap[st] || `<span style="display:inline-block;padding:2px 6px;border-radius:5px;background:#FEE2E2;color:#991B1B;border:1px solid #FCA5A5;font-size:8px;font-weight:900;">REGISTRADA</span>`;
                            const safeProdAttr = String(d.product_name || d.sku || '').replace(/"/g, '&quot;');
                            const safeNfAttr = String(rec.invoice_number || '').replace(/"/g, '&quot;');
                            return `
                                <div style="font-size:10px;color:#7F1D1D;font-weight:700;margin:0;line-height:1.35;">
                                    • ${d.product_name}: Esperado <strong>${d.expected_qty}</strong> / Conferido <strong>${d.counted_qty}</strong>
                                    (${d.divergence_qty > 0 ? '+' : ''}${d.divergence_qty}) — <span style="text-transform:uppercase;">${d.reason}</span>
                                    ${d.notes ? `(${d.notes})` : ''}
                                    <div style="margin-top:5px;display:flex;align-items:center;justify-content:space-between;gap:6px;flex-wrap:wrap;">
                                        ${badge}
                                        <div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;">
                                            ${st === 'CANHOTO_RETIDO' && Number(d.pending_qty || 0) > 0 ? `
                                                <button type="button"
                                                    onclick="window.openQuickComplementFromAudit('${d.id}', '${String(d.sku || '').replace(/'/g, '')}', '${safeProdAttr.replace(/'/g, '')}', '${safeNfAttr.replace(/'/g, '')}', '${String(rec.supplier || '').replace(/"/g, '&quot;').replace(/'/g, '')}', ${Number(d.pending_qty || 0)})"
                                                    style="background:#EA580C;color:#FFFFFF;border:none;border-radius:6px;padding:4px 8px;font-size:8.5px;font-weight:900;text-transform:uppercase;cursor:pointer;">
                                                    📦 RECEBER COMPLEMENTO
                                                </button>
                                            ` : ''}
                                            ${st !== 'COMPLEMENTO_RECEBIDO' ? `
                                                <button type="button"
                                                    data-div-id="${d.id}"
                                                    data-div-name="${safeProdAttr}"
                                                    data-div-nf="${safeNfAttr}"
                                                    data-div-current="${st}"
                                                    data-div-amount="${amtNum}"
                                                    data-div-diff="${Number(d.divergence_qty || 0)}"
                                                    onclick="window.openReclassifyDivergenceModal(this)"
                                                    style="background:#FFFFFF;color:#124191;border:1px solid #BFDBFE;border-radius:6px;padding:3px 8px;font-size:8.5px;font-weight:900;text-transform:uppercase;cursor:pointer;">
                                                    ✏️ ALTERAR DESFECHO
                                                </button>
                                            ` : ''}
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                ` : '';

                const reqHtml = (rec.product_requests || []).length > 0 ? `
                    <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:4px;">
                        <p style="font-size:9px;font-weight:900;color:#92400E;margin:0;text-transform:uppercase;">🚩 Solicitações de Cadastro (${rec.product_requests.length})</p>
                        ${rec.product_requests.map(pr => `
                            <p style="font-size:10px;color:#78350F;font-weight:700;margin:0;">
                                • ${pr.raw_description} — <span style="text-transform:uppercase;">${pr.status}</span>${pr.created_sku ? ` (SKU: ${pr.created_sku})` : ''}
                            </p>
                        `).join('')}
                    </div>
                ` : '';

                const validationLine = rec.status === 'PENDENTE'
                    ? '<span style="color:#B45309;font-weight:900;">Aguardando cadastro e validação do Estoquista</span>'
                    : `<span>Validado por <strong style="color:#1E293B;">${rec.resolved_by_name || rec.resolved_by_id}</strong> em ${fmtDate(rec.resolved_at)}</span>`;

                return `
                    <article style="background:#FFFFFF;border-radius:14px;padding:14px;box-shadow:0 1px 3px rgba(15,23,42,0.07);border:1px solid #E2E8F0;border-left:4px solid ${borderLeftColor};display:flex;flex-direction:column;gap:10px;">
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
                            <div style="min-width:0;flex:1;">
                                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                                    <span style="font-size:9px;font-family:monospace;font-weight:900;background:#F1F5F9;color:#334155;padding:2px 6px;border-radius:5px;">${rec.protocol}</span>
                                    <span style="font-size:11px;font-weight:900;color:#124191;text-transform:uppercase;">NF ${rec.invoice_number}</span>
                                </div>
                                <h3 style="font-size:13px;font-weight:900;color:#0F172A;margin:4px 0 0;text-transform:uppercase;line-height:1.25;">${rec.supplier}</h3>
                            </div>
                            ${statusBadge(rec.status)}
                        </div>

                        <div style="background:#F8FAFC;border-radius:8px;padding:9px;font-size:10px;color:#475569;display:flex;flex-direction:column;gap:3px;border:1px solid #F1F5F9;">
                            <p style="margin:0;">Conferido por <strong style="color:#1E293B;">${rec.submitted_by_name}</strong> (${rec.submitted_by_id}) em <strong>${fmtDate(rec.created_at)}</strong></p>
                            <p style="margin:0;">${validationLine}</p>
                            <p style="margin:0;">Totais: <strong>${rec.total_items} item(ns)</strong> · <strong>${rec.total_units} unidade(s)</strong></p>
                        </div>

                        <div>
                            <p style="font-size:9px;font-weight:900;color:#94A3B8;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 4px;">Itens Conferidos</p>
                            <div>${itemsHtml}</div>
                        </div>

                        ${divHtml}
                        ${reqHtml}
                    </article>
                `;
            }).join('');
        } catch (err) {
            if (listEl) {
                listEl.innerHTML = `<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:12px;padding:14px;font-size:12px;font-weight:800;color:#B91C1C;">❌ ${err.message}</div>`;
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new KippeApplication();
    app.bootstrap();
});

// ═══════════════════════════════════════════════════════════
// Validade — Tela operacional (feature isolada)
// ═══════════════════════════════════════════════════════════
document.getElementById('btn-module-validity')?.addEventListener('click', () => {
  document.querySelectorAll('main > section[id$="-view"]').forEach(el => el.classList.add('hidden'));
  document.getElementById('validity-view')?.classList.remove('hidden');
  window.scrollTo(0, 0);
  window.ValidityFeature?.mount();
});

document.getElementById('btn-back-validity')?.addEventListener('click', () => {
  document.getElementById('validity-view')?.classList.add('hidden');
  document.getElementById('home-module-view')?.classList.remove('hidden');
});

// Wire da feature Conference (navegação + listeners)

