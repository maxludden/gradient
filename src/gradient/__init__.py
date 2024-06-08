"""Gradient is a python library for generating gradients in the terminal.

Gradient is a python library built on top of the great \
    [rich](https://github.com/Textualize/rich) library to \
    enable the generation of gradients in the terminal. It \
    is inspired by the [lolcat](https://github.com/tehmaze/lolcat) \
    project. Gradient is designed to be easy to use and \
    extendable. It is also designed to be used as a library \
    or as a command line tool.
"""

# ruff: noqa: F403, F401
from rich.console import (
    Console,
    JustifyMethod,
    OverflowMethod,
    RenderableType,
    RenderResult,
)
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, TaskID
from rich.style import Style, StyleType
from rich.text import Text, Span, TextType

from gradient.color import Color