import { APIClient } from './api.js';
import { UIManager } from './ui.js';
import { Router } from './router.js';
import { ScannerManager } from './scanner.js';

class KippeApplication {
    constructor() {
        this.api = new APIClient();
        this.ui = new UIManager();
        this.router = new Router(this.ui, this.api);
        this.operatorName = localStorage.getItem('kippe_operator') || null;

        this.scanner = new ScannerManager((scannedCode) => {
            this.handleScanSuccess(scannedCode);
        });
    }

    async bootstrap() {
        console.log('[KIPPE] A iniciar KIPPE Platform Mobile...');
        this._registerServiceWorker();
        this.router.init();
        
        this.initIdentityManager();

        this.ui.bindSearchEvent((sku) => this.fetchAndRenderSku(sku));
        
        // NOVO: Liga o motor preditivo de procura
        this.ui.bindSearchAutocomplete(
            async (term) => {
                try { return await this.api.searchCatalog(term); } 
                catch (e) { return []; }
            },
            (sku) => { this.fetchAndRenderSku(sku); }
        );

        const scanBtn = document.getElementById('btn-scan');
        if (scanBtn) scanBtn.addEventListener('click', () => this.scanner.start());

        const quickReceiveBtn = document.getElementById('btn-quick-receive');
        if (quickReceiveBtn) {
            quickReceiveBtn.addEventListener('click', () => {
                const currentSku = document.getElementById('searchInput').value.trim();
                this.ui.showReceiveModal(currentSku);
            });
        }

        const submitReceiveBtn = document.getElementById('submit-receive-btn');
        if (submitReceiveBtn) submitReceiveBtn.addEventListener('click', () => this.submitReceive());

        const btnOpenTransfer = document.getElementById('btn-open-transfer');
        if (btnOpenTransfer) btnOpenTransfer.addEventListener('click', () => {
            this.ui.showTransferModal(document.getElementById('searchInput').value.trim());
        });

        const btnOpenAdjustment = document.getElementById('btn-open-adjustment');
        if (btnOpenAdjustment) btnOpenAdjustment.addEventListener('click', () => {
            this.ui.showAdjustmentModal(document.getElementById('searchInput').value.trim());
        });

        const submitTransferBtn = document.getElementById('submit-transfer-btn');
        if (submitTransferBtn) submitTransferBtn.addEventListener('click', () => this.submitTransfer());

        const submitAdjustmentBtn = document.getElementById('submit-adjustment-btn');
        if (submitAdjustmentBtn) submitAdjustmentBtn.addEventListener('click', () => this.submitAdjustment());
    }

    initIdentityManager() {
        if (!this.operatorName) {
            this.ui.showLockscreen();
        } else {
            this.ui.hideLockscreen(this.operatorName);
        }

        if (this.ui.elements.btnLogin) {
            this.ui.elements.btnLogin.addEventListener('click', () => {
                const name = this.ui.getLoginInputValue();
                if (name && name.length >= 2) {
                    this.operatorName = name.toUpperCase();
                    localStorage.setItem('kippe_operator', this.operatorName);
                    this.ui.hideLockscreen(this.operatorName);
                } else {
                    alert('Insira um nome válido para aceder ao sistema.');
                }
            });
        }

        if (this.ui.elements.btnLogout) {
            this.ui.elements.btnLogout.addEventListener('click', () => {
                localStorage.removeItem('kippe_operator');
                this.operatorName = null;
                if (this.ui.elements.dashboard) this.ui.elements.dashboard.classList.add('hidden');
                this.ui.showLockscreen();
            });
        }
    }

    handleScanSuccess(scannedCode) {
        this.ui.setInputValue(scannedCode);
        this.fetchAndRenderSku(scannedCode);
    }

    async fetchAndRenderSku(sku) {
        this.ui.showLoader();
        try {
            const data = await this.api.getSku(sku);
            this.ui.hideLoader();
            this.ui.renderDashboard(data);
        } catch (error) {
            this.ui.hideLoader();
            this.ui.showError(error.message || "SKU não encontrado.");
        }
    }

    async submitReceive() {
        const formData = this.ui.getReceiveFormData();
        if (!formData.quantity || isNaN(formData.quantity) || formData.quantity <= 0) {
            alert("Quantidade inválida."); return;
        }
        
        const payload = { ...formData, operator: this.operatorName || "Desconhecido" };
        try {
            this.ui.hideReceiveModal();
            this.ui.showLoader();
            await this.api.registerReceive(payload);
            this.fetchAndRenderSku(payload.sku);
        } catch (error) {
            this.ui.hideLoader();
            alert("Erro: " + error.message);
        }
    }

    async submitTransfer() {
        const formData = this.ui.getTransferFormData();
        if (!formData.quantity || isNaN(formData.quantity) || formData.quantity <= 0) return;
        
        const payload = { ...formData, operator: this.operatorName || "Desconhecido" };
        try {
            this.ui.hideTransferModal();
            this.ui.showLoader();
            await this.api.registerTransfer(payload);
            this.fetchAndRenderSku(payload.sku);
        } catch (error) {
            this.ui.hideLoader();
            alert("Erro: " + error.message);
        }
    }

    async submitAdjustment() {
        const formData = this.ui.getAdjustmentFormData();
        if (!formData.quantity || isNaN(formData.quantity)) return;
        
        const payload = { ...formData, operator: this.operatorName || "Desconhecido" };
        try {
            this.ui.hideAdjustmentModal();
            this.ui.showLoader();
            await this.api.registerAdjustment(payload);
            this.fetchAndRenderSku(payload.sku);
        } catch (error) {
            this.ui.hideLoader();
            alert("Erro: " + error.message);
        }
    }

    _registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/web/sw.js')
                    .catch(err => console.error('[KIPPE] Service Worker falhou:', err));
            });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const app = new KippeApplication();
    app.bootstrap();
});

