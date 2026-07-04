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
            closeReceiveModal: document.getElementById('close-receive-modal')
        };

        if (this.elements.closeReceiveModal) {
            this.elements.closeReceiveModal.addEventListener('click', () => this.hideReceiveModal());
        }
    }

    bindSearchEvent(callback) {
        if (!this.elements.searchBtn || !this.elements.searchInput) return;
        this.elements.searchBtn.addEventListener('click', () => {
            const sku = this.elements.searchInput.value.trim();
            if (sku) callback(sku);
        });
        this.elements.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const sku = this.elements.searchInput.value.trim();
                if (sku) callback(sku);
            }
        });
    }

    setInputValue(value) {
        if (this.elements.searchInput) this.elements.searchInput.value = value;
    }

    showLoader() {
        if (this.elements.errorContainer) this.elements.errorContainer.classList.add('hidden');
        if (this.elements.btnQuickReceive) this.elements.btnQuickReceive.classList.add('hidden');
        if (this.elements.dashboard) this.elements.dashboard.classList.add('hidden');
        if (this.elements.loader) this.elements.loader.classList.remove('hidden');
    }

    hideLoader() {
        if (this.elements.loader) this.elements.loader.classList.add('hidden');
    }

    showError(message) {
        if (this.elements.errorContainer) {
            this.elements.errorToast.textContent = message;
            this.elements.errorContainer.classList.remove('hidden');
            if (message.includes("não possui histórico") || message.includes("Ledger") || message.includes("não encontrada")) {
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
        if (this.elements.receiveModal) this.elements.receiveModal.classList.remove('hidden');
    }

    hideReceiveModal() {
        if (this.elements.receiveModal) this.elements.receiveModal.classList.add('hidden');
    }

    getReceiveFormData() {
        return {
            sku: document.getElementById('receive-sku').value,
            description: document.getElementById('receive-desc').value,
            category: document.getElementById('receive-cat').value,
            quantity: parseInt(document.getElementById('receive-qty').value, 10),
            batch_code: document.getElementById('receive-batch').value || "LOTE-PADRAO",
            supplier: document.getElementById('receive-supplier').value || "Fornecedor Padrão",
            invoice_id: document.getElementById('receive-invoice').value || "NF-SIMULADA",
            expiration_date: document.getElementById('receive-exp').value || "2099-12-31" // Formato YYYY-MM-DD
        };
    }

    renderDashboard(data) {
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
            repBadge.textContent = "ESTOQUE SAUDÁVEL";
        }

        this._renderBatchMatrix(data.traceability, data.balances.depot);
        this._renderOperationalTruth(data.operational_metrics);
        this._renderHistoryTimeline(data.traceability, data.operational_metrics);

        if (this.elements.dashboard) this.elements.dashboard.classList.remove('hidden');
    }

    _safeSetText(elementId, text) {
        const el = document.getElementById(elementId);
        if (el) el.textContent = text ?? 'N/A';
    }

    _renderBatchMatrix(trace, depotBalance) {
        if (!this.elements.batchBody) return;
        this.elements.batchBody.innerHTML = ''; 
        if (trace.active_batch && trace.active_batch !== "N/A") {
            const tr = document.createElement('tr');
            tr.className = "border-b border-gray-50 hover:bg-gray-50 font-mono";
            tr.innerHTML = `
                <td class="py-3 text-left pl-2 font-bold text-blue-900">${trace.active_batch}</td>
                <td class="py-3 font-sans font-bold">${depotBalance} un</td>
                <td class="py-3 text-gray-600">${this._formatDate(trace.first_expiration_date)}</td>
                <td class="py-3 pr-2"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">FEFO ATIVO</span></td>
            `;
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
            this.elements.historyTimeline.appendChild(this._createTimelineRow(
                this._formatDate(trace.last_receipt_date),
                "RECEBIMENTO",
                `Entrada via fornecedor: ${trace.primary_supplier}`,
                "bg-green-500"
            ));
        }
        if (metrics.divergence_count > 0 && metrics.last_divergence !== "Nenhuma") {
            this.elements.historyTimeline.appendChild(this._createTimelineRow(
                "AJUSTE MANUAL",
                "DIVERGÊNCIA OPERACIONAL",
                `Evento registrado: ${metrics.last_divergence}`,
                "bg-red-500"
            ));
        }
    }

    _createTimelineRow(date, title, desc, dotColorClass) {
        const div = document.createElement('div');
        div.className = "relative mb-2";
        div.innerHTML = `
            <div class="absolute -left-[21px] mt-1.5 w-3 h-3 rounded-full ${dotColorClass} border-2 border-white shadow-sm"></div>
            <p class="text-[10px] font-bold text-gray-400 font-mono uppercase">${date}</p>
            <h4 class="text-xs font-black text-gray-800 uppercase mt-0.5">${title}</h4>
            <p class="text-xs text-gray-500 mt-0.5">${desc}</p>
        `;
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

