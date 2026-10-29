"""
Script de prueba rápida del equipo de Ingeniería.
Úsalo para verificar que todo funciona antes de conectar el HTML 3D.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    print("❌ Falta GROQ_API_KEY en el archivo .env")
    print("   1. Ve a https://console.groq.com/keys")
    print("   2. Crea una key gratis")
    print("   3. Pégala en backend/.env")
    sys.exit(1)

print("✅ API Key detectada")
print("🚀 Lanzando equipo de Ingeniería con una tarea de prueba...\n")

from agents.engineering_crew import run_engineering_task

def on_event(event):
    t = event.get("type", "")
    msg = event.get("message", "")
    if t in ("status", "info", "completed", "error"):
        print(f"[{t.upper()}] {msg[:200]}")

result = run_engineering_task(
    "Escribe un pequeño script en Python que calcule los primeros 10 números de Fibonacci "
    "e imprima el resultado. Guarda el script en un archivo llamado fibonacci.py y "
    "también genera un informe breve de lo que hiciste.",
    on_event=on_event
)

print("\n" + "="*60)
if result.get("success"):
    print("✅ TAREA COMPLETADA")
    print("="*60)
    print(result.get("result", "")[:2000])
else:
    print("❌ ERROR")
    print(result.get("error"))