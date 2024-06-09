import pytesta
from pathlib import Path
from gradient.log import Log
from rich.console import Console

log = Log()
console = log.console

LOGS_DIR = Path(__file__).parent.parent / 'logs'
console.print(f"[bi #99ff00]LOGS_DIR[/]: [b #ffffff]{str(LOGS_DIR.resolve())}")

def instantiate_log_console():
    _console = Console(width=120, height=60)
    log = Log(console=_console)
    console = log.console
    assert console.width == 120,f"Deferent console used: Width -> {console.width}"
    assert console.height == 60, f"Different console used: Height -> {console.height}"