// Accounts view — table, filter/search, drilldown panel

let allAccounts = [];
let sparklineChart = null;
let selectedAccountId = null;

async function loadAccounts() {
  let rows;
  try {
    const res = await fetch('/api/accounts');
    rows = await res.json();
  } catch (e) {
    console.error('Accounts load failed', e);
    return;
  }
  allAccounts = rows;
  renderAccountsTable(rows);

  const badge = document.getElementById('nav-account-count');
  if (badge) badge.textContent = `${rows.length} accounts`;
}

function renderAccountsTable(rows) {
  const { fmtEur, fmtDays, healthDot, renewalClass } = window.App;
  const tbody = document.getElementById('accounts-tbody');
  const countEl = document.getElementById('accounts-count');

  if (countEl) countEl.textContent = `${rows.length} accounts`;

  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">No accounts match filter.</td></tr>';
    return;
  }

  tbody.innerHTML = rows.map(r => `
    <tr data-id="${r.account_id}" class="${r.account_id === selectedAccountId ? 'selected' : ''}">
      <td class="td-name">${r.account_name}</td>
      <td style="color:var(--muted)">${r.segment}</td>
      <td class="num td-mono">${fmtEur(r.current_arr_eur)}</td>
      <td>
        <div class="health-cell">
          ${healthDot(r.health_band)}
          <span class="health-band-text ${window.App.healthCls(r.health_band)}">${r.health_band || '—'}</span>
        </div>
      </td>
      <td class="num td-mono renewal-days ${renewalClass(r.days_to_renewal)}">${fmtDays(r.days_to_renewal)}</td>
      <td style="color:var(--dim);font-size:0.75rem;font-family:var(--mono)">${r.owner_ae || '—'}</td>
    </tr>
  `).join('');

  tbody.querySelectorAll('tr').forEach(row => {
    row.addEventListener('click', () => openPanel(row.dataset.id));
  });
}

async function openPanel(accountId) {
  selectedAccountId = accountId;

  // Mark selected row
  document.querySelectorAll('#accounts-tbody tr').forEach(r => {
    r.classList.toggle('selected', r.dataset.id === accountId);
  });

  const panel = document.getElementById('account-panel');
  panel.hidden = false;

  // Fetch account detail
  let detail;
  try {
    const res = await fetch(`/api/accounts/${accountId}`);
    detail = await res.json();
  } catch (e) {
    console.error('Account detail failed', e);
    return;
  }

  const { fmtEur, fmtDays, healthDot, healthCls } = window.App;
  const { overview, health, expansion, usage_trend, primary_risk_driver } = detail;

  // Header
  const dot = document.getElementById('panel-health-dot');
  dot.textContent = '●';
  dot.className = `panel-health-dot ${healthCls(health?.health_band)}`;

  document.getElementById('panel-name').textContent = overview?.account_name || '—';
  document.getElementById('panel-meta').textContent =
    `${overview?.segment || ''} · ${overview?.country || ''} · ${overview?.plan || ''} plan`;

  // KPI grid
  document.getElementById('panel-arr').textContent = fmtEur(overview?.current_arr_eur);
  document.getElementById('panel-score').textContent = health?.health_score !== undefined
    ? health.health_score.toFixed(2) : '—';
  document.getElementById('panel-renews').textContent = fmtDays(health?.days_to_renewal);
  document.getElementById('panel-util').textContent = expansion?.seat_utilization_ratio !== undefined
    ? `${Math.round(expansion.seat_utilization_ratio * 100)}%` : '—';

  // Sparkline
  renderSparkline(usage_trend || []);

  // Signals
  renderSignals(health, primary_risk_driver);

  // Expansion
  const expEl = document.getElementById('panel-expansion');
  if (expansion) {
    expEl.innerHTML = `
      <div class="exp-score">${expansion.expansion_score?.toFixed(2) || '—'}
        <span style="font-size:0.75rem;color:var(--muted);font-weight:400"> expansion score</span>
      </div>
      <div class="exp-angle">${expansion.expansion_band || '—'} — ${expansion.recommended_angle || ''}</div>
    `;
  } else {
    expEl.textContent = '—';
  }

  // "Ask Intelligence" button wiring
  document.getElementById('btn-ask-account').onclick = () => {
    window._chatPresetAccount = accountId;
    window.App.showView('intelligence');
    const sel = document.getElementById('chat-account-select');
    if (sel) sel.value = accountId;
  };
}

function renderSparkline(trend) {
  const wrap = document.querySelector('.sparkline-wrap');
  const caption = document.getElementById('sparkline-caption');

  if (!trend || trend.length === 0) {
    if (wrap) wrap.innerHTML = '<canvas id="sparkline-chart" height="60"></canvas>';
    if (caption) caption.textContent = 'No usage data';
    return;
  }

  // Re-create canvas to avoid Chart.js reuse error
  if (wrap) wrap.innerHTML = '<canvas id="sparkline-chart" height="60"></canvas>';
  const ctx = document.getElementById('sparkline-chart').getContext('2d');

  const values = trend.map(p => p.active_users);
  const maxVal = Math.max(...values);
  const minVal = Math.min(...values);
  const dropPct = maxVal > 0 ? Math.round((1 - minVal / maxVal) * 100) : 0;

  if (sparklineChart) { try { sparklineChart.destroy(); } catch(e){} }

  sparklineChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: trend.map(p => p.date_day),
      datasets: [{
        data: values,
        borderColor: dropPct > 30 ? '#f87171' : dropPct > 10 ? '#fbbf24' : '#4ade80',
        borderWidth: 1.5,
        pointRadius: 2,
        pointHoverRadius: 4,
        fill: true,
        backgroundColor: dropPct > 30
          ? 'rgba(248,113,113,0.07)'
          : dropPct > 10 ? 'rgba(251,191,36,0.07)' : 'rgba(74,222,128,0.07)',
        tension: 0.35,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: {
        callbacks: { label: ctx => ` ${ctx.raw} users` },
        bodyFont: { family: 'JetBrains Mono', size: 11 },
      }},
      scales: { x: { display: false }, y: { display: false } },
      animation: { duration: 400 },
    },
  });

  if (caption) {
    if (dropPct > 0) {
      caption.textContent = `↓ ${dropPct}% drop from peak (${maxVal} → ${minVal} users)`;
      caption.style.color = dropPct > 30 ? 'var(--red)' : 'var(--yellow)';
    } else {
      caption.textContent = `↑ Stable — ${maxVal} peak users`;
      caption.style.color = 'var(--green)';
    }
  }
}

function renderSignals(health, primaryRisk) {
  const signals = document.getElementById('panel-signals');
  if (!health) { signals.innerHTML = '<div class="empty-state">No health data</div>'; return; }

  const items = [];

  const drop = health.usage_drop_ratio;
  if (drop >= 0.3) {
    items.push({ dot: 'dot-red', text: `Usage dropped ${Math.round(drop * 100)}% from peak` });
  } else if (drop >= 0.1) {
    items.push({ dot: 'dot-yellow', text: `Usage down ${Math.round(drop * 100)}% from peak` });
  } else {
    items.push({ dot: 'dot-green', text: 'Usage stable / growing' });
  }

  if (health.tickets_high > 0) {
    items.push({ dot: 'dot-red', text: `${health.tickets_high} high-severity ticket${health.tickets_high > 1 ? 's' : ''} open` });
  } else {
    items.push({ dot: 'dot-green', text: 'No high-severity tickets' });
  }

  if (health.unpaid_invoices > 0) {
    items.push({ dot: 'dot-red', text: `${health.unpaid_invoices} unpaid invoice${health.unpaid_invoices > 1 ? 's' : ''}` });
  } else {
    items.push({ dot: 'dot-green', text: 'All invoices paid' });
  }

  const dtr = health.days_to_renewal;
  if (dtr !== null && dtr !== undefined) {
    const cls = dtr <= 14 ? 'dot-red' : dtr <= 60 ? 'dot-yellow' : 'dot-green';
    items.push({ dot: cls, text: `Renewal in ${dtr} days` });
  }

  signals.innerHTML = items.map(s => `
    <div class="panel-signal">
      <span class="signal-dot ${s.dot}">●</span>
      <span>${s.text}</span>
    </div>
  `).join('');
}

function filterAccounts() {
  const q = document.getElementById('account-search').value.toLowerCase();
  const seg = document.getElementById('filter-segment').value;
  const health = document.getElementById('filter-health').value;

  const filtered = allAccounts.filter(r => {
    const matchQ = !q || r.account_name.toLowerCase().includes(q);
    const matchSeg = !seg || r.segment === seg;
    const matchHealth = !health || r.health_band === health;
    return matchQ && matchSeg && matchHealth;
  });

  renderAccountsTable(filtered);
}

// Wire filters
document.getElementById('account-search').addEventListener('input', filterAccounts);
document.getElementById('filter-segment').addEventListener('change', filterAccounts);
document.getElementById('filter-health').addEventListener('change', filterAccounts);

document.getElementById('panel-close').addEventListener('click', () => {
  document.getElementById('account-panel').hidden = true;
  selectedAccountId = null;
  document.querySelectorAll('#accounts-tbody tr').forEach(r => r.classList.remove('selected'));
});

window.loadAccounts = loadAccounts;
window.openAccountPanel = openPanel;
