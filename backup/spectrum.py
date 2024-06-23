from __future__ import annotations

from typing import List, Tuple

from rich.console import Console
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.traceback import install as tr_install

from gradient._color import Color
from gradient.theme import GradientTheme

console = Console()
tr_install(console=console, show_locals=True)


class Spectrum(List[Color]):
    """The colors from which to create random gradients."""

    NAMES: Tuple[str, ...] = (
        "magenta",
        "purple",
        "violet",
        "blue",
        "dodgerblue",
        "deepskyblue",
        "lightskyblue",
        "cyan",
        "springgreen",
        "lime",
        "greenyellow",
        "yellow",
        "orange",
        "darkorange",
        "tomato",
        "red",
        "deeppink",
        "hotpink",
    )

    HEX = (
        "#FF00FF",
        "#AF00FF",
        "#5F00FF",
        "#0000FF",
        "#0055FF",
        "#0087FF",
        "#00C3FF",
        "#00FFFF",
        "#00FFAF",
        "#00FF00",
        "#AFFF00",
        "#FFFF00",
        "#FFAF00",
        "#FF8700",
        "#FF4B00",
        "#FF0000",
        "#FF005F",
        "#FF00AF"
    )

    RGB = (
        "rgb(255, 0, 255)",
        "rgb(175, 0, 255)",
        "rgb(95, 0, 255)",
        "rgb(0, 0, 255)",
        "rgb(0, 85, 255)",
        "rgb(0, 135, 255)",
        "rgb(0, 195, 255)",
        "rgb(0, 255, 255)",
        "rgb(0, 255, 175)",
        "rgb(0, 255, 0)",
        "rgb(175, 255, 0)",
        "rgb(255, 255, 0)",
        "rgb(255, 175, 0)",
        "rgb(255, 135, 0)",
        "rgb(255, 75, 0)",
        "rgb(255, 0, 0)",
        "rgb(255, 0, 95)",
        "rgb(255, 0, 175)"
    )

    def __init__(self) -> None:
        self.COLORS: List[Color] = [Color(hex) for hex in self.HEX]
        super().__init__(self.COLORS)

    def __rich__(self) -> Table:
        table = Table(
            "[b i #ffffff]Sample[/]",
            "[b i #ffffff]Name[/]",
            "[b i #ffffff]Hex[/]",
            "[b i #ffffff]RGB[/]",
            title="[b #ffffff]Gradient Colors[/]",
            show_footer=False,
            show_header=True,
            row_styles=(
                [
                    "on #1f1f1f",
                    "on #000000"
                ]
            )
        )
        for color in self.COLORS:
            assert color.triplet, "ColorTriplet must not be None"
            triplet = color.triplet
            hex_str = triplet.hex.upper()
            if hex_str in [
                "#AF00FF",
                "#5F00FF",
                "#0000FF",
                "#0055FF",
            ]:
                foreground = "#ffffff"
            else:
                foreground = "#000000"
            bg_style = Style(color=foreground, bgcolor=hex_str, bold=True)
            style = Style(color=hex_str, bold=True)
            index = self.HEX.index(hex_str)
            name = self.NAMES[index].capitalize()
            table.add_row(
                Text(" " * 10, style=bg_style),
                Text(name, style=style),
                Text(hex_str, style=style),
                Text(triplet.rgb, style=style),
            )
        return table


if __name__ == "__main__":
    console = Console(record=True, theme=GradientTheme()(), width=64)
    console.line(2)
    console.print(Spectrum(), justify="center")
    console.line(2)
    console.save_svg("docs/img/spectrum.svg")
