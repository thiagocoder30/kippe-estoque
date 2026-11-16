/**
 * Tela de Conferência de NF — captura de bipes + divergências
 * Estado em memória (localStorage pra sobreviver a refresh).
 */

const ConferenceFeature = (() => {
  const STORAGE_KEY = 'kippe_conference_state';

  let state = {
    supplier: '',
    invoice_number: '',
    items: [],
  };

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) state = JSON.parse(raw);
    } catch { /* ignora */ }
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function el(tag, attrs = {}, children = []) {
    const n = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'className') n.className = v;
      else if (k.startsWith('on')) n.addEventListener(k.slice(2).toLowerCase(), v);
      else n.setAttribute(k, v);
    });
    (Array.isArray(children) ? children : [children]).forEach(c => {
      if (c == null) return;
      n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return n;
  }

  async function fetchProduct(identifier) {
    const trySku = await fetch(`/api/sku/${encodeURIComponent(identifier)}`, { credentials: 'same-origin' });
    if (trySku.ok) return trySku.json();
    const tryQuery = await fetch(`/api/product/query?q=${encodeURIComponent(identifier)}`, { credentials: 'same-origin' });
    if (tryQuery.ok) {
      const data = await tryQuery.json();
      return Array.isArray(data) ? data[0] : data;
    }
    return null;
  }

  function itemStatus(item) {
    if (item.scanned === item.expected) return 'ok';
    if (item.scanned > item.expected) return 'div';
    return 'pending';
  }

  function renderItem(item, idx) {
    const st = itemStatus(item);
    const colors = {
      ok: 'border-l-green-500 bg-green-50',
      pending: 'border-l-yellow-500 bg-yellow-50',
      div: 'border-l-red-500 bg-red-50',
    };
    const label = { ok: '✓ OK', pending: '⏳ PENDENTE', div: '⚠ DIVERG.' };

    return el('div', { className: `border-l-4 ${colors[st]} p-3 rounded mb-2` }, [
      el('div', { className: 'flex justify-between items-start' }, [
        el('div', { className: 'flex-1' }, [
          el('div', { className: 'font-bold text-xs text-gray-800' }, item.name || item.sku),
          el('div', { className: 'text-[10px] text-gray-500 font-mono mt-0.5' }, `SKU: ${item.sku}`),
          el('div', { className: 'text-[10px] text-gray-500 mt-1' }, `Lote: ${item.batch_code || '-'} | Val: ${item.expiration_date || '-'}`)
        ]),
        el('div', { className: 'text-right ml-2' }, [
          el('div', { className: 'font-black text-sm' }, `${item.scanned} / ${item.expected}`),
          el('div', { className: 'text-[9px] font-bold uppercase' }, label[st]),
        ]),
      ]),
      el('div', { className: 'flex gap-1 mt-2' }, [
        el('button', { type: 'button', className: 'flex-1 bg-white border border-gray-300 text-gray-700 px-2 py-1 rounded text-[10px] font-bold', onclick: () => adjust(idx, -1) }, '− 1'),
        el('button', { type: 'button', className: 'flex-1 bg-white border border-gray-300 text-gray-700 px-2 py-1 rounded text-[10px] font-bold', onclick: () => adjust(idx, 1) }, '+ 1'),
        el('button', { type: 'button', className: 'bg-white border border-red-300 text-red-600 px-2 py-1 rounded text-[10px] font-bold', onclick: () => removeItem(idx) }, 'REMOVER'),
      ]),
    ]);
  }

  function render() {
    const supplierInput = document.getElementById('conference-supplier-input');
    if (supplierInput) supplierInput.value = state.supplier || '';
    const invoiceInput = document.getElementById('conference-invoice-input');
    if (invoiceInput) invoiceInput.value = state.invoice_number || '';

    const list = document.getElementById('conf-items-list');
    if (list) {
      list.innerHTML = '';
      if (state.items.length === 0) {
        list.innerHTML = '<p class="text-xs text-gray-400 text-center py-4">Nenhum item. Toque em "+ ITEM" ou bipe um código.</p>';
      } else {
        state.items.forEach((item, i) => list.appendChild(renderItem(item, i)));
      }
    }

    const counts = { ok: 0, pending: 0, div: 0 };
    state.items.forEach(it => counts[itemStatus(it)]++);
    
    const okEl = document.getElementById('conf-progress-ok');
    const pendEl = document.getElementById('conf-progress-pending');
    const divEl = document.getElementById('conf-progress-div');
    
    if (okEl) okEl.textContent = counts.ok;
    if (pendEl) pendEl.textContent = counts.pending;
    if (divEl) divEl.textContent = counts.div;

    const btn = document.getElementById('btn-conference-finalize');
    if (btn) btn.disabled = state.items.length === 0 || counts.div > 0 || counts.pending > 0;
  }

  function showDetailsModal(foundData, callback) {
    document.getElementById('conf-details-modal')?.remove();

    const today = new Date();
    const nextYear = new Date(today.setFullYear(today.getFullYear() + 1)).toISOString().slice(0, 10);

    const modal = el('div', {
      id: 'conf-details-modal',
      className: 'fixed inset-0 z-[200] bg-black/80 flex items-center justify-center p-4'
    }, [
      el('div', { className: 'bg-white rounded-xl shadow-xl w-full max-w-sm overflow-hidden' }, [
        el('div', { className: 'p-4 bg-[#124191] text-white' }, [
          el('h3', { className: 'font-black text-lg leading-tight' }, foundData.name || foundData.sku),
          el('p', { className: 'text-xs text-blue-200 mt-1' }, `SKU: ${foundData.sku}`)
        ]),
        el('div', { className: 'p-4 space-y-4' }, [
          el('div', {}, [
            el('label', { className: 'block text-[10px] font-black text-gray-500 mb-1 uppercase' }, 'Data de Validade *'),
            el('input', { type: 'date', id: 'conf-modal-exp', value: nextYear, className: 'w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 font-bold outline-none' })
          ]),
          el('div', {}, [
            el('label', { className: 'block text-[10px] font-black text-gray-500 mb-1 uppercase' }, 'Código do Lote (Opcional)'),
            el('input', { type: 'text', id: 'conf-modal-batch', placeholder: 'Ex: L123', className: 'w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 font-bold outline-none uppercase' })
          ])
        ]),
        el('div', { className: 'p-4 bg-gray-50 flex gap-2' }, [
          el('button', {
            type: 'button',
            className: 'flex-1 bg-white border border-gray-300 text-gray-700 font-bold py-2 rounded-lg active:scale-95',
            onclick: () => modal.remove()
          }, 'CANCELAR'),
          el('button', {
            type: 'button',
            className: 'flex-1 bg-[#124191] text-white font-bold py-2 rounded-lg active:scale-95',
            onclick: () => {
              const exp = document.getElementById('conf-modal-exp').value;
              const batch = document.getElementById('conf-modal-batch').value;
              if (!exp) { alert('A validade é obrigatória!'); return; }
              modal.remove();
              callback(exp, batch);
            }
          }, 'CONFIRMAR')
        ])
      ])
    ]);
    document.body.appendChild(modal);
  }

  async function scan(identifier) {
    if (!identifier) return;
    try {
      const found = await fetchProduct(identifier.trim());
      if (!found) {
        alert('❌ Produto não encontrado: ' + identifier);
        return;
      }
      const sku = found.id || found.sku || identifier;
      let item = state.items.find(i => i.sku === sku);
      
      if (item) {
        if (!item.expiration_date) {
          showDetailsModal({ sku, name: found.name, ean: found.ean }, (exp, batch) => {
            item.expiration_date = exp;
            item.batch_code = batch || `LOTE-${exp.replace(/-/g, '')}`;
            item.scanned++;
            save();
            render();
          });
        } else {
          item.scanned++;
          save();
          render();
        }
      } else {
        showDetailsModal({ sku, name: found.name, ean: found.ean }, (exp, batch) => {
          state.items.push({
            sku,
            ean: found.ean || '',
            name: found.name || sku,
            expected: 1,
            scanned: 1,
            expiration_date: exp,
            batch_code: batch || `LOTE-${exp.replace(/-/g, '')}`
          });
          save();
          render();
        });
      }
    } catch (err) {
      alert('❌ Erro ao buscar produto: ' + (err.message || err));
    }
  }

  function adjust(idx, delta) {
    state.items[idx].expected = Math.max(0, state.items[idx].expected + delta);
    if (state.items[idx].scanned > state.items[idx].expected) {
      state.items[idx].scanned = state.items[idx].expected;
    }
    save();
    render();
  }

  function removeItem(idx) {
    if (!confirm('Remover este item?')) return;
    state.items.splice(idx, 1);
    save();
    render();
  }

  function clearConference() {
    if (confirm('Tem certeza que deseja apagar todos os itens desta conferência?')) {
      state = { supplier: '', invoice_number: '', items: [] };
      save();
      render();
    }
  }

  async function addManual() {
    const identifier = prompt('Digite o SKU ou EAN:');
    if (!identifier) return;
    scan(identifier);
  }

  async function finalize() {
    if (!confirm('Finalizar conferência e dar entrada no estoque?')) return;

    const items = state.items
      .filter(it => it.scanned > 0)
      .map(it => ({
        sku: it.sku,
        quantity: it.scanned,
        batch_code: it.batch_code,
        expiration_date: it.expiration_date,
        manufacturing_date: '',
        supplier: state.supplier || 'PADRAO',
      }));

    if (items.length === 0) {
      alert('Nenhum item com quantidade > 0');
      return;
    }

    try {
      const res = await fetch('/api/conference/finalize', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items, supplier: state.supplier, invoice_number: state.invoice_number }),
      });
      const data = await res.json().catch(() => ({}));

      if (data.errors && data.errors.length > 0) {
        const errList = data.errors.map(e => `• ${e.sku || '?'}: ${e.error}`).join('\n');
        alert(`⚠️ ${data.success} itens OK, ${data.failed} falharam:\n\n${errList}`);
      } else if (res.ok) {
        alert(`✅ ${data.success} itens conferidos e estoque atualizado!`);
        state = { supplier: '', invoice_number: '', items: [] };
        save();
        render();
        document.getElementById('btn-back-conference')?.click();
      } else {
        throw new Error(data.error || `HTTP ${res.status}`);
      }
    } catch (e) {
      alert(`❌ Erro ao finalizar: ${e.message}`);
    }
  }

  function mount() {
    load();
    render();
  }

  function wire() {
    // Botão que abre a tela a partir do modal "Como Receber?"
    const openBtn = document.getElementById('btn-inbound-conference');
    if (openBtn && !openBtn.dataset.wired) {
      openBtn.dataset.wired = '1';
      openBtn.addEventListener('click', () => {
        document.getElementById('inbound-method-modal')?.classList.add('hidden');
        document.getElementById('home-module-view')?.classList.add('hidden');
        document.getElementById('conference-view')?.classList.remove('hidden');
        mount();
      });
    }

    // Botão voltar
    const backBtn = document.getElementById('btn-back-conference');
    if (backBtn && !backBtn.dataset.wired) {
      backBtn.dataset.wired = '1';
      backBtn.addEventListener('click', () => {
        document.getElementById('conference-view')?.classList.add('hidden');
        document.getElementById('home-module-view')?.classList.remove('hidden');
      });
    }

    // Campo de fornecedor
    const supplierInput = document.getElementById('conference-supplier-input');
    if (supplierInput && !supplierInput.dataset.wired) {
      supplierInput.dataset.wired = '1';
      supplierInput.addEventListener('input', (e) => {
        state.supplier = e.target.value.toUpperCase();
        save();
      });
    }

    // Campo de NF
    const invoiceInput = document.getElementById('conference-invoice-input');
    if (invoiceInput && !invoiceInput.dataset.wired) {
      invoiceInput.dataset.wired = '1';
      invoiceInput.addEventListener('input', (e) => {
        state.invoice_number = e.target.value;
        save();
      });
    }

    // Botão LIMPAR
    const clearBtn = document.getElementById('btn-conference-clear');
    if (clearBtn && !clearBtn.dataset.wired) {
      clearBtn.dataset.wired = '1';
      clearBtn.addEventListener('click', clearConference);
    }

    // Botão + ITEM
    const addBtn = document.getElementById('btn-conference-add');
    if (addBtn && !addBtn.dataset.wired) {
      addBtn.dataset.wired = '1';
      addBtn.addEventListener('click', addManual);
    }

    // Botão BIPAR
    const scanBtn = document.getElementById('conf-scan-btn');
    const scanInput = document.getElementById('conf-scan-input');
    if (scanBtn && !scanBtn.dataset.wired) {
      scanBtn.dataset.wired = '1';
      scanBtn.addEventListener('click', () => {
        if (scanInput) {
          scan(scanInput.value);
          scanInput.value = '';
          scanInput.focus();
        }
      });
    }

    // Enter no campo de scan
    if (scanInput && !scanInput.dataset.wired) {
      scanInput.dataset.wired = '1';
      scanInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          scan(e.target.value);
          e.target.value = '';
        }
      });
    }

    // Botão Finalizar
    const finalizeBtn = document.getElementById('btn-conference-finalize');
    if (finalizeBtn && !finalizeBtn.dataset.wired) {
      finalizeBtn.dataset.wired = '1';
      finalizeBtn.addEventListener('click', finalize);
    }
  }

  return { mount, wire };
})();

window.ConferenceFeature = ConferenceFeature;

// Garantir que o wire rode mesmo se o DOM já estiver carregado
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => window.ConferenceFeature.wire());
} else {
  // DOM já pronto
  setTimeout(() => window.ConferenceFeature.wire(), 0);
}
