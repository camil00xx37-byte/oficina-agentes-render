# Oficina de Agentes IA – Backend (Departamento de Ingeniería)

Sistema de agentes autónomos conectado a tu simulación 3D.

## ¿Qué hace este backend?

- Recibe tareas desde tu HTML por **WebSocket**
- Las asigna al equipo de **Ingeniería** (Iván, Nora, Sergio, Clara)
- Los agentes pueden:
  - Investigar en internet
  - Escribir y ejecutar código Python
  - Leer y crear archivos
  - Guardar lecciones aprendidas (para no repetir errores)
  - Generar informes de lo realizado
- Envía eventos en tiempo real de vuelta al frontend (para que los avatares reaccionen)

---

## Instalación rápida (portátil)

### 1. Requisitos
- Python 3.10 o superior
- Una API Key **gratis** de Groq → https://console.groq.com/keys

### 2. Instalar

```bash
cd oficina-agentes/backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configurar la API Key

```bash
cp .env.example .env
```

Abre el archivo `.env` y pega tu key:

```
GROQ_API_KEY=gsk_tu_clave_aqui
GROQ_MODEL=llama-3.3-70b-versatile
```

### 4. Arrancar el servidor

```bash
python main.py
```

Verás algo como:
```
Uvicorn running on http://0.0.0.0:8000
```

---

## Cómo conectar tu HTML

En tu archivo `oficina-agentes-3d-v7.html` añade este código JavaScript (puedes pegarlo al final del `<script>` existente, antes del cierre).

```js
// ========== CONEXIÓN CON BACKEND DE AGENTES ==========
const AGENT_WS_URL = "ws://localhost:8000/ws";
let agentSocket = null;
let agentConnected = false;

function connectAgents() {
  agentSocket = new WebSocket(AGENT_WS_URL);

  agentSocket.onopen = () => {
    agentConnected = true;
    console.log("✅ Conectado al backend de agentes");
    say(asis, "Backend de agentes conectado");
    setTimeout(() => say(asis, ""), 2500);
  };

  agentSocket.onclose = () => {
    agentConnected = false;
    console.log("Backend desconectado. Reintentando en 3s...");
    setTimeout(connectAgents, 3000);
  };

  agentSocket.onerror = (e) => console.error("Error WebSocket agentes:", e);

  agentSocket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleAgentEvent(data);
    } catch (err) {
      console.error("Error parseando mensaje:", err);
    }
  };
}

function handleAgentEvent(data) {
  const type = data.type;

  if (type === "connected") {
    msg(asis, data.message || "Agentes listos");
  }
  else if (type === "task_started") {
    msg(asis, data.message || "Tarea enviada a Ingeniería");
    // Aquí puedes hacer que los avatares de Ingeniería se pongan a trabajar
    const ing = byId.ing;
    if (ing && ing.ag) {
      ing.ag.forEach(a => {
        if (!a.busy) {
          a.busy = true;
          a.work = true;
        }
      });
    }
  }
  else if (type === "status" || type === "info") {
    msg(asis, data.message || "");
  }
  else if (type === "task_finished") {
    const success = data.success;
    const result = data.result || "";
    
    msg(asis, success 
      ? "✅ Ingeniería terminó la tarea" 
      : "❌ Hubo un problema en Ingeniería");

    // Mostrar resultado en el chat (recortado si es muy largo)
    const shortResult = result.length > 600 ? result.slice(0, 600) + "..." : result;
    const d = document.createElement("div");
    d.className = "msg";
    d.style.borderLeftColor = "#8a63d2";
    d.innerHTML = `<b style="color:#8a63d2">Informe Ingeniería</b><div style="white-space:pre-wrap;font-size:.8rem;margin-top:4px">${shortResult.replace(/</g,"&lt;")}</div>`;
    const chat = $("#chat");
    if (chat.querySelector(".empty")) chat.innerHTML = "";
    chat.append(d);
    chat.scrollTop = chat.scrollHeight;

    // Liberar agentes
    const ing = byId.ing;
    if (ing && ing.ag) {
      ing.ag.forEach(a => {
        a.busy = false;
        a.work = false;
      });
    }

    // Actualizar tarea en el panel si existe
    // (puedes mejorar esto según tu lógica de tasks)
  }
  else if (type === "error") {
    msg(asis, "Error: " + (data.message || "desconocido"));
  }
}

// Enviar tarea real al backend (en lugar de la simulación)
function submitRealTask(text, dep) {
  text = text.trim();
  if (!text) return;

  if (!agentConnected) {
    msg(asis, "El backend de agentes no está conectado. Arranca el servidor primero.");
    return;
  }

  // Crear la tarea visual como antes
  const t = { id: ++n, text, st: "proceso", pct: 10, dept: "Ingeniería", c: "#8a63d2" };
  tasks.push(t);
  render();

  agentSocket.send(JSON.stringify({
    type: "task",
    text: text,
    department: dep ? dep.id : "ing"
  }));
}

// Conectar al cargar
connectAgents();
```

Luego, en la función `submit` original, puedes decidir si usar la simulación o el backend real.  
Una forma sencilla es cambiar el botón de enviar para que use `submitRealTask` cuando el backend esté conectado.

Ejemplo rápido (modifica el onclick del botón #go):

```js
$('#go').onclick = () => {
  const text = $('#inp').value;
  if (agentConnected) {
    submitRealTask(text, byId.ing);   // fuerza Ingeniería por ahora
  } else {
    submit(text);                     // comportamiento original (simulación)
  }
  $('#inp').value = '';
};
```

---

## Probar

1. Arranca el backend (`python main.py`)
2. Abre tu HTML
3. Escribe una tarea relacionada con ingeniería, por ejemplo:

   > "Crea un script en Python que descargue el título de una página web y lo guarde en un archivo"

4. Observa cómo el equipo trabaja y te devuelve el informe.

---

## Estructura de carpetas

```
oficina-agentes/
├── backend/
│   ├── main.py                 ← Servidor FastAPI + WebSocket
│   ├── agents/
│   │   └── engineering_crew.py ← Los 4 agentes de Ingeniería
│   ├── tools/
│   │   ├── web_search.py
│   │   ├── code_executor.py
│   │   ├── file_tools.py
│   │   └── memory_tool.py
│   ├── memory/
│   │   └── lessons.json        ← Lecciones aprendidas (se crea solo)
│   ├── workspace/              ← Archivos que crean los agentes
│   ├── .env
│   └── requirements.txt
└── README.md
```

---

## Próximos pasos (cuando esto funcione)

1. Mejorar la animación de los avatares mientras trabajan
2. Añadir más herramientas (Git, bases de datos, etc.)
3. Replicar el mismo patrón para Marketing, Diseño, etc.
4. Si los límites de Groq free se quedan cortos → pasar a plan de pago barato

¿Listo para probar? Sigue los pasos de instalación y avísame cómo te va.