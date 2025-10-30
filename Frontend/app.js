const API = "http://127.0.0.1:8010";
let current = null;

const list = document.getElementById("list");
const convTitle = document.getElementById("convTitle");
const msgs = document.getElementById("msgs");
const input = document.getElementById("input");
const sendBtn = document.getElementById("sendBtn");
const renameBtn = document.getElementById("renameBtn");
const deleteBtn = document.getElementById("deleteBtn");

function setComposerEnabled(on) {
  input.disabled = !on;
  sendBtn.disabled = !on;
}
function setActionButtonsEnabled(on) {
  renameBtn.disabled = !on;
  deleteBtn.disabled = !on;
}
function toast(msg) {
  console.log("[UI]", msg);
}

window.onerror = (m, f, l, c, e) => {
  console.error("JS erro:", m, f, l, c, e);
};
async function api(path, opts = {}) {
  const r = await fetch(API + path, opts).catch(e => {
    throw new Error("Falha de rede/CORS: " + e.message);
  });
  if (!r.ok) {
    const t = await r.text().catch(() => "");
    throw new Error(`HTTP ${r.status} ${r.statusText} | ${t}`);
  }
  return r.json();
}

(async () => {
  try { await api("/ping"); }
  catch (e) { toast("Backend inacessível: " + e.message); }
})();


async function loadConversations(selectId = null) {
  try {
    const data = await api("/conversations");
    list.innerHTML = "";
    data.forEach(c => {
      const div = document.createElement("div");
      div.className = "conv" + (current && current.id === c.id ? " active" : "");
      div.textContent = c.title;
      div.dataset.id = c.id;   
      div.onclick = () => selectConversation(c);
      list.appendChild(div);
    });

    if (selectId) {
      const found = data.find(x => x.id === selectId);
      if (found) await selectConversation(found);
    } else if (current) {
      const keep = data.find(x => x.id === current.id);
      if (keep) await selectConversation(keep);
    } else if (data.length) {
      await selectConversation(data[0]);
    } else {
      current = null;
      convTitle.textContent = "Selecione uma conversa";
      msgs.innerHTML = '<div class="empty">Sem conversa selecionada.</div>';
      setComposerEnabled(false);
      setActionButtonsEnabled(false);
    }
  } catch (e) {
    setComposerEnabled(false);
    setActionButtonsEnabled(false);
    toast("Erro ao listar conversas: " + e.message);
  }
}

async function selectConversation(c) {
  current = c;
  convTitle.textContent = c.title;

  [...document.querySelectorAll(".conv")].forEach(el => {
    el.classList.toggle("active", Number(el.dataset.id) === c.id);
  });

  setComposerEnabled(true);
  setActionButtonsEnabled(true);
  await loadMessages();
}

async function loadMessages() {
  if (!current) return;
  try {
    const data = await api(`/conversations/${current.id}/messages`);
    msgs.innerHTML = "";
    if (!data.length) {
      msgs.innerHTML = '<div class="empty">Sem mensagens ainda.</div>';
      return;
    }
    data.forEach(m => {
      const div = document.createElement("div");
      div.className = "bubble " + (m.role === "user" ? "user" : "assistant");
      div.textContent = m.content;
      msgs.appendChild(div);
    });
    msgs.scrollTop = msgs.scrollHeight;
  } catch (e) {
    toast("Erro ao carregar mensagens: " + e.message);
  }
}

document.getElementById("newConv").addEventListener("submit", async (e) => {
  e.preventDefault();
  const titleEl = document.getElementById("title");
  const title = titleEl.value.trim() || "Nova conversa";
  try {
    const res = await api("/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title })
    });
    titleEl.value = "";
    await loadConversations(res.id);
  } catch (e) {
    toast("Erro ao criar conversa: " + e.message);
  }
});

renameBtn.addEventListener("click", async () => {
  if (!current) return;
  const newTitle = prompt("Novo título:", current.title);
  if (!newTitle || newTitle.trim() === current.title) return;
  try {
    await api(`/conversations/${current.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: newTitle.trim() })
    });
    await loadConversations(current.id);
  } catch (e) {
    toast("Erro ao renomear: " + e.message);
  }
});

deleteBtn.addEventListener("click", async () => {
  if (!current) return;
  if (!confirm(`Apagar "${current.title}"?`)) return;
  try {
    await api(`/conversations/${current.id}`, { method: "DELETE" });
    current = null;
    await loadConversations();
  } catch (e) {
    toast("Erro ao apagar: " + e.message);
  }
});

document.getElementById("composer").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!current) return toast("Selecione ou crie uma conversa primeiro.");
  const text = input.value.trim();
  if (!text) return;

  const u = document.createElement("div");
  u.className = "bubble user";
  u.textContent = text;
  msgs.appendChild(u);
  msgs.scrollTop = msgs.scrollHeight;
  input.value = "";
  setComposerEnabled(false);
  setActionButtonsEnabled(false);

  try {
    const res = await api("/chat/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: current.id, message: text })
    });
    const a = document.createElement("div");
    a.className = "bubble assistant";
    a.textContent = res.reply || "(sem resposta)";
    msgs.appendChild(a);
    msgs.scrollTop = msgs.scrollHeight;
  } catch (err) {
    const a = document.createElement("div");
    a.className = "bubble assistant";
    a.textContent = "Erro ao enviar: " + err.message;
    msgs.appendChild(a);
  } finally {
    setComposerEnabled(true);
    setActionButtonsEnabled(true);
    input.focus();
  }
});


loadConversations();
window.addEventListener("focus", () => current && loadMessages());
