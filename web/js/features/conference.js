/**
 * Tela de Conferência de NF — captura de bipes + divergências
 * Estado em memória (localStorage pra sobreviver a refresh).
 */

const ConferenceFeature = (() => {
  const STORAGE_KEY = 'kippe_conference_state';

  let state = {
    supplier: '',
    invoiceNumber: '',
    items: [], // { sku, ean, name, expected, scanned, batches: [{ code, expiration, qty }] }
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
    // Tenta SKU direto, depois busca
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

    return el('div', { className: `border-l-4 ${colors[st]} p-3 rounded` }, [
      el('div', { className: 'flex justify-between items-start' }, [
        el('div', { className: 'flex-1' }, [
          el('div', { className: 'font-bold text-xs text-gray-800' }, item.name || item.sku),
          el('div', { className: 'text-[10px] text-gray-500 font-mono mt-0.5' }, `${item.sku} · EAN ${item.ean || '-'}`),
        ]),
        el('div', { className: 'text-right ml-2' }, [
          el('div', { className: 'font-black text-sm' }, `${item.scanned} / ${item.expected}`),
          el('div', { className: 'text-[9px] font-bold uppercase' }, label[st]),
        ]),
      ]),
      el('div', { className: 'flex gap-1 mt-2' }, [
        el('button', {
          className: 'flex-1 bg-white border border-gray-300 text-gray-700 px-2 py-1 rounded text-[10px] font-bold',
          onclick: () => adjust(idx, -1),
        }, '− 1'),
        el('button', {
          className: 'flex-1 bg-white border border-gray-300 text-gray-700 px-2 py-1 rounded text-[10px] font-bold',
          onclick: () => adjust(idx, 1),
        }, '+ 1'),
        el('button', {
          className: 'bg-white border border-red-300 text-red-600 px-2 py-1 rounded text-[10px] font-bold',
          onclick: () => removeItem(idx),
        }, 'REMOVER'),
      ]),
    ]);
  }

  function render() {
    document.getElementById('conference-supplier').textContent =
      state.supplier || 'FORNECEDOR DESCONHECIDO';

    const list = document.getElementById('conf-items-list');
    list.innerHTML = '';

    if (state.items.length === 0) {
      list.innerHTML = '<p class="text-xs text-gray-400 text-center py-4">Nenhum item adicionado. Toque em "+ ITEM" ou bipe um código.</p>';
    } else {
      state.items.forEach((item, i) => list.appendChild(renderItem(item, i)));
    }

    const counts = { ok: 0, pending: 0, div: 0 };
    state.items.forEach(it => counts[itemStatus(it)]++);
    document.getElementById('conf-progress-ok').textContent = counts.ok;
    document.getElementById('conf-progress-pending').textContent = counts.pending;
    document.getElementById('conf-progress-div').textContent = counts.div;

    const btn = document.getElementById('btn-conference-finalize');
    btn.disabled = state.items.length === 0 || counts.div > 0 || counts.pending > 0;
  }

  async function scan(identifier) {
    if (!identifier) return;
    const found = await fetchProduct(identifier.trim());
    if (!found) {
      alert('❌ Produto não encontrado: ' + identifier);
      return;
    }
    const sku = found.id || found.sku || identifier;
    let item = state.items.find(i => i.sku === sku);
    if (item) {
      item.scanned++;
    } else {
      item = {
        sku,
        ean: found.ean || '',
        name: found.name || sku,
        expected: 1,
        scanned: 1,
        batches: [],
      };
      state.items.push(item);
    }
    save();
    render();
  }

  function adjust(idx, delta) {
    state.items[idx].expected = Math.max(0, state.items[idx].expected + delta);
    // Se expected < scanned, ajusta scanned também
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

  async function addManual() {
    const identifier = prompt('Digite o SKU ou EAN:');
    if (!identifier) return;
    const found = await fetchProduct(identifier);
    if (!found) { alert('❌ Produto não encontrado'); return; }
    const sku = found.id || found.sku;
    if (state.items.find(i => i.sku === sku)) { alert('Produto já na lista'); return; }
    state.items.push({
      sku,
      ean: found.ean || '',
      name: found.name || sku,
      expected: 1,
      scanned: 0,
      batches: [],
    });
    save();
    render();
  }

  async function finalize() {
    if (!confirm('Finalizar conferência e dar entrada no estoque?')) return;

    // Prepara items no formato esperado pelo backend
    const items = state.items
      .filter(it => it.scanned > 0)
      .map(it => ({
        sku: it.sku,
        quantity: it.scanned,
        batch_code: it.batch_code || `LOTE-${new Date().toISOString().slice(0,10).replace(/-/g,'')}`,
        expiration_date: it.expiration_date || new Date(Date.now() + 365*24*60*60*1000).toISOString().slice(0,10),
        manufacturing_date: it.manufacturing_date || '',
        supplier: it.supplier || 'PADRAO',
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
        state = { supplier: '', invoiceNumber: '', items: [] };
        save();
        render();
        document.getElementById('btn-back-conference').click();
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
    document.getElementById('btn-inbound-conference')?.addEventListener('click', () => {
      document.getElementById('inbound-method-modal')?.classList.add('hidden');
      document.getElementById('home-module-view')?.classList.add('hidden');
      document.getElementById('conference-view')?.classList.remove('hidden');
      mount();
    });
    document.getElementById('btn-back-conference')?.addEventListener('click', () => {
      document.getElementById('conference-view')?.classList.add('hidden');
      document.getElementById('home-module-view')?.classList.remove('hidden');
    });
    document.getElementById('btn-conference-add')?.addEventListener('click', addManual);
    document.getElementById('conf-scan-btn')?.addEventListener('click', () => {
      const input = document.getElementById('conf-scan-input');
      scan(input.value);
      input.value = '';
      input.focus();
    });
    document.getElementById('conf-scan-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        scan(e.target.value);
        e.target.value = '';
      }
    });
    document.getElementById('btn-conference-finalize')?.addEventListener('click', finalize);
  }

  return { mount, wire };
})();

window.ConferenceFeature = ConferenceFeature;
