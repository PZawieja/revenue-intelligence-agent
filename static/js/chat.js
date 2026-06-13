// Intelligence view — Piotr agent

let chatHistory = [];
let useAI = true;
let aiAvailable = false;
let accountHealthMap = {};

// ─── Initialisation ────────────────────────────────────────────────

async function initIntelligence() {
  setWelcomeGreeting();
  await Promise.all([
    loadAccountNames(),
    loadAIConfig(),
    loadSnapshot(),
  ]);
  wireInput();
  wireStarters();
  wireNewConversation();
}

function setWelcomeGreeting() {
  // sub-text is populated after snapshot loads with real account count
}

async function loadAccountNames() {
  try {
    const res = await fetch('/api/accounts/names');
    const names = await res.json();
    const sel = document.getElementById('chat-account-select');
    names.forEach(({ id, name, health }) => {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = name;
      if (health) opt.dataset.health = health;
      sel.appendChild(opt);
      if (health) accountHealthMap[id] = health;
    });
    if (window._chatPresetAccount) {
      sel.value = window._chatPresetAccount;
      window._chatPresetAccount = null;
      updateAccountDot();
      updateInputPlaceholder();
    }
    sel.addEventListener('change', () => {
      updateAccountDot();
      updateInputPlaceholder();
    });
  } catch (e) {
    console.error('Failed to load account names', e);
  }
}

async function loadAIConfig() {
  try {
    const res = await fetch('/api/chat/config');
    const cfg = await res.json();
    aiAvailable = cfg.ai_available;
  } catch (_) {
    aiAvailable = false;
  }

  const btn = document.getElementById('ai-toggle');
  if (!aiAvailable) {
    btn.disabled = true;
    btn.title = 'Set ANTHROPIC_API_KEY to enable AI mode';
    useAI = false;
  } else {
    const saved = localStorage.getItem('intel_use_ai');
    useAI = saved === null ? true : saved === 'true';
    applyAIToggle();
    btn.addEventListener('click', () => {
      useAI = !useAI;
      localStorage.setItem('intel_use_ai', String(useAI));
      applyAIToggle();
    });
  }
}

function applyAIToggle() {
  const btn = document.getElementById('ai-toggle');
  btn.classList.toggle('active', useAI);
  btn.setAttribute('aria-pressed', String(useAI));
}

async function loadSnapshot() {
  try {
    const res = await fetch('/api/chat/snapshot');
    const d = await res.json();

    const riskCard = document.getElementById('snap-risk');
    riskCard.classList.remove('snapshot-loading');
    riskCard.classList.add('danger');
    riskCard.querySelector('.snapshot-icon').textContent = '●';
    riskCard.querySelector('.snapshot-value').textContent = `${d.at_risk_count} accounts`;
    riskCard.querySelector('.snapshot-label').textContent = `${fmtEur(d.at_risk_arr)} ARR at Critical risk`;
    riskCard.addEventListener('click', () => sendMessage('Show ARR exposure by health band'));

    const renewCard = document.getElementById('snap-renewals');
    renewCard.classList.remove('snapshot-loading');
    renewCard.classList.toggle('warn', d.urgent_renewals > 0);
    renewCard.classList.toggle('good', d.urgent_renewals === 0);
    renewCard.querySelector('.snapshot-icon').textContent = '⊙';
    renewCard.querySelector('.snapshot-value').textContent = `${d.urgent_renewals} renewing`;
    const urgentLabel = d.urgent_account
      ? `within 30 days · ${d.urgent_account.split(' ').slice(0, 2).join(' ')} ${d.urgent_days}d`
      : 'within 30 days — urgent';
    renewCard.querySelector('.snapshot-label').textContent = urgentLabel;
    renewCard.addEventListener('click', () => sendMessage('Show renewals at risk in the next 30 days'));

    const expCard = document.getElementById('snap-expansion');
    expCard.classList.remove('snapshot-loading');
    expCard.classList.add('good');
    expCard.querySelector('.snapshot-icon').textContent = '↑';
    if (d.expansion_count > 0) {
      expCard.querySelector('.snapshot-value').textContent = `${d.expansion_count} candidates`;
      const topLabel = d.top_expansion_name
        ? `Top: ${d.top_expansion_name.split(' ').slice(0, 2).join(' ')} · ${(d.top_expansion_score || 0).toFixed(2)}`
        : 'Expansion opportunities ready';
      expCard.querySelector('.snapshot-label').textContent = topLabel;
    } else {
      expCard.querySelector('.snapshot-value').textContent = '—';
      expCard.querySelector('.snapshot-label').textContent = 'No expansion candidates';
    }
    expCard.addEventListener('click', () => sendMessage('Show expansion shortlist'));

    const subEl = document.getElementById('intel-welcome-sub');
    if (subEl) {
      const totalAccounts = (d.at_risk_count || 0) + (d.urgent_renewals !== undefined ? 50 : 0);
      subEl.textContent = `I've got your portfolio loaded — tell me what to look at first.`;
    }
  } catch (e) {
    console.error('Snapshot failed', e);
  }
}

function updateAccountDot() {
  const sel = document.getElementById('chat-account-select');
  const dot = document.getElementById('intel-account-dot');
  if (!sel.value) {
    dot.textContent = '○';
    dot.className = 'intel-account-dot';
    return;
  }
  const health = accountHealthMap[sel.value];
  const clsMap = { red: 'dot-red', yellow: 'dot-yellow', green: 'dot-green' };
  dot.textContent = '●';
  dot.className = `intel-account-dot ${clsMap[health] || 'dot-gray'}`;
}

function updateInputPlaceholder() {
  const sel = document.getElementById('chat-account-select');
  const input = document.getElementById('chat-input');
  if (sel.value) {
    const name = sel.options[sel.selectedIndex].textContent;
    input.placeholder = `Ask about ${name}…`;
  } else {
    input.placeholder = 'Ask about an account or your portfolio…';
  }
}

function wireInput() {
  const sendBtn = document.getElementById('chat-send');
  const input = document.getElementById('chat-input');

  sendBtn.addEventListener('click', () => sendMessage(input.value));
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input.value); }
    if (e.key === 'Escape') {
      document.getElementById('chat-account-select').value = '';
      updateAccountDot();
      updateInputPlaceholder();
    }
  });
  input.addEventListener('input', () => {
    sendBtn.classList.toggle('has-value', input.value.trim().length > 0);
  });
  document.getElementById('intel-clear-btn').addEventListener('click', () => {
    document.getElementById('chat-account-select').value = '';
    updateAccountDot();
    updateInputPlaceholder();
  });
}

function wireStarters() {
  document.querySelectorAll('.intel-starter').forEach(btn => {
    btn.addEventListener('click', () => sendMessage(btn.dataset.q));
  });
}

function wireNewConversation() {
  const btn = document.getElementById('intel-new-conv-btn');
  if (btn) btn.addEventListener('click', clearConversation);
}

function clearConversation() {
  chatHistory = [];
  const messages = document.getElementById('chat-messages');
  while (messages.children.length > 1) messages.removeChild(messages.lastChild);
  const welcome = document.getElementById('intel-welcome');
  if (welcome) welcome.style.display = '';
  const newConvBtn = document.getElementById('intel-new-conv-btn');
  if (newConvBtn) newConvBtn.style.display = 'none';
  document.getElementById('chat-input').focus();
}

// ─── Send ───────────────────────────────────────────────────────────

async function sendMessage(text) {
  if (!text || !text.trim()) return;

  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  input.value = '';
  sendBtn.disabled = true;
  sendBtn.classList.remove('has-value');

  const welcome = document.getElementById('intel-welcome');
  if (welcome) welcome.style.display = 'none';

  const newConvBtn = document.getElementById('intel-new-conv-btn');
  if (newConvBtn) newConvBtn.style.display = '';

  const messages = document.getElementById('chat-messages');
  messages.appendChild(userBubble(text));
  scrollToBottom();

  const accountId = document.getElementById('chat-account-select').value || null;
  const cardEl = createStreamCard();
  messages.appendChild(cardEl);
  scrollToBottom();

  chatHistory.push({ role: 'user', content: text });

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: text,
        account_id: accountId,
        history: chatHistory.slice(-6),
        use_ai: useAI,
      }),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.error) {
      finalizeCardError(cardEl, data.narrative || 'Unknown error');
    } else {
      setCardStatus(cardEl, data.status || 'Processing…');
      await typewriterNarrative(cardEl, data.narrative || '');
      finalizeCard(cardEl, data);
      chatHistory.push({ role: 'assistant', content: data.narrative || '' });
      if (chatHistory.length > 12) chatHistory = chatHistory.slice(-12);
    }
  } catch (err) {
    finalizeCardError(cardEl, 'Something went wrong — ' + err.message);
  }

  sendBtn.disabled = false;
  input.focus();
  scrollToBottom();
}

async function typewriterNarrative(cardEl, text) {
  const status = cardEl.querySelector('#_cstatus');
  const narrative = cardEl.querySelector('#_cnarrative');
  const textEl = cardEl.querySelector('#_cnarr-text');
  if (status) status.style.display = 'none';
  if (narrative) narrative.style.display = '';

  const CHAR_DELAY = 10;
  for (let i = 0; i < text.length; i++) {
    if (textEl) textEl.textContent += text[i];
    if (i % 8 === 0) scrollToBottom();
    await new Promise(r => setTimeout(r, CHAR_DELAY));
  }
}

// ─── Card Construction ──────────────────────────────────────────────

function createStreamCard() {
  const wrapper = document.createElement('div');
  wrapper.className = 'chat-message-ai';
  wrapper.innerHTML = `
    <div class="chat-card">
      <div class="chat-card-header">
        <div class="chat-card-agent">
          <span class="chat-card-agent-diamond">◆</span>
          <span>Piotr</span>
        </div>
        <div class="chat-card-dot dot-gray" id="_cdot">●</div>
        <div class="chat-card-title" id="_ctitle">Thinking…</div>
        <div class="chat-card-meta">
          <span class="chat-card-time">${nowHHMM()}</span>
        </div>
      </div>
      <div class="chat-card-body" id="_cbody">
        <div class="chat-status-bar" id="_cstatus" role="status" aria-live="polite">
          <div class="chat-status-spinner"></div>
          <span id="_cstatus-text">Processing…</span>
        </div>
        <div class="chat-narrative" id="_cnarrative" style="display:none">
          <span id="_cnarr-text"></span><span class="streaming-cursor" id="_ccursor"></span>
        </div>
      </div>
    </div>
  `;
  return wrapper;
}

function setCardStatus(wrapper, text) {
  const el = wrapper.querySelector('#_cstatus-text');
  if (el) el.textContent = text;
}

function finalizeCard(wrapper, data) {
  const cursor = wrapper.querySelector('#_ccursor');
  if (cursor) cursor.remove();

  const titleEl = wrapper.querySelector('#_ctitle');
  if (titleEl) titleEl.textContent = data.title || data.intent || 'Response';

  const dotEl = wrapper.querySelector('#_cdot');
  if (dotEl && data.rows && data.rows.length && data.rows[0].health_band) {
    const cls = { green: 'dot-green', yellow: 'dot-yellow', red: 'dot-red' }[data.rows[0].health_band] || 'dot-gray';
    dotEl.className = `chat-card-dot ${cls}`;
  }
  if (dotEl && !data.account_name) {
    dotEl.className = 'chat-card-dot';
    dotEl.style.color = 'var(--accent2)';
    dotEl.textContent = '◆';
  }

  const metaEl = wrapper.querySelector('.chat-card-meta');
  if (metaEl && data.intent) {
    const badge = document.createElement('span');
    badge.className = 'chat-card-intent';
    badge.textContent = data.intent.replace(/_/g, ' ');
    metaEl.prepend(badge);
  }

  const body = wrapper.querySelector('#_cbody');
  if (!body) return;

  if (data.bullets && data.bullets.length) {
    const bulletsDiv = document.createElement('div');
    bulletsDiv.className = 'chat-bullets';
    data.bullets.forEach(b => {
      const d = document.createElement('div');
      d.className = 'chat-bullet';
      d.textContent = b;
      bulletsDiv.appendChild(d);
    });
    body.appendChild(bulletsDiv);
  }

  const tableHtml = buildInlineTable(data.intent, data.rows || []);
  if (tableHtml) {
    const wrap = document.createElement('div');
    wrap.className = 'chat-inline-table';
    wrap.innerHTML = tableHtml;
    body.appendChild(wrap);
  }

  if (data.next_action) {
    const na = document.createElement('div');
    na.className = 'chat-next-action';
    na.innerHTML = `<span class="chat-next-label">// next action</span>${escHtml(data.next_action)}`;
    body.appendChild(na);
  }

  if (data.followups && data.followups.length) {
    const fups = document.createElement('div');
    fups.className = 'chat-followups';
    const label = document.createElement('span');
    label.className = 'chat-followups-label';
    label.textContent = '// continue exploring';
    fups.appendChild(label);
    const chips = document.createElement('div');
    chips.className = 'chat-followups-chips';
    data.followups.forEach(q => {
      const btn = document.createElement('button');
      btn.className = 'followup-chip';
      btn.textContent = q;
      btn.addEventListener('click', () => sendMessage(q));
      chips.appendChild(btn);
    });
    fups.appendChild(chips);
    body.appendChild(fups);
  }

  if (data.evidence && data.evidence.sql) {
    const card = wrapper.querySelector('.chat-card');
    card.appendChild(buildEvidence(data.evidence));
  }
}

function finalizeCardError(wrapper, msg) {
  const card = wrapper.querySelector('.chat-card');
  if (card) card.classList.add('chat-card-error');
  const cursor = wrapper.querySelector('#_ccursor');
  if (cursor) cursor.remove();
  const status = wrapper.querySelector('#_cstatus');
  if (status) status.remove();
  const narrative = wrapper.querySelector('#_cnarrative');
  if (narrative) { narrative.style.display = ''; }
  const txt = wrapper.querySelector('#_cnarr-text');
  if (txt) txt.textContent = msg;
  const titleEl = wrapper.querySelector('#_ctitle');
  if (titleEl) titleEl.textContent = 'Error';
}

// ─── Inline tables ──────────────────────────────────────────────────

function buildInlineTable(intent, rows) {
  if (!rows || rows.length < 2) return '';
  if (intent === 'renewals_at_risk') return renewalsTable(rows);
  if (intent === 'expansion_shortlist') return expansionTable(rows);
  if (intent === 'arr_exposure_overview') return arrBandsTable(rows);
  return '';
}

function renewalsTable(rows) {
  const head = `<thead><tr>
    <th>Account</th>
    <th class="num">ARR</th>
    <th class="num">Days</th>
    <th>Health</th>
    <th>Risk driver</th>
  </tr></thead>`;
  const body = rows.slice(0, 8).map(r => {
    const daysClass = (r.days_to_renewal <= 14) ? 'urgent' : (r.days_to_renewal <= 30 ? 'soon' : '');
    const pill = healthPill(r.health_band);
    return `<tr>
      <td class="td-name">${escHtml(r.account_name || '—')}</td>
      <td class="num">${fmtEur(r.current_arr_eur)}</td>
      <td class="num" style="color:${daysClass==='urgent'?'var(--red)':daysClass==='soon'?'var(--yellow)':'inherit'}">${r.days_to_renewal != null ? r.days_to_renewal + 'd' : '—'}</td>
      <td class="td-health">${pill}</td>
      <td style="color:var(--muted);font-size:0.68rem">${escHtml((r.primary_risk_driver || '').replace(/_/g, ' '))}</td>
    </tr>`;
  }).join('');
  return `<table class="inline-table">${head}<tbody>${body}</tbody></table>`;
}

function expansionTable(rows) {
  const head = `<thead><tr>
    <th>Account</th>
    <th class="num">ARR</th>
    <th class="num">Score</th>
    <th>Angle</th>
  </tr></thead>`;
  const body = rows.slice(0, 8).map(r => {
    const score = r.expansion_score != null ? r.expansion_score.toFixed(2) : '—';
    return `<tr>
      <td class="td-name">${escHtml(r.account_name || '—')}</td>
      <td class="num">${fmtEur(r.current_arr_eur)}</td>
      <td class="num" style="color:var(--green)">${score}</td>
      <td style="color:var(--muted);font-size:0.68rem">${escHtml((r.recommended_angle || '').replace(/_/g, ' '))}</td>
    </tr>`;
  }).join('');
  return `<table class="inline-table">${head}<tbody>${body}</tbody></table>`;
}

function arrBandsTable(rows) {
  const head = `<thead><tr>
    <th>Health band</th>
    <th class="num">ARR</th>
    <th class="num">Accounts</th>
  </tr></thead>`;
  const body = rows.map(r => {
    const pill = healthPill(r.health_band);
    return `<tr>
      <td>${pill}</td>
      <td class="num">${fmtEur(r.arr_eur)}</td>
      <td class="num">${r.accounts_count}</td>
    </tr>`;
  }).join('');
  return `<table class="inline-table">${head}<tbody>${body}</tbody></table>`;
}

function healthPill(band) {
  const labels = { red: 'Critical', yellow: 'Warning', green: 'Healthy' };
  const cls = { red: 'pill-red', yellow: 'pill-yellow', green: 'pill-green' }[band] || '';
  return `<span class="pill ${cls}"><span class="pill-dot">●</span>${labels[band] || band}</span>`;
}

// ─── Evidence accordion ─────────────────────────────────────────────

function buildEvidence(ev) {
  if (!ev || !ev.sql) return document.createDocumentFragment();
  const g = ev.guardrails || {};
  const badges = [
    { label: 'SELECT-only', ok: g.select_only },
    { label: 'Allowlisted',  ok: g.allowlisted_assets },
    { label: 'No PII',       ok: g.no_pii_columns },
    { label: 'Row limit',    ok: g.row_limit_present },
  ].map(b => `<span class="guardrail-badge ${b.ok ? 'guardrail-ok' : 'guardrail-warn'}">${b.label} ${b.ok ? '✓' : '✗'}</span>`).join('');

  const div = document.createElement('div');
  div.className = 'chat-evidence';
  div.innerHTML = `
    <button class="evidence-toggle" onclick="toggleEvidence(this)" aria-expanded="false" aria-label="Show SQL evidence">
      <span class="evidence-arrow">▶</span>
      Evidence — SQL · Guardrails
    </button>
    <div class="evidence-body" hidden>
      <div class="guardrail-row">${badges}</div>
      <div class="evidence-sql-wrap">
        <button class="sql-copy-btn" onclick="copySQL(this)" data-sql="${escAttr(ev.sql)}">Copy</button>
        <pre class="evidence-sql">${escHtml(ev.sql)}</pre>
      </div>
    </div>
  `;
  return div;
}

function toggleEvidence(btn) {
  const body = btn.nextElementSibling;
  const arrow = btn.querySelector('.evidence-arrow');
  const isOpen = !body.hidden;
  body.hidden = isOpen;
  arrow.classList.toggle('open', !isOpen);
  btn.setAttribute('aria-expanded', String(!isOpen));
}
window.toggleEvidence = toggleEvidence;

function copySQL(btn) {
  const sql = btn.dataset.sql;
  navigator.clipboard.writeText(sql).then(() => {
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 1500);
  });
}
window.copySQL = copySQL;

// ─── User bubble ────────────────────────────────────────────────────

function userBubble(text) {
  const el = document.createElement('div');
  el.className = 'chat-message-user';
  el.innerHTML = `<div class="chat-bubble-user">${escHtml(text)}</div>`;
  return el;
}

// ─── Helpers ────────────────────────────────────────────────────────

function fmtEur(v) {
  if (!v && v !== 0) return '—';
  v = Math.round(v);
  if (v >= 1_000_000) return `€${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000)     return `€${(v / 1_000).toFixed(0)}k`;
  return `€${v}`;
}

function nowHHMM() {
  const d = new Date();
  return d.getHours().toString().padStart(2, '0') + ':' + d.getMinutes().toString().padStart(2, '0');
}

function escHtml(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function escAttr(s) {
  return String(s || '').replace(/"/g, '&quot;');
}

function scrollToBottom() {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;
  const nearBottom = msgs.scrollHeight - msgs.scrollTop - msgs.clientHeight < 200;
  if (nearBottom) msgs.scrollTop = msgs.scrollHeight;
}

window.initIntelligence = initIntelligence;
