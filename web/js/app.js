import { APIClient } from './api.js';
import { UIManager } from './ui.js';
import { Router } from './router.js';
import { ScannerManager } from './scanner.js';

class KippeApplication {
    constructor() {
        this.api = new APIClient();
        this.ui = new UIManager();
        this.router = new Router(this.ui, this.api);
        
        this.scanner = new ScannerManager((scannedCode) => {
            this.handleScanSuccess(scannedCode);
        });
    }

    async bootstrap() {
        console.log('[KIPPE] Inicializando KIPPE Platform Mobile...');
        this._registerServiceWorker();
        this.router.init();
        
        this.ui.bindSearchEvent((sku) => this.fetchAndRenderSku(sku));

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

        // BIND: Botões de Ações Operacionais no Dashboard
        const btnOpenTransfer = document.getElementById('btn-open-transfer');
        if (btnOpenTransfer) {
            btnOpenTransfer.addEventListener('click', () => {
                const currentSku = document.getElementById('searchInput').value.trim();
                this.ui.showTransferModal(currentSku);
            });
        }

        const btnOpenAdjustment = document.getElementById('btn-open-adjustment');
        if (btnOpenAdjustment) {
            btnOpenAdjustment.addEventListener('click', () => {
                const currentSku = document.getElementById('searchInput').value.trim();
                this.ui.showAdjustmentModal(currentSku);
            });
        }

        // BIND: Submissão dos Modais
        const submitTransferBtn = document.getElementById('submit-transfer-btn');
        if (submitTransferBtn) submitTransferBtn.addEventListener('click', () => this.submitTransfer());

        const submitAdjustmentBtn = document.getElementById('submit-adjustment-btn');
        if (submitAdjustmentBtn) submitAdjustmentBtn.addEventListener('click', () => this.submitAdjustment());
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
        const payload = { ...formData, operator: "PWA Mobile" };
        try {
            this.ui.hideReceiveModal();
            this.ui.showLoader();
            await this.api.registerReceive(payload);
            this.fetchAndRenderSku(payload.sku);
        } catch (error) {
            this.ui.hideLoader();
            alert("Erro ao registar entrada: " + error.message);
        }
    }

    async submitTransfer() {
        const formData = this.ui.getTransferFormData();
        if (!formData.quantity || isNaN(formData.quantity) || formData.quantity <= 0) {
            alert("Quantidade inválida."); return;
        }
        const payload = { ...formData, operator: "PWA Mobile" };
        try {
            this.ui.hideTransferModal();
            this.ui.showLoader();
            await this.api.registerTransfer(payload);
            this.fetchAndRenderSku(payload.sku);
        } catch (error) {
            this.ui.hideLoader();
            alert("Erro na transferência: " + error.message);
        }
    }

    async submitAdjustment() {
        const formData = this.ui.getAdjustmentFormData();
        if (!formData.quantity || isNaN(formData.quantity)) {
            alert("Quantidade inválida."); return;
        }
        const payload = { ...formData, operator: "Auditor Mobile" };
        try {
            this.ui.hideAdjustmentModal();
            this.ui.showLoader();
            await this.api.registerAdjustment(payload);
            this.fetchAndRenderSku(payload.sku);
        } catch (error) {
            this.ui.hideLoader();
            alert("Erro no ajuste: " + error.message);
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

