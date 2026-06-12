// Portfolio view — KPI cards, charts, renewals, risk matrix

let healthChart = null;
let arrChart = null;
let pipelineChart = null;

async function loadPortfolio() {
  let data;
  try {
    const res = await fetch('/api/portfolio');
    data = await res.json();
  } catch (e) {
    console.error('Portfolio load failed', e);
    return;
  }

  renderKPIs(data.kpis);
  renderCharts(data.kpis, data.arr_bands);
  renderRenewalPipeline(data.renewal_pipeline || []);
  renderRenewals(data.renewals_90d);
  renderRiskMatrix(data.risk_matrix);

  const badge = document.getElementById('nav-account-count');
  if (badge) badge.textContent = `${data.kpis.total_accounts} accounts`;
}

function renderKPIs(k) {
  const { fmtEur, fmtDays } = window.App;

  const arrCard = document.getElementById('kpi-arr');
  arrCard.classList.remove('skeleton');
  arrCard.innerHTML = `
    <div class="kpi-label">Total ARR</div>
    <div class="kpi-value">${fmtEur(k.total_arr)}</div>
    <div class="kpi-sub">${k.total_accounts} accounts</div>
  `;

  const riskCard = document.getElementById('kpi-risk');
  riskCard.classList.remove('skeleton');
  riskCard.innerHTML = `
    <div class="kpi-label">ARR at Risk</div>
    <div class="kpi-value${k.arr_at_risk_pct > 25 ? ' danger' : k.arr_at_risk_pct > 10 ? ' warn' : ''}">${fmtEur(k.arr_at_risk)}</div>
    <div class="kpi-sub">${k.arr_at_risk_pct}% of portfolio</div>
  `;

  const redCard = document.getElementById('kpi-red');
  redCard.classList.remove('skeleton');
  redCard.innerHTML = `
    <div class="kpi-label">At-Risk Accounts</div>
    <div class="kpi-value${k.red_count > 5 ? ' danger' : ''}">${k.red_count} <span style="font-size:1rem;color:var(--muted)">●</span></div>
    <div class="kpi-sub">
      <span class="dot-yellow">●</span> ${k.yellow_count} at risk &nbsp;
      <span class="dot-green">●</span> ${k.green_count} healthy
    </div>
  `;

  const renewCard = document.getElementById('kpi-renewal');
  renewCard.classList.remove('skeleton');
  renewCard.innerHTML = `
    <div class="kpi-label">Next Renewal</div>
    <div class="kpi-value${k.next_renewal_days <= 7 ? ' danger' : k.next_renewal_days <= 30 ? ' warn' : ''}">${fmtDays(k.next_renewal_days)}</div>
    <div class="kpi-sub">${k.next_renewal_name || '—'}</div>
  `;
}

function renderCharts(kpis, bands) {
  // Donut — health distribution
  const donutCtx = document.getElementById('chart-health').getContext('2d');
  const green = kpis.green_count, yellow = kpis.yellow_count, red = kpis.red_count;
  const total = green + yellow + red;

  if (healthChart) healthChart.destroy();
  healthChart = new Chart(donutCtx, {
    type: 'doughnut',
    data: {
      labels: ['Healthy', 'At Risk', 'Critical'],
      datasets: [{
        data: [green, yellow, red],
        backgroundColor: ['#4ade80', '#fbbf24', '#f87171'],
        borderWidth: 0,
        hoverOffset: 4,
      }],
    },
    options: {
      cutout: '72%',
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
      animation: { duration: 600 },
    },
  });

  const center = document.getElementById('donut-center');
  if (center) {
    center.innerHTML = `<div class="dc-value">${total}</div><div class="dc-label">accounts</div>`;
  }

  const legend = document.getElementById('chart-health-legend');
  if (legend) {
    legend.innerHTML = [
      { label: 'Healthy',   count: green,  cls: 'dot-green' },
      { label: 'At Risk',   count: yellow, cls: 'dot-yellow' },
      { label: 'Critical',  count: red,    cls: 'dot-red' },
    ].map(row => `
      <div class="legend-row">
        <span><span class="legend-dot ${row.cls}">●</span>${row.label}</span>
        <span style="font-family:var(--mono)">${row.count}</span>
      </div>
    `).join('');
  }

  // Horizontal bar — ARR by band
  const barCtx = document.getElementById('chart-arr-bands').getContext('2d');
  const orderedBands = ['green', 'yellow', 'red'];
  const bandMap = Object.fromEntries((bands || []).map(b => [b.health_band, b]));
  const barLabels = ['Healthy', 'At Risk', 'Critical'];
  const barValues = orderedBands.map(b => Math.round((bandMap[b]?.arr_eur || 0) / 1000));
  const barColors = ['#4ade80', '#fbbf24', '#f87171'];

  if (arrChart) arrChart.destroy();
  arrChart = new Chart(barCtx, {
    type: 'bar',
    data: {
      labels: barLabels,
      datasets: [{
        data: barValues,
        backgroundColor: barColors,
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: {
        callbacks: { label: ctx => ` €${ctx.raw}k` },
      }},
      scales: {
        x: {
          grid: { color: '#232328' },
          ticks: { color: '#9b9792', font: { family: 'JetBrains Mono', size: 10 }, callback: v => `€${v}k` },
          border: { color: '#232328' },
        },
        y: {
          grid: { display: false },
          ticks: { color: '#d4d0c8', font: { family: 'Inter', size: 13 } },
          border: { color: '#232328' },
        },
      },
      animation: { duration: 600 },
    },
  });
}

function renderRenewalPipeline(pipeline) {
  const ctx = document.getElementById('chart-renewal-pipeline');
  if (!ctx) return;

  const labels = pipeline.map(d => d.month);
  const toK = v => Math.round(v / 1000);

  if (pipelineChart) pipelineChart.destroy();
  pipelineChart = new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Healthy',
          data: pipeline.map(d => toK(d.green)),
          backgroundColor: 'rgba(74,222,128,0.80)',
          borderRadius: 3,
          borderSkipped: false,
        },
        {
          label: 'At Risk',
          data: pipeline.map(d => toK(d.yellow)),
          backgroundColor: 'rgba(251,191,36,0.80)',
          borderRadius: 3,
          borderSkipped: false,
        },
        {
          label: 'Critical',
          data: pipeline.map(d => toK(d.red)),
          backgroundColor: 'rgba(248,113,113,0.90)',
          borderRadius: 3,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: ctx => ` ${ctx.dataset.label}: €${ctx.raw}k` },
        },
      },
      scales: {
        x: {
          stacked: true,
          grid: { display: false },
          ticks: { color: '#9b9792', font: { family: 'JetBrains Mono', size: 9 } },
          border: { color: '#232328' },
        },
        y: {
          stacked: true,
          grid: { color: '#232328' },
          ticks: { color: '#9b9792', font: { family: 'JetBrains Mono', size: 9 }, callback: v => `€${v}k` },
          border: { color: '#232328' },
        },
      },
      animation: { duration: 600 },
    },
  });
}

function renderRenewals(renewals) {
  const { fmtEur, fmtDays, healthDot, renewalClass } = window.App;
  const list = document.getElementById('renewals-list');
  const count = document.getElementById('renewals-count');
  if (!renewals || renewals.length === 0) {
    list.innerHTML = '<div class="empty-state">No at-risk renewals in the next 90 days.</div>';
    if (count) count.textContent = '0';
    return;
  }
  if (count) count.textContent = renewals.length;
  list.innerHTML = renewals.map(r => `
    <div class="renewal-row">
      <div class="renewal-name">${r.account_name}</div>
      <div>${healthDot(r.health_band)}</div>
      <div class="renewal-arr">${fmtEur(r.current_arr_eur)}</div>
      <div class="renewal-date">${r.renewal_date}</div>
      <div class="renewal-driver">${r.primary_risk_driver || '—'}</div>
      <div class="renewal-days ${renewalClass(r.days_to_renewal)}">${fmtDays(r.days_to_renewal)}</div>
    </div>
  `).join('');
}

function renderRiskMatrix(rows) {
  const { fmtEur, fmtDays, healthDot, renewalClass } = window.App;
  const tbody = document.getElementById('risk-matrix-body');
  const count = document.getElementById('risk-matrix-count');
  if (!rows || rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="loading-cell">No data.</td></tr>';
    return;
  }
  if (count) count.textContent = rows.length;
  tbody.innerHTML = rows.map(r => {
    const usagePct = r.usage_drop_ratio !== null && r.usage_drop_ratio !== undefined
      ? `${Math.round(r.usage_drop_ratio * 100)}%`
      : '—';
    return `
      <tr data-id="${r.account_id}" onclick="App.showView('accounts')">
        <td class="td-name">${r.account_name}</td>
        <td>${r.segment || '—'}</td>
        <td class="num td-mono">${fmtEur(r.current_arr_eur)}</td>
        <td>
          <div class="health-cell">
            ${healthDot(r.health_band)}
            <span class="health-band-text ${window.App.healthCls(r.health_band)}">${r.health_band || '—'}</span>
          </div>
        </td>
        <td class="num td-mono">${usagePct}</td>
        <td class="num td-mono">${r.tickets_high ?? 0}</td>
        <td style="color:var(--muted);font-size:0.75rem">${r.primary_risk_driver || '—'}</td>
        <td class="num td-mono renewal-days ${renewalClass(r.days_to_renewal)}">${fmtDays(r.days_to_renewal)}</td>
      </tr>
    `;
  }).join('');
}

window.loadPortfolio = loadPortfolio;

// Default view — start loading immediately when this script runs
loadPortfolio();
