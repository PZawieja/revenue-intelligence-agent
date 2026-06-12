// Intelligence view — chat, intent cards, evidence accordion

let chatAccountNames = [];

async function initIntelligence() {
  try {
    const res = await fetch('/api/accounts/names');
    const names = await res.json();
    chatAccountNames = names;

    const sel = document.getElementById('chat-account-select');
    names.forEach(({ id, name }) => {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = name;
      sel.appendChild(opt);
    });

    // Pre-select from accounts panel if set
    if (window._chatPresetAccount) {
      sel.value = window._chatPresetAccount;
      window._chatPresetAccount = null;
    }
  } catch (e) {
    console.error('Failed to load account names', e);
  }
}

async function sendMessage(text) {
  if (!text.trim()) return;

  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  input.value = '';
  sendBtn.disabled = true;

  // Hide welcome screen after first message
  const welcome = document.querySelector('.chat-welcome');
  if (welcome) welcome.style.display = 'none';

  const messages = document.getElementById('chat-messages');

  // Add user bubble
  messages.appendChild(userBubble(text));

  // Add typing indicator
  const typingEl = typingIndicator();
  messages.appendChild(typingEl);
  scrollToBottom();

  const accountId = document.getElementById('chat-account-select').value || null;

  let data;
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text, account_id: accountId }),
    });
    data = await res.json();
  } catch (e) {
    data = { error: 'Network error — is the server running?' };
  }

  typingEl.remove();

  if (data.error) {
    messages.appendChild(errorCard(data.error));
  } else {
    messages.appendChild(responseCard(data));
  }

  sendBtn.disabled = false;
  scrollToBottom();
}

function userBubble(text) {
  const el = document.createElement('div');
  el.className = 'chat-message-user';
  el.innerHTML = `<div class="chat-bubble-user">${escHtml(text)}</div>`;
  return el;
}

function typingIndicator() {
  const el = document.createElement('div');
  el.className = 'chat-typing';
  el.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
  return el;
}

function errorCard(msg) {
  const el = document.createElement('div');
  el.className = 'chat-message-ai';
  el.innerHTML = `
    <div class="chat-card">
      <div class="chat-card-body">
        <div class="chat-narrative" style="color:var(--red)">${escHtml(msg)}</div>
      </div>
    </div>
  `;
  return el;
}

function responseCard(d) {
  const { healthDot } = window.App;

  const bandDot = d.account_name
    ? `<span class="chat-card-dot ${bandFromScore(d)}">${'●'}</span>`
    : `<span class="chat-card-dot" style="color:var(--accent2)">◆</span>`;

  const bulletsHtml = (d.bullets || []).map(b =>
    `<div class="chat-bullet">${escHtml(b)}</div>`
  ).join('');

  const nextActionHtml = d.next_action ? `
    <div class="chat-next-action">
      <div class="chat-next-label">// next action</div>
      ${escHtml(d.next_action)}
    </div>
  ` : '';

  const followupsHtml = (d.followups || []).length ? `
    <div class="chat-followups">
      ${d.followups.map(q => `<button class="followup-chip" data-q="${escAttr(q)}">${escHtml(q)}</button>`).join('')}
    </div>
  ` : '';

  const evidenceHtml = buildEvidence(d.evidence);

  const el = document.createElement('div');
  el.className = 'chat-message-ai';
  el.innerHTML = `
    <div class="chat-card">
      <div class="chat-card-header">
        ${bandDot}
        <div class="chat-card-title">${escHtml(d.title || d.intent)}</div>
        <div class="chat-card-intent">${escHtml(d.intent || '')}</div>
      </div>
      <div class="chat-card-body">
        <div class="chat-narrative">${escHtml(d.narrative || '')}</div>
        ${bulletsHtml ? `<div class="chat-bullets">${bulletsHtml}</div>` : ''}
        ${nextActionHtml}
        ${followupsHtml}
      </div>
      ${evidenceHtml}
    </div>
  `;

  // Wire follow-up chips
  el.querySelectorAll('.followup-chip').forEach(btn => {
    btn.addEventListener('click', () => sendMessage(btn.dataset.q));
  });

  return el;
}

function buildEvidence(ev) {
  if (!ev || !ev.sql) return '';
  const g = ev.guardrails || {};
  const badges = [
    { label: 'SELECT-only', ok: g.select_only },
    { label: 'Allowlisted',  ok: g.allowlisted_assets },
    { label: 'No PII',       ok: g.no_pii_columns },
    { label: 'Row limit',    ok: g.row_limit_present },
  ].map(b => `<span class="guardrail-badge ${b.ok ? 'guardrail-ok' : 'guardrail-warn'}">${b.label} ${b.ok ? '✓' : '✗'}</span>`).join('');

  return `
    <div class="chat-evidence">
      <button class="evidence-toggle" onclick="toggleEvidence(this)">
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
    </div>
  `;
}

function toggleEvidence(btn) {
  const body = btn.nextElementSibling;
  const arrow = btn.querySelector('.evidence-arrow');
  const isOpen = !body.hidden;
  body.hidden = isOpen;
  arrow.classList.toggle('open', !isOpen);
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

function bandFromScore(d) {
  // Try to derive band from title or rows
  if (!d.rows || !d.rows.length) return 'dot-gray';
  const row = d.rows[0];
  if (row.health_band) return { green: 'dot-green', yellow: 'dot-yellow', red: 'dot-red' }[row.health_band] || 'dot-gray';
  return 'dot-gray';
}

function scrollToBottom() {
  const msgs = document.getElementById('chat-messages');
  msgs.scrollTop = msgs.scrollHeight;
}

function escHtml(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(s) {
  return String(s || '').replace(/"/g,'&quot;');
}

// Event wiring
document.getElementById('chat-send').addEventListener('click', () => {
  sendMessage(document.getElementById('chat-input').value);
});
document.getElementById('chat-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(e.target.value); }
});
document.querySelectorAll('.chat-starter').forEach(btn => {
  btn.addEventListener('click', () => sendMessage(btn.dataset.q));
});

window.initIntelligence = initIntelligence;
