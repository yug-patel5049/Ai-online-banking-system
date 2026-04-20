const API = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://127.0.0.1:5000"
  : "https://ai-online-banking-system.onrender.com";
let accounts = [];

// ── Auth guard — runs AFTER DOM is ready ──────────────────────────────────────
function getToken() {
  return localStorage.getItem("token");
}

function authHeaders() {
  return { "Content-Type": "application/json", "Authorization": `Bearer ${getToken()}` };
}

async function apiFetch(url, opts = {}) {
  opts.headers = { ...authHeaders(), ...(opts.headers || {}) };
  try {
    const res = await fetch(API + url, opts);
    if (res.status === 401) {
      // Only redirect if it's not the initial load check
      localStorage.clear();
      location.href = "index.html";
      return res;
    }
    return res;
  } catch (err) {
    console.error("Network error:", err);
    throw err;
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", async () => {
  // Auth guard runs here — after DOM is ready and localStorage is accessible
  const token = getToken();
  if (!token) {
    location.href = "index.html";
    return;  // stop execution
  }

  const name = localStorage.getItem("name") || "User";
  document.getElementById("sbName").textContent = name;
  document.getElementById("av").textContent = name[0].toUpperCase();
  await refresh();
});

async function refresh() {
  await loadAccounts();
  await loadDashboard();
}

// ── Navigation ────────────────────────────────────────────────────────────────
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const page = btn.dataset.page;
    document.getElementById(`page-${page}`).classList.add("active");
    if (page === "transfer") fillSelect("tFrom");
    if (page === "history") fillSelect("hAccSel");
    if (page === "ai") { fillSelect("aiAccSel"); if (accounts.length) loadInsights(); }
  });
});

// ── Accounts ──────────────────────────────────────────────────────────────────
async function loadAccounts() {
  const res = await apiFetch("/api/accounts");
  accounts = res.ok ? await res.json() : [];
  fillSelect("dAcc");
  fillSelect("wAcc");
  renderAccounts();
}

function fillSelect(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = accounts.map(a =>
    `<option value="${a.account_number}">${a.account_type} ••${a.account_number.slice(-4)} — ₹${fmt(a.balance)}</option>`
  ).join("") || `<option value="">No accounts</option>`;
}

function renderAccounts() {
  const el = document.getElementById("accList");
  if (!el) return;
  el.innerHTML = accounts.length
    ? accounts.map(a => `
      <div class="bank-card">
        <div class="bc-type">${a.account_type} Account</div>
        <div class="bc-num">•••• •••• ${a.account_number.slice(-4)}</div>
        <div class="bc-lbl">Available Balance</div>
        <div class="bc-bal">₹${fmt(a.balance)}</div>
      </div>`).join("")
    : `<p class="empty">No accounts yet.</p>`;
}

async function doNewAccount() {
  const type = document.getElementById("newAccType").value;
  const res = await apiFetch("/api/accounts", {
    method: "POST", body: JSON.stringify({ account_type: type })
  });
  if (res.ok) { closeModal("mNewAcc"); await refresh(); }
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
async function loadDashboard() {
  const total = accounts.reduce((s, a) => s + a.balance, 0);
  document.getElementById("sTotalBal").textContent = `₹${fmt(total)}`;
  document.getElementById("sAccCount").textContent = accounts.length;

  let cr = 0, db = 0;
  const all = [];
  for (const a of accounts) {
    const res = await apiFetch(`/api/transactions/${a.account_number}`);
    if (res.ok) {
      const txns = await res.json();
      txns.forEach(t => {
        if (t.type === "credit") cr += t.amount; else db += t.amount;
        all.push(t);
      });
    }
  }
  document.getElementById("sTotalCr").textContent = `₹${fmt(cr)}`;
  document.getElementById("sTotalDb").textContent = `₹${fmt(db)}`;
  all.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  renderTxns("recentTxns", all.slice(0, 10));
}

// ── Transactions ──────────────────────────────────────────────────────────────
async function loadHistory() {
  const acc = document.getElementById("hAccSel").value;
  if (!acc) return;
  const res = await apiFetch(`/api/transactions/${acc}`);
  const txns = res.ok ? await res.json() : [];
  renderTxns("histTxns", txns);
}

function renderTxns(id, txns) {
  const el = document.getElementById(id);
  if (!txns.length) { el.innerHTML = `<li class="empty">No transactions found.</li>`; return; }
  el.innerHTML = txns.map(t => `
    <li class="txn-row">
      <div class="txn-ic ${t.type}">${t.type === "credit" ? "⬇️" : "⬆️"}</div>
      <div class="txn-info">
        <div class="txn-desc">${esc(t.description)}</div>
        <div class="txn-date">${fmtDate(t.created_at)}</div>
      </div>
      <div>
        <div class="txn-amt ${t.type}">${t.type === "credit" ? "+" : "−"}₹${fmt(t.amount)}</div>
        <div class="txn-bal">Bal: ₹${fmt(t.balance_after)}</div>
      </div>
    </li>`).join("");
}

// ── Deposit ───────────────────────────────────────────────────────────────────
async function doDeposit() {
  const errEl = document.getElementById("dErr");
  errEl.style.display = "none";
  const res = await apiFetch("/api/deposit", {
    method: "POST",
    body: JSON.stringify({
      account_number: document.getElementById("dAcc").value,
      amount: document.getElementById("dAmt").value,
      description: document.getElementById("dDesc").value || "Deposit"
    })
  });
  const d = await res.json();
  if (res.ok) { closeModal("mDeposit"); await refresh(); }
  else { errEl.textContent = d.error; errEl.style.display = "block"; }
}

// ── Withdraw ──────────────────────────────────────────────────────────────────
async function doWithdraw() {
  const errEl = document.getElementById("wErr");
  errEl.style.display = "none";
  const res = await apiFetch("/api/withdraw", {
    method: "POST",
    body: JSON.stringify({
      account_number: document.getElementById("wAcc").value,
      amount: document.getElementById("wAmt").value,
      description: document.getElementById("wDesc").value || "Withdrawal"
    })
  });
  const d = await res.json();
  if (res.ok) { closeModal("mWithdraw"); await refresh(); }
  else { errEl.textContent = d.error; errEl.style.display = "block"; }
}

// ── Transfer ──────────────────────────────────────────────────────────────────
async function doTransfer() {
  const errEl = document.getElementById("tErr"), okEl = document.getElementById("tOk");
  errEl.style.display = okEl.style.display = "none";
  const res = await apiFetch("/api/transfer", {
    method: "POST",
    body: JSON.stringify({
      from_account: document.getElementById("tFrom").value,
      to_account: document.getElementById("tTo").value,
      amount: document.getElementById("tAmt").value
    })
  });
  const d = await res.json();
  if (res.ok) {
    okEl.textContent = `Transfer successful! New balance: ₹${fmt(d.balance)}`;
    okEl.style.display = "block";
    await refresh();
  } else { errEl.textContent = d.error; errEl.style.display = "block"; }
}

// ── AI Insights ───────────────────────────────────────────────────────────────
async function loadInsights() {
  const acc = document.getElementById("aiAccSel").value;
  if (!acc) return;
  const res = await apiFetch(`/api/ai/insights/${acc}`);
  if (!res.ok) return;
  const { analysis, savings_advice, fraud } = await res.json();

  let html = `<span class="risk-badge risk-${fraud.risk}">🛡️ Fraud Risk: ${fraud.risk.toUpperCase()}</span>`;
  fraud.alerts.forEach(a => html += insight("b-alert", "⚠️ Alert", a));
  (analysis.insights || []).forEach(i => html += insight("b-info", "📊 Insight", i));
  (analysis.tips || []).forEach(t => html += insight("b-tip", "💡 Tip", t));
  (savings_advice || []).forEach(s => html += insight("b-warn", "🏦 Advice", s));
  html += `<div style="margin-top:14px;padding:12px;background:var(--bg);border-radius:8px;font-size:12px;color:var(--muted)">
    Spent ₹${fmt(analysis.total_spent)} · Earned ₹${fmt(analysis.total_earned)} · Avg ₹${fmt(analysis.avg_transaction)} · ${analysis.transaction_count} transactions
  </div>`;
  document.getElementById("aiOut").innerHTML = html;
}

function insight(cls, label, text) {
  return `<div class="insight"><span class="badge ${cls}">${label}</span>${esc(text)}</div>`;
}

// ── AI Chat ───────────────────────────────────────────────────────────────────
async function sendChat() {
  const inp = document.getElementById("chatIn");
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = "";
  addBubble("user", msg);
  const res = await apiFetch("/api/ai/chat", {
    method: "POST", body: JSON.stringify({ message: msg })
  });
  const d = await res.json();
  addBubble("bot", d.reply || "Sorry, I couldn't process that.");
}

function addBubble(role, text) {
  const c = document.getElementById("chatMsgs");
  c.innerHTML += `<div class="msg ${role}"><div class="bubble">${esc(text)}</div></div>`;
  c.scrollTop = c.scrollHeight;
}

// ── Modals ────────────────────────────────────────────────────────────────────
function openModal(id) { document.getElementById(id).classList.add("open"); }
function closeModal(id) { document.getElementById(id).classList.remove("open"); }
document.querySelectorAll(".overlay").forEach(o =>
  o.addEventListener("click", e => { if (e.target === o) o.classList.remove("open"); })
);

// ── Logout ────────────────────────────────────────────────────────────────────
function logout() { localStorage.clear(); location.href = "index.html"; }

// ── Utils ─────────────────────────────────────────────────────────────────────
function fmt(n) { return Number(n).toLocaleString("en-IN", {minimumFractionDigits:2, maximumFractionDigits:2}); }
function fmtDate(s) { return new Date(s).toLocaleString("en-IN", {dateStyle:"medium", timeStyle:"short"}); }
function esc(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
