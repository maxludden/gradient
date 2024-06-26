# ruff: noqa: F401
from __future__ import annotations

from atexit import register as atexit_register
from datetime import datetime
from pathlib import Path
from re import findall
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

import loguru
from loguru import logger as _logger
from pydantic_extra_types.color import Color

# from dotenv import load_dotenv
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.traceback import install as tr_install

from rich_gradient.run import run

HOME = Path.home()
CWD = Path("/Users/maxludden/dev/py/supergene_gui")
LOGS_DIR: Path = Path("/Users/maxludden/dev/py/supergene_gui/logs")
FORMAT: str = """{time:hh:mm:ss:SSS A} | {extra[run_padding1]}Run {extra[run]}{extra[run_padding2]} | {file.name: ^13} | Line {line: ^5} | {level: ^8} ﰲ  {message}"""


def get_console() -> Console:
    """Get a Rich console.
    `
        Returns:
            Console: A Rich console.
    """
    console = Console()
    tr_install(console=console)
    return console


def generate_logs(console: Console) -> None:
    """Generate log files if they do not exist.

    Args:
        console (Console): The rich console.
    """
    num_logs: int = len(list(LOGS_DIR.iterdir()))
    if num_logs < 2:
        log_levels: list[str] = [
            "trace.log",
            # "debug.log",
            # "info.log",
            # "warning.log",
            # "error.log",
            # "critical.log",
        ]
        for level in log_levels:
            path: Path = LOGS_DIR / level
            if not path.exists():
                console.log(
                    Panel(
                        f"[#ffffff]Creating missing log file[/][b #5f00af]:[/] [b i #af00ff]{level}"
                    )
                )
                with open(path, "w", encoding="utf-8") as outfile:
                    outfile.write(level.upper())


def get_progress(console: Console = get_console()) -> Progress:
    """Get a Rich progress bar.

    Args:
        console (Console, optional): A Rich console. Defaults to console.

    Returns:
        Progress: A Rich progress bar.
    """
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(),
        BarColumn(bar_width=None),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


class Log:
    """Generate a logger.

    Args:
        run (int, optional): The run number. Defaults to Run().run.
        log_to_console (str | int, optional): The logging level for the console. Defaults to "SUCCESS".
        console (Console, optional): A rich console. Defaults to None.
        logger (Logger, optional): A loguru logger. Defaults to logger.

    Raises:
        TypeError: If the logger is not a loguru logger.
        ValueError: If the level is not a valid logging level.
    """

    FORMAT: str = """{time:hh:mm:ss:SSS A} | {extra[run_padding1]}Run {extra[run]}{extra[run_padding2]} | {file.name: ^13} | Line {line: ^5} | {level: ^8} ﰲ {message}"""
    HANDLERS: List[Dict[str, Any]] = [
        {
            "sink": LOGS_DIR / "trace.log",
            "level": "TRACE",
            "mode": "w",
            "format": FORMAT,
            "backtrace": True,
            "diagnose": True,
            "colorize": True,
            "enqueue": True,
        },
        {
            "sink": LOGS_DIR / "debug.log",
            "level": "DEBUG",
            "mode": "w",
            "format": FORMAT,
            "backtrace": True,
            "diagnose": True,
            "colorize": True,
            "enqueue": True,
        },
        {
            "sink": LOGS_DIR / "info.log",
            "level": "INFO",
            "mode": "w",
            "format": FORMAT,
            "backtrace": True,
            "diagnose": True,
            "colorize": True,
            "enqueue": True,
        },
        {
            "sink": LOGS_DIR / "success.log",
            "level": "SUCCESS",
            "mode": "w",
            "format": FORMAT,
            "backtrace": True,
            "diagnose": True,
            "colorize": True,
            "enqueue": True,
        },
        {
            "sink": LOGS_DIR / "warning.log",
            "level": "WARNING",
            "mode": "w",
            "format": FORMAT,
            "backtrace": True,
            "diagnose": True,
            "colorize": True,
            "enqueue": True,
        },
        {
            "sink": LOGS_DIR / "error.log",
            "level": "ERROR",
            "mode": "w",
            "format": FORMAT,
            "backtrace": True,
            "diagnose": True,
            "colorize": True,
            "enqueue": True,
        },
        {
            "sink": LOGS_DIR / "critical.log",
            "level": "CRITICAL",
            "mode": "w",
            "format": FORMAT,
            "backtrace": True,
            "diagnose": True,
            "colorize": True,
            "enqueue": True,
        },
    ]

    def __init__(
        self,
        *,
        run: int = run.run,
        log_to_console: str | int = "SUCCESS",
        console: Console = Console(),
        progress: Optional[Progress] = None,
        logger: Optional[Log] | Optional[loguru.Logger] = None,
        verbose: bool = False,
    ) -> None:
        """Generate a logger.

        Args:
            run (int, optional): The run number. Defaults to Run().run.
            log_to_console (str | int, optional): The logging level for the console. Defaults to "SUCCESS".
            console (Console, optional): A rich console. Defaults to None.
            progress (Progress, optional): A rich progress bar. Defaults to None.
            logger (Logger, optional): A loguru logger. Defaults to None.
            verbose (bool): Whether to print verbose logs. Default to False.

        Raises:
            TypeError: If the logger is not a loguru logger.
            ValueError: If the level is not a valid logging level.
        """
        if isinstance(log_to_console, str):
            log_to_console = self.level_str_to_int(log_to_console)
        self.log_to_console: int = log_to_console
        self.console: Console = console or get_console()
        # generate_logs(console=self.console)
        self.verbose: bool = verbose
        handlers = self.setup_logs()
        self.progress: Progress = progress or get_progress(console=self.console)
        self.run: int = run
        self.parse_logger(logger)
        run_padding1, run_padding2 = self.get_padding()
        self.sinks: List[int] = self.logger.configure(
            handlers=handlers,
            extra={
                "log_to_console": self.log_to_console,
                "run": self.run,
                "run_padding1": run_padding1,
                "run_padding2": run_padding2,
            },
            activation=[("maxgradient", False)],
        )

    def setup_logs(self) -> List[Dict[str, Any]]:
        """Parse handlers and setup logs."""
        handlers: List[Dict[str, Any]] = []
        match self.verbose:
            case True:
                handlers = self.HANDLERS
            case False:
                handlers = [self.HANDLERS[0]]
        handlers.append(
            dict(
                sink=self.rich_sink,
                filter=self.rich_filter,
                format="{message}",
                backtrace=True,
                diagnose=True,
                colorize=True,
                level=self.log_to_console,
                serialize=True,
                enqueue=True,
            )
        )
        return handlers

    def parse_logger(self, logger: Optional[Log] | Optional[loguru.Logger]) -> None:
        """Parse the logger and remove any existing sinks.

        Args:
            logger (Optional[Log] | Optional[loguru.Logger]): The logger to parse.
        """
        match logger:
            case None:
                self.logger: loguru.Logger = loguru.logger
            case _ if not hasattr(logger, "logger"):
                self.logger = loguru.logger
            case _ if isinstance(logger, Log):
                self.run = logger.run
                self.console = logger.console
                self.progress = logger.progress
                self.logger = logger.logger

            case _ if isinstance(logger, loguru.Logger):
                self.logger = logger
            case _:
                raise TypeError(
                    f"Logger must be a loguru logger, you entered: {logger} of type {type(logger)}."
                )
        self.logger.remove()

    def enable(self, module: str = "") -> None:
        """Enable logging for a module.

        Args:
            module (str, optional): The module to enable logging for. Defaults to None.
        """
        self.logger.enable(module)

    def disable(self, module: str = "") -> None:
        """Disable logging for a module.

        Args:
            module (str, optional): The module to disable logging for. Defaults to None.
        """
        self.logger.disable(module)

    def get_padding(self) -> Tuple[str, str]:
        """Generate padding for the run number."""
        run_string: str = str(self.run)
        run_str: str = f"Run {run_string}"
        double_padding = 12 - len(run_str)
        if double_padding % 2 == 0:
            run_padding1 = " " * (double_padding // 2)
            run_padding2 = run_padding1
        else:
            run_padding1 = " " * (double_padding // 2)
            run_padding2 = run_padding1 + " "
        return f"{run_padding1} ", f"{run_padding2} "

    @staticmethod
    def level_str_to_int(level: str) -> int:
        """Convert a logging level string to an integer.

        Args:
            level (str): A logging level string.

        Returns:
            int: A logging level integer.
        """
        assert level, "No level provided."
        match level.lower():
            case "trace":
                return 5
            case "debug":
                return 10
            case "info":
                return 20
            case "success":
                return 25
            case "warning":
                return 30
            case "error":
                return 40
            case "critical":
                return 50
            case _:
                raise ValueError(
                    f"Level parsed incorrectly. String must be a logging \
    level (`TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`), you entered: {level}"
                )

    @staticmethod
    def get_level_style_from_int(level: int) -> Style:
        """Get the rich style to apple to the logging level.

        Args:
            level (int): A logging level integer.

        Returns:
            str: A rich style.
        """
        assert level > 0, "Level must be greater than 0."
        match level:
            case _ if level <= 5:  # trace
                return Style.parse("#99ff00")
            case _ if level <= 10:  # debug
                return Style.parse("#aaaaaa")
            case _ if level <= 20:  # info
                return Style.parse("#00afff")
            case _ if level <= 25:  # success
                return Style.parse("bold #00ff00")
            case _ if level <= 30:  # warning
                return Style.parse("italic #ffaf00")
            case _ if level <= 40:  # error
                return Style.parse("bold #ff5000")
            case _ if level <= 50:  # critical
                return Style.parse("bold #ff0000")
            case _:
                raise ValueError(
                    f"Invalid Level: {level} Level must be between 0 and 50."
                )

    @staticmethod
    def get_level_gradient(level: int) -> Tuple[List[Color], bool, bool]:
        """Get the colors to generate a gradient based of label.

        Args:
            level (str): The logging level.

        Returns:
            List[Color, Bool, Bool]: A tuple consisting of:
                - a list of colors to generate a gradient
                - a boolean for bold
                - a boolean for italic
        """
        match level:
            case _ if level <= 5:
                return (
                    [
                        Color("#cccccc"),
                        Color("#aaaaaa"),
                        Color("#888888"),
                    ],
                    True,
                    False,
                )
            case _ if level <= 10:
                return (
                    [
                        Color("#77cccc"),
                        Color("#55aaaa"),
                        Color("#338888"),
                    ],
                    False,
                    False,
                )
            case _ if level <= 20:
                return (
                    [
                        Color("#00cfff"),
                        Color("#00afff"),
                        Color("#008fff"),
                    ],
                    True,
                    False,
                )
            case _ if level <= 25:
                return (
                    [
                        Color("#00aa00"),
                        Color("#00ff00"),
                        Color("#afff00"),
                    ],
                    True,
                    False,
                )
            case _ if level <= 30:
                return (
                    [
                        Color("#ffdd00"),
                        Color("#ffcc00"),
                        Color("#ffaa00"),
                    ],
                    True,
                    False,
                )
            case _ if level <= 40:
                return (
                    [Color("#ff7700"), Color("#ff5500"), Color("#ff0000")],
                    True,
                    False,
                )
            case _ if level <= 50:
                return (
                    [
                        Color("#ff0000"),
                        Color("#ff005f"),
                        Color("#ff00af"),
                    ],
                    True,
                    True,
                )
            case _:
                raise ValueError(
                    f"Invalid Level: {level} Level must be between 0 and 50."
                )

    @staticmethod
    def level_color(msg: loguru.Message) -> Style:
        """Generate a color for the logging levels.

        Args:
            level (str|int): The logging level. Can be a string or an integer.

        Returns:
            Style: A style for the logging level.

        """
        record = msg.record
        level = record["level"].name
        assert level, "No level provided."
        if isinstance(level, str):
            match level.lower():
                case "trace":
                    return Style(color="#ffd4ff", bold=True)
                case "debug":
                    return Style(color="#ff00ff", bold=True)
                case "info":
                    return Style(color="#5f00ff", bold=True)
                case "success":
                    return Style(color="#00ff00", bold=True)
                case "warning":
                    return Style(color="#af00ff", bold=True)
                case "error":
                    return Style(color="#000000", bgcolor="#ff00af", bold=True)
                case "critical":
                    return Style(
                        color="#ffeeee",
                        bgcolor="#880000",
                        bold=True,
                        italic=True,
                        blink=True,
                    )
                case _:
                    raise ValueError(
                        f"Level parsed incorrectly. String must be a logging \
    level (`TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`), you entered: {level}"
                    )
        elif isinstance(level, int):
            assert level > 0, "Level must be greater than 0."
            if level <= 5:  # trace
                return Style(color="#ffd4ff", bold=True)
            elif level <= 10:  # debug
                return Style(color="#ff00ff", bold=True)
            elif level <= 20:  # info
                return Style(color="#5f00ff", bold=True)
            elif level <= 25:  # success
                return Style(color="#00ff00", bold=True)
            elif level <= 30:  # warning
                return Style(color="#af00ff", bold=True)
            elif level <= 40:  # error
                return Style(color="#000000", bgcolor="#ff00af", bold=True)
            elif level <= 50:  # critical
                return Style(
                    color="#ffeeee",
                    bgcolor="#880000",
                    bold=True,
                    blink=True,
                )
            else:
                raise ValueError(
                    f"Level parsed incorrectly. Invalid integer: integer \
    level must be a valid logging level between 0 and 50. You entered:{level}"
                )
        else:
            raise TypeError(
                f"Level parsed incorrectly. Level must be a string or an \
    integer, you entered: {level}"
            )

    def logging_prompt(self, msg: loguru.Message) -> str:
        """Generate a prompt for the logging levels."""
        record: loguru.Record = msg.record
        level = record["level"].name
        return level

    def rich_filter(self, record) -> bool:
        """Filter log records to only those that have a rich message."""
        log_to_console: int = int(record["extra"]["log_to_console"])
        level = record["level"].no
        print_to_console: bool = level >= log_to_console
        if not print_to_console:
            return False
        return True

    def log(self, level: str | int, message: Any, *args, **kwargs) -> None:
        """Log a message.

        Args:
            level (str): The logging level.
            message (Any): The object(s) to log.
        """
        record = message.record
        level = record["level"].no
        self.logger.log(level, message, *args, **kwargs)

    def trace(self, message: Any, *args, **kwargs) -> None:
        """Log a message with level 'TRACE'.

        Args:
            message (Any): The object(s) to log.

        Example:
            >>> log.trace("Trace message.")
        """
        self.logger.trace(message, *args, **kwargs)

    def debug(self, message: Any, *args, **kwargs) -> None:
        """Log a message with the level 'DEBUG'.

        Args:
            message (Any): The object(s) to log.

        Example:
            >>> log.debug("Debug message.")
        """
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: Any, *args, **kwargs) -> None:
        """Log a message with the level 'INFO'.

        Args:
            message (Any): The object(s) to log.

        Example:
            >>> log.info("Info message.")
        """
        self.logger.info(message, *args, **kwargs)

    def success(self, message: Any, *args, **kwargs) -> None:
        """Log a message with the level 'SUCCESS'.

        Args:
            message (Any): The object(s) to log.

        Example:
            >>> log.success("Success message.")
        """
        self.logger.success(message, *args, **kwargs)

    def warning(self, message: Any, *args, **kwargs) -> None:
        """Log a message with the level 'WARNING'.

        Args:
            message (Any): The object(s) to log.

        Example:
            >>> log.warning("Warning message.")
        """
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: Any, *args, **kwargs) -> None:
        """Log an message with the level 'ERROR'.

        Args:
            message (Any): The object(s) to log.

        Example:
            >>> log.error("Error message.")
        """
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: Any, *args, **kwargs) -> None:
        """Log a message with the level 'CRITICAL'.

        Args:
            message (Any): The object(s) to log.

        Example:
            >>> log.critical("Critical message.")
        """
        self.logger.critical(message, *args, **kwargs)

    def opt(
        self,
        *,
        exception: Optional[bool | Tuple | Exception] = None,
        record: bool = False,
        lazy: bool = False,
        colors: bool = False,
        raw: bool = False,
        capture: bool = True,
        depth: int = 0,
        ansi: int = False,
    ) -> loguru.Logger:
        """Set options for the logger.

        Args:
            exception (bool, tuple, Exception, optional):
                If It Does Not Evaluate As ``False``, The Passed Exception Is Formatted And Added To The
                Log Message. It Could Be An |Exception| Object Or A ``(Type, Value, Traceback)`` Tuple,
                Otherwise The Exception Information Is Retrieved From |Sys.Exc_info|. Defaults to None.
            record (bool, optional):
                If ``True``, The Record Dict Contextualizing The Logging Call Can Be Used To Format The
                Message By Using ``{Record[Key]}`` In The Log Message. Defaults to False.
            lazy (bool, optional):
                If ``True``, The Logging Call Attribute To Format The Message Should Be Functions Which
                Will Be Called Only If The Level Is High Enough. This Can Be Used To Avoid Expensive
                Functions If Not Necessary. Defaults to False.
            colors (bool, optional):
                If ``True``, Logged Message Will Be Colorized According To The Markups It Possibly
                Contains. Defaults to False.
            raw (bool, optional):
                If ``True``, The Formatting Of Each Sink Will Be Bypassed And The Message Will Be Sent
                As Is. Defaults to False.
            capture (bool, optional):
                If ``False``, The ``**Kwargs`` Of Logged Message Will Not Automatically Populate
                The ``Extra`` Dict (Although They Are Still Used For Formatting). Defaults to True.
            depth (int, optional):
                Specify Which Stacktrace Should Be Used To Contextualize The Logged Message. This Is
                Useful While Using The Logger From Inside A Wrapped Function To Retrieve Worthwhile
                Information. Defaults to 0.
            ansi (int, optional):
                Deprecated Since Version 0.4.1: The ``Ansi`` Parameter Will Be Removed In Loguru 1.0.0,
                It Is Replaced By ``Colors`` Which Is A More Appropriate Name. Defaults to False.
        """
        return self.logger.opt(
            exception=exception,  # type: ignore
            record=record,
            lazy=lazy,
            colors=colors,
            raw=raw,
            capture=capture,
            depth=depth,
            ansi=ansi,  # type: ignore
        )

    def rich_sink(self, message: loguru.Message) -> None:
        """Log a message to the rich console.

        Args:
            message (loguru.Message): A loguru message.
        """
        record: loguru.Record = message.record
        level: int = record["level"].no
        if level < self.log_to_console:
            return
        level_style: Style = self.get_level_style_from_int(level)
        colors, bold, italic = self.get_level_gradient(level)

        def gen_title(record: loguru.Record, colors: List[Color] = colors) -> Text:
            """Generate a title for the log panel"""
            line_string: str = f"Line {record['line']}"
            title_strings = [
                f"  {record["level"].name.upper(): ^8} ",
                " | ",
                f"{record['file'].name: ^10}",
                " | ",
                f"{line_string: ^13}",
            ]
            title_string = "".join(title_strings)

            title = Text(f"{title_string}")

            title.highlight_words("|", style="italic #000000 on  #666666 ")
            title.stylize(Style(reverse=True))
            return title

        def gen_subtitle(record: loguru.Record) -> Text:
            """Generate a subtitle for the log panel"""
            subtitle = Text.assemble(
                *[
                    Text("Run ", style=f"i {colors[0]}"),
                    Text(f"{self.run}", style=f"i {colors[0]}"),
                    Text(" | ", style="dim #aaaaaa"),
                    Text(
                        f"{record['time'].strftime('%I:%M:%S.')}",
                        style=f"i {colors[0]}",
                    ),
                    Text(
                        f"{record['time'].strftime('%f')[:-3]}", style=f"i {colors[0]}"
                    ),
                    Text(f"{record['time'].strftime(' %p')}", style=f"i {colors[0]}"),
                ]
            )
            subtitle.highlight_words(":", style="b #666666")
            subtitle.highlight_words(".", style="b #666666")
            return subtitle

        def gen_message(record: loguru.Record) -> Text:
            """Generate a message for the log panel."""
            message = Text(record["message"], style="bold #cccccc")
            return message

        title_text = gen_title(record=record)
        subtitle_text = gen_subtitle(record=record)
        message_text = gen_message(record=record)

        def gen_log_panel(
            message: Text = message_text,
            title: Text = title_text,
            subtitle: Text = subtitle_text,
        ) -> Panel:
            """Generate a log panel."""
            log_panel = Panel(
                message,
                title=title,
                title_align="left",
                subtitle=subtitle,
                subtitle_align="right",
                border_style=level_style + Style(bold=True),
                padding=(1, 4),
            )
            return log_panel

        self.console.print(gen_log_panel())

    @staticmethod
    def clear_logs(retain: int = 2) -> None:
        """Clear logs older than the specified number of runs.

        If run is less than 3, add a header to the log file.
        Args:
            retain (int, optional): The number of runs to retain. Defaults to 3.
        """
        sleep(1)
        log_levels: List[str] = [
            "trace",
            # "debug",
            # "info",
            # "success",
            # "warning",
            "error",
            # "critical",
        ]
        for level in log_levels:
            # read the newest log file
            with open(LOGS_DIR / f"{level}.log", "r") as logfile:
                log_contents = logfile.read()

            # rename the newest log file
            now = datetime.now().isoformat()
            filepath = LOGS_DIR / f"{level}_{now}.log"
            with open(filepath, "w") as outfile:
                outfile.write(log_contents)

            (LOGS_DIR / f"{level}.log").unlink()

        sleep(0.5)
        missnamed = "/Users/maxludden/dev/py/supergene-gui/logs/info.logwarning.log"
        if Path(missnamed).exists():
            with open(missnamed, "r") as infile:
                log_contents = infile.read()
            with open(f"info_{now}.log", "w") as outfile:
                outfile.write(log_contents)
            Path(missnamed).unlink()

        sleep(0.5)
        for level in log_levels:
            logs = []
            for item in LOGS_DIR.iterdir():
                if item.is_file() and item.stem.startswith(level):
                    logs.append(item)
            # get all log files sorted by modified time
            logs = sorted(logs, key=lambda f: f.stat().st_mtime)
            if len(logs) > retain:
                logs_to_remove = logs[:-retain]
                for log in logs_to_remove:
                    log.unlink()


# atexit_register(Log.clear_logs)
global log
global console
global progress
console: Console = Console()
progress: Progress = get_progress(console=console)
log: Log = Log(
    run=run.run,
    log_to_console="SUCCESS",
    console=console,
    progress=progress,
    logger=_logger,
)


if __name__ == "__main__":
    import time

    console = get_console()

    log = Log(console=console, log_to_console="TRACE")
    log.trace("Trace message.")
    log.debug("Debug message.")
    log.info("Info message.")
    log.success("Success message.")
    log.warning("Warning message.")
    log.error("Error message.")
    log.critical("Critical message.")
    time.sleep(1)

    # Divider
    console.line(2)
    console.print(Rule("Lazy Logging"))
    console.line(2)

    # # Lazy logging
    log.opt(lazy=True).trace("Lazy message.")
    log.opt(lazy=True).debug("Lazy message.")
    log.opt(lazy=True).info("Lazy message.")
    log.opt(lazy=True).success("Lazy message.")
    log.opt(lazy=True).warning("Lazy message.")
    log.opt(lazy=True).error("Lazy message.")
    log.opt(lazy=True).critical("Lazy message.")
