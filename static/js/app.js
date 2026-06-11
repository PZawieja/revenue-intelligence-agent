// SPA shell — view switching, shared utilities

const VIEWS = ['portfolio', 'accounts', 'intelligence'];
let _initialized = { portfolio: true }; // portfolio self-starts in portfolio.js

function showView(name) {
  VIEWS.forEach(v => {
    const el = document.getElementById(`view-${v}`);
    const tab = document.querySelector(`[data-view="${v}"]`);
    if (el) el.hidden = (v !== name);
    if (el && v === name) el.classList.add('active');
    else if (el) el.classList.remove('active');
    if (tab) tab.classList.toggle('active', v === name);
  });

  if (!_initialized[name]) {
    _initialized[name] = true;
    if (name === 'portfolio' && window.loadPortfolio) window.loadPortfolio();
    if (name === 'accounts'  && window.loadAccounts)  window.loadAccounts();
    if (name === 'intelligence' && window.initIntelligence) window.initIntelligence();
  }
}

document.querySelectorAll('.nav-tab').forEach(btn => {
  btn.addEventListener('click', () => showView(btn.dataset.view));
});

// Shared helpers
function fmtEur(v) {
  if (!v && v !== 0) return '—';
  v = Math.round(v);
  if (v >= 1_000_000) return `€${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000)     return `€${(v / 1_000).toFixed(0)}k`;
  return `€${v}`;
}

function fmtDays(d) {
  if (d === null || d === undefined) return '—';
  if (d === 0) return 'Today';
  if (d === 1) return '1d';
  return `${d}d`;
}

function healthDot(band) {
  const cls = { green: 'dot-green', yellow: 'dot-yellow', red: 'dot-red' }[band] || 'dot-gray';
  return `<span class="dot ${cls}">●</span>`;
}

function healthCls(band) {
  return { green: 'dot-green', yellow: 'dot-yellow', red: 'dot-red' }[band] || 'dot-gray';
}

function renewalClass(days) {
  if (days === null || days === undefined) return '';
  if (days <= 14) return 'urgent';
  if (days <= 30) return 'soon';
  return '';
}

// Expose to other modules
window.App = { showView, fmtEur, fmtDays, healthDot, healthCls, renewalClass };

// portfolio.js calls loadPortfolio() directly when it loads.
// Nav tab clicks use showView() for lazy init of accounts + intelligence.
