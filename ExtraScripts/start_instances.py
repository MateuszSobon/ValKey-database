"""Uruchamia 3 instancje aplikacji (porty 8001-8003). Zatrzymanie: Ctrl+C."""
import subprocess
import sys

PORTS = [8001, 8002, 8003]

procs = [subprocess.Popen([sys.executable, "app.py", str(p)]) for p in PORTS]
print(f"Uruchomiono instancje na portach: {PORTS}. Ctrl+C konczy wszystkie.")

try:
    for p in procs:
        p.wait()
except KeyboardInterrupt:
    for p in procs:
        p.terminate()
    print("Zatrzymano instancje.")
