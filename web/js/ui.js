/**
 * Gerenciador de Interface de Usuário Vanilla JS.
 */
export class UIManager {
    constructor() {
        this.elements = {
            dashboard: document.getElementById('dashboard-view'),
            loader: document.getElementById('global-loader'),
            errorContainer: document.getElementById('error-container'),
            errorToast: document.getElementById('error-toast'),
            btnQuickReceive: document.getElementById('btn-quick-receive'),
            searchInput: document.getElementById('searchInput'),
            searchBtn: document.getElementById('searchBtn'),
            batchBody: document.getElementById('batch-matrix-body'),
            historyTimeline: document.getElementById('history-timeline'),
            receiveModal: document.getElementById('receive-modal'),
            closeReceiveModal: document.getElementById('close-receive-modal'),
            transferModal: document.getElementById('transfer-modal'),
            closeTransferModal: document.getElementById('close-transfer-modal'),
            adjustmentModal: document.getElementById('adjustment-modal'),
            closeAdjustmentModal: document.getElementById('close-adjustment-modal'),
            lockscreen: document.getElementById('lockscreen-modal'),
            operatorInput: document.getElementById('operator-input'),
            btnLogin: document.getElementById('btn-login'),
            btnLogout: document.getElementById('btn-logout'),
            operatorDisplay: document.getElementById('operator-display-name'),
            
            // Elementos da Câmera Fotográfica (Auditoria Visual)
            photoInput: document.getElementById('receive-photo-input'),
            photoPreview: document.getElementById('receive-photo-preview'),
            photoPlaceholder: document.getElementById('receive-photo-placeholder'),
            dashboardPhotoContainer: document.getElementById('prodPhotoContainer'),
            dashboardPhotoImg: document.getElementById('prodPhoto')
        };

        if (this.elements.closeReceiveModal) this.elements.closeReceiveModal.addEventListener('click', () => this.hideReceiveModal());
        if (this.elements.closeTransferModal) this.elements.closeTransferModal.addEventListener('click', () => this.hideTransferModal());
        if (this.elements.closeAdjustmentModal) this.elements.closeAdjustmentModal.addEventListener('click', () => this.hideAdjustmentModal());

        // Evento de Compressão de Imagem no momento da captura
        if (this.elements.photoInput) {
            this.elements.photoInput.addEventListener('change', (e) => this.handlePhotoUpload(e));
        }
    }

    // Comprime a foto no celular para evitar sobrecarregar o SQLite no Termux
    handlePhotoUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const MAX_WIDTH = 400; // Tamanho ideal para miniaturas Enterprise
                const scaleSize = MAX_WIDTH / img.width;
                canvas.width = MAX_WIDTH;
                canvas.height = img.height * scaleSize;
                
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                
                const compressedBase64 = canvas.toDataURL('image/jpeg', 0.7); // 70% quality
                
                this.elements.photoPreview.src = compressedBase64;
                this.elements.photoPreview.classList.remove('hidden');
                this.elements.photoPlaceholder.classList.add('hidden');
                this.elements.photoInput.dataset.base64 = compressedBase64; // Guarda para o envio
            };
            img.src = event.target.result;
        };
        reader.readAsDataURL(file);
    }

    showLockscreen() {
        if (this.elements.lockscreen) {
            this.elements.lockscreen.classList.remove('hidden');
            this.elements.lockscreen.classList.add('flex');
            if (this.elements.operatorInput) this.elements.operatorInput.value = '';
        }
    }

    hideLockscreen(operatorName) {
        if (this.elements.lockscreen) {
            this.elements.lockscreen.classList.add('hidden');
            this.elements.lockscreen.classList.remove('flex');
        }
        if (this.elements.operatorDisplay) this.elements.operatorDisplay.textContent = operatorName;
    }

    getLoginInputValue() { return this.elements.operatorInput ? this.elements.operatorInput.value.trim() : ''; }

    bindSearchAutocomplete(fetchSuggestionsCallback, selectSuggestionCallback) {
        const input = this.elements.searchInput;
        const suggBox = document.getElementById('search-suggestions');
        let timeout = null;
        if (!input || !suggBox) return;

        document.addEventListener('click', (e) => {
            if(!input.contains(e.target) && !suggBox.contains(e.target)) suggBox.classList.add('hidden');
        });

        input.addEventListener('input', (e) => {
            clearTimeout(timeout);
            const term = e.target.value.trim();
            if (term.length < 3) { suggBox.classList.add('hidden'); return; }
            timeout = setTimeout(async () => {
                const results = await fetchSuggestionsCallback(term);
                suggBox.innerHTML = '';
                if (results && results.length > 0) {
                    results.forEach(item => {
                        const li = document.createElement('li');
                        li.className = "p-3 hover:bg-blue-50 cursor-pointer flex justify-between items-center transition-colors";
                        
                        // Exibe a miniatura na busca se existir
                        const thumb = item.photo ? `<img src="${item.photo}" class="w-8 h-8 object-cover rounded mr-3">` : `<div class="w-8 h-8 bg-gray-200 rounded mr-3"></div>`;
                        
                        li.innerHTML = `
                            <div class="flex items-center w-3/4">${thumb}<span class="font-bold text-sm text-gray-700 truncate">${item.description}</span></div>
                            <span class="text-[10px] bg-gray-100 text-gray-500 font-mono px-2 py-1 rounded w-1/4 text-center truncate">${item.sku}</span>
                        `;
                        li.addEventListener('click', () => {
                            input.value = item.sku;
                            suggBox.classList.add('hidden');
                            selectSuggestionCallback(item.sku);
                        });
                        suggBox.appendChild(li);
                    });
                    suggBox.classList.remove('hidden');
                } else {
                    suggBox.innerHTML = `<li class="p-3 text-xs text-gray-400 text-center">Nenhum produto encontrado</li>`;
                    suggBox.classList.remove('hidden');
                }
            }, 300);
        });
    }

    bindSearchEvent(callback) {
        if (!this.elements.searchBtn || !this.elements.searchInput) return;
        this.elements.searchBtn.addEventListener('click', () => {
            const sku = this.elements.searchInput.value.trim();
            if (sku) callback(sku);
            document.getElementById('search-suggestions').classList.add('hidden');
        });
        this.elements.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const sku = this.elements.searchInput.value.trim();
                if (sku) callback(sku);
                document.getElementById('search-suggestions').classList.add('hidden');
            }
        });
    }

    setInputValue(value) { if (this.elements.searchInput) this.elements.searchInput.value = value; }

    showLoader() {
        if (this.elements.errorContainer) this.elements.errorContainer.classList.add('hidden');
        if (this.elements.btnQuickReceive) this.elements.btnQuickReceive.classList.add('hidden');
        if (this.elements.dashboard) this.elements.dashboard.classList.add('hidden');
        if (this.elements.loader) this.elements.loader.classList.remove('hidden');
    }

    hideLoader() { if (this.elements.loader) this.elements.loader.classList.add('hidden'); }

    showError(message) {
        if (this.elements.errorContainer) {
            this.elements.errorToast.textContent = message;
            this.elements.errorContainer.classList.remove('hidden');
            if (message.includes("não possui") || message.includes("Ledger") || message.includes("encontrada")) {
                this.elements.btnQuickReceive.classList.remove('hidden');
            }
        }
    }

    showReceiveModal(sku) {
        document.getElementById('receive-sku').value = sku;
        document.getElementById('receive-desc').value = '';
        document.getElementById('receive-qty').value = '';
        document.getElementById('receive-batch').value = '';
        document.getElementById('receive-supplier').value = '';
        document.getElementById('receive-invoice').value = '';
        document.getElementById('receive-exp').value = '';
        
        // Limpa a foto anterior
        this.elements.photoPreview.src = '';
        this.elements.photoPreview.classList.add('hidden');
        this.elements.photoPlaceholder.classList.remove('hidden');
        this.elements.photoInput.dataset.base64 = '';
        
        if (this.elements.receiveModal) this.elements.receiveModal.classList.remove('hidden');
    }
    
    hideReceiveModal() { if (this.elements.receiveModal) this.elements.receiveModal.classList.add('hidden'); }
    
    getReceiveFormData() {
        return {
            sku: document.getElementById('receive-sku').value,
            description: document.getElementById('receive-desc').value,
            category: document.getElementById('receive-cat').value,
            quantity: parseInt(document.getElementById('receive-qty').value, 10),
            batch_code: document.getElementById('receive-batch').value || "LOTE-PADRAO",
            supplier: document.getElementById('receive-supplier').value || "Fornecedor Padrão",
            invoice_id: document.getElementById('receive-invoice').value || "S/N",
            expiration_date: document.getElementById('receive-exp').value || "2099-12-31",
            photo: this.elements.photoInput.dataset.base64 || null // Anexa a foto Base64 se tirada!
        };
    }

    showTransferModal(sku) {
        document.getElementById('transfer-sku').value = sku;
        document.getElementById('transfer-qty').value = '';
        if (this.elements.transferModal) this.elements.transferModal.classList.remove('hidden');
    }
    hideTransferModal() { if (this.elements.transferModal) this.elements.transferModal.classList.add('hidden'); }
    getTransferFormData() { return { sku: document.getElementById('transfer-sku').value, quantity: parseInt(document.getElementById('transfer-qty').value, 10), batch_code: document.getElementById('transfer-batch').value || "LOTE-PADRAO" }; }

    showAdjustmentModal(sku) {
        document.getElementById('adjustment-sku').value = sku;
        document.getElementById('adjustment-qty').value = '';
        document.getElementById('adjustment-reason').value = '';
        if (this.elements.adjustmentModal) this.elements.adjustmentModal.classList.remove('hidden');
    }
    hideAdjustmentModal() { if (this.elements.adjustmentModal) this.elements.adjustmentModal.classList.add('hidden'); }
    getAdjustmentFormData() { return { sku: document.getElementById('adjustment-sku').value, quantity: parseInt(document.getElementById('adjustment-qty').value, 10), divergence_type: document.getElementById('adjustment-type').value, reason: document.getElementById('adjustment-reason').value || "Auditoria Mobile" }; }

    renderDashboard(data) {
        // Exibe a Foto do Produto se ela tiver sido guardada no SQLite!
        if (data.photo && data.photo !== "None") {
            this.elements.dashboardPhotoImg.src = data.photo;
            this.elements.dashboardPhotoContainer.classList.remove('hidden');
        } else {
            this.elements.dashboardPhotoContainer.classList.add('hidden');
        }

        this._safeSetText('prodName', data.description);
        this._safeSetText('prodSku', data.sku);
        this._safeSetText('stockTotal', data.balances.total);
        this._safeSetText('stockDepot', data.balances.depot);
        this._safeSetText('stockStore', data.balances.store);
        this._safeSetText('locZone', data.physical_location.zone);
        this._safeSetText('locDetails', data.physical_location.details);
        this._safeSetText('repSugg', data.replenishment.suggested_quantity + " un");
        this._safeSetText('repMin', data.replenishment.min_stock_reference);
        this._safeSetText('repIdeal', data.replenishment.ideal_stock_reference);

        const repCard = document.getElementById('replenishCard');
        const repBadge = document.getElementById('repBadge');
        if (data.replenishment.needs_purchasing) {
            repCard.className = "bg-white p-5 rounded-xl shadow-sm border border-red-300 border-l-4 border-l-red-500";
            repBadge.className = "text-[10px] font-bold px-2 py-1 rounded bg-red-100 text-red-700";
            repBadge.textContent = "ALERTA RUPTURA";
        } else {
            repCard.className = "bg-white p-5 rounded-xl shadow-sm border border-green-300 border-l-4 border-l-green-500";
            repBadge.className = "text-[10px] font-bold px-2 py-1 rounded bg-green-100 text-green-700";
            repBadge.textContent = "STOCK SAUDÁVEL";
        }

        this._renderBatchMatrix(data.traceability, data.balances.depot);
        this._renderOperationalTruth(data.operational_metrics);
        this._renderHistoryTimeline(data.traceability, data.operational_metrics);

        if (this.elements.dashboard) this.elements.dashboard.classList.remove('hidden');
    }

    _safeSetText(elementId, text) { const el = document.getElementById(elementId); if (el) el.textContent = text ?? 'N/A'; }

    _renderBatchMatrix(trace, depotBalance) {
        if (!this.elements.batchBody) return;
        this.elements.batchBody.innerHTML = ''; 
        if (trace.active_batch && trace.active_batch !== "N/A") {
            const tr = document.createElement('tr');
            tr.className = "border-b border-gray-50 hover:bg-gray-50 font-mono";
            tr.innerHTML = `<td class="py-3 text-left pl-2 font-bold text-blue-900">${trace.active_batch}</td><td class="py-3 font-sans font-bold">${depotBalance} un</td><td class="py-3 text-gray-600">${this._formatDate(trace.first_expiration_date)}</td><td class="py-3 pr-2"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">FEFO ATIVO</span></td>`;
            this.elements.batchBody.appendChild(tr);
        } else {
            this.elements.batchBody.innerHTML = `<tr><td colspan="4" class="py-4 text-gray-400 text-xs">Nenhum lote ativo encontrado</td></tr>`;
        }
    }

    _renderOperationalTruth(metrics) {
        this._safeSetText('auditScore', metrics.trust_score + "%");
        this._safeSetText('auditAction', metrics.recommended_action);
        this._safeSetText('auditDivCount', metrics.divergence_count);
        this._safeSetText('auditLastDiv', metrics.last_divergence);
        const scoreEl = document.getElementById('auditScore');
        const riskBadge = document.getElementById('auditRiskBadge');
        if (metrics.trust_score >= 90) {
            scoreEl.className = "text-3xl font-black text-green-600";
            riskBadge.className = "text-[10px] font-bold px-2 py-0.5 rounded bg-green-100 text-green-800";
            riskBadge.textContent = `${metrics.risk_level} RISK`;
        } else {
            scoreEl.className = "text-3xl font-black text-amber-600";
            riskBadge.className = "text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800";
            riskBadge.textContent = `${metrics.risk_level} RISK`;
        }
    }

    _renderHistoryTimeline(trace, metrics) {
        if (!this.elements.historyTimeline) return;
        this.elements.historyTimeline.innerHTML = ''; 
        if (trace.last_receipt_date && trace.last_receipt_date !== "N/A") {
            this.elements.historyTimeline.appendChild(this._createTimelineRow(this._formatDate(trace.last_receipt_date), "RECEÇÃO", `Entrada via Fornecedor`, "bg-green-500"));
        }
        if (metrics.divergence_count > 0 && metrics.last_divergence !== "Nenhuma") {
            this.elements.historyTimeline.appendChild(this._createTimelineRow("AJUSTE", "DIVERGÊNCIA OPERACIONAL", `Evento: ${metrics.last_divergence}`, "bg-red-500"));
        }
    }

    _createTimelineRow(date, title, desc, dotColorClass) {
        const div = document.createElement('div');
        div.className = "relative mb-2";
        div.innerHTML = `<div class="absolute -left-[21px] mt-1.5 w-3 h-3 rounded-full ${dotColorClass} border-2 border-white shadow-sm"></div><p class="text-[10px] font-bold text-gray-400 font-mono uppercase">${date}</p><h4 class="text-xs font-black text-gray-800 uppercase mt-0.5">${title}</h4><p class="text-xs text-gray-500 mt-0.5">${desc}</p>`;
        return div;
    }

    _formatDate(dateStr) {
        if (!dateStr || dateStr === "N/A") return "N/A";
        if (dateStr.includes('-')) {
            const parts = dateStr.split('-');
            if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
        return dateStr;
    }
}

