/**
 * Tela de Conferência de NF — captura de bipes + divergências
 * Estado em memória (localStorage pra sobreviver a refresh).
 */

const ConferenceFeature = (() => {
  const STORAGE_KEY = 'kippe_conference_state';
  const LEARNED_MAP_KEY = 'kippe_ocr_ean_map';

  let state = {
    supplier: '',
    invoice_number: '',
    invoices: [],
    items: [],
  };

  function extractPackFromText(txt) {
    const m = String(txt || '').toUpperCase().match(/\b(\d{1,3})\s*[Xx]\s*\d+(?:[.,]\d+)?\s*(?:G|GR|KG|ML|L|UN|M)\b/);
    return m ? Math.max(1, parseInt(m[1], 10)) : 1;
  }

  function resolveEffectivePackFactor(aiFactor, savedFactor, rawText) {
    const parsedAi = Math.max(1, parseInt(aiFactor, 10) || 1);
    const parsedText = extractPackFromText(rawText);
    const explicitNfFactor = parsedAi > 1 ? parsedAi : parsedText;
    const parsedSaved = Math.max(1, parseInt(savedFactor, 10) || 1);
    if (explicitNfFactor > 1) return explicitNfFactor;
    if (parsedSaved > 1) return parsedSaved;
    return 1;
  }

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        state = JSON.parse(raw);
        if (!Array.isArray(state.invoices)) {
          state.invoices = state.invoice_number ? [String(state.invoice_number).trim()] : [];
        }
        if (Array.isArray(state.items)) {
          state.items = state.items.map(it => {
            const factor = resolveEffectivePackFactor(it.pack_factor, 1, it.raw_ocr_name || it.name);
            const nfQty = Math.max(0, parseInt(it.nf_qty ?? it.expected, 10) || 0);
            return {
              ...it,
              nf_qty: nfQty,
              pack_factor: factor,
              expected: nfQty * factor,
            };
          });
        }
      }
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

  function isConferenceOnlyRole() {
    if (typeof window.kippeCanManageCatalog === 'function') {
      return !window.kippeCanManageCatalog();
    }
    return false;
  }

  function normalizeDesc(str) {
    return (str || '')
      .toUpperCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^A-Z0-9\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function loadLearnedMap() {
    try {
      const m = JSON.parse(localStorage.getItem(LEARNED_MAP_KEY) || '{}');
      if (m['MILHO CONSERVA LATA STELLA DORO']) {
        delete m['MILHO CONSERVA LATA STELLA DORO'];
        localStorage.setItem(LEARNED_MAP_KEY, JSON.stringify(m));
      }
      return m;
    } catch { return {}; }
  }
  function _unused_loadLearnedMap() {
    try {
      return JSON.parse(localStorage.getItem(LEARNED_MAP_KEY) || '{}');
    } catch {
      return {};
    }
  }

  function saveLearnedLink(ocrDescription, productInfo, packFactor = 1, explicitFactor = false) {
    const key = normalizeDesc(ocrDescription);
    if (!key || !productInfo || !productInfo.sku) return;
    const map = loadLearnedMap();
    const existing = map[key] || {};
    const incoming = Math.max(1, parseInt(packFactor, 10) || 1);
    const prev = Math.max(1, parseInt(existing.pack_factor, 10) || 1);
    const finalFactor = explicitFactor ? incoming : (incoming > 1 ? incoming : prev);

    map[key] = {
      sku: productInfo.sku,
      ean: productInfo.ean || existing.ean || '',
      name: productInfo.name || existing.name || ocrDescription,
      pack_factor: finalFactor,
      updatedAt: Date.now()
    };
    localStorage.setItem(LEARNED_MAP_KEY, JSON.stringify(map));
    fetch('/api/catalog/aliases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        alias: ocrDescription,
        supplier: state.supplier || '',
        sku: productInfo.sku,
        ean: productInfo.ean || '',
        name: productInfo.name || ocrDescription,
        pack_factor: finalFactor,
        explicit_factor: explicitFactor
      })
    }).catch(() => {});
  }

  function isUnlinkedItem(item) {
    return !item.sku || String(item.sku).startsWith('TEMP-');
  }

  function renderItem(item, idx) {
    const factor = Math.max(1, parseInt(item.pack_factor, 10) || 1);
    const nfQty = Math.max(0, parseInt(item.nf_qty ?? item.expected, 10) || 0);
    item.pack_factor = factor;
    item.nf_qty = nfQty;
    item.expected = nfQty * factor;

    const st = itemStatus(item);
    const unlinked = isUnlinkedItem(item);

    const cardBorder = {
      ok: 'border-green-200 border-l-green-600 bg-green-50',
      pending: 'border-gray-200 border-l-yellow-500 bg-white',
      div: 'border-red-200 border-l-red-600 bg-red-50',
    };
    const badgeStyle = {
      ok: 'bg-green-100 text-green-800 border-green-300',
      pending: 'bg-yellow-50 text-yellow-800 border-yellow-300',
      div: 'bg-red-100 text-red-800 border-red-300',
    };
    const badgeLabel = {
      ok: '✓ OK',
      pending: '⏳ PENDENTE',
      div: '⚠ DIVERG.',
    };

    const linkIcon = el('span', { className: 'inline-flex items-center mr-1.5' });
    linkIcon.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>';

    const boxIcon = el('span', { className: 'inline-flex items-center mr-1.5' });
    boxIcon.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>';

    const trashBtn = el('button', {
      type: 'button',
      title: 'Remover item',
      ariaLabel: 'Remover item',
      className: 'bg-red-50 border border-red-200 text-red-600 px-3 py-2 rounded-lg text-xs font-bold uppercase active:scale-95 flex items-center justify-center',
      onclick: () => removeItem(idx)
    });
    trashBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';

    const updateConversion = (newNfQty, newFactor) => {
      item.nf_qty = Math.max(0, parseInt(newNfQty, 10) || 0);
      item.pack_factor = Math.max(1, parseInt(newFactor, 10) || 1);
      item.expected = item.nf_qty * item.pack_factor;
      if (item.raw_ocr_name && !isUnlinkedItem(item)) {
        saveLearnedLink(item.raw_ocr_name, { sku: item.sku, ean: item.ean, name: item.catalog_name || item.name }, item.pack_factor, true);
      }
      save();
      render();
    };

    return el('div', {
      className: `border border-l-4 ${cardBorder[st]} rounded-xl p-3 mb-2.5 shadow-sm`
    }, [
      // FAIXA 1: Nome do produto + Status
      el('div', { className: 'flex items-start justify-between gap-2' }, [
        el('div', { className: 'font-black text-xs text-gray-800 uppercase leading-snug break-words flex-1' }, item.name || item.sku),
        el('span', {
          className: `shrink-0 px-2 py-0.5 rounded-full border text-[9px] font-black uppercase ${badgeStyle[st]}`
        }, badgeLabel[st]),
      ]),

      // Etiqueta de item pesável (KG -> Caixas/Volumes)
      ...((String(item.unit || '').toUpperCase() === 'KG' || Number(item.weight_kg) > 0) ? [
        el('div', { className: 'mt-1.5' }, [
          el('span', {
            className: 'inline-block px-2 py-0.5 rounded bg-purple-50 border border-purple-300 text-purple-900 text-[9px] font-black uppercase'
          }, `⚖️ PESÁVEL (KG) · NF: ${Number(item.weight_kg || 0).toLocaleString('pt-BR')} KG (${item.nf_qty} CX/VOL)`)
        ])
      ] : []),

      // Subtítulo SKU / EAN
      unlinked
        ? el('div', { className: 'mt-1.5 flex flex-wrap gap-1' }, [
            item.pending_registration
              ? el('span', {
                  className: 'inline-block px-2 py-0.5 rounded bg-amber-100 border border-amber-400 text-amber-900 text-[9px] font-black uppercase'
                }, '🚩 CADASTRO SOLICITADO AO ESTOQUISTA')
              : el('span', {
                  className: 'inline-block px-2 py-0.5 rounded bg-yellow-50 border border-yellow-300 text-yellow-800 text-[9px] font-black uppercase'
                }, '⚠ SEM EAN · BIPE O PRODUTO OU VINCULE')
          ])
        : el('div', { className: 'text-[10px] text-gray-500 font-mono font-bold mt-1 truncate' },
            `SKU: ${item.sku}${item.ean && item.ean !== item.sku ? ` · EAN: ${item.ean}` : ''}`
          ),

      // FAIXA 2: Bloco Unificado 2x2 (Conversão NF x Fator + Conferido + Lote + Validade)
      el('div', { className: 'bg-gray-50 border border-gray-200 rounded-xl p-2.5 mt-2.5 space-y-2' }, [
        // Linha 1: Esperado (Qtd NF x Un/Cx = Total UN) + Conferido (UN)
        el('div', { className: 'grid grid-cols-2 gap-2' }, [
          el('div', { className: 'bg-white border border-gray-200 rounded-lg p-2 flex flex-col justify-between' }, [
            el('div', { className: 'flex items-center justify-between gap-1' }, [
              el('span', { className: 'text-[8px] font-black text-gray-500 uppercase' }, 'QTD NF'),
              el('span', { className: 'text-[8px] font-black text-[#124191] uppercase' }, 'UN / CX')
            ]),
            el('div', { className: 'flex items-center gap-1 mt-1' }, [
              el('input', {
                type: 'number',
                value: item.nf_qty,
                min: '0',
                ariaLabel: 'Quantidade na NF',
                className: 'w-full h-8 text-center font-black text-xs rounded-lg border border-gray-300 bg-gray-50 text-gray-800 outline-none focus:bg-white focus:border-blue-300',
                onchange: (e) => updateConversion(e.target.value, item.pack_factor)
              }),
              el('span', { className: 'text-[10px] font-black text-gray-400' }, '×'),
              el('input', {
                type: 'number',
                value: item.pack_factor,
                min: '1',
                ariaLabel: 'Unidades por caixa',
                className: 'w-full h-8 text-center font-black text-xs rounded-lg border border-blue-200 bg-blue-50 text-[#124191] outline-none focus:bg-white focus:border-blue-400',
                onchange: (e) => updateConversion(item.nf_qty, e.target.value)
              })
            ]),
            el('div', { className: 'mt-1.5 pt-1 border-t border-gray-100 text-center text-[9px] font-black text-gray-700 uppercase' },
              `ESPERADO: ${item.expected} UN`
            )
          ]),

          el('div', {
            className: `border rounded-lg p-2 flex flex-col justify-between ${
              item.scanned === item.expected && item.expected > 0
                ? 'bg-green-50 border-green-300'
                : 'bg-red-50 border-red-200'
            }`
          }, [
            el('label', { className: 'text-[9px] font-black text-gray-500 uppercase text-center' }, 'CONFERIDO (UN)'),
            el('input', {
              type: 'number',
              value: item.scanned,
              min: '0',
              className: `w-full mt-1 h-8 text-center font-black text-sm rounded-lg border bg-white outline-none ${
                item.scanned === item.expected && item.expected > 0
                  ? 'border-green-300 text-green-800'
                  : 'border-red-300 text-red-800'
              }`,
              onchange: (e) => {
                item.scanned = parseInt(e.target.value, 10) || 0;
                save();
                render();
              }
            }),
            el('button', {
              type: 'button',
              className: 'mt-1.5 w-full py-1 rounded bg-white border border-gray-300 text-[9px] font-black text-gray-700 uppercase active:scale-95',
              onclick: () => {
                item.scanned = item.expected;
                save();
                render();
              }
            }, `✓ BATER ${item.expected} UN`)
          ])
        ]),

        // Linha 2: Lote + Validade (apenas para Estoquista / Gerente / Admin)
        ...(isConferenceOnlyRole() ? [] : [
          el('div', { className: 'grid grid-cols-2 gap-2 pt-2 border-t border-gray-200' }, [
            el('div', { className: 'bg-white border border-gray-200 rounded-lg p-2' }, [
              el('label', { className: 'block text-[9px] font-black text-gray-500 uppercase mb-1' }, 'LOTE'),
              el('input', {
                type: 'text',
                value: item.batch_code || '',
                placeholder: 'EX: L123',
                className: 'w-full h-8 bg-gray-50 border border-gray-200 rounded-lg px-2 py-1 text-xs font-bold uppercase text-gray-800 outline-none focus:bg-white focus:border-blue-300',
                onchange: (e) => {
                  item.batch_code = e.target.value.trim().toUpperCase();
                  save();
                }
              })
            ]),
            el('div', { className: 'bg-white border border-gray-200 rounded-lg p-2' }, [
              el('label', { className: 'block text-[9px] font-black text-gray-500 uppercase mb-1' }, 'VALIDADE'),
              el('input', {
                type: 'date',
                value: item.expiration_date || '',
                className: 'w-full h-8 bg-gray-50 border border-gray-200 rounded-lg px-1.5 py-1 text-xs font-bold text-gray-800 outline-none focus:bg-white focus:border-blue-300',
                onchange: (e) => {
                  item.expiration_date = e.target.value;
                  save();
                }
              })
            ])
          ])
        ])
      ]),

      // FAIXA 3: Ação Principal + Trocar SKU + Remover
      el('div', { className: 'flex items-center gap-1.5 mt-2.5' }, unlinked ? [
        el('button', {
          type: 'button',
          className: 'flex-1 bg-[#124191] text-white py-2 px-3 rounded-lg text-[10px] font-black uppercase tracking-wider shadow-sm active:scale-95 flex items-center justify-center',
          onclick: () => promptManualLinkForItem(idx)
        }, [linkIcon, 'VINCULAR EAN / PRODUTO']),
        trashBtn
      ] : [
        el('button', {
          type: 'button',
          className: 'flex-1 bg-blue-50 border border-blue-200 text-[#124191] py-2 px-2.5 rounded-lg text-[10px] font-black uppercase tracking-wider active:scale-95 flex items-center justify-center',
          onclick: () => {
            showDetailsModal(
              { sku: item.sku, name: item.name, ean: item.ean },
              (exp, batch, qty, unitsPerBox) => {
                item.expiration_date = exp;
                item.batch_code = batch;
                item.scanned = qty;
                if (unitsPerBox && unitsPerBox > 1) {
                  item.pack_factor = unitsPerBox;
                  item.expected = (item.nf_qty || 1) * unitsPerBox;
                  if (item.raw_ocr_name) {
                    saveLearnedLink(item.raw_ocr_name, { sku: item.sku, ean: item.ean, name: item.catalog_name || item.name }, unitsPerBox, true);
                  }
                }
                save();
                render();
              },
              {
                qty: item.scanned > 0 ? item.scanned : (item.expected || 1),
                exp: item.expiration_date,
                batch: item.batch_code,
                unitsPerBox: item.pack_factor,
                boxCount: item.nf_qty || 1
              }
            );
          }
        }, [boxIcon, 'CAIXA / LOTE']),
        el('button', {
          type: 'button',
          title: 'Trocar produto vinculado',
          className: 'bg-yellow-50 border border-yellow-300 text-yellow-800 py-2 px-2.5 rounded-lg text-[10px] font-black uppercase tracking-wider active:scale-95 flex items-center justify-center',
          onclick: () => promptManualLinkForItem(idx)
        }, '🔄 TROCAR SKU'),
        trashBtn
      ]),
    ]);
  }

  function render() {
    const finBtn = document.getElementById('btn-conference-finalize');
    if (finBtn) {
      finBtn.textContent = isConferenceOnlyRole()
        ? '✅ CONCLUIR E ENVIAR P/ ESTOQUISTA'
        : 'FINALIZAR CONFERÊNCIA';
    }
    const supplierInput = document.getElementById('conference-supplier-input');
    if (supplierInput) supplierInput.value = state.supplier || '';
    const invoiceInput = document.getElementById('conference-invoice-input');
    if (invoiceInput) invoiceInput.value = state.invoice_number || '';
    if (typeof renderAttachedInvoicesBanner === 'function') renderAttachedInvoicesBanner();

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

  function showDetailsModal(foundData, callback, defaults = {}) {
    document.getElementById('conf-details-modal')?.remove();

    const today = new Date();
    const nextYear = new Date(today.setFullYear(today.getFullYear() + 1)).toISOString().slice(0, 10);
    const initialUnitsBox = Math.max(1, parseInt(defaults.unitsPerBox, 10) || 1);
    const initialBoxCount = Math.max(1, parseInt(defaults.boxCount, 10) || 1);
    const initialQty = defaults.qty != null && defaults.qty > 0 ? String(defaults.qty) : String(initialUnitsBox * initialBoxCount);
    const initialExp = defaults.exp || nextYear;
    const initialBatch = defaults.batch || '';

    let currentMode = initialUnitsBox > 1 ? 'box' : 'unit';

    const modal = el('div', {
      id: 'conf-details-modal',
      className: 'fixed inset-0 z-[200] bg-black/80 flex items-center justify-center p-4'
    }, [
      el('div', { className: 'bg-white rounded-xl shadow-xl w-full max-w-sm overflow-hidden flex flex-col max-h-[90vh]' }, [
        el('div', { className: 'p-4 bg-[#124191] text-white flex-shrink-0' }, [
          el('h3', { className: 'font-black text-sm leading-tight uppercase' }, foundData.name || foundData.sku),
          el('p', { className: 'text-[10px] text-blue-200 mt-1 uppercase font-mono' }, `SKU: ${foundData.sku}${foundData.ean ? ` · EAN: ${foundData.ean}` : ''}`)
        ]),
        el('div', { className: 'p-4 space-y-4 overflow-y-auto' }, [

          el('div', { className: 'border border-gray-200 rounded-lg p-3' }, [
            el('label', { className: 'block text-[10px] font-black text-gray-500 mb-2 uppercase' }, 'Modo de Entrada'),
            el('div', { className: 'flex gap-2 mb-3' }, [
              el('button', {
                type: 'button', id: 'btn-mode-unit',
                className: currentMode === 'unit'
                  ? 'flex-1 py-1.5 rounded font-bold text-xs bg-[#124191] text-white shadow-sm'
                  : 'flex-1 py-1.5 rounded font-bold text-xs bg-gray-100 text-gray-600',
                onclick: () => switchMode('unit')
              }, 'UNIDADES'),
              el('button', {
                type: 'button', id: 'btn-mode-box',
                className: currentMode === 'box'
                  ? 'flex-1 py-1.5 rounded font-bold text-xs bg-[#124191] text-white shadow-sm'
                  : 'flex-1 py-1.5 rounded font-bold text-xs bg-gray-100 text-gray-600',
                onclick: () => switchMode('box')
              }, 'FARDO / CAIXA')
            ]),

            el('div', { id: 'container-mode-unit', className: currentMode === 'unit' ? '' : 'hidden' }, [
              el('label', { className: 'block text-[10px] font-black text-gray-500 mb-1 uppercase' }, 'Quantidade Conferida (Unidades) *'),
              el('input', { type: 'number', id: 'conf-modal-qty', value: initialQty, min: '1', className: 'w-full bg-blue-50 border border-blue-300 text-blue-800 rounded-lg px-3 py-2 font-black text-xl outline-none text-center' })
            ]),

            el('div', { id: 'container-mode-box', className: currentMode === 'box' ? '' : 'hidden' }, [
              el('div', { className: 'grid grid-cols-2 gap-2' }, [
                el('div', {}, [
                  el('label', { className: 'block text-[10px] font-black text-gray-500 mb-1 uppercase' }, 'Un / Caixa'),
                  el('input', { type: 'number', id: 'conf-modal-units-box', value: String(initialUnitsBox > 1 ? initialUnitsBox : 12), min: '1', className: 'w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 font-bold outline-none text-center' })
                ]),
                el('div', {}, [
                  el('label', { className: 'block text-[10px] font-black text-gray-500 mb-1 uppercase' }, 'Qtd Caixas'),
                  el('input', { type: 'number', id: 'conf-modal-box-count', value: String(initialBoxCount), min: '1', className: 'w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 font-bold outline-none text-center' })
                ])
              ]),
              el('div', { className: 'mt-2 bg-green-50 text-green-700 p-2 rounded text-center font-bold text-sm border border-green-200' }, [
                'Total: ', el('span', { id: 'conf-modal-calc-total' }, String((initialUnitsBox > 1 ? initialUnitsBox : 12) * initialBoxCount)), ' UN'
              ])
            ])
          ]),

          el('div', {}, [
            el('label', { className: 'block text-[10px] font-black text-gray-500 mb-1 uppercase' }, 'Data de Validade *'),
            el('input', { type: 'date', id: 'conf-modal-exp', value: initialExp, className: 'w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 font-bold outline-none' })
          ]),
          el('div', {}, [
            el('label', { className: 'block text-[10px] font-black text-gray-500 mb-1 uppercase' }, 'Código do Lote *'),
            el('input', { type: 'text', id: 'conf-modal-batch', value: initialBatch, placeholder: 'Ex: L123', className: 'w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 font-bold outline-none uppercase' })
          ])
        ]),
        el('div', { className: 'p-4 bg-gray-50 flex gap-2 flex-shrink-0' }, [
          el('button', {
            type: 'button',
            className: 'flex-1 bg-white border border-gray-300 text-gray-700 font-bold py-2 rounded-lg active:scale-95',
            onclick: () => modal.remove()
          }, 'CANCELAR'),
          el('button', {
            type: 'button',
            className: 'flex-1 bg-green-600 text-white font-bold py-2 rounded-lg active:scale-95',
            onclick: () => {
              const exp = document.getElementById('conf-modal-exp').value;
              const batch = document.getElementById('conf-modal-batch').value.trim().toUpperCase();
              if (!exp) { alert('A validade é obrigatória!'); return; }
              if (!batch) { alert('O código do lote é obrigatório!'); return; }

              let finalQty = 1;
              let detectedFactor = 1;
              if (currentMode === 'unit') {
                finalQty = parseInt(document.getElementById('conf-modal-qty').value, 10);
              } else {
                const units = parseInt(document.getElementById('conf-modal-units-box').value, 10) || 0;
                const boxes = parseInt(document.getElementById('conf-modal-box-count').value, 10) || 0;
                finalQty = units * boxes;
                detectedFactor = units > 1 ? units : 1;
              }

              if (!finalQty || finalQty <= 0) { alert('A quantidade calculada deve ser maior que zero!'); return; }

              modal.remove();
              callback(exp, batch, finalQty, detectedFactor);
            }
          }, 'CONFIRMAR')
        ])
      ])
    ]);

    document.body.appendChild(modal);

    function switchMode(mode) {
      currentMode = mode;
      const btnUnit = document.getElementById('btn-mode-unit');
      const btnBox = document.getElementById('btn-mode-box');
      const contUnit = document.getElementById('container-mode-unit');
      const contBox = document.getElementById('container-mode-box');

      if (mode === 'unit') {
        btnUnit.className = 'flex-1 py-1.5 rounded font-bold text-xs bg-[#124191] text-white shadow-sm';
        btnBox.className = 'flex-1 py-1.5 rounded font-bold text-xs bg-gray-100 text-gray-600';
        contUnit.classList.remove('hidden');
        contBox.classList.add('hidden');
      } else {
        btnBox.className = 'flex-1 py-1.5 rounded font-bold text-xs bg-[#124191] text-white shadow-sm';
        btnUnit.className = 'flex-1 py-1.5 rounded font-bold text-xs bg-gray-100 text-gray-600';
        contBox.classList.remove('hidden');
        contUnit.classList.add('hidden');
        updateTotal();
      }
    }

    function updateTotal() {
      const u = parseInt(document.getElementById('conf-modal-units-box').value, 10) || 0;
      const c = parseInt(document.getElementById('conf-modal-box-count').value, 10) || 0;
      document.getElementById('conf-modal-calc-total').textContent = u * c;
    }

    document.getElementById('conf-modal-units-box')?.addEventListener('input', updateTotal);
    document.getElementById('conf-modal-box-count')?.addEventListener('input', updateTotal);

    setTimeout(() => document.getElementById(currentMode === 'box' ? 'conf-modal-units-box' : 'conf-modal-qty')?.focus(), 100);
  }

  function showLinkOcrModal(productInfo, unlinkedEntries, onSelectIndex, onAddAsExtra) {
    document.getElementById('conf-link-ocr-modal')?.remove();

    const modal = el('div', {
      id: 'conf-link-ocr-modal',
      className: 'fixed inset-0 z-[210] bg-black/80 flex items-center justify-center p-4'
    }, [
      el('div', { className: 'bg-white rounded-xl shadow-xl w-full max-w-sm overflow-hidden flex flex-col max-h-[85vh]' }, [
        el('div', { className: 'p-4 bg-[#124191] text-white' }, [
          el('div', { className: 'text-[9px] font-black uppercase tracking-widest text-blue-200' }, 'Vincular Produto Bipado à NF'),
          el('h3', { className: 'font-black text-sm mt-0.5 leading-snug' }, productInfo.name || productInfo.sku),
          el('p', { className: 'text-[10px] font-mono text-blue-100 mt-1' }, `SKU: ${productInfo.sku}${productInfo.ean ? ` · EAN: ${productInfo.ean}` : ''}`)
        ]),
        el('div', { className: 'p-3 bg-blue-50 border-b border-blue-100 text-[10px] font-bold text-blue-900' },
          'Toque no item da Nota Fiscal correspondente (esse vínculo ficará salvo para as próximas notas):'
        ),
        el('div', { className: 'p-3 space-y-2 overflow-y-auto flex-1' }, [
          ...unlinkedEntries.map(({ item, index }) =>
            el('button', {
              type: 'button',
              className: 'w-full text-left p-3 rounded-lg border border-gray-200 hover:border-blue-500 bg-gray-50 active:scale-[0.99] transition flex items-center justify-between gap-2',
              onclick: () => {
                modal.remove();
                onSelectIndex(index);
              }
            }, [
              el('div', { className: 'min-w-0 flex-1' }, [
                el('div', { className: 'font-black text-xs text-gray-800 leading-tight' }, item.name),
                el('div', { className: 'text-[9px] font-bold text-gray-500 uppercase mt-1' }, `Esperado na NF: ${item.expected} UN`)
              ]),
              el('span', { className: 'bg-[#124191] text-white text-[9px] font-black px-2 py-1 rounded uppercase shrink-0' }, 'Vincular')
            ])
          ),
          el('button', {
            type: 'button',
            className: 'w-full text-center p-2.5 rounded-lg border border-dashed border-gray-300 text-gray-600 font-bold text-[10px] uppercase mt-2',
            onclick: () => {
              modal.remove();
              onAddAsExtra();
            }
          }, '➕ Não está na lista (Adicionar como item extra)')
        ]),
        el('div', { className: 'p-3 bg-gray-50 border-t border-gray-200' }, [
          el('button', {
            type: 'button',
            className: 'w-full bg-white border border-gray-300 text-gray-700 font-bold py-2 rounded-lg text-xs uppercase',
            onclick: () => modal.remove()
          }, 'Cancelar')
        ])
      ])
    ]);

    document.body.appendChild(modal);
  }

  function promptManualLinkForItem(itemIndex) {
    const target = state.items[itemIndex];
    if (!target) return;

    document.getElementById('conf-manual-link-modal')?.remove();

    let searchTimer = null;

    const closeModal = () => {
      clearTimeout(searchTimer);
      document.getElementById('conf-manual-link-modal')?.remove();
    };

    const submitCode = (rawCode) => {
      const clean = (rawCode || '').trim();
      if (!clean) {
        alert('Digite ou bipe um código EAN / SKU.');
        return;
      }
      closeModal();
      scan(clean, itemIndex);
    };

    const openNewProductForItem = () => {
      const typed = (inputEl.value || '').trim();
      const isBarcode = /^\d{8,}$/.test(typed);
      closeModal();
      const qcModal = document.getElementById('quick-create-modal');
      if (!qcModal) {
        alert('Use o botão "+ NOVO PRODUTO" na tela inicial para cadastrar.');
        return;
      }
      qcModal.classList.remove('hidden');
      const eanField = document.getElementById('qc-ean');
      const intField = document.getElementById('qc-internal-code');
      const nameField = document.getElementById('qc-name');
      if (eanField) eanField.value = isBarcode ? typed : '';
      if (intField) intField.value = '';
      if (nameField) nameField.value = target.name || '';
      setTimeout(() => (isBarcode ? nameField : eanField)?.focus(), 100);

      document.getElementById('qc-save').onclick = async () => {
        const newName = (document.getElementById('qc-name')?.value || '').trim();
        if (!newName) { alert('O nome do produto é obrigatório.'); return; }
        const eanVal = (document.getElementById('qc-ean')?.value || '').trim();
        const internalVal = (document.getElementById('qc-internal-code')?.value || '').trim();
        const finalCode = eanVal || internalVal || 'SKU-' + Date.now().toString().slice(-6);

        const res = await fetch('/api/produto', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: finalCode,
            name: newName,
            ean: eanVal,
            category: document.getElementById('qc-category')?.value || 'GERAL',
            unit: document.getElementById('qc-unit')?.value || 'UN'
          })
        });
        if (!res.ok) { alert('Erro ao cadastrar produto.'); return; }
        qcModal.classList.add('hidden');
        bindProductToOcrIndex(itemIndex, { sku: finalCode, name: newName, ean: eanVal });
      };
    };

    const resultsBox = el('div', {
      id: 'conf-link-suggestions',
      className: 'space-y-1.5 max-h-52 overflow-y-auto'
    });

    const inputEl = el('input', {
      type: 'text',
      id: 'conf-manual-link-input',
      placeholder: 'EX: 7896089... OU NOME DO PRODUTO',
      autocomplete: 'off',
      className: 'w-full bg-gray-50 border border-gray-300 focus:border-blue-300 focus:bg-white rounded-lg px-3 py-2.5 text-xs font-bold uppercase text-gray-800 outline-none'
    });

    const runLiveSearch = async (q) => {
      const term = q.trim();
      if (term.length < 2) {
        resultsBox.innerHTML = '<div class="text-[10px] font-bold text-gray-400 text-center py-3 uppercase">DIGITE O EAN OU NOME PARA BUSCAR NO CATÁLOGO...</div>';
        return;
      }

      resultsBox.innerHTML = '<div class="text-[10px] font-bold text-gray-400 text-center py-3 uppercase">BUSCANDO NO CATÁLOGO...</div>';

      try {
        const res = await fetch(`/api/catalog/search?q=${encodeURIComponent(term)}`, { credentials: 'same-origin' });
        if (!res.ok) throw new Error('Falha na busca');
        const list = await res.json();

        resultsBox.innerHTML = '';
        if (!Array.isArray(list) || list.length === 0) {
          resultsBox.appendChild(
            el('div', { className: 'text-[10px] font-bold text-gray-500 text-center py-2.5 bg-gray-50 rounded-lg border border-dashed border-gray-300 px-2 uppercase' },
              'NENHUM PRODUTO ENCONTRADO NO CATÁLOGO.'
            )
          );
          return;
        }

        list.slice(0, 8).forEach((prod) => {
          const pSku = prod.sku || prod.id;
          const pEan = prod.ean || '';
          const pName = prod.name || pSku;

          resultsBox.appendChild(
            el('button', {
              type: 'button',
              className: 'w-full text-left p-2.5 rounded-lg border border-gray-200 bg-white active:scale-95 flex items-center justify-between gap-2',
              onclick: () => {
                closeModal();
                bindProductToOcrIndex(itemIndex, { sku: pSku, name: pName, ean: pEan, pack_factor: prod.pack_factor || 1 });
              }
            }, [
              el('div', { className: 'min-w-0 flex-1' }, [
                el('div', { className: 'font-black text-xs text-gray-800 uppercase leading-snug' }, pName),
                el('div', { className: 'text-[10px] font-mono font-bold text-gray-500 mt-0.5' },
                  `SKU: ${pSku}${pEan && pEan !== pSku ? ` · EAN: ${pEan}` : ''}`
                )
              ]),
              el('span', {
                className: 'shrink-0 bg-blue-50 text-[#124191] border border-blue-200 text-[9px] font-black px-2 py-1 rounded uppercase'
              }, 'VINCULAR')
            ])
          );
        });
      } catch {
        resultsBox.innerHTML = '<div class="text-[10px] font-bold text-red-500 text-center py-2 uppercase">ERRO AO CONSULTAR CATÁLOGO.</div>';
      }
    };

    inputEl.addEventListener('input', (e) => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => runLiveSearch(e.target.value), 200);
    });

    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        submitCode(inputEl.value);
      }
    });

    const modal = el('div', {
      id: 'conf-manual-link-modal',
      className: 'fixed inset-0 z-[210] bg-black/80 flex items-center justify-center p-4',
      onclick: (e) => { if (e.target === modal) closeModal(); }
    }, [
      el('div', { className: 'bg-white rounded-xl shadow-xl w-full max-w-sm overflow-hidden flex flex-col max-h-[88vh]' }, [
        el('div', { className: 'p-4 bg-[#124191] text-white flex items-start justify-between gap-2' }, [
          el('div', { className: 'min-w-0 flex-1' }, [
            el('div', { className: 'text-[9px] font-black uppercase tracking-wider text-blue-200' }, 'VINCULAR EAN / PRODUTO'),
            el('h3', { className: 'font-black text-sm mt-0.5 uppercase leading-tight break-words' }, target.raw_ocr_name || target.name),
            el('div', { className: 'text-[10px] font-bold text-blue-200 mt-1 uppercase' }, `QUANTIDADE NA NF: ${target.expected} UN`)
          ]),
          el('button', {
            type: 'button',
            ariaLabel: 'Fechar',
            className: 'text-blue-200 hover:text-white text-base font-black leading-none px-1',
            onclick: closeModal
          }, '✕')
        ]),

        el('div', { className: 'p-4 space-y-3 overflow-y-auto' }, [
          el('div', {}, [
            el('label', { className: 'block text-[10px] font-black text-gray-500 uppercase mb-1' },
              'BIPE O CÓDIGO DE BARRAS OU DIGITE EAN / NOME'
            ),
            inputEl
          ]),
          resultsBox,
          isConferenceOnlyRole()
            ? el('button', {
                type: 'button',
                className: 'w-full py-2.5 px-3 rounded-lg border-2 border-amber-400 bg-amber-50 text-amber-900 font-black text-[10px] uppercase active:scale-95',
                onclick: async () => {
                  const typedEan = (inputEl.value || '').replace(/\D/g, '');
                  const res = await fetch('/api/receiving/requests/product', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                      raw_description: target.raw_ocr_name || target.name,
                      suggested_ean: typedEan,
                      supplier: state.supplier || '',
                      invoice_number: state.invoice_number || '',
                      nf_qty: target.nf_qty || 1,
                      pack_factor: target.pack_factor || 1,
                      batch_code: target.batch_code || '',
                      expiration_date: target.expiration_date || ''
                    })
                  });
                  const out = await res.json();
                  if (!res.ok) {
                    await window.kippeModalAlert('❌ ' + (out.error || 'Erro ao solicitar cadastro.'), 'ERRO NA SOLICITAÇÃO');
                    return;
                  }
                  target.pending_registration = true;
                  save();
                  closeModal();
                  render();
                  await window.kippeModalAlert('🚩 Solicitação enviada! O Estoquista receberá este item para cadastrar e você já pode concluir a conferência.', 'SOLICITAÇÃO ENVIADA');
                }
              }, '🚩 SOLICITAR CADASTRO AO ESTOQUISTA')
            : el('button', {
                type: 'button',
                className: 'w-full py-2 px-3 rounded-lg border border-dashed border-gray-300 bg-gray-50 text-gray-700 font-black text-[10px] uppercase active:scale-95',
                onclick: openNewProductForItem
              }, '+ CADASTRAR PRODUTO NOVO (NÃO EXISTE NO SISTEMA)')
        ]),

        el('div', { className: 'p-4 bg-gray-50 border-t border-gray-200 flex gap-2' }, [
          el('button', {
            type: 'button',
            className: 'flex-1 bg-white border border-gray-300 text-gray-700 font-bold py-2 rounded-lg text-xs uppercase active:scale-95',
            onclick: closeModal
          }, 'CANCELAR'),
          el('button', {
            type: 'button',
            className: 'flex-1 bg-[#124191] text-white font-black py-2 rounded-lg text-xs uppercase tracking-wider shadow-sm active:scale-95',
            onclick: () => submitCode(inputEl.value)
          }, 'BUSCAR / BIPAR')
        ])
      ])
    ]);

    document.body.appendChild(modal);
    setTimeout(() => {
      inputEl.focus();
      const words = normalizeDesc(target.raw_ocr_name || target.name).split(' ').filter(w => w.length >= 3).slice(0, 3);
      if (words.length > 0) runLiveSearch(words.join(' '));
    }, 80);
  }

  function bindProductToOcrIndex(ocrIndex, productInfo) {
    const target = state.items[ocrIndex];
    if (!target) return;
    const originalOcrName = target.raw_ocr_name || target.name;
    const savedFactor = Math.max(1, parseInt(productInfo.pack_factor, 10) || 1);
    const currentFactor = Math.max(1, parseInt(target.pack_factor, 10) || 1);
    const factor = currentFactor > 1 ? currentFactor : savedFactor;
    const nfQty = Math.max(1, parseInt(target.nf_qty ?? target.expected, 10) || 1);

    saveLearnedLink(originalOcrName, productInfo, factor);

    target.raw_ocr_name = originalOcrName;
    target.catalog_name = productInfo.name || originalOcrName;
    target.sku = productInfo.sku;
    target.ean = productInfo.ean || productInfo.sku;
    target.nf_qty = nfQty;
    target.pack_factor = factor;
    target.expected = nfQty * factor;
    if (productInfo.name) {
      target.name = `${productInfo.name} (NF: ${originalOcrName})`;
    }
    save();
    render();

    showDetailsModal(
      { sku: target.sku, name: target.name, ean: target.ean },
      (exp, batch, qty, unitsPerBox) => {
        target.expiration_date = exp;
        target.batch_code = batch;
        target.scanned = qty;
        if (unitsPerBox && unitsPerBox > 1) {
          target.pack_factor = unitsPerBox;
          target.expected = target.nf_qty * unitsPerBox;
          saveLearnedLink(originalOcrName, productInfo, unitsPerBox, true);
        }
        save();
        render();
        document.getElementById('conf-scan-input')?.focus();
      },
      {
        qty: target.expected || 1,
        exp: target.expiration_date,
        batch: target.batch_code,
        unitsPerBox: factor,
        boxCount: nfQty
      }
    );
  }

  async function scan(identifier, forcedOcrIndex = null) {
    if (!identifier) return;
    try {
      const found = await fetchProduct(identifier.trim());

      if (!found) {
        const qcModal = document.getElementById('quick-create-modal');
        if (!qcModal) {
          alert('❌ Produto não encontrado: ' + identifier);
          return;
        }
        qcModal.classList.remove('hidden');

        const isNumeric = /^\d+$/.test(identifier.trim());
        const isLikelyEan = isNumeric && identifier.trim().length >= 8;

        document.getElementById('qc-ean').value = isLikelyEan ? identifier.trim() : '';
        document.getElementById('qc-internal-code').value = !isLikelyEan ? identifier.trim() : '';
        document.getElementById('qc-name').value = forcedOcrIndex != null && state.items[forcedOcrIndex]
          ? state.items[forcedOcrIndex].name
          : '';

        setTimeout(() => document.getElementById('qc-name').focus(), 100);

        document.getElementById('qc-save').onclick = async () => {
          const newName = document.getElementById('qc-name').value.trim();
          if (!newName) { alert('O nome do produto é obrigatório.'); return; }

          const eanVal = document.getElementById('qc-ean').value.trim();
          const internalVal = document.getElementById('qc-internal-code').value.trim();
          const finalCode = eanVal || internalVal || 'SKU-' + Date.now().toString().slice(-6);

          const res = await fetch('/api/produto', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              id: finalCode,
              name: newName,
              ean: eanVal,
              category: document.getElementById('qc-category')?.value || 'GERAL',
              unit: document.getElementById('qc-unit')?.value || 'UN'
            })
          });

          if (!res.ok) { alert('Erro ao cadastrar'); return; }

          document.getElementById('quick-create-modal').classList.add('hidden');
          scan(finalCode, forcedOcrIndex);
        };
        return;
      }

      const sku = found.id || found.sku || identifier;
      const productInfo = { sku, name: found.name || sku, ean: found.ean || '' };

      // 1. Se veio de clique direto em "Vincular EAN" de um item específico
      if (forcedOcrIndex != null && state.items[forcedOcrIndex]) {
        bindProductToOcrIndex(forcedOcrIndex, productInfo);
        return;
      }

      // 2. Se o SKU já está vinculado na lista atual
      const existingItem = state.items.find(i => !isUnlinkedItem(i) && i.sku === sku);
      if (existingItem) {
        if (!existingItem.batch_code || !existingItem.expiration_date) {
          showDetailsModal(
            productInfo,
            (exp, batch, qty) => {
              existingItem.expiration_date = exp;
              existingItem.batch_code = batch;
              existingItem.scanned = qty;
              save();
              render();
            },
            { qty: existingItem.expected || 1 }
          );
        } else {
          existingItem.scanned++;
          save();
          render();
        }
        return;
      }

      // 3. Se existem itens importados da NF ainda sem vínculo, oferece vínculo em 1 toque
      const unlinkedEntries = state.items
        .map((item, index) => ({ item, index }))
        .filter(({ item }) => isUnlinkedItem(item));

      const addAsNormalItem = () => {
        showDetailsModal(productInfo, (exp, batch, qty) => {
          state.items.push({
            sku: sku,
            ean: found.ean || '',
            name: found.name || sku,
            expected: qty,
            scanned: qty,
            expiration_date: exp,
            batch_code: batch
          });
          save();
          render();
          document.getElementById('conf-scan-input')?.focus();
        });
      };

      if (unlinkedEntries.length > 0) {
        showLinkOcrModal(
          productInfo,
          unlinkedEntries,
          (chosenIndex) => bindProductToOcrIndex(chosenIndex, productInfo),
          addAsNormalItem
        );
        return;
      }

      addAsNormalItem();
    } catch (err) {
      alert('❌ Erro ao buscar produto: ' + (err.message || err));
    }
  }

  function removeItem(idx) {
    const target = state.items[idx];
    if (!target) return;

    document.getElementById('conf-remove-modal')?.remove();

    const closeModal = () => document.getElementById('conf-remove-modal')?.remove();

    const confirmBtn = el('button', {
      type: 'button',
      className: 'flex-1 bg-red-600 text-white font-black py-2 rounded-lg text-xs uppercase tracking-wider shadow-sm active:scale-95 flex items-center justify-center gap-1.5',
      onclick: () => {
        closeModal();
        state.items.splice(idx, 1);
        save();
        render();
      }
    });
    confirmBtn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg><span>REMOVER</span>';

    const modal = el('div', {
      id: 'conf-remove-modal',
      className: 'fixed inset-0 z-[210] bg-black/80 flex items-center justify-center p-4',
      onclick: (e) => { if (e.target === modal) closeModal(); }
    }, [
      el('div', { className: 'bg-white rounded-xl shadow-xl w-full max-w-sm overflow-hidden flex flex-col' }, [
        el('div', { className: 'p-4 bg-[#124191] text-white flex items-start justify-between gap-2' }, [
          el('div', {}, [
            el('div', { className: 'text-[9px] font-black uppercase tracking-wider text-blue-200' }, 'CONFIRMAR EXCLUSÃO'),
            el('h3', { className: 'font-black text-sm mt-0.5 uppercase leading-tight' }, 'REMOVER ESTE ITEM?')
          ]),
          el('button', {
            type: 'button',
            ariaLabel: 'Fechar',
            className: 'text-blue-200 hover:text-white text-base font-black leading-none px-1',
            onclick: closeModal
          }, '✕')
        ]),

        el('div', { className: 'p-4 space-y-2.5' }, [
          el('div', { className: 'bg-red-50 border border-red-200 rounded-lg p-3' }, [
            el('div', { className: 'font-black text-xs text-gray-800 uppercase leading-snug break-words' }, target.name || target.sku),
            el('div', { className: 'text-[10px] font-bold text-gray-500 uppercase mt-1' },
              `ESPERADO: ${target.expected} UN · CONFERIDO: ${target.scanned} UN`
            )
          ]),
          el('p', { className: 'text-[11px] font-bold text-gray-500 leading-snug' },
            'O item será retirado apenas desta conferência atual.'
          )
        ]),

        el('div', { className: 'p-4 bg-gray-50 border-t border-gray-200 flex gap-2' }, [
          el('button', {
            type: 'button',
            className: 'flex-1 bg-white border border-gray-300 text-gray-700 font-bold py-2 rounded-lg text-xs uppercase active:scale-95',
            onclick: closeModal
          }, 'CANCELAR'),
          confirmBtn
        ])
      ])
    ]);

    document.body.appendChild(modal);
  }

  function clearConference() {
    document.getElementById('conf-clear-modal')?.remove();
    const closeModal = () => document.getElementById('conf-clear-modal')?.remove();

    const modal = el('div', {
      id: 'conf-clear-modal',
      className: 'fixed inset-0 z-[210] bg-black/80 flex items-center justify-center p-4',
      onclick: (e) => { if (e.target === modal) closeModal(); }
    }, [
      el('div', { className: 'bg-white rounded-xl shadow-xl w-full max-w-sm overflow-hidden flex flex-col' }, [
        el('div', { className: 'p-4 bg-[#124191] text-white flex items-start justify-between gap-2' }, [
          el('div', {}, [
            el('div', { className: 'text-[9px] font-black uppercase tracking-wider text-blue-200' }, 'LIMPAR CONFERÊNCIA'),
            el('h3', { className: 'font-black text-sm mt-0.5 uppercase leading-tight' }, 'APAGAR TODOS OS ITENS?')
          ]),
          el('button', {
            type: 'button',
            ariaLabel: 'Fechar',
            className: 'text-blue-200 hover:text-white text-base font-black leading-none px-1',
            onclick: closeModal
          }, '✕')
        ]),
        el('div', { className: 'p-4' }, [
          el('p', { className: 'text-xs font-bold text-gray-600 leading-snug' },
            'Isso vai zerar o fornecedor, o número da NF e todos os itens bipados ou importados nesta tela.'
          )
        ]),
        el('div', { className: 'p-4 bg-gray-50 border-t border-gray-200 flex gap-2' }, [
          el('button', {
            type: 'button',
            className: 'flex-1 bg-white border border-gray-300 text-gray-700 font-bold py-2 rounded-lg text-xs uppercase active:scale-95',
            onclick: closeModal
          }, 'CANCELAR'),
          el('button', {
            type: 'button',
            className: 'flex-1 bg-red-600 text-white font-black py-2 rounded-lg text-xs uppercase tracking-wider shadow-sm active:scale-95',
            onclick: () => {
              closeModal();
              state = { supplier: '', invoice_number: '', items: [] };
              save();
              render();
            }
          }, 'LIMPAR TUDO')
        ])
      ])
    ]);

    document.body.appendChild(modal);
  }

  async function finalize(forceDuplicate = false, precomputedDivergences = null) {
    const isConfRole = isConferenceOnlyRole();
    const unlinkedItems = state.items.filter(it => it.scanned > 0 && isUnlinkedItem(it));
    const hasUnlinked = unlinkedItems.length > 0;
    const routeToQueue = isConfRole || hasUnlinked;

    const missingExp = routeToQueue ? [] : state.items.filter(it => it.scanned > 0 && !it.expiration_date);
    if (missingExp.length > 0) {
      await window.kippeModalAlert(
        `⚠️ Informe a DATA DE VALIDADE para:

${missingExp[0].name}`,
        'VALIDADE OBRIGATÓRIA'
      );
      return;
    }

    const items = state.items
      .filter(it => it.scanned > 0)
      .map(it => ({
        sku: it.sku,
        name: it.name || it.raw_ocr_name || it.sku,
        quantity: it.scanned,
        batch_code: it.batch_code,
        expiration_date: it.expiration_date,
        manufacturing_date: '',
        supplier: state.supplier || 'PADRAO',
        nf_allocations: Array.isArray(it.nf_allocations) ? it.nf_allocations : [],
      }));

    if (items.length === 0) {
      await window.kippeModalAlert('⚠️ Nenhum item com quantidade conferida maior que zero.', 'CONFERÊNCIA VAZIA');
      return;
    }

    let divergences = precomputedDivergences;
    if (!divergences) {
      const divergentItems = state.items.filter(it => (it.expected || 0) > 0 && (it.scanned || 0) !== (it.expected || 0));
      if (divergentItems.length > 0) {
        divergences = await promptDivergenceFormalization(divergentItems);
        if (!divergences) return;
      } else {
        const confirmTitle = routeToQueue ? 'ENVIAR AO ESTOQUISTA' : 'FINALIZAR CONFERÊNCIA';
        const confirmMsg = routeToQueue
          ? `Concluir a conferência de ${items.length} item(ns)${hasUnlinked ? ` (${unlinkedItems.length} sem vínculo)` : ''} e enviar para a fila do Estoquista?`
          : 'Finalizar conferência e dar entrada no estoque?';
        const confirmBtn = routeToQueue ? 'ENVIAR AGORA' : 'FINALIZAR';
        if (!(await window.kippeModalConfirm(confirmMsg, confirmTitle, confirmBtn))) return;
        divergences = [];
      }
    }

    const pendingToQueue = unlinkedItems.filter(u => !u.pending_registration);
    const batchReqPromise = pendingToQueue.length > 0
      ? fetch('/api/receiving/requests/product/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({
            items: pendingToQueue.map(uItem => ({
              raw_description: uItem.raw_ocr_name || uItem.name,
              suggested_ean: '',
              supplier: state.supplier || '',
              invoice_number: state.invoice_number || '',
              nf_qty: uItem.nf_qty || 1,
              pack_factor: uItem.pack_factor || 1,
              batch_code: uItem.batch_code || '',
              expiration_date: uItem.expiration_date || ''
            }))
          })
        }).then(r => {
          if (r.ok) {
            pendingToQueue.forEach(u => { u.pending_registration = true; });
            save();
          }
        }).catch(() => {})
      : Promise.resolve();

    const invoicesPayload = Array.isArray(state.invoices) && state.invoices.length > 0
      ? state.invoices
      : (state.invoice_number ? [state.invoice_number] : []);

    try {
      const [res] = await Promise.all([
        fetch('/api/conference/finalize', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items,
          supplier: state.supplier,
          invoice_number: state.invoice_number,
          invoices: invoicesPayload,
          divergences,
          force: forceDuplicate,
        }),
      }),
        batchReqPromise,
      ]);
      const data = await res.json().catch(() => ({}));

      if (res.status === 409 && data.duplicate) {
        if (await window.kippeModalConfirm(
          `⚠️ ${data.error}

Deseja autorizar o envio duplicado mesmo assim?`,
          'DUPLICIDADE DE NF-e',
          'AUTORIZAR ENVIO'
        )) {
          return finalize(true, divergences);
        }
        return;
      }

      if (data.errors && data.errors.length > 0) {
        const errList = data.errors.map(e => `• ${e.sku || '?'}: ${e.error}`).join('\n');
        await window.kippeModalAlert(`⚠️ ${data.success} itens OK, ${data.failed} falharam:

${errList}`, 'RESULTADO PARCIAL');
      } else if (res.ok) {
        const divNote = data.divergences_recorded > 0 ? `
(${data.divergences_recorded} divergência(s) formalizada(s))` : '';
        if (data.queued) {
          const reqNote = unlinkedItems.length > 0
            ? `

${unlinkedItems.length} item(ns) sem cadastro foram encaminhados automaticamente ao Estoquista.`
            : '';
          await window.kippeModalAlert(
            `✅ Conferência concluída e enviada para a fila do Estoquista!${reqNote}${divNote}`,
            'CONFERÊNCIA ENVIADA'
          );
        } else {
          await window.kippeModalAlert(
            `✅ ${data.success} itens conferidos e estoque atualizado!${divNote}`,
            'ESTOQUE ATUALIZADO'
          );
        }
        state = { supplier: '', invoice_number: '', invoices: [], items: [] };
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
        document.querySelectorAll('main > section[id$="-view"]').forEach(el => el.classList.add('hidden'));
        document.getElementById('conference-view')?.classList.remove('hidden');
        window.scrollTo(0, 0);
        mount();
      });
    }

    // Botão VOLTAR
    const backBtn = document.getElementById('btn-back-conference');
    if (backBtn && !backBtn.dataset.wired) {
      backBtn.dataset.wired = '1';
      backBtn.addEventListener('click', () => {
        if (typeof window.showHome === 'function') {
          window.showHome();
        } else {
          document.querySelectorAll('main > section[id$="-view"]').forEach(el => el.classList.add('hidden'));
          document.getElementById('home-module-view')?.classList.remove('hidden');
          window.scrollTo(0, 0);
        }
      });
    }

    // Botão LIMPAR
    const clearBtn = document.getElementById('btn-conference-clear');
    if (clearBtn && !clearBtn.dataset.wired) {
      clearBtn.dataset.wired = '1';
      clearBtn.addEventListener('click', clearConference);
    }

    // Lógica do Botão de IA
    const ICON_CAMERA = `
        <span class="kippe-ocr-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/>
                <circle cx="12" cy="13" r="3"/>
            </svg>
        </span>
        <span class="kippe-ocr-text">
            <span class="kippe-ocr-title">Foto da NF</span>
            <span class="kippe-ocr-sub">Câmera OCR</span>
        </span>`;

    const ICON_PDF = `
        <span class="kippe-ocr-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
        </span>
        <span class="kippe-ocr-text">
            <span class="kippe-ocr-title">Importar PDF</span>
            <span class="kippe-ocr-sub">DANFE / Scan</span>
        </span>`;

    const ICON_SPINNER = `
        <span class="kippe-ocr-icon">
            <svg class="kippe-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <circle cx="12" cy="12" r="9" stroke-opacity="0.25"/>
                <path d="M12 3a9 9 0 0 1 9 9" stroke-linecap="round"/>
            </svg>
        </span>
        <span class="kippe-ocr-text">
            <span class="kippe-ocr-title">Lendo Nota...</span>
            <span class="kippe-ocr-sub">Aguarde</span>
        </span>`;

    const ocrProgress = (() => {
        let timer = null;
        let hideTimer = null;
        let startTime = 0;
        let currentPct = 0;

        const els = () => ({
            box: document.getElementById('kippe-ocr-progress'),
            stage: document.getElementById('kippe-ocr-stage-text'),
            meta: document.getElementById('kippe-ocr-meta-text'),
            fill: document.getElementById('kippe-ocr-fill'),
        });

        const renderMeta = () => {
            const { meta } = els();
            if (!meta) return;
            const secs = ((performance.now() - startTime) / 1000).toFixed(1);
            meta.textContent = `${currentPct}% · ${secs}s`;
        };

        return {
            start(initialStage = 'Preparando arquivo...') {
                clearInterval(timer);
                clearTimeout(hideTimer);
                startTime = performance.now();
                currentPct = 5;
                const { box, stage, fill } = els();
                if (!box) return;
                box.className = 'kippe-ocr-progress is-active';
                if (stage) stage.textContent = initialStage;
                if (fill) fill.style.width = '5%';
                renderMeta();
                timer = setInterval(renderMeta, 200);
            },
            update(pct, stageText) {
                currentPct = Math.max(currentPct, Math.min(99, pct));
                const { stage, fill } = els();
                if (stage && stageText) stage.textContent = stageText;
                if (fill) fill.style.width = `${currentPct}%`;
                renderMeta();
            },
            succeed(finalText) {
                clearInterval(timer);
                currentPct = 100;
                const { box, stage, fill } = els();
                if (!box) return;
                box.className = 'kippe-ocr-progress is-active is-success';
                if (stage) stage.textContent = finalText;
                if (fill) fill.style.width = '100%';
                renderMeta();
                hideTimer = setTimeout(() => {
                    box.className = 'kippe-ocr-progress';
                }, 3500);
            },
            fail(errText) {
                clearInterval(timer);
                const { box, stage, fill } = els();
                if (!box) return;
                box.className = 'kippe-ocr-progress is-active is-error';
                if (stage) stage.textContent = errText;
                if (fill) fill.style.width = '100%';
                renderMeta();
                hideTimer = setTimeout(() => {
                    box.className = 'kippe-ocr-progress';
                }, 5000);
            }
        };
    })();

    const setOcrLoading = (loading, source = 'pdf') => {
        const btnCam = document.getElementById('btn-ai-camera');
        const btnFile = document.getElementById('btn-ai-file');
        if (btnCam) {
            btnCam.disabled = loading;
            btnCam.innerHTML = (loading && source === 'camera') ? ICON_SPINNER : ICON_CAMERA;
        }
        if (btnFile) {
            btnFile.disabled = loading;
            btnFile.innerHTML = (loading && source === 'pdf') ? ICON_SPINNER : ICON_PDF;
        }
    };

    const mergeOrPushConsolidatedItem = (newItem, incomingInv) => {
        const allocEntry = incomingInv
            ? [{ invoice_number: incomingInv, nf_qty: newItem.nf_qty, expected_units: newItem.expected }]
            : [];
        newItem.nf_allocations = allocEntry;

        const existingIdx = state.items.findIndex(existing => {
            if (!isUnlinkedItem(existing) && !isUnlinkedItem(newItem) && existing.sku === newItem.sku) {
                return true;
            }
            return normalizeDesc(existing.raw_ocr_name || existing.name) === normalizeDesc(newItem.raw_ocr_name || newItem.name);
        });

        if (existingIdx >= 0) {
            const target = state.items[existingIdx];
            target.nf_qty = (target.nf_qty || 0) + (newItem.nf_qty || 0);
            target.expected = (target.expected || 0) + (newItem.expected || 0);
            if (newItem.weight_kg) {
                target.weight_kg = Number(((target.weight_kg || 0) + Number(newItem.weight_kg || 0)).toFixed(3));
                target.unit = 'KG';
            }
            if (!Array.isArray(target.nf_allocations)) {
                target.nf_allocations = [];
            }
            if (incomingInv) {
                const prevAlloc = target.nf_allocations.find(a => a.invoice_number === incomingInv);
                if (prevAlloc) {
                    prevAlloc.nf_qty += newItem.nf_qty;
                    prevAlloc.expected_units += newItem.expected;
                } else {
                    target.nf_allocations.push({
                        invoice_number: incomingInv,
                        nf_qty: newItem.nf_qty,
                        expected_units: newItem.expected,
                    });
                }
            }
        } else {
            state.items.push(newItem);
        }
    };

    const appendExtractedItems = async (data) => {
        const incomingSupplier = String(data.supplier || '').trim().toUpperCase();
        const incomingInvoice = String(data.invoice_number || '').trim();

        if (incomingSupplier && !state.supplier) {
            state.supplier = incomingSupplier;
        }

        if (!Array.isArray(state.invoices)) {
            state.invoices = state.invoice_number ? [String(state.invoice_number).trim()] : [];
        }

        const effectiveSupplier = state.supplier || incomingSupplier;

        let dupPromise = Promise.resolve(null);
        if (incomingInvoice) {
            if (state.invoices.includes(incomingInvoice)) {
                ocrProgress.fail(`NF ${incomingInvoice} já está anexada`);
                alert(`⚠️ A NF ${incomingInvoice} já foi adicionada neste romaneio de conferência.`);
                return;
            }
            dupPromise = fetch('/api/invoices/check-duplicate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    supplier: effectiveSupplier,
                    invoice_number: incomingInvoice,
                }),
            }).then(r => (r.ok ? r.json() : null)).catch(() => null);
        }

        const rawItems = Array.isArray(data.items) ? data.items : [];
        const learnedMap = loadLearnedMap();

        // Consulta o catálogo em lote único (elimina gargalo N+1 na nuvem)
        const unlearnedIndices = [];
        const unlearnedDescriptions = [];
        rawItems.forEach((item, idx) => {
            const normKey = normalizeDesc(item.description);
            const learned = learnedMap[normKey];
            if (!(learned && learned.sku)) {
                unlearnedIndices.push(idx);
                unlearnedDescriptions.push(item.description);
            }
        });

        const batchMatchPromise = unlearnedDescriptions.length > 0
            ? fetch('/api/catalog/batch-match', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    supplier: effectiveSupplier,
                    items: unlearnedDescriptions,
                }),
            })
                .then(r => (r.ok ? r.json() : { matches: [] }))
                .then(payload => {
                    const arr = new Array(rawItems.length).fill(null);
                    const matchedList = Array.isArray(payload.matches) ? payload.matches : [];
                    unlearnedIndices.forEach((origIdx, mIdx) => {
                        arr[origIdx] = matchedList[mIdx] ? [matchedList[mIdx]] : null;
                    });
                    return arr;
                })
                .catch(() => new Array(rawItems.length).fill(null))
            : Promise.resolve(new Array(rawItems.length).fill(null));

        const [chkData, searchResults] = await Promise.all([
            dupPromise,
            batchMatchPromise,
        ]);

        if (incomingInvoice) {
            if (chkData && chkData.duplicate) {
                const proceedDup = confirm(
                    `⚠️ TRAVA DE NF-e DUPLICADA:\n\n${chkData.message}\n\nDeseja importar esta nota mesmo assim?`
                );
                if (!proceedDup) {
                    ocrProgress.fail(`NF ${incomingInvoice} bloqueada (duplicada)`);
                    return;
                }
            }
            state.invoices.push(incomingInvoice);
            state.invoice_number = state.invoices.join(', ');
        }

        if (rawItems.length > 0) {
            let autoLinkedCount = 0;

            rawItems.forEach((item, idx) => {
                const normKey = normalizeDesc(item.description);
                const learned = learnedMap[normKey];
                const aiFactor = Math.max(1, parseInt(item.pack_factor, 10) || 1);
                const nfQty = Math.max(1, parseInt(item.quantity, 10) || 1);

                if (learned && learned.sku) {
                    const factor = resolveEffectivePackFactor(aiFactor, learned.pack_factor, item.description);
                    autoLinkedCount++;
                    mergeOrPushConsolidatedItem({
                        sku: learned.sku,
                        ean: learned.ean || learned.sku,
                        name: `${learned.name} (NF: ${item.description})`,
                        catalog_name: learned.name,
                        raw_ocr_name: item.description,
                        unit: item.unit || 'UN',
                        weight_kg: Number(item.weight_kg) || 0,
                        nf_qty: nfQty,
                        pack_factor: factor,
                        expected: nfQty * factor,
                        scanned: 0,
                        expiration_date: '',
                        batch_code: ''
                    }, incomingInvoice);
                } else {
                    let matchedCatalog = null;
                    const candidates = searchResults[idx];
                    const top = Array.isArray(candidates) ? candidates[0] : null;
                    if (top && top.sku) {
                        const nfTokens = normKey.split(' ').filter(t => t.length >= 2);
                        const catTokens = normalizeDesc(top.name).split(' ').filter(t => t.length >= 2);
                        const common = catTokens.filter(t => nfTokens.includes(t)).length;
                        const ratio = catTokens.length > 0 ? (common / catTokens.length) : 0;
                        if (top.alias_match || ratio >= 0.70) {
                            matchedCatalog = top;
                        }
                    }

                    if (matchedCatalog) {
                        const mSku = matchedCatalog.sku || matchedCatalog.id;
                        const effectiveFactor = resolveEffectivePackFactor(aiFactor, matchedCatalog.pack_factor, item.description);
                        saveLearnedLink(item.description, { sku: mSku, ean: matchedCatalog.ean || mSku, name: matchedCatalog.name }, effectiveFactor);
                        autoLinkedCount++;
                        mergeOrPushConsolidatedItem({
                            sku: mSku,
                            ean: matchedCatalog.ean || mSku,
                            name: `${matchedCatalog.name} (NF: ${item.description})`,
                            catalog_name: matchedCatalog.name,
                            raw_ocr_name: item.description,
                            unit: item.unit || 'UN',
                            weight_kg: Number(item.weight_kg) || 0,
                            nf_qty: nfQty,
                            pack_factor: effectiveFactor,
                            expected: nfQty * effectiveFactor,
                            scanned: 0,
                            expiration_date: '',
                            batch_code: ''
                        }, incomingInvoice);
                    } else {
                        const factor = resolveEffectivePackFactor(aiFactor, 1, item.description);
                        mergeOrPushConsolidatedItem({
                            sku: 'TEMP-' + Math.random().toString(36).slice(2, 7).toUpperCase(),
                            ean: '',
                            name: item.description,
                            raw_ocr_name: item.description,
                            unit: item.unit || 'UN',
                            weight_kg: Number(item.weight_kg) || 0,
                            nf_qty: nfQty,
                            pack_factor: factor,
                            expected: nfQty * factor,
                            scanned: 0,
                            expiration_date: '',
                            batch_code: ''
                        }, incomingInvoice);
                    }
                }
            });

            save();
            render();
            const pgInfo = data.pages_processed > 1 ? ` de ${data.pages_processed} págs` : '';
            const nfTag = incomingInvoice ? ` (NF ${incomingInvoice})` : '';
            const suffix = autoLinkedCount > 0 ? ` · ${autoLinkedCount} vinculados` : '';
            ocrProgress.succeed(`${rawItems.length} itens importados${nfTag}${pgInfo}${suffix}`);
        } else {
            save();
            render();
            ocrProgress.fail('Nenhum item encontrado na nota');
            alert('⚠️ Nenhum item identificado no arquivo.');
        }
    };

    const consumeOcrStream = async (res) => {
        if (!res.ok) {
            const errTxt = await res.text();
            let msg = `Falha HTTP ${res.status}`;
            try { msg = JSON.parse(errTxt).error || msg; } catch {}
            throw new Error(msg);
        }

        if (!res.body) {
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            return data;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let finalPayload = null;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;
                const evt = JSON.parse(trimmed);
                if (evt.error) throw new Error(evt.error);
                if (typeof evt.progress === 'number') {
                    ocrProgress.update(evt.progress, evt.stage);
                }
                if (evt.done) {
                    finalPayload = evt;
                }
            }
        }

        if (buffer.trim()) {
            const evt = JSON.parse(buffer.trim());
            if (evt.error) throw new Error(evt.error);
            if (evt.done) finalPayload = evt;
        }

        return finalPayload || { items: [] };
    };

    let nfPhotoQueue = [];

    const clearNfPhotoQueue = () => {
        nfPhotoQueue.forEach(item => {
            if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
        });
        nfPhotoQueue = [];
    };

    const addFilesToNfQueue = async (fileList) => {
        const arr = Array.from(fileList || []).filter(f => f && f.size > 0);
        for (const f of arr) {
            if (nfPhotoQueue.length >= 12) {
                alert('⚠️ Limite máximo de 12 páginas por nota fiscal.');
                break;
            }
            let safeBlob;
            try {
                const buf = await f.arrayBuffer();
                safeBlob = new Blob([buf], { type: f.type || 'image/jpeg' });
            } catch {
                safeBlob = f;
            }
            nfPhotoQueue.push({
                blob: safeBlob,
                name: f.name || `pagina_${nfPhotoQueue.length + 1}.jpg`,
                previewUrl: URL.createObjectURL(safeBlob),
            });
        }
        renderMultiPhotoTray();
    };

    const postFilesToOcr = async (fileEntries) => {
        const totalBytes = fileEntries.reduce((acc, item) => acc + (item.blob?.size || 0), 0);
        const VERCEL_SAFE_LIMIT = 3.5 * 1024 * 1024;

        if (totalBytes > VERCEL_SAFE_LIMIT) {
            try {
                const signRes = await fetch('/api/invoices/upload-urls', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        files: fileEntries.map((f, idx) => ({
                            name: f.name || `arquivo_${idx + 1}`,
                            type: f.type || f.blob?.type || 'application/octet-stream',
                        })),
                    }),
                });
                if (signRes.ok) {
                    const signData = await signRes.json();
                    if (signData.enabled && Array.isArray(signData.uploads) && signData.uploads.length === fileEntries.length) {
                        const storagePaths = [];
                        for (let i = 0; i < fileEntries.length; i++) {
                            const entry = fileEntries[i];
                            const target = signData.uploads[i];
                            const putRes = await fetch(target.signed_url, {
                                method: 'PUT',
                                headers: {
                                    'Content-Type': entry.type || entry.blob?.type || 'application/octet-stream',
                                    'x-upsert': 'true',
                                },
                                body: entry.blob,
                            });
                            if (!putRes.ok) {
                                throw new Error(`Falha ao transferir arquivo grande (${putRes.status})`);
                            }
                            storagePaths.push({
                                path: target.path,
                                name: target.name,
                                mime_type: target.mime_type,
                            });
                        }

                        return fetch('/api/invoices/ocr', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'Accept': 'application/x-ndjson',
                            },
                            credentials: 'same-origin',
                            body: JSON.stringify({ storage_paths: storagePaths }),
                        });
                    }
                }
            } catch (storageErr) {
                console.warn('Fallback para envio direto:', storageErr);
            }
        }

        const formData = new FormData();
        if (fileEntries.length === 1) {
            const single = fileEntries[0];
            formData.append('file', single.blob, single.name || 'nota_fiscal.pdf');
        } else {
            fileEntries.forEach((item, idx) => {
                formData.append('files', item.blob, item.name || `pagina_${idx + 1}.jpg`);
            });
        }

        return fetch('/api/invoices/ocr', {
            method: 'POST',
            headers: { 'Accept': 'application/x-ndjson' },
            body: formData,
            credentials: 'same-origin',
        });
    };

    const uploadNfPhotoBatch = async (photoItems) => {
        if (!photoItems || photoItems.length === 0) return;
        setOcrLoading(true, 'camera');
        const total = photoItems.length;
        ocrProgress.start(total > 1 ? `Enviando ${total} fotos da NF para IA...` : 'Lendo foto da NF...');

        try {
            const res = await postFilesToOcr(
                photoItems.map((item, idx) => ({
                    blob: item.blob,
                    name: item.name || `pagina_${idx + 1}.jpg`,
                    type: item.blob?.type || 'image/jpeg',
                }))
            );

            const data = await consumeOcrStream(res);
            await appendExtractedItems(data);
        } catch (err) {
            ocrProgress.fail('Falha na leitura das fotos');
            alert('❌ Erro ao ler NF: ' + err.message);
        } finally {
            setOcrLoading(false);
        }
    };

    const renderMultiPhotoTray = () => {
        let modal = document.getElementById('nf-multiphoto-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'nf-multiphoto-modal';
            modal.className = 'fixed inset-0 z-[175] bg-black/75 flex items-center justify-center p-3';
            document.body.appendChild(modal);
        }

        const count = nfPhotoQueue.length;
        const svgCam = `<svg style="width:16px;height:16px;min-width:16px;flex-shrink:0;" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/><circle cx="12" cy="13" r="3"/></svg>`;
        const svgGal = `<svg style="width:16px;height:16px;min-width:16px;flex-shrink:0;" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path stroke-linecap="round" stroke-linejoin="round" d="M21 15l-5-5L5 21"/></svg>`;
        const svgDoc = `<svg style="width:18px;height:18px;min-width:18px;flex-shrink:0;" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>`;
        const svgClose = `<svg style="width:15px;height:15px;min-width:15px;flex-shrink:0;" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>`;

        modal.style.cssText = 'position:fixed;inset:0;z-index:9992;background:rgba(15,23,42,0.82);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center;padding:14px;box-sizing:border-box;';

        const bodyHtml = count > 0
            ? `<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;">` +
              nfPhotoQueue.map((item, idx) => `
                <div style="position:relative;border-radius:12px;overflow:hidden;border:1px solid #CBD5E1;background:#F1F5F9;aspect-ratio:3/4;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
                    <img src="${item.previewUrl}" alt="Página ${idx + 1}" style="width:100%;height:100%;object-fit:cover;display:block;">
                    <div style="position:absolute;inset:0 0 auto 0;height:28px;background:linear-gradient(to bottom,rgba(15,23,42,0.65),transparent);"></div>
                    <span style="position:absolute;top:6px;left:6px;background:#124191;color:#FFFFFF;font-size:9px;font-weight:900;letter-spacing:0.05em;padding:2px 7px;border-radius:6px;">
                        PÁG. ${idx + 1}
                    </span>
                    <button type="button" data-remove-nf-page="${idx}" aria-label="Remover página ${idx + 1}"
                        style="position:absolute;top:6px;right:6px;width:24px;height:24px;border-radius:9999px;background:rgba(255,255,255,0.95);color:#D9232E;border:1px solid #FECACA;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 1px 2px rgba(0,0,0,0.12);">
                        <svg style="width:12px;height:12px;" fill="none" stroke="currentColor" stroke-width="2.8" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                </div>
              `).join('') + `</div>`
            : `<div style="padding:28px 18px;text-align:center;background:#F8FAFC;border:1.5px dashed #CBD5E1;border-radius:14px;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                    <div style="width:42px;height:42px;border-radius:9999px;background:#EFF6FF;color:#124191;border:1px solid #DBEAFE;display:flex;align-items:center;justify-content:center;margin-bottom:10px;">
                        ${svgDoc}
                    </div>
                    <p style="margin:0;font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:0.04em;color:#1E293B;">
                        Nenhuma página anexada
                    </p>
                    <p style="margin:6px 0 0 0;font-size:10px;line-height:1.45;color:#64748B;max-width:250px;">
                        Capture cada folha da DANFE em sequência ou selecione múltiplas imagens da galeria.
                    </p>
               </div>`;

        modal.innerHTML = `
            <div style="background:#FFFFFF;border-radius:18px;box-shadow:0 24px 48px rgba(15,23,42,0.35);width:100%;max-width:420px;max-height:88vh;display:flex;flex-direction:column;overflow:hidden;border:1px solid #E2E8F0;">
                <div style="background:#124191;color:#FFFFFF;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;gap:10px;border-bottom:3px solid #D9232E;">
                    <div style="display:flex;align-items:center;gap:10px;min-width:0;">
                        <div style="width:34px;height:34px;border-radius:10px;background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.18);display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                            ${svgDoc}
                        </div>
                        <div style="min-width:0;">
                            <h3 style="margin:0;font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:0.05em;line-height:1.25;">
                                Digitalização de Nota Fiscal
                            </h3>
                            <p style="margin:3px 0 0 0;font-size:10px;color:#BFDBFE;font-weight:600;">
                                ${count === 0 ? 'Captura multi-página com leitura por IA' : `${count} ${count === 1 ? 'página na fila' : 'páginas na fila'} · Ordenado por captura`}
                            </p>
                        </div>
                    </div>
                    <button type="button" id="nf-tray-close" aria-label="Fechar"
                        style="width:32px;height:32px;border-radius:8px;background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.18);color:#FFFFFF;display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;">
                        ${svgClose}
                    </button>
                </div>

                <div style="padding:12px 14px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;background:#F8FAFC;border-bottom:1px solid #E2E8F0;">
                    <button type="button" id="nf-tray-cam-btn"
                        style="background:#124191;color:#FFFFFF;border:none;border-radius:12px;padding:11px 12px;font-size:10px;font-weight:900;text-transform:uppercase;letter-spacing:0.05em;display:flex;align-items:center;justify-content:center;gap:7px;cursor:pointer;box-shadow:0 1px 2px rgba(18,65,145,0.25);">
                        ${svgCam}
                        <span>${count > 0 ? 'NOVA PÁGINA' : 'CÂMERA'}</span>
                    </button>
                    <button type="button" id="nf-tray-gal-btn"
                        style="background:#FFFFFF;color:#124191;border:1.5px solid #124191;border-radius:12px;padding:11px 12px;font-size:10px;font-weight:900;text-transform:uppercase;letter-spacing:0.05em;display:flex;align-items:center;justify-content:center;gap:7px;cursor:pointer;">
                        ${svgGal}
                        <span>GALERIA</span>
                    </button>
                </div>

                <div style="padding:14px;overflow-y:auto;flex:1;background:#FFFFFF;">
                    ${bodyHtml}
                </div>

                <div style="padding:12px 14px;border-top:1px solid #E2E8F0;background:#F8FAFC;display:flex;align-items:center;gap:10px;">
                    <button type="button" id="nf-tray-cancel"
                        style="padding:12px 14px;border-radius:12px;background:#FFFFFF;border:1px solid #CBD5E1;color:#475569;font-size:10px;font-weight:900;text-transform:uppercase;letter-spacing:0.05em;cursor:pointer;flex-shrink:0;">
                        CANCELAR
                    </button>
                    <button type="button" id="nf-tray-submit" ${count === 0 ? 'disabled' : ''}
                        style="flex:1;padding:12px 14px;border-radius:12px;border:none;background:${count > 0 ? '#059669' : '#CBD5E1'};color:${count > 0 ? '#FFFFFF' : '#64748B'};font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:0.05em;display:flex;align-items:center;justify-content:center;gap:7px;cursor:${count > 0 ? 'pointer' : 'not-allowed'};box-shadow:${count > 0 ? '0 2px 6px rgba(5,150,105,0.28)' : 'none'};">
                        ${svgDoc}
                        <span>${count > 0 ? `PROCESSAR ${count} ${count === 1 ? 'PÁGINA' : 'PÁGINAS'}` : 'AGUARDANDO PÁGINAS'}</span>
                    </button>
                </div>
            </div>
        `;

        document.getElementById('nf-tray-cam-btn')?.addEventListener('click', () => {
            document.getElementById('ai-upload-camera')?.click();
        });
        document.getElementById('nf-tray-gal-btn')?.addEventListener('click', () => {
            document.getElementById('ai-upload-gallery')?.click();
        });

        const closeAndClear = () => {
            clearNfPhotoQueue();
            modal.remove();
        };
        document.getElementById('nf-tray-close')?.addEventListener('click', closeAndClear);
        document.getElementById('nf-tray-cancel')?.addEventListener('click', closeAndClear);

        modal.querySelectorAll('[data-remove-nf-page]').forEach(btn => {
            btn.addEventListener('click', () => {
                const idx = parseInt(btn.getAttribute('data-remove-nf-page'), 10);
                if (!Number.isNaN(idx) && nfPhotoQueue[idx]) {
                    if (nfPhotoQueue[idx].previewUrl) URL.revokeObjectURL(nfPhotoQueue[idx].previewUrl);
                    nfPhotoQueue.splice(idx, 1);
                    renderMultiPhotoTray();
                }
            });
        });

        document.getElementById('nf-tray-submit')?.addEventListener('click', async () => {
            if (nfPhotoQueue.length === 0) return;
            const batch = [...nfPhotoQueue];
            nfPhotoQueue = [];
            modal.remove();
            try {
                await uploadNfPhotoBatch(batch);
            } finally {
                batch.forEach(item => {
                    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
                });
            }
        });
    };

    document.getElementById('btn-ai-camera')?.addEventListener('click', () => {
        renderMultiPhotoTray();
    });

    document.getElementById('btn-ai-file')?.addEventListener('click', () => {
        document.getElementById('ai-upload-file')?.click();
    });

    const handleMultiImagePick = async (e) => {
        if (!e.target.files || e.target.files.length === 0) return;
        await addFilesToNfQueue(e.target.files);
        e.target.value = '';
    };

    const handlePdfUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setOcrLoading(true, 'pdf');
        ocrProgress.start('Lendo PDF selecionado...');

        try {
            let safeBlob;
            try {
                const buffer = await file.arrayBuffer();
                safeBlob = new Blob([buffer], { type: file.type || 'application/pdf' });
            } catch {
                safeBlob = file;
            }

            const res = await postFilesToOcr([
                {
                    blob: safeBlob,
                    name: file.name || 'nota_fiscal.pdf',
                    type: file.type || 'application/pdf',
                },
            ]);

            const data = await consumeOcrStream(res);
            await appendExtractedItems(data);
        } catch (err) {
            ocrProgress.fail('Falha na leitura do PDF');
            alert('❌ Erro ao ler NF: ' + err.message);
        } finally {
            setOcrLoading(false);
            e.target.value = '';
        }
    };

    document.getElementById('ai-upload-camera')?.addEventListener('change', handleMultiImagePick);
    document.getElementById('ai-upload-gallery')?.addEventListener('change', handleMultiImagePick);
    document.getElementById('ai-upload-file')?.addEventListener('change', handlePdfUpload);

    const params = new URLSearchParams(window.location.search);
    const shareId = params.get('share_id');
    if (shareId) {
        const cleanUrl = window.location.pathname + window.location.hash;
        window.history.replaceState({}, document.title, cleanUrl);

        const openConfTrigger = document.querySelector('#btn-inbound-conference, [data-screen="conference"], [data-target="conference"], #btn-open-conference, [onclick*="conference"]');
        if (openConfTrigger) openConfTrigger.click();

        setTimeout(async () => {
            setOcrLoading(true, 'pdf');
            ocrProgress.start('Recebendo PDF do Adobe Scan...');
            try {
                const res = await fetch(`/api/invoices/shared/${shareId}`, {
                    headers: { 'Accept': 'application/x-ndjson' },
                    credentials: 'same-origin'
                });
                const data = await consumeOcrStream(res);
                await appendExtractedItems(data);
            } catch (err) {
                ocrProgress.fail('Erro ao importar PDF compartilhado');
                alert('❌ Erro ao importar NF compartilhada: ' + err.message);
            } finally {
                setOcrLoading(false);
            }
        }, 250);
    }


    document.getElementById('conference-supplier-input')?.addEventListener('input', (e) => {
      state.supplier = e.target.value.toUpperCase();
      save();
    });

    document.getElementById('conference-invoice-input')?.addEventListener('input', (e) => {
      state.invoice_number = e.target.value;
      save();
    });

    document.getElementById('btn-conference-add')?.addEventListener('click', async () => {
      const identifier = prompt('Digite o SKU ou EAN:');
      if (identifier) scan(identifier);
    });

    const scanBtnEl = document.getElementById('conf-scan-btn');
    if (scanBtnEl && !document.getElementById('conf-camera-scan-btn')) {
      const camScanBtn = document.createElement('button');
      camScanBtn.type = 'button';
      camScanBtn.id = 'conf-camera-scan-btn';
      camScanBtn.title = 'Abrir câmera para bipar código';
      camScanBtn.className = 'bg-slate-800 text-white px-3 rounded-lg font-black text-xs shadow-sm active:scale-95 flex items-center justify-center';
      camScanBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="7" y1="12" x2="17" y2="12"/></svg>';
      camScanBtn.addEventListener('click', () => {
        if (typeof window.kippeOpenConferenceScanner === 'function') {
          window.kippeOpenConferenceScanner();
        } else {
          document.getElementById('nav-scan')?.click();
        }
      });
      scanBtnEl.before(camScanBtn);
    }

    document.getElementById('conf-scan-btn')?.addEventListener('click', () => {
      const input = document.getElementById('conf-scan-input');
      if (input) {
        scan(input.value);
        input.value = '';
        input.focus();
      }
    });

    document.getElementById('conf-scan-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        scan(e.target.value);
        e.target.value = '';
      }
    });

    document.getElementById('btn-conference-finalize')?.addEventListener('click', finalize);
    
    // Botão cancelar do Quick Create
    document.getElementById('qc-cancel')?.addEventListener('click', () => {
      document.getElementById('quick-create-modal').classList.add('hidden');
      document.getElementById('conf-scan-input').focus();
    });
  }

  return { mount, wire, scan };
})();

window.ConferenceFeature = ConferenceFeature;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => window.ConferenceFeature.wire());
} else {
  setTimeout(() => window.ConferenceFeature.wire(), 0);
}
