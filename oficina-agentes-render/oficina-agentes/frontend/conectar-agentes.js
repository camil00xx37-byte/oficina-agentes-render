// ============================================================
//  CONEXIÓN COMPLETA CON BACKEND DE AGENTES
// ============================================================

const AGENT_WS_URL = "ws://localhost:8000/ws";
let agentSocket = null;
let agentConnected = false;

function connectAgents() {
  try {
    agentSocket = new WebSocket(AGENT_WS_URL);
  } catch (e) {
    setTimeout(connectAgents, 4000);
    return;
  }

  agentSocket.onopen = () => {
    agentConnected = true;
    console.log("✅ Backend de agentes conectado");
    if (typeof say === "function" && typeof asis !== "undefined") {
      say(asis, "Oficina de agentes conectada");
      setTimeout(() => say(asis, ""), 2800);
    }
  };

  agentSocket.onclose = () => {
    agentConnected = false;
    setTimeout(connectAgents, 3000);
  };

  agentSocket.onerror = () => {};

  agentSocket.onmessage = (event) => {
    try {
      handleAgentEvent(JSON.parse(event.data));
    } catch (err) {
      console.error(err);
    }
  };
}

function handleAgentEvent(data) {
  const type = data.type;

  if (type === "connected" || type === "status" || type === "info") {
    if (typeof msg === "function" && typeof asis !== "undefined") {
      msg(asis, data.message || "");
    }
  }
  else if (type === "task_started") {
    if (typeof msg === "function" && typeof asis !== "undefined") {
      msg(asis, data.message || "Tarea enviada");
    }
    try {
      const dep = byId[data.department];
      if (dep && dep.ag) {
        dep.ag.forEach(a => { a.busy = true; a.work = true; });
      }
    } catch(e){}
  }
  else if (type === "task_finished") {
    const approved = data.assistant_approved;
    if (typeof msg === "function" && typeof asis !== "undefined") {
      msg(asis, approved
        ? "✅ Asistente APROBÓ el entregable"
        : "⚠️ Asistente RECHAZÓ el entregable");
    }

    try {
      const chat = document.querySelector("#chat");
      if (chat) {
        if (chat.querySelector(".empty")) chat.innerHTML = "";
        const d = document.createElement("div");
        d.className = "msg";
        d.style.borderLeftColor = approved ? "#2ecc71" : "#e74c3c";
        const comment = (data.assistant_comment || data.result || "").slice(0, 700);
        d.innerHTML = `<b style="color:${approved ? "#2ecc71" : "#e74c3c"}">
          ${approved ? "✅ Aprobado por Asistente" : "❌ Rechazado por Asistente"}
          </b>
          <div style="white-space:pre-wrap;font-size:.78rem;margin-top:6px">${comment.replace(/</g,"&lt;")}</div>`;
        chat.appendChild(d);
        chat.scrollTop = chat.scrollHeight;
      }
    } catch(e){}

    try {
      const dep = byId[data.department];
      if (dep && dep.ag) {
        dep.ag.forEach(a => { a.busy = false; a.work = false; });
      }
    } catch(e){}
  }
  else if (type === "assistant_review") {
    if (typeof msg === "function" && typeof asis !== "undefined") {
      msg(asis, data.message || "");
    }
  }
  else if (type === "meeting_report" || type === "meeting_started") {
    if (data.report && typeof sx !== "undefined" && typeof stex !== "undefined") {
      try {
        sx.fillStyle = "#fff";
        sx.fillRect(0, 0, 1024, 576);
        sx.fillStyle = "#7b5cff";
        sx.fillRect(0, 0, 1024, 70);
        sx.fillStyle = "#fff";
        sx.font = "700 32px system-ui,sans-serif";
        sx.fillText("Informe de Reunión", 36, 45);
        sx.fillStyle = "#14232b";
        sx.font = "20px system-ui,sans-serif";
        const lines = data.report.split("\n").slice(0, 18);
        lines.forEach((line, i) => {
          sx.fillText(line.slice(0, 75), 36, 110 + i * 26);
        });
        stex.needsUpdate = true;
      } catch(e) {}
    }
    if (typeof msg === "function" && typeof asis !== "undefined") {
      msg(asis, "Informe de reunión listo en la pantalla");
    }
  }
  else if (type === "error") {
    if (typeof msg === "function" && typeof asis !== "undefined") {
      msg(asis, "Error: " + (data.message || ""));
    }
  }
}

function submitRealTask(text, deptId) {
  text = (text || "").trim();
  if (!text) return;
  if (!agentConnected) {
    if (typeof msg === "function" && typeof asis !== "undefined") {
      msg(asis, "Backend no conectado. Arranca: python main.py");
    }
    return;
  }

  try {
    const t = {
      id: ++n,
      text,
      st: "proceso",
      pct: 15,
      dept: (byId[deptId] && byId[deptId].n) || deptId,
      c: (byId[deptId] && hex(byId[deptId].c)) || "#7b5cff"
    };
    tasks.push(t);
    render();
  } catch(e){}

  agentSocket.send(JSON.stringify({
    type: "task",
    text: text,
    department: deptId || "ing"
  }));
}

function startRealMeeting() {
  if (!agentConnected) {
    if (typeof meeting === "function") meeting();
    return;
  }
  agentSocket.send(JSON.stringify({ type: "meeting" }));
  if (typeof meeting === "function") meeting();
}

connectAgents();

document.addEventListener("DOMContentLoaded", () => {
  const goBtn = document.querySelector("#go");
  if (goBtn) {
    goBtn.onclick = () => {
      const text = (document.querySelector("#inp") || {}).value || "";
      if (agentConnected && text.trim()) {
        let dept = "ing";
        try {
          if (typeof route === "function") {
            const d = route(text);
            if (d && d.id) dept = d.id;
          }
        } catch(e){}
        submitRealTask(text, dept);
        document.querySelector("#inp").value = "";
      } else if (typeof submit === "function") {
        submit(text);
        document.querySelector("#inp").value = "";
      }
    };
  }

  const mbtn = document.querySelector("#mbtn");
  if (mbtn) {
    mbtn.onclick = () => startRealMeeting();
  }
});

console.log("Script de agentes cargado.");
