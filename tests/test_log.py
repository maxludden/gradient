import pytest

from pathlib import Path
from gradient.log import Log
from rich.console import Console

log = Log()
console = log.console

LOGS_DIR = Path(__file__).parent.parent / 'logs'
console.print(f"[bi #99ff00]LOGS_DIR[/]: [b #ffffff]{str(LOGS_DIR.resolve())}")

@pytest.fixture
def test_console():
    return Console()

@pytest.fixture
def test_logger():
    _console = test_console()
    return Log(console=_console)

def determing_LOGS_DIR_from_texts():
    


def instantiate_log_console():
    console = test_console()
    log = Log(console=console)
    console = log.console
    assert console.width == 120,f"Deferent console used: Width -> {console.width}"
    assert console.height == 60, f"Different console used: Height -> {console.height}"