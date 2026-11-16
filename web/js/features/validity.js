/**
 * Tela de Validade — Dashboard operacional (Tailwind puro)
 * Zero dependência externa (air-gapped).
 */

const ValidityFeature = (() => {
  const URGENCY = {
    expired:   { icon: '🔴', title: 'VENCIDOS',          hint: 'Ação imediata',
                 border: 'border-l-red-600', bg: 'bg-red-50' },
    critical:  { icon: '🟠', title: 'VENCE EM ≤7 DIAS',  hint: 'Priorizar venda',
                 border: 'border-l-orange-500', bg: 'bg-orange-50' },
    warning:   { icon: '🟡', title: 'VENCE EM 8-30 DIAS',hint: 'Monitorar',
                 border: 'border-l-yellow-500', bg: 'bg-yellow-50' },
    attention: { icon: '🟢', title: 'VENCE EM 31-90 DIAS',hint: 'Estoque normal',
                 border: 'border-l-green-500', bg: 'bg-green-50' },
    safe:      { icon: '⚪', title: 'ACIMA DE 90 DIAS',  hint: 'Sem urgência',
                 border: 'border-l-gray-300', bg: 'bg-gray-50' },
  };

  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'className') node.className = v;
      else if (k.startsWith('on')) node.addEventListener(k.slice(2).toLowerCase(), v);
      else node.setAttribute(k, v);
    });
    (Array.isArray(children) ? children : [children]).forEach(c => {
      if (c == null) return;
      node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return node;
  }

  async function fetchReport() {
    const res = await fetch('/api/relatorios/vencimentos', { credentials: 'same-origin' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function renderSummary(summary) {
    return el('div', { className: 'grid grid-cols-2 gap-2 mb-4' },
      ['expired', 'critical', 'warning', 'attention'].map(key => {
        const u = URGENCY[key];
        return el('div', { className: `p-2 rounded-lg ${u.bg} text-xs font-bold uppercase` }, [
          el('div', { className: 'text-lg' }, `${u.icon} ${summary[key] ?? 0}`),
          el('div', { className: 'text-gray-700 text-[10px]' }, u.title),
        ]);
      })
    );
  }

  function renderItem(item) {
    const u = URGENCY[item.urgency] || URGENCY.safe;
    const locIcon = item.location === 'store' ? '🏪' : '📦';
    const locLabel = item.location === 'store' ? 'LOJA' : 'ESTOQUE';
    const daysText = item.days_remaining < 0
      ? `venceu há ${Math.abs(item.days_remaining)}d`
      : `vence em ${item.days_remaining}d`;

    return el('div', { className: `border-l-4 ${u.border} bg-white p-3 rounded shadow-sm` }, [
      el('div', { className: 'flex justify-between items-start' }, [
        el('div', { className: 'font-bold text-sm text-gray-800' }, item.name),
        el('div', { className: 'text-xs font-bold text-red-700 whitespace-nowrap ml-2' }, daysText),
      ]),
      el('div', { className: 'text-[11px] text-gray-600 mt-1' },
        `Lote ${item.batch} · ${locIcon} ${locLabel} · Qtd ${item.quantity}` +
        (item.location_id ? ` · ${item.location_id}` : '')
      ),
      el('div', { className: 'flex gap-2 mt-2' }, [
        (item.urgency === 'expired' || item.urgency === 'critical')
          ? el('button', {
              className: 'bg-red-600 text-white px-3 py-1 rounded text-xs font-bold',
              onclick: () => markDiscard(item),
            }, 'DESCARTAR')
          : null,
        el('button', {
          className: 'bg-gray-200 text-gray-700 px-3 py-1 rounded text-xs font-bold',
          onclick: () => openDetail(item),
        }, 'DETALHES'),
      ].filter(Boolean)),
    ]);
  }

  async function markDiscard(item) {
    if (!confirm(`Descartar lote ${item.batch} de "${item.name}"? Será auditado.`)) return;
    try {
      const res = await fetch('/api/adjustment', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sku: item.sku,
          batch_code: item.batch,
          quantity: -Math.abs(item.quantity),
          reason: 'expired_discard',
          warehouse_id: item.warehouse_id,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      alert('✅ Descarte registrado');
      await reload();
    } catch (e) {
      alert(`❌ ${e.message}`);
    }
  }

  function openDetail(item) {
    alert(
      `Produto: ${item.name}\n` +
      `SKU: ${item.sku}\n` +
      `Lote: ${item.batch}\n` +
      `Validade: ${item.expiration}\n` +
      `Dias: ${item.days_remaining}\n` +
      `Local: ${item.location === 'store' ? 'LOJA' : 'ESTOQUE'}\n` +
      `Qtd: ${item.quantity}`
    );
  }

  function renderReport(data) {
    const root = el('div', { className: 'space-y-4' }, [renderSummary(data.summary || {})]);

    const groups = {};
    (data.items || []).forEach(item => {
      (groups[item.urgency] = groups[item.urgency] || []).push(item);
    });

    ['expired', 'critical', 'warning', 'attention', 'safe'].forEach(key => {
      const items = groups[key] || [];
      if (items.length === 0) return;
      const u = URGENCY[key];
      root.appendChild(el('div', { className: 'bg-white p-3 rounded-xl shadow-sm' }, [
        el('h2', { className: 'font-black text-sm text-gray-800 uppercase mb-1' },
          `${u.icon} ${u.title} (${items.length})`),
        el('p', { className: 'text-[10px] text-gray-500 uppercase mb-3' }, u.hint),
        el('div', { className: 'space-y-2' }, items.slice(0, 50).map(renderItem)),
        items.length > 50
          ? el('p', { className: 'text-center text-xs text-gray-500 mt-2' },
              `+ ${items.length - 50} itens nesta faixa`)
          : null,
      ].filter(Boolean)));
    });

    return root;
  }

  async function reload() {
    const root = document.getElementById('validity-root');
    if (!root) return;
    root.innerHTML = '<p class="text-xs text-gray-500 p-4">Carregando...</p>';
    try {
      const data = await fetchReport();
      root.innerHTML = '';
      root.appendChild(renderReport(data));
    } catch (e) {
      root.innerHTML = `<p class="text-red-600 text-xs p-4">Erro: ${e.message}</p>`;
    }
  }

  function mount() {
    const root = document.getElementById('validity-root');
    if (!root) {
      console.warn('[Validity] #validity-root não encontrado');
      return;
    }
    reload();
  }

  return { mount, reload };
})();

window.ValidityFeature = ValidityFeature;
