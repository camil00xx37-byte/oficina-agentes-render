# Oficina de Agentes – Proyecto listo

Solo te falta poner tu API key gratuita de Groq.

## 1. API Key (1 minuto)

1. Entra en https://console.groq.com/keys
2. Inicia sesión
3. Crea una API Key
4. Cópiala

En la carpeta backend:

```bash
cp .env.example .env
```

Abre `.env` y pega:

```
GROQ_API_KEY=gsk_tu_clave_aqui
GROQ_MODEL=llama-3.3-70b-versatile
```

## 2. Arrancar el backend

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

Deja esa ventana abierta (http://localhost:8000).

## 3. Conectar tu HTML 3D

Abre tu HTML. Al final del `<script>` (antes de `</script>`) pega todo el contenido del archivo:

`frontend/conectar-agentes.js`

## Qué está configurado

### Todos los departamentos
Ingeniería, Marketing, Diseño, Operaciones, RRHH, Contabilidad, Administrativo  
(cada uno con 1 jefe + 3 agentes)

### Asistente con poder superior
- Revisa TODOS los entregables
- Aprueba o rechaza automáticamente
- Solo lo aprobado te llega limpio
- Autoridad por encima de los jefes de área

### Archivos
- incoming/  → lo que tú subes
- outgoing/  → lo que entregan los agentes (pendiente de Asistente)
- approved/  → lo que la Asistente aprobó
- rejected/  → lo que rechazó

### Reunión
El botón "Iniciar reunión" genera un informe real y lo muestra en la pantalla 3D de la sala de reuniones.

## Flujo de trabajo

1. Escribes una tarea
2. Se asigna al departamento
3. Los agentes trabajan
4. Generan entregable
5. La Asistente lo revisa
6. Si aprueba → te llega
7. Si rechaza → te avisa con motivo
8. En la reunión ves el resumen

Cuando lo tengas corriendo, avísame.
