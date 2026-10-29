# Subir la Oficina de Agentes a Render (web pública)

El proyecto ya está preparado para desplegarse en **un solo servicio** de Render:
- Frontend 3D (HTML + Three.js)
- Backend FastAPI + WebSockets + CrewAI

---

## 1. Sube el código a GitHub

1. Crea un repositorio nuevo en GitHub (puede ser privado).
2. Desde la carpeta del proyecto:

```bash
cd oficina-agentes
git init
git add .
git commit -m "Oficina de Agentes lista para Render"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/oficina-agentes.git
git push -u origin main
```

> **Importante:** no subas el archivo `.env` (ya está en `.gitignore`).

---

## 2. Crea el servicio en Render

1. Entra en [https://dashboard.render.com](https://dashboard.render.com) e inicia sesión.
2. **New → Web Service**.
3. Conecta tu cuenta de GitHub y selecciona el repositorio `oficina-agentes`.
4. Configura así:

| Campo              | Valor                                      |
|--------------------|--------------------------------------------|
| **Name**           | `oficina-agentes` (o el que quieras)       |
| **Region**         | `Oregon` (o el más cercano)                |
| **Root Directory** | `backend`                                  |
| **Runtime**        | `Python 3`                                 |
| **Build Command**  | `pip install -r requirements.txt`          |
| **Start Command**  | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type**  | Free (o Starter si quieres más potencia)   |

5. En **Environment Variables** añade:

| Key            | Value                          |
|----------------|--------------------------------|
| `GROQ_API_KEY` | `gsk_tu_clave_real_aqui`       |
| `GROQ_MODEL`   | `llama-3.3-70b-versatile`      |

> Consigue la key gratis en: https://console.groq.com/keys

6. Pulsa **Create Web Service**.

Render instalará las dependencias y arrancará el servidor. Tarda 2-5 minutos la primera vez.

---

## 3. Abre tu web

Cuando el estado sea **Live**, Render te dará una URL del tipo:

```
https://oficina-agentes-xxxx.onrender.com
```

Ábrela en el navegador. Verás la oficina 3D y se conectará automáticamente al backend (WebSocket `wss://...`).

---

## Notas importantes

### Plan Free de Render
- El servicio se **duerme** tras ~15 min de inactividad.
- La primera petición después de dormir puede tardar 30-60 segundos en despertar.
- Los archivos que generen los agentes se borran al reiniciar (el disco es efímero). Para persistencia necesitas un disco o un plan de pago.

### Si da error de build
- Asegúrate de que **Root Directory** es exactamente `backend`.
- Comprueba que `requirements.txt` está dentro de `backend/`.

### Si los agentes no responden
- Verifica que `GROQ_API_KEY` está bien puesta en Environment Variables.
- Mira los logs en el dashboard de Render (pestaña **Logs**).

### Actualizar
Cada `git push` a `main` despliega automáticamente (si tienes Auto-Deploy activado).

---

¡Listo! Cuando lo tengas desplegado, comparte la URL y lo probamos.
