# common.py
# ruff: noqa: F401
from typing import List, Optional, TypeAlias, Union

from gradient.color import Color, ColorType, get_console
from gradient.spectrum import Spectrum
from gradient.theme import GRADIENT_TERMINAL_THEME

console = get_console()
VERBOSE: bool = False

GradientColors: TypeAlias = Union[
    Optional[List[ColorType]], Optional[List[Color]], Optional[List[str]]
]
