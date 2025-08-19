const ghostCharts = { status: null, maint: null, movement: null, type: null, stockStacked: null };
function applyInitialTheme() {
  const htmlTheme = document.documentElement.getAttribute('data-theme');
  const saved = localStorage.getItem('ghoststock-theme');
  if (htmlTheme && htmlTheme !== saved) {
    document.documentElement.setAttribute('data-theme', htmlTheme);
    try { localStorage.setItem('ghoststock-theme', htmlTheme); } catch(_) {}
    return;
  }
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  applyInitialTheme();
  const cmdkBtn = document.getElementById('cmdk-btn');
  if (cmdkBtn) cmdkBtn.addEventListener('click', openCommandPalette);
  const cmdkClose = document.getElementById('cmdk-close');
  if (cmdkClose) cmdkClose.addEventListener('click', closeCommandPalette);
  const menuToggle = document.getElementById('menu-toggle');
  const navLinks = document.getElementById('nav-links');
  if (menuToggle && navLinks) {
    menuToggle.addEventListener('click', () => {
      navLinks.classList.toggle('show');
    });
    document.addEventListener('click', (e) => {
      if (!navLinks.contains(e.target) && e.target !== menuToggle) {
        navLinks.classList.remove('show');
      }
    });
  }

  document.addEventListener('ghostia:start', () => {
    const t = document.querySelector('.page-title');
    const m = document.querySelector('.muted');
    if (t) t.classList.add('hidden');
    if (m) m.classList.add('hidden');
  });

  const input = document.getElementById('search-q');
  const box = document.getElementById('autocomplete');
  if (input && box) {
    let controller;
    function hide(){ box.style.display = 'none'; box.innerHTML=''; }
    input.addEventListener('input', async () => {
      const q = input.value.trim();
      if (q.length < 2) { hide(); return; }
      if (controller) controller.abort();
      controller = new AbortController();
      try {
        const res = await fetch('/items/api/autocomplete?q=' + encodeURIComponent(q), { signal: controller.signal });
        const items = await res.json();
        if (!Array.isArray(items) || !items.length) { hide(); return; }
        box.innerHTML = items.map(i => `<div class="cmdk-item" data-id="${i.id}" style="padding:8px 10px;cursor:pointer">${i.name}</div>`).join('');
        box.style.display = 'block';
        box.querySelectorAll('.cmdk-item').forEach(div => {
          div.addEventListener('click', () => { window.location.href = `/items/${div.dataset.id}`; });
        });
      } catch (_) { hide(); }
    });
    document.addEventListener('click', (e) => { if (!box.contains(e.target) && e.target !== input) hide(); });
  }

  const timeline = document.getElementById('timeline');
  if (timeline) {
    const m = window.location.pathname.match(/\/items\/(\d+)/);
    const id = m ? m[1] : null;
    if (id) {
      (async () => {
        try {
          const res = await fetch(`/items/${id}/history`);
          const data = await res.json();
          if (data?.movements?.length) {
            timeline.innerHTML = data.movements.map(mv => `
              <div style="display:flex;gap:8px;align-items:center;margin:6px 0">
                <span class="badge">${mv.timestamp}</span>
                <span>${String(mv.action||'').replace('_',' ')}: <strong>${mv.from||'-'}</strong> → <strong>${mv.to||'-'}</strong></span>
              </div>
            `).join('');
          } else {
            timeline.innerHTML = '<p class="muted">Sem eventos registrados.</p>';
          }
        } catch (_) {
          timeline.innerHTML = '<p class="muted">Erro ao carregar timeline.</p>';
        }
      })();
    }
  }
});

function initItemMap() {
  const el = document.getElementById('map');
  if (!el) return;
  const lat = parseFloat(el.dataset.lat || '');
  const lng = parseFloat(el.dataset.lng || '');
  const type = (el.dataset.type || '').toLowerCase();
  if (Number.isNaN(lat) || Number.isNaN(lng)) return;
  function fallbackIframe() {
    const delta = 0.01;
    const bbox = [lng - delta, lat - delta, lng + delta, lat + delta];
    el.innerHTML = `<iframe title="Mapa" style="border:0;width:100%;height:100%;border-radius:12px" src="https://www.openstreetmap.org/export/embed.html?bbox=${bbox.join('%2C')}&layer=mapnik&marker=${lat}%2C${lng}" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>`;
  }
  try {
    if (!window.L) { fallbackIframe(); return; }
    const map = L.map('map').setView([lat, lng], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(map);
    const iconMap = {
      cama: '/static/img/cama_real.jpg',
      cadeira_rodas: '/static/img/cadeira_rodas.svg',
      cadeira_higienica: '/static/img/cadeira_higienica.svg',
      muletas: '/static/img/muletas.svg',
      andador: '/static/img/andador.svg',
      colchao_pneumatico: '/static/img/cama_real.jpg'
    };
    const iconUrl = iconMap[type] || '/static/img/logo.png';
    const markerIcon = L.icon({
      iconUrl,
      iconSize: [28, 28],
      iconAnchor: [14, 28],
      popupAnchor: [0, -24]
    });
    L.marker([lat, lng], { icon: markerIcon }).addTo(map).bindPopup(el.dataset.name || 'Localização');
    setTimeout(() => {
      const hasTiles = el.querySelector('.leaflet-tile, .leaflet-marker-icon');
      if (!hasTiles) fallbackIframe();
    }, 1000);
  } catch (_) {
    fallbackIframe();
  }
}

document.addEventListener('DOMContentLoaded', initItemMap);

async function initMapAll() {
  const el = document.getElementById('map-all');
  if (!el) return;
  function fallback(msg){ el.innerHTML = `<p class="muted" style="padding:12px">${msg}</p>`; }
  try {
    if (!window.L) { fallback('Mapa indisponível'); return; }
    const res = await fetch('/items/api/geo');
    const data = await res.json();
    const map = L.map('map-all').setView([-23.55, -46.63], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(map);
    const markers = L.markerClusterGroup();
    const iconMap = {
      cama: '/static/img/cama_real.jpg',
      cadeira_rodas: '/static/img/cadeira_rodas.svg',
      cadeira_higienica: '/static/img/cadeira_higienica.svg',
      muletas: '/static/img/muletas.svg',
      andador: '/static/img/andador.svg',
      colchao_pneumatico: '/static/img/cama_real.jpg'
    };
    data.items.forEach(it => {
      const iconUrl = iconMap[it.type] || '/static/img/logo.png';
      const markerIcon = L.icon({ iconUrl, iconSize: [24,24], iconAnchor:[12,24], popupAnchor:[0,-20] });
      const m = L.marker([it.lat, it.lng], { icon: markerIcon }).bindPopup(`#${it.id} - ${it.name}`);
      markers.addLayer(m);
    });
    map.addLayer(markers);
    if (data.items.length) {
      const group = new L.featureGroup(data.items.map(it => L.marker([it.lat, it.lng])));
      try { map.fitBounds(group.getBounds().pad(0.2)); } catch(_) {}
    }
  } catch (_) {
    fallback('Falha ao carregar dados geográficos');
  }
}

document.addEventListener('DOMContentLoaded', initMapAll);
function renderStatusChart(disponiveis, locados) {
  const ctx = document.getElementById('statusChart');
  if (!ctx) return;
  const cfg = {
    type: 'bar',
    data: { labels: ['Disponíveis', 'Locados'], datasets: [{ data: [disponiveis, locados], backgroundColor: ['#00c2ff', '#3b82f6'] }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text') } }, y: { ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text') } } } }
  };
  if (!ghostCharts.status) { ghostCharts.status = new Chart(ctx, cfg); } else { ghostCharts.status.data.datasets[0].data = [disponiveis, locados]; ghostCharts.status.update(); }
}

function renderMaintenanceChart(maintenance) {
  const ctx = document.getElementById('maintChart');
  if (!ctx) return;
  const cfg = {
    type: 'bar',
    data: { labels: ['Vencidas', 'Próximas'], datasets: [{ data: [maintenance.due, maintenance.soon], backgroundColor: ['#ef4444', '#f59e0b'] }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text') } }, y: { ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text') } } } }
  };
  if (!ghostCharts.maint) { ghostCharts.maint = new Chart(ctx, cfg); } else { ghostCharts.maint.data.datasets[0].data = [maintenance.due, maintenance.soon]; ghostCharts.maint.update(); }
}

function renderMovementChart(movement) {
  const ctx = document.getElementById('moveChart');
  if (!ctx) return;
  const labels = movement.map(m => m.label);
  const values = movement.map(m => m.count);

  function smoothSeries(series, windowSize) {
    const smoothed = [];
    const size = Math.max(1, Number(windowSize) || 1);
    const half = Math.floor(size / 2);
    for (let i = 0; i < series.length; i += 1) {
      const start = Math.max(0, i - half);
      const end = Math.min(series.length - 1, i + half);
      let sum = 0;
      let count = 0;
      for (let j = start; j <= end; j += 1) { sum += Number(series[j] || 0); count += 1; }
      smoothed.push(count ? sum / count : Number(series[i] || 0));
    }
    return smoothed;
  }

  const smoothedValues = smoothSeries(values, 5);
  const maxVal = Math.max(1, ...smoothedValues);
  const cfg = {
    type: 'line',
    data: { labels, datasets: [{
      label: 'Movimentações por mês',
      data: smoothedValues,
      borderColor: '#00c2ff',
      backgroundColor: 'rgba(0, 194, 255, 0.18)',
      tension: 0.2,
      cubicInterpolationMode: 'monotone',
      pointRadius: 1,
      fill: true
    }] },
    options: {
      plugins: { legend: { labels: { color: getComputedStyle(document.documentElement).getPropertyValue('--text') } } },
      scales: {
        x: { ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text') } },
        y: { beginAtZero: true, suggestedMax: maxVal * 1.15,
          ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text'),
            callback: function(value) { try { const n = Number(value); return n >= 1000 ? (n/1000)+'k' : n; } catch(_) { return value; } }
          }
        }
      }
    }
  };
  try {
    if (!ghostCharts.movement) {
      ghostCharts.movement = new Chart(ctx, cfg);
    } else {
      ghostCharts.movement.data.labels = labels;
      ghostCharts.movement.data.datasets[0].data = smoothedValues;
      ghostCharts.movement.update();
    }
  } catch (e) {}
}

function renderTypeChart(byType) {
  const ctx = document.getElementById('typeChart');
  if (!ctx) return;
  ctx.style.height = '80px';
  const labels = ['Cama', 'Cadeira higiênica', 'Cadeira de rodas', 'Muletas', 'Andador', 'Colchão pneumático (CPNEU)'];
  const keys = ['cama', 'cadeira_higienica', 'cadeira_rodas', 'muletas', 'andador', 'colchao_pneumatico'];
  const values = keys.map(k => byType[k] || 0);
  const cfg = {
    type: 'pie',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: ['#00c2ff', '#3b82f6', '#f59e0b', '#10b981', '#6366f1', '#ef4444'] }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: getComputedStyle(document.documentElement).getPropertyValue('--text'), boxWidth: 8, font: { size: 9 } } } }
    }
  };
  if (ghostCharts.type) { ghostCharts.type.destroy(); }
  ghostCharts.type = new Chart(ctx, cfg);
}

function renderStockStackedChart(byStockStatus) {
  const ctx = document.getElementById('stockStackedChart');
  if (!ctx) return;
  const labels = ['AL', 'AS', 'AV', 'AB'];
  const disponiveis = labels.map(k => (byStockStatus[k]?.disponivel) || 0);
  const locados = labels.map(k => (byStockStatus[k]?.locado) || 0);
  const cfg = {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Disponíveis', data: disponiveis, backgroundColor: '#10b981' },
        { label: 'Locados', data: locados, backgroundColor: '#3b82f6' }
      ]
    },
    options: {
      responsive: true,
      scales: {
        x: { stacked: true, ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text') } },
        y: { stacked: true, ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text') } }
      },
      plugins: { legend: { labels: { color: getComputedStyle(document.documentElement).getPropertyValue('--text') } } }
    }
  };
  if (!ghostCharts.stockStacked) {
    ghostCharts.stockStacked = new Chart(ctx, cfg);
  } else {
    ghostCharts.stockStacked.data.datasets[0].data = disponiveis;
    ghostCharts.stockStacked.data.datasets[1].data = locados;
    ghostCharts.stockStacked.update();
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const saved = localStorage.getItem('ghoststock-theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
  if (window.location.pathname.includes('dashboard')) {
    const hasCharts = document.getElementById('typeChart') || document.getElementById('moveChart');
    if (!hasCharts) {
      return;
    }
    async function loadStats() {
      const res = await fetch('/admin/api/dashboard-stats');
      if (!res.ok) throw new Error('api-failed');
      const data = await res.json();
      const totalEl = document.getElementById('stat-total');
      const dispEl = document.getElementById('stat-disponiveis');
      const usoEl = document.getElementById('stat-emuso');
      const maintDueEl = document.getElementById('stat-maintenance-due');
      const maintSoonEl = document.getElementById('stat-maintenance-soon');
      if (totalEl) totalEl.innerText = data.total;
      if (dispEl) dispEl.innerText = data.disponiveis;
      if (usoEl) usoEl.innerText = data.em_uso;
      if (maintDueEl) maintDueEl.innerText = Number(data?.maintenance?.due || 0);
      if (maintSoonEl) maintSoonEl.innerText = Number(data?.maintenance?.soon || 0);
       renderTypeChart(data.by_type || {});
      renderStockStackedChart(data.by_stock_status || {});
      renderStatusChart(data.disponiveis, data.em_uso);
      renderMovementChart(data.movement || []);
      const total = Number(totalEl?.innerText || 0);
      const disp = Number(dispEl?.innerText || 0);
      const card = document.getElementById('card-disponiveis');
      if (card) card.style.boxShadow = (total > 0 && disp / total < 0.1) ? '0 0 0 2px #ef4444' : '';
    }
    try {
      await loadStats();
    } catch (_) {
      try {
        const el = document.getElementById('dash-initial');
        if (el && el.dataset.json) {
          const initial = JSON.parse(el.dataset.json);
          renderTypeChart(initial.by_type || {});
          renderStockStackedChart(initial.by_stock_status || {});
          renderStatusChart(initial.disponiveis || 0, initial.em_uso || 0);
          renderMovementChart(initial.movement || []);
        }
      } catch (e) {  }
    }
    setInterval(loadStats, 30000);
  }
});

function initCatalog3D() {
  const grid = document.querySelector('.catalog-grid');
  if (!grid) return;
  grid.querySelectorAll('.catalog-card').forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const rx = ((y / rect.height) - 0.5) * -10;
      const ry = ((x / rect.width) - 0.5) * 10;
      card.style.transform = `rotateX(${rx}deg) rotateY(${ry}deg)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = 'rotateX(0) rotateY(0)';
    });
  });
}

document.addEventListener('DOMContentLoaded', initCatalog3D);

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.catalog-thumb img').forEach(img => {
    const src = img.getAttribute('src');
    const fallback = src; // já é SVG na maioria dos casos
    img.addEventListener('error', () => {
      img.src = fallback;
    }, { once: true });
  });
});

function openCommandPalette() {
  const modal = document.getElementById('cmdk');
  if (!modal) return;
  modal.classList.remove('hidden');
  setTimeout(() => document.getElementById('cmdk-input')?.focus(), 0);
  renderCmdkResults('');
}
function closeCommandPalette() {
  document.getElementById('cmdk')?.classList.add('hidden');
}
function renderCmdkResults(query) {
  const el = document.getElementById('cmdk-results');
  if (!el) return;
  const q = (query || '').toLowerCase();
  const commands = [
    { label: 'Ir para Itens', action: () => location.href = '/items/' },
    { label: 'Novo item', action: () => location.href = '/items/new' },
    { label: 'Scan QR', action: () => location.href = '/qr/scan' },
    { label: 'Catálogo técnico', action: () => location.href = '/catalog' },
    { label: 'Sobre', action: () => location.href = '/about' },
    { label: 'Itens locados (todos)', action: () => location.href = '/items/?status=locado' },
    { label: 'Itens disponíveis (todos)', action: () => location.href = '/items/?status=disponivel' },
    { label: 'Locados no estoque AL', action: () => location.href = '/items/?status=locado&origin_stock=AL' },
    { label: 'Locados no estoque AS', action: () => location.href = '/items/?status=locado&origin_stock=AS' },
    { label: 'Locados no estoque AV', action: () => location.href = '/items/?status=locado&origin_stock=AV' },
    { label: 'Locados no estoque AB', action: () => location.href = '/items/?status=locado&origin_stock=AB' },
  ];
  if (q.startsWith('maps ')) {
    const code = q.replace('maps', '').trim();
    if (code) {
      commands.unshift({ label: `Abrir Maps para ${code}`, action: async () => {
        try {
          const res = await fetch('/items/?status=locado');
          window.open(`https://www.google.com/maps/search/${encodeURIComponent(code)}`,'_blank','noopener');
        } catch (_) {
          window.open(`https://www.google.com/maps/search/${encodeURIComponent(code)}`,'_blank','noopener');
        }
      }});
    }
  }
  const filtered = commands.filter(c => c.label.toLowerCase().includes(q));
  el.innerHTML = filtered.map((c, i) => `<div class="cmdk-item" data-idx="${i}">${c.label}</div>`).join('');
  el.querySelectorAll('.cmdk-item').forEach((div, i) => {
    div.addEventListener('click', () => filtered[i].action());
  });
}

document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    const isOpen = !document.getElementById('cmdk')?.classList.contains('hidden');
    if (isOpen) closeCommandPalette(); else openCommandPalette();
  } else if (e.key === 'Escape') {
    closeCommandPalette();
  }
});

document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('cmdk-input');
  if (input) {
    input.addEventListener('input', (e) => renderCmdkResults(e.target.value));
  }

  const traceBtn = document.getElementById('open-trace');
  const traceClose = document.getElementById('trace-close');
  const traceBackdrop = document.getElementById('trace-backdrop');
  const STOCK_CITY = { AL: 'Rio de Janeiro', AS: 'São Paulo', AV: 'Valinhos', AB: 'Belo Horizonte' };
  function openTraceModal(lat, lng, stock, patient, location) {
    const modal = document.getElementById('trace-modal');
    const info = document.getElementById('trace-info');
    const link = document.getElementById('trace-link');
    const city = STOCK_CITY[stock] || '-';
    const url = `https://www.google.com/maps?q=${lat},${lng}`;
    info.innerHTML = `
      <p><strong>Estoque de origem:</strong> ${stock} - ${city}</p>
      <p><strong>Paciente:</strong> ${patient || '-'}</p>
      <p><strong>Local atual:</strong> ${location || city}</p>
      <p><strong>Coordenadas:</strong> ${Number(lat).toFixed(6)}, ${Number(lng).toFixed(6)}</p>
    `;
    link.href = url;
    modal.classList.remove('hidden');
  }
  function closeTraceModal() {
    const modal = document.getElementById('trace-modal');
    if (modal) modal.classList.add('hidden');
  }
  if (traceBtn) {
    traceBtn.addEventListener('click', () => {
      openTraceModal(traceBtn.dataset.lat, traceBtn.dataset.lng, traceBtn.dataset.stock, traceBtn.dataset.patient, traceBtn.dataset.location);
    });
  }
  if (traceClose) traceClose.addEventListener('click', closeTraceModal);
  if (traceBackdrop) traceBackdrop.addEventListener('click', closeTraceModal);

  const imgBtn = document.getElementById('img-search-btn');
  const imgInput = document.getElementById('img-search-input');
  const imgModal = document.getElementById('img-modal');
  const imgResults = document.getElementById('img-results');
  const imgClose = document.getElementById('img-close');
  const imgBackdrop = document.getElementById('img-backdrop');
  function closeImgModal(){ imgModal?.classList.add('hidden'); }
  if (imgBtn && imgInput) {
    imgBtn.addEventListener('click', () => imgInput.click());
    imgInput.addEventListener('change', async () => {
      const f = imgInput.files?.[0];
      if (!f) return;
      const form = new FormData();
      form.append('file', f);
      imgResults.innerHTML = 'Processando imagem...';
      imgModal?.classList.remove('hidden');
      try {
        const res = await fetch('/items/image-search', { method: 'POST', body: form });
        const data = await res.json();
        if (data.error) {
          imgResults.innerHTML = `<p class="muted">Falha no OCR: ${data.detail || data.error}</p>`;
        } else if (data.matches?.length) {
          imgResults.innerHTML = data.matches.map(m => `<div style="padding:6px 0"><a class="btn-link" href="/items/${m.id}">${m.name}</a> <span class="badge ${m.status}">${m.status}</span></div>`).join('');
        } else {
          imgResults.innerHTML = '<p class="muted">Nenhum item correspondente encontrado.</p>';
        }
      } catch (e) {
        imgResults.innerHTML = '<p class="muted">Erro na busca por imagem.</p>';
      }
      imgInput.value = '';
    });
  }
  if (imgClose) imgClose.addEventListener('click', closeImgModal);
  if (imgBackdrop) imgBackdrop.addEventListener('click', closeImgModal);
});


