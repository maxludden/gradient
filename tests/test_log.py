import pytest
from pathlib import Path
from gradient.log import Log


ONOI
log = Log()
console = log.console

LOGS_DIR = Path(__file__).parent.parent / 'logs'
console.print(f"[bi #99ff00]LOGS_DIR[/]: [b #ffffff]{str(LOGS_DIR.resolve())}")

def test_log_trace(caplog):
    log = Log(verbose=True)
    
    log.trace("Trace message.")
    with open(LOGS_DIR / 'trace.log', 'r') as infile:
        lines=infile.readlines()
        last_line = lines[-1]
        assert "Trace message." in last_line

def test_log_debug(caplog):
    log = Log(log_to_console="DEBUG")
    log.debug("Debug message.")
    assert "Debug message." in caplog.text

def test_log_info(caplog):
    log = Log(log_to_console="INFO")
    log.info("Info message.")
    assert "Info message." in caplog.text

def test_log_success(caplog):
    log = Log(log_to_console="SUCCESS")
    log.success("Success message.")
    assert "Success message." in caplog.text

def test_log_warning(caplog):
    log = Log(log_to_console="WARNING")
    log.warning("Warning message.")
    assert "Warning message." in caplog.text

def test_log_error(caplog):
    log = Log(log_to_console="ERROR")
    log.error("Error message.")
    assert "Error message." in caplog.text

def test_log_critical(caplog):
    log = Log(log_to_console="CRITICAL")
    log.critical("Critical message.")
    assert "Critical message." in caplog.text

def test_log_lazy_logging(caplog):
    log = Log(log_to_console="TRACE")
    log.opt(lazy=True).trace("Lazy message.")
    assert "Lazy message." in caplog.text
    log.opt(lazy=True).debug("Lazy message.")
    assert "Lazy message." in caplog.text
    log.opt(lazy=True).info("Lazy message.")
    assert "Lazy message." in caplog.text
    log.opt(lazy=True).success("Lazy message.")
    assert "Lazy message." in caplog.text
    log.opt(lazy=True).warning("Lazy message.")
    assert "Lazy message." in caplog.text
    log.opt(lazy=True).error("Lazy message.")
    assert "Lazy message." in caplog.text
    log.opt(lazy=True).critical("Lazy message.")
    assert "Lazy message." in caplog.text
