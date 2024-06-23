from typing import Optional

from rich.console import Console
from rich.traceback import install as tr_install
from rich.theme import Theme

from rich_gradient.log import Log
from rich_gradient.default_styles import DEFAULT_STYLES

theme = Theme(DEFAULT_STYLES)


def get_log(console: Optional[Console] = None, record: bool = False) -> Log:
    """Retrieve a rich console to print with.

    Args:
        console (Console): A rich console to print with.
        record (bool): Wether to record the console to save to disk.
    """
    if console is None:
        console = Console(theme=theme, record=record)
    tr_install(console=console)
    log = Log(console=console)
    return log
