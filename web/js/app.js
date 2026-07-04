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
        
        // 1. Busca por Digitação
        this.ui.bindSearchEvent((sku) => this.fetchAndRenderSku(sku));

        // 2. Botão de Scan (Câmera)
        const scanBtn = document.getElementById('btn-scan');
        if (scanBtn) {
            scanBtn.addEventListener('click', () => this.scanner.start());
        }

        // 3. Botão "Registrar Nova Entrada" (aparece quando dá erro)
        const quickReceiveBtn = document.getElementById('btn-quick-receive');
        if (quickReceiveBtn) {
            quickReceiveBtn.addEventListener('click', () => {
                const currentSku = document.getElementById('searchInput').value.trim();
                this.ui.showReceiveModal(currentSku);
            });
        }

        // 4. Submissão do Formulário de Recebimento
        const submitReceiveBtn = document.getElementById('submit-receive-btn');
        if (submitReceiveBtn) {
            submitReceiveBtn.addEventListener('click', () => this.submitReceive());
        }
    }

    handleScanSuccess(scannedCode) {
        console.log("[KIPPE] Código capturado:", scannedCode);
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
            // A UI inteligentemente mostrará o botão para registrar entrada
            this.ui.showError(error.message || "SKU não encontrado.");
        }
    }

    // NOVO: Fluxo de Escrita (Command)
    async submitReceive() {
        const formData = this.ui.getReceiveFormData();
        
        if (!formData.quantity || isNaN(formData.quantity) || formData.quantity <= 0) {
            alert("Por favor, insira uma quantidade válida maior que zero.");
            return;
        }

        // Adiciona dados operacionais padronizados
        const payload = {
            ...formData,
            operator: "Mobile App PWA" // Rastreabilidade do autor
        };

        try {
            // Fecha o modal e mostra carregamento
            this.ui.hideReceiveModal();
            this.ui.showLoader();
            
            // Dispara o Command pro Backend via rede
            await this.api.registerReceive(payload);
            
            // Se sucesso, puxa o Dashboard atualizado para provar a gravação
            this.fetchAndRenderSku(payload.sku);

        } catch (error) {
            this.ui.hideLoader();
            alert("Erro ao registrar entrada: " + error.message);
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

