"""
Color definitions are used as per the CSS3
[CSS Color Module Level 3](http://www.w3.org/TR/css3-color/#svg-color) specification.

A few colors have multiple names referring to the sames colors, eg. `grey` and `gray` or `aqua` and `cyan`.

In these cases the _last_ color when sorted alphabetically takes preferences,
eg. `Color((0, 255, 255)).as_named() == 'cyan'` because "cyan" comes after "aqua".
"""

from __future__ import annotations

import math
import re
from colorsys import hls_to_rgb, rgb_to_hls
from itertools import cycle
from random import randint
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    Tuple,
    TypeAlias,
    Union,
    cast,
)

from pydantic import GetJsonSchemaHandler
from pydantic._internal import _repr
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, PydanticCustomError, core_schema
from pydantic_extra_types.color import Color as PyColor
from pydantic_extra_types.color import ColorType as PyColorType
from rich.color import Color as RichColor
from rich.color import ColorParseError
from rich.color import ColorType as RichColorType
from rich.color import blend_rgb
from rich.color_triplet import ColorTriplet
from rich.console import Console
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.traceback import install as tr_install

from gradient.log import Log
from gradient.default_styles import DEFAULT_STYLES

GradientColorTuple: TypeAlias = Union[Tuple[int, int, int], Tuple[int, int, int, float]]
ColorType: TypeAlias = Union[
    GradientColorTuple, str, "Color", PyColorType, RichColor, RichColorType
]
HslColorTuple: TypeAlias = Union[
    Tuple[float, float, float], Tuple[float, float, float, float]
]

def get_console(record: bool = False) -> Console:
    """Generate a rich console with rich tracebacks.

    Args:
        record (bool, optional): Whether to record the console. Defaults to False.

    Returns:
        Console: a rich console.
    """
    theme: Theme = Theme(DEFAULT_STYLES)
    console = Console(theme=theme, record=record)
    tr_install(console=console, show_locals=True)
    return console


class GradientRGBA:
    """
    Internal use only as a representation of a color.
    """

    __slots__ = "red", "green", "blue", "alpha", "_tuple"

    def __init__(self, red: float, green: float, blue: float, alpha: float | None):
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha

        self._tuple: tuple[float, float, float, float | None] = (
            red,
            green,
            blue,
            alpha,
        )

    def __getitem__(self, item: Any) -> Any:
        return self._tuple[item]

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, GradientRGBA) and self._tuple == other._tuple

    @property
    def triplet(self) -> ColorTriplet:
        """Return the color as a ColorTriplet."""
        return self.as_triplet()

    def as_triplet(self) -> ColorTriplet:
        """Return the color as a ColorTriplet."""
        return ColorTriplet(
            red=self.float_to_255(self.red),
            green=self.float_to_255(self.green),
            blue=self.float_to_255(self.blue),
        )

    @classmethod
    def from_triplet(cls, triplet: ColorTriplet) -> GradientRGBA:
        """Create an RGBA from a ColorTriplet."""
        return cls(
            red=triplet.red / 255,
            green=triplet.green / 255,
            blue=triplet.blue / 255,
            alpha=None,
        )

    @classmethod
    def from_rgb(cls, rgb: str) -> GradientRGBA:
        """Create an RGBA from RGB color code."""
        rgb_match = re.match(
            r"r?g?b?\((?P<red>\d+), ?(?P<green>\d+), ?(?P<blue>\d+)\)", rgb
        )
        if rgb_match:
            red = int(rgb_match.group("red")) / 255
            green = int(rgb_match.group("green")) / 255
            blue = int(rgb_match.group("blue")) / 255
            return cls(red, green, blue, None)
        raise ValueError(f"Invalid RGB color code: {rgb}")

    @staticmethod
    def float_to_255(c: float) -> int:
        """
        Converts a float value between 0 and 1 (inclusive) to an integer between 0 and 255 (inclusive).

        Args:
            c: The float value to be converted. Must be between 0 and 1 (inclusive).

        Returns:
            The integer equivalent of the given float value rounded to the nearest whole number.
        """
        return round(c * 255)

    def __repr__(self) -> str:
        return f"RGBA({self.triplet.hex})"

    def __rich_repr__(self) -> Text:
        return Text.assemble(
            *[
                Text("RGBA", style="bold #ffffff"),
                Text("(", style="bold {self.as_hex}"),
                Text(f"{self.red}, ", style="bold #ff0000"),
                Text(", ", style="bold #ffffff"),
                Text(f"{self.green}, ", style="bold #00ff00"),
                Text(", ", style="bold #ffffff"),
                Text(f"{self.blue}, ", style="bold #0000ff"),
                Text(", ", style="bold #ffffff"),
                Text(f"{self.alpha}%", style="bold #afafaf"),
                Text(")", style="bold #ffffff"),
            ]
        )


# these are not compiled here to avoid import slowdown, they'll be compiled the first time they're used, then cached
_r_255 = r"(\d{1,3}(?:\.\d+)?)"
_r_comma = r"\s*,\s*"
_r_alpha = r"(\d(?:\.\d+)?|\.\d+|\d{1,2}%)"
_r_h = r"(-?\d+(?:\.\d+)?|-?\.\d+)(deg|rad|turn)?"
_r_sl = r"(\d{1,3}(?:\.\d+)?)%"
r_hex_short = r"\s*(?:#|0x)?([0-9a-f])([0-9a-f])([0-9a-f])([0-9a-f])?\s*"
r_hex_long = r"\s*(?:#|0x)?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})?\s*"
# CSS3 RGB examples: rgb(0, 0, 0), rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 50%)
r_rgb = rf"\s*rgba?\(\s*{_r_255}{_r_comma}{_r_255}{_r_comma}{_r_255}(?:{_r_comma}{_r_alpha})?\s*\)\s*"
# CSS3 HSL examples: hsl(270, 60%, 50%), hsla(270, 60%, 50%, 0.5), hsla(270, 60%, 50%, 50%)
r_hsl = rf"\s*hsla?\(\s*{_r_h}{_r_comma}{_r_sl}{_r_comma}{_r_sl}(?:{_r_comma}{_r_alpha})?\s*\)\s*"
# CSS4 RGB examples: rgb(0 0 0), rgb(0 0 0 / 0.5), rgb(0 0 0 / 50%), rgba(0 0 0 / 50%)
r_rgb_v4_style = (
    rf"\s*rgba?\(\s*{_r_255}\s+{_r_255}\s+{_r_255}(?:\s*/\s*{_r_alpha})?\s*\)\s*"
)
# CSS4 HSL examples: hsl(270 60% 50%), hsl(270 60% 50% / 0.5), hsl(270 60% 50% / 50%), hsla(270 60% 50% / 50%)
r_hsl_v4_style = (
    rf"\s*hsla?\(\s*{_r_h}\s+{_r_sl}\s+{_r_sl}(?:\s*/\s*{_r_alpha})?\s*\)\s*"
)

# colors where the two hex characters are the same, if all colors match this the short version of hex colors can be used
repeat_colors = {int(c * 2, 16) for c in "0123456789abcdef"}
rads = 2 * math.pi


class Color:
    """
    Represents a color.
    """

    __slots__ = "_original", "_rgba"

    def __init__(self, value: ColorType) -> None:
        self._rgba: GradientRGBA = GradientRGBA(0, 0, 0, 1)
        self._original: ColorType = value

        if isinstance(value, (tuple, list)):
            self._rgba = self.parse_tuple(value)

        elif isinstance(value, str):
            self._rgba = self.parse_str(value)

        elif isinstance(value, PyColor):
            r, g, b, a = value._rgba._tuple
            self._rgba = GradientRGBA(r, g, b, a)
            self._original = value._original

        elif isinstance(value, Color):
            self._rgba = value._rgba
            self._original = value._original

        elif isinstance(value, RichColor):
            assert value.triplet, "RichColor must have a triplet"
            self._rgba = self.parse_rich_color(value)
            self._original = value.triplet.hex
        else:
            raise PydanticCustomError(
                "color_error",
                "value is not a valid color: value must be a tuple, list or string",
            )

        # if we've got here value must be a valid color
        self._original = value

    def __rich__(self) -> Text:
        return Text.assemble(
            *[
                Text("Color", style="bold #ffffff"),
                Text("(", style="bold #ffffff"),
                Text(f"{self.as_named()}", style=f"bold {self.as_hex}"),
                Text(")", style="bold #ffffff"),
            ]
        )

    @property
    def rich(self) -> RichColor:
        return self.as_rich()

    def as_rich(self) -> RichColor:
        """
        Returns a `rich.color.Color` object representing the color.
        """
        try:
            RGBA = self._rgba
            red = self.float_to_255(RGBA.red)
            green = self.float_to_255(RGBA.green)
            blue = self.float_to_255(RGBA.blue)
            triplet = ColorTriplet(red=red, green=green, blue=blue)
        except ColorParseError as cpe:
            raise ColorParseError(f"Could not parse color: {self}") from cpe
        else:
            return RichColor.from_triplet(triplet)

    @classmethod
    def from_rich(cls, rich_color: RichColor) -> Color:
        try:
            triplet = rich_color.triplet
        except ColorParseError as cpe:
            raise ColorParseError(f"Could not parse color: {rich_color}") from cpe
        else:
            assert triplet, "ColorTriplet must not be None"
            red, green, blue = triplet.red, triplet.green, triplet.blue
            rgba = GradientRGBA(
                red=red / 255.0, green=green / 255.0, blue=blue / 255.0, alpha=None
            )
            return cls(rgba.triplet.hex)

    @property
    def style(self) -> Style:
        return self.as_style()

    def as_style(
        self,
        bgcolor: Optional[RichColor] = None,
        bold: Optional[bool] = None,
        dim: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        blink: Optional[bool] = None,
        blink2: Optional[bool] = None,
        reverse: Optional[bool] = None,
        conceal: Optional[bool] = None,
        strike: Optional[bool] = None,
        underline2: Optional[bool] = None,
        frame: Optional[bool] = None,
        encircle: Optional[bool] = None,
        overline: Optional[bool] = None,
        link: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Style:
        """
                A terminal style.

        A terminal style consists of the color (color), a background color (bgcolor), and a number of attributes, such
        as bold, italic etc. The attributes have 3 states: they can either be on (True), off (False), or not set (None).

        Args:
            bgcolor (RichColor, optional): Background color. Defaults to None.
            bold (bool, optional): Enable bold text. Defaults to None.
            dim (bool, optional): Enable dim text. Defaults to None.
            italic (bool, optional): Enable italic text. Defaults to None.
            underline (bool, optional): Enable underlined text. Defaults to None.
            blink (bool, optional): Enabled blinking text. Defaults to None.
            blink2 (bool, optional): Enable fast blinking text. Defaults to None.
            reverse (bool, optional): Enabled reverse text. Defaults to None.
            conceal (bool, optional): Enable concealed text. Defaults to None.
            strike (bool, optional): Enable strikethrough text. Defaults to None.
            underline2 (bool, optional): Enable doubly underlined text. Defaults to None.
            frame (bool, optional): Enable framed text. Defaults to None.
            encircle (bool, optional): Enable encircled text. Defaults to None.
            overline (bool, optional): Enable overlined text. Defaults to None.
            link (str, link): Link URL. Defaults to None.
        """

        return Style(
            color=self.as_rich(),
            bgcolor=bgcolor,
            bold=bold,
            dim=dim,
            italic=italic,
            underline=underline,
            blink=blink,
            blink2=blink2,
            reverse=reverse,
            conceal=conceal,
            strike=strike,
            underline2=underline2,
            frame=frame,
            encircle=encircle,
            overline=overline,
            link=link,
            meta=meta,
        )

    @property
    def bg_style(self) -> Style:
        return self.as_bg_style()

    def as_bg_style(
        self,
        color: Optional[RichColor] = None,
        bold: Optional[bool] = True,
        dim: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        blink: Optional[bool] = None,
        blink2: Optional[bool] = None,
        reverse: Optional[bool] = None,
        conceal: Optional[bool] = None,
        strike: Optional[bool] = None,
        underline2: Optional[bool] = None,
        frame: Optional[bool] = None,
        encircle: Optional[bool] = None,
        overline: Optional[bool] = None,
        link: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Style:
        """
                A terminal style.

        A terminal style consists of the color (color), a background color (bgcolor), and a number of attributes, such
        as bold, italic etc. The attributes have 3 states: they can either be on (True), off (False), or not set (None).

        Args:
            color (RichColor, optional): Foreground color. Defaults to None, which will generate a foreground color based on the contrast ratio.
            bold (bool, optional): Enable bold text. Defaults to True.
            dim (bool, optional): Enable dim text. Defaults to None.
            italic (bool, optional): Enable italic text. Defaults to None.
            underline (bool, optional): Enable underlined text. Defaults to None.
            blink (bool, optional): Enabled blinking text. Defaults to None.
            blink2 (bool, optional): Enable fast blinking text. Defaults to None.
            reverse (bool, optional): Enabled reverse text. Defaults to None.
            conceal (bool, optional): Enable concealed text. Defaults to None.
            strike (bool, optional): Enable strikethrough text. Defaults to None.
            underline2 (bool, optional): Enable doubly underlined text. Defaults to None.
            frame (bool, optional): Enable framed text. Defaults to None.
            encircle (bool, optional): Enable encircled text. Defaults to None.
            overline (bool, optional): Enable overlined text. Defaults to None.
            link (str, link): Link URL. Defaults to None.
        """
        if color is None:
            color = self.get_contrast()
        return Style(
            color=color,
            bgcolor=self.as_rich(),
            bold=bold,
            dim=dim,
            italic=italic,
            underline=underline,
            blink=blink,
            blink2=blink2,
            reverse=reverse,
            conceal=conceal,
            strike=strike,
            underline2=underline2,
            frame=frame,
            encircle=encircle,
            overline=overline,
            link=link,
            meta=meta,
        )

    def get_contrast(self) -> RichColor:
        """Generate a foreground color for the color style.

        Generate a foreground color for the color style based on the color's
        contrast ratio. If the color is dark, the foreground color will be
        white. If the color is light, the foreground color will be black.

        Returns:
            str: The foreground color.
        """
        import colorsys

        def rgb_to_hsv(color: Color) -> Tuple[float, float, float]:
            """Convert an RGB color to HSV."""
            rgba: GradientRGBA = color._rgba
            h, s, v = colorsys.rgb_to_hsv(r=rgba.red, g=rgba.green, b=rgba.blue)
            return h, s, v

        def hsv_to_hsl(hue, saturation, value):
            lightness = (
                (2 - saturation) * value / 2
                if value <= 0.5
                else saturation * value / (2 - saturation)
            )
            saturation = (
                0
                if lightness == 0 or lightness == 1
                else (value - lightness) / min(lightness, 1 - lightness)
            )
            return hue, saturation, lightness

        def color_distance(color1: Color, color2: Color):
            """Calculate the distance between two colors."""
            h1, s1, v1 = rgb_to_hsv(color1)
            h2, s2, v2 = rgb_to_hsv(color2)
            dh: float = min(abs(h1 - h2), 1 - abs(h1 - h2))
            ds: float = abs(s1 - s2)
            dv: float = abs(v1 - v2)
            color_distance: float = dh + ds + dv
            return color_distance

        def find_closest_color(color1: Color, color_list: List[Color]):
            """Calculate the closest color in a list."""
            closest_color = None
            min_distance = float("inf")
            for color in color_list:
                distance = color_distance(color1, color)
                if distance < min_distance:
                    min_distance = distance
                    closest_color = color
            return closest_color

        color_list: List[Color] = [Color("#000000"), Color("#ffffff")]
        closest = find_closest_color(
            self,
            color_list=color_list,
        )
        if closest == Color("#000000"):
            return Color("#ffffff").as_rich()
        else:
            return Color("#000000").as_rich()

    def get_alpha_style(self, bg_color: Optional[Color] = None) -> ColorTriplet:
        """Calculate the alpha value for the color style by blending it with the background color.

        Args:
            bg_color (Color): The background color.

        Returns:
            ColorTriplet: The color with alpha.
        """
        if bg_color is None:
            bg_color = Color("#000000")
        triplet: ColorTriplet = self.as_triplet()
        bg_triplet: ColorTriplet = bg_color.as_triplet()
        alpha = self._rgba.alpha
        if alpha is None:
            return triplet
        elif alpha == 1:
            return triplet
        elif alpha == 0:
            return bg_triplet
        else:
            return blend_rgb(triplet, bg_triplet, alpha)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        field_schema: dict[str, Any] = {}
        field_schema.update(type="string", format="color")
        return field_schema

    def original(self) -> ColorType:  # type: ignore
        """
        Original value passed to `Color`.
        """
        return self._original  # type: ignore

    @property
    def name(self) -> str:
        """
        The name of the color.add()

        Returns:
            str: The color name.
        """
        return str(self.as_named(fallback=True))

    def as_named(self, *, fallback: bool = True, verbose: bool = False) -> str:
        """
        Returns the name of the color if it can be found in `COLORS_BY_VALUE` dictionary,
        otherwise returns the hexadecimal representation of the color or raises `ValueError`.

        Args:
            fallback: If True, falls back to returning the hexadecimal representation of
                the color instead of raising a ValueError when no named color is found.

        Returns:
            The name of the color, or the hexadecimal representation of the color.

        Raises:
            ValueError: When no named color is found and fallback is `False`.
        """
        if self._rgba.alpha is None:
            rgb = cast(Tuple[int, int, int], self.as_rgb_tuple())
            if verbose:
                console = Console(color_system="truecolor")
                tr_install(console=console)
                # console.log("Entered Color.as_named()", log_locals=True)
            try:
                return COLORS_BY_VALUE[rgb]
            except KeyError as e:
                if fallback:
                    return self.as_hex()
                else:
                    raise ValueError(
                        "no named color found, use fallback=True, as_hex() or as_rgb()"
                    ) from e
        else:
            return self.as_hex()

    @property
    def hex(self) -> str:
        """
        Color as a 6 character hex string  ➡︎`#ffffff`
        """
        return self.as_hex(format="long")

    @property
    def hex_short(self) -> str:
        """
        Color as a short hex string  ➡︎`#fff`
        """
        return self.as_hex(format="short")

    def as_hex(self, format: Literal["short", "long"] = "short") -> str:
        """Returns the hexadecimal representation of the color.

        Hex string representing the color can be 3, 4, 6, or 8 characters depending on whether the string
        a "short" representation of the color is possible and whether there's an alpha channel.

        Returns:
            The hexadecimal representation of the color.
        """
        values = [self.float_to_255(c) for c in self._rgba[:3]]
        if self._rgba.alpha is not None:
            values.append(self.float_to_255(self._rgba.alpha))

        as_hex = "".join(f"{v:02x}" for v in values)
        if format == "short" and all(c in repeat_colors for c in values):
            as_hex = "".join(as_hex[c] for c in range(0, len(as_hex), 2))
        return f"#{as_hex}"

    @property
    def rgb(self) -> str:
        """
        Color as an `rgb(<r>, <g>, <b>)` or `rgba(<r>, <g>, <b>, <a>)` string.
        """
        return self.as_rgb()

    def as_rgb(self) -> str:
        """
        Color as an `rgb(<r>, <g>, <b>)` or `rgba(<r>, <g>, <b>, <a>)` string.
        """
        if self._rgba.alpha is None:
            return f"rgb({self.float_to_255(self._rgba.red)}, {self.float_to_255(self._rgba.green)}, {self.float_to_255(self._rgba.blue)})"
        else:
            return (
                f"rgba({self.float_to_255(self._rgba.red)}, {self.float_to_255(self._rgba.green)}, {self.float_to_255(self._rgba.blue)}, "
                f"{round(self._alpha_float(), 2)})"
            )

    @property
    def rgb_tuple(self) -> GradientColorTuple:
        """Return the color as an RGB or RGBA tuple."""
        return self.as_rgb_tuple()

    def as_rgb_tuple(self, *, alpha: bool | None = None) -> GradientColorTuple:
        """
        Returns the color as an RGB or RGBA tuple.

        Args:
            alpha: Whether to include the alpha channel. There are three options for this input:

                - `None` (default): Include alpha only if it's set. (e.g. not `None`)
                - `True`: Always include alpha.
                - `False`: Always omit alpha.

        Returns:
            A tuple that contains the values of the red, green, and blue channels in the range 0 to 255.
                If alpha is included, it is in the range 0 to 1.
        """
        r, g, b = (self.float_to_255(c) for c in self._rgba[:3])
        if alpha is None:
            if self._rgba.alpha is None:
                return r, g, b
            else:
                return r, g, b, self._alpha_float()
        elif alpha:
            return r, g, b, self._alpha_float()
        else:
            # alpha is False
            return r, g, b

    @property
    def triplet(self) -> ColorTriplet:
        """Return the color as a ColorTriplet."""
        return self.as_triplet()

    def as_triplet(self) -> ColorTriplet:
        """Return the color as a ColorTriplet."""
        return self._rgba.as_triplet()

    @property
    def hsl(self) -> str:
        """
        Color as an `hsl(<h>, <s>, <l>)` or `hsl(<h>, <s>, <l>, <a>)` string.
        """
        return self.as_hsl()

    def as_hsl(self) -> str:
        """
        Color as an `hsl(<h>, <s>, <l>)` or `hsl(<h>, <s>, <l>, <a>)` string.
        """
        if self._rgba.alpha is None:
            h, s, li = self.as_hsl_tuple(alpha=False)  # type: ignore
            return f"hsl({h * 360:0.0f}, {s:0.0%}, {li:0.0%})"
        else:
            h, s, li, a = self.as_hsl_tuple(alpha=True)  # type: ignore
            return f"hsl({h * 360:0.0f}, {s:0.0%}, {li:0.0%}, {round(a, 2)})"

    def as_hsl_tuple(self, *, alpha: bool | None = None) -> HslColorTuple:
        """
        Returns the color as an HSL or HSLA tuple.

        Args:
            alpha: Whether to include the alpha channel.

                - `None` (default): Include the alpha channel only if it's set (e.g. not `None`).
                - `True`: Always include alpha.
                - `False`: Always omit alpha.

        Returns:
            The color as a tuple of hue, saturation, lightness, and alpha (if included).
                All elements are in the range 0 to 1.

        Note:
            This is HSL as used in HTML and most other places, not HLS as used in Python's `colorsys`.
        """
        h, l, s = rgb_to_hls(  # noqa: E741
            self._rgba.red, self._rgba.green, self._rgba.blue
        )  # noqa: E741
        if alpha is None:
            if self._rgba.alpha is None:
                return h, s, l
            else:
                return h, s, l, self._alpha_float()
        if alpha:
            return h, s, l, self._alpha_float()
        else:
            # alpha is False
            return h, s, l

    def _alpha_float(self) -> float:
        """
        Returns a float value representing the alpha channel of the RGBA color.
        """
        return 1 if self._rgba.alpha is None else self._rgba.alpha

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[Any], handler: Callable[[Any], CoreSchema]
    ) -> core_schema.CoreSchema:
        return core_schema.with_info_plain_validator_function(
            cls._validate, serialization=core_schema.to_string_ser_schema()
        )

    @classmethod
    def _validate(cls, __input_value: Any, _: Any) -> Color:
        return cls(__input_value)

    def __str__(self) -> str:
        return str(self.as_named(fallback=True))

    def __repr__(self) -> str:
        return f"Color{self._original}"

    def __repr_args__(self) -> _repr.ReprArgs:
        return [(None, self.as_named(fallback=True))] + [("rgb", self.as_rgb_tuple())]

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Color) and self.as_rgb_tuple() == other.as_rgb_tuple()

    def __hash__(self) -> int:
        return hash(self.as_rgb_tuple())

    @classmethod
    def parse_rich_color(cls, value: RichColor) -> GradientRGBA:
        """
        Parse a RichColor to an RGBA tuple.

        Args:
            value: A RichColor instance.

        Returns:
            An `RGBA` tuple parsed from the input RichColor.
        """
        triplet = value.triplet
        if not triplet:
            raise PydanticCustomError(
                "color_error", "value is not a valid color: triplet is None"
            )
        return cls.ints_to_rgba(triplet.red, triplet.green, triplet.blue, None)

    @classmethod
    def parse_tuple(cls, value: tuple[Any, ...] | List[Any]) -> GradientRGBA:
        """Parse a tuple or list to get RGBA values.

        Args:
            value: A tuple or list.

        Returns:
            An `RGBA` tuple parsed from the input tuple.

        Raises:
            PydanticCustomError: If tuple is not valid.
        """
        if len(value) == 3:
            r, g, b = (cls.parse_color_value(v) for v in value)
            return GradientRGBA(r, g, b, None)
        elif len(value) == 4:
            r, g, b = (cls.parse_color_value(v) for v in value[:3])
            return GradientRGBA(r, g, b, cls.parse_float_alpha(value[3]))
        else:
            raise PydanticCustomError(
                "color_error",
                "value is not a valid color: tuples must have length 3 or 4",
            )

    @classmethod
    def parse_str(cls, value: str) -> GradientRGBA:
        """
        Parse a string representing a color to an RGBA tuple.

        Possible formats for the input string include:

        * named color, see `COLORS_BY_NAME`
        * hex short eg. `<prefix>fff` (prefix can be `#`, `0x` or nothing)
        * hex long eg. `<prefix>ffffff` (prefix can be `#`, `0x` or nothing)
        * `rgb(<red>, <green>, <blue>)`
        * `rgba(<red>, <green>, <blue>, <alpha>)`
        * `transparent`

        Args:
            value: A string representing a color.

        Returns:
            An `RGBA` tuple parsed from the input string.

        Raises:
            ValueError: If the input string cannot be parsed to an RGBA tuple.
        """
        log = Log(console=get_console())
        log.debug(f"Entered Color.parse_str({value})")

        value_lower = value.lower()
        log.debug(f"value_lower: {value_lower}")
        try:
            red, green, blue = COLORS_BY_NAME[value_lower]
            log.debug(f"red: {red}, green: {green}, blue:{blue}")
        except KeyError:
            log.debug(f"KeyError: {value_lower}")
            pass
        else:
            return cls.ints_to_rgba(red, green, blue, None)

        m = re.fullmatch(r_hex_short, value_lower)
        if m:
            *rgb, a = m.groups()
            red, green, blue = (int(v * 2, 16) for v in rgb)
            if a:
                alpha: float | None = int(a * 2, 16) / 255
            else:
                alpha = None
            return cls.ints_to_rgba(red, green, blue, alpha)

        m = re.fullmatch(r_hex_long, value_lower)
        if m:
            *rgb, a = m.groups()
            red, green, blue = (int(v, 16) for v in rgb)
            if a:
                alpha = int(a, 16) / 255
            else:
                alpha = None
            return cls.ints_to_rgba(red, green, blue, alpha)

        m = re.fullmatch(r_rgb, value_lower) or re.fullmatch(
            r_rgb_v4_style, value_lower
        )
        if m:
            return cls.ints_to_rgba(*m.groups())  # type: ignore

        m = re.fullmatch(r_hsl, value_lower) or re.fullmatch(
            r_hsl_v4_style, value_lower
        )
        if m:
            return cls.parse_hsl(*m.groups())  # type: ignore

        if value_lower == "transparent":
            return GradientRGBA(0, 0, 0, 0)
        raise PydanticCustomError(
            "color_error",
            "value is not a valid color: string not recognised as a valid color",
        )

    @classmethod
    def ints_to_rgba(
        cls,
        red: int | str,
        green: int | str,
        blue: int | str,
        alpha: float | None = None,
    ) -> GradientRGBA:
        """
        Converts integer or string values for RGB color and an optional alpha value to an `RGBA` object.

        Args:
            red: An integer or string representing the red color value.
            green: An integer or string representing the green color value.
            blue: An integer or string representing the blue color value.
            alpha: A float representing the alpha value. Defaults to None.

        Returns:
            An instance of the `RGBA` class with the corresponding color and alpha values.
        """
        return GradientRGBA(
            cls.parse_color_value(red),
            cls.parse_color_value(green),
            cls.parse_color_value(blue),
            cls.parse_float_alpha(alpha),
        )

    @staticmethod
    def parse_color_value(value: int | str, max_val: int = 255) -> float:
        """
        Parse the color value provided and return a number between 0 and 1.

        Args:
            value: An integer or string color value.
            max_val: Maximum range value. Defaults to 255.

        Raises:
            PydanticCustomError: If the value is not a valid color.

        Returns:
            A number between 0 and 1.
        """
        try:
            color = float(value)
        except ValueError:
            raise PydanticCustomError(
                "color_error",
                "value is not a valid color: color values must be a valid number",
            )
        if 0 <= color <= max_val:
            return color / max_val
        else:
            raise PydanticCustomError(
                "color_error",
                "Value is not a valid color: color values must be in the range 0 to {max_val}",
                {"max_val": max_val},
            )

    @staticmethod
    def parse_float_alpha(value: None | str | float | int) -> float | None:
        """
        Parse an alpha value checking it's a valid float in the range 0 to 1.

        Args:
            value: The input value to parse.

        Returns:
            The parsed value as a float, or `None` if the value was None or equal 1.

        Raises:
            PydanticCustomError: If the input value cannot be successfully parsed as a float in the expected range.
        """
        if value is None:
            return None
        try:
            if isinstance(value, str) and value.endswith("%"):
                alpha = float(value[:-1]) / 100
            else:
                alpha = float(value)
        except ValueError:
            raise PydanticCustomError(
                "color_error",
                "value is not a valid color: alpha values must be a valid float",
            )

        if math.isclose(alpha, 1):
            return None
        elif 0 <= alpha <= 1:
            return alpha
        else:
            raise PydanticCustomError(
                "color_error",
                "value is not a valid color: alpha values must be in the range 0 to 1",
            )

    @classmethod
    def parse_hsl(
        cls, h: str, h_units: str, sat: str, light: str, alpha: float | None = None
    ) -> GradientRGBA:
        """
        Parse raw hue, saturation, lightness, and alpha values and convert to RGBA.

        Args:
            h: The hue value.
            h_units: The unit for hue value.
            sat: The saturation value.
            light: The lightness value.
            alpha: Alpha value.

        Returns:
            An instance of `RGBA`.
        """
        s_value, l_value = (
            cls.parse_color_value(sat, 100),
            cls.parse_color_value(light, 100),
        )

        h_value = float(h)
        if h_units in {None, "deg"}:
            h_value = h_value % 360 / 360
        elif h_units == "rad":
            h_value = h_value % rads / rads
        else:
            # turns
            h_value = h_value % 1

        r, g, b = hls_to_rgb(h_value, l_value, s_value)
        return GradientRGBA(r, g, b, cls.parse_float_alpha(alpha))

    @staticmethod
    def float_to_255(c: float) -> int:
        """
        Converts a float value between 0 and 1 (inclusive) to an integer between 0 and 255 (inclusive).

        Args:
            c: The float value to be converted. Must be between 0 and 1 (inclusive).

        Returns:
            The integer equivalent of the given float value rounded to the nearest whole number.
        """
        return round(c * 255)

    @classmethod
    def generate_table(
        cls, title: str, show_index: bool = True, caption: Optional[Text] = None
    ) -> Table:
        """
        Generate a table to display colors.

        Args:
            title: The title for the table.
            show_index: Whether to show the index column.

        Returns:
            A `rich.table.Table` instance.
        """
        color_title = cls.colortitle(title)
        table = Table(
            title=color_title, expand=False, caption=caption, caption_justify="right"
        )
        if show_index:
            table.add_column(cls.colortitle("Index"), style="bold", justify="right")
        table.add_column(cls.colortitle("Sample"), style="bold", justify="center")
        table.add_column(cls.colortitle("Name"), style="bold", justify="left")
        table.add_column(cls.colortitle("Hex"), style="bold", justify="left")
        table.add_column(cls.colortitle("RGB"), style="bold", justify="left")
        return table

    @classmethod
    def colortitle(cls, title: str) -> Text:
        """Return the colored title."""
        title_list: List[str] = list(title)
        length = len(title)
        COLORS = cycle(
            [
                "#FF00FF",
                "#AF00FF",
                "#5F00FF",
                "#0000FF",
                "#0055FF",
                "#0080FF",
                "#00C0FF",
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
            ]
        )
        color_title = Text()
        # randomize
        for _ in range(randint(0, 16)):
            next(COLORS)
        for index in range(length):
            char: str = title_list[index]
            color: str = next(COLORS)
            color_title.append(Text(char, style=f"bold {color}"))
        return color_title

    @classmethod
    def color_table(
        cls,
        title: str,
        start: int,
        end: int,
        caption: Optional[Text] = None,
        *,
        show_index: bool = False,
    ) -> Table:
        table = cls.generate_table(title, show_index, caption)
        for index, (key, _) in enumerate(COLORS_BY_NAME.items()):
            if index < start:
                continue
            elif index > end:
                break
            color = Color(key)

            color_index = Text(f"{index: >3}", style=color.as_style(bold=True))
            style = color.as_style(bold=True)
            sample = Text(f"{'█' * 10}", style=style)
            name = Text(f"{key.capitalize(): <20}", style=style)
            hex_str = f" {color.as_hex('long').upper()} "
            hex = Text(f"{hex_str: ^7}", style=color.as_bg_style())
            triplet = color._rgba.as_triplet()
            red = Text(f"{triplet.red: >3}", style=Color("#f00").style)
            green = Text(f"{triplet.green: >3}", style=Color("#0f0").style)
            blue = Text(f"{triplet.blue: >3}", style=Color("#00afff").style)
            rgb = Text.assemble(
                *[
                    Text("rgb", style=color.as_style(bold=True)),
                    Text("(", style="b #ffffff"),
                    red,
                    Text(",", style="b #ffffff"),
                    green,
                    Text(",", style="b #ffffff"),
                    blue,
                    Text(")", style="b #ffffff"),
                ]
            )
            if show_index:
                table.add_row(color_index, sample, name, hex, rgb)
            else:
                table.add_row(sample, name, hex, rgb)
        return table

    @classmethod
    def example(cls, record: bool = False):
        from rich.console import Console

        console = Console(record=True) if record else Console()

        def table_generator() -> Generator:
            tables: List[Tuple[str, int, int, Optional[Text]]] = [
                (
                    "Gradient Colors",
                    0,
                    17,
                    Text(
                        "These colors have been adapted to make naming easier.",
                        style="i d #ffffff",
                    ),
                ),
                ("CSS3 Colors", 18, 147, None),
                ("Rich Colors", 148, 342, None),
            ]
            for table in tables:
                yield table

        for title, start, end, caption in table_generator():
            console.line(2)
            table = cls.color_table(title, start, end, caption=caption)
            console.print(table, justify="center")
            console.line(2)

        if record:
            try:
                console.save_svg("docs/img/colors.svg")
            except TypeError:
                pass


COLORS_BY_NAME: Dict[str, Tuple[int, int, int]] = {
    "magenta": (255, 0, 255),
    "purple": (175, 0, 255),
    "violet": (95, 0, 255),
    "blue": (0, 0, 255),
    "dodgerblue": (0, 85, 255),
    "deepskyblue": (0, 135, 255),
    "lightskyblue": (0, 195, 255),
    "cyan": (0, 255, 255),
    "springgreen": (0, 255, 175),
    "lime": (0, 255, 0),
    "greenyellow": (175, 255, 0),
    "yellow": (255, 255, 0),
    "orange": (255, 175, 0),
    "darkorange": (255, 135, 0),
    "tomato": (255, 75, 0),
    "red": (255, 0, 0),
    "deeppink": (255, 0, 95),
    "hotpink": (255, 0, 175),
    "aliceblue": (240, 248, 255),
    "antiquewhite": (250, 235, 215),
    "aquamarine": (127, 255, 212),
    "azure": (240, 255, 255),
    "beige": (245, 245, 220),
    "bisque": (255, 228, 196),
    "black": (0, 0, 0),
    "blanchedalmond": (255, 235, 205),
    "brown": (165, 42, 42),
    "burlywood": (222, 184, 135),
    "cadetblue": (95, 158, 160),
    "chartreuse": (127, 255, 0),
    "chocolate": (210, 105, 30),
    "coral": (255, 127, 80),
    "cornflowerblue": (100, 149, 237),
    "cornsilk": (255, 248, 220),
    "crimson": (220, 20, 60),
    "darkblue": (0, 0, 139),
    "darkcyan": (0, 139, 139),
    "darkgoldenrod": (184, 134, 11),
    "darkgray": (169, 169, 169),
    "darkgreen": (0, 100, 0),
    "darkgrey": (169, 169, 169),
    "darkkhaki": (189, 183, 107),
    "darkmagenta": (139, 0, 139),
    "darkolivegreen": (85, 107, 47),
    "cssdarkorange": (255, 140, 0),
    "darkorchid": (153, 50, 204),
    "darkred": (139, 0, 0),
    "darksalmon": (233, 150, 122),
    "darkseagreen": (143, 188, 143),
    "darkslateblue": (72, 61, 139),
    "darkslategray": (47, 79, 79),
    "darkslategrey": (47, 79, 79),
    "darkturquoise": (0, 206, 209),
    "darkviolet": (148, 0, 211),
    "deepskyblue_css": (0, 191, 255),
    "dimgray": (105, 105, 105),
    "dimgrey": (105, 105, 105),
    "dodgerblue_css": (30, 144, 255),
    "firebrick": (178, 34, 34),
    "floralwhite": (255, 250, 240),
    "forestgreen": (34, 139, 34),
    "gainsboro": (220, 220, 220),
    "ghostwhite": (248, 248, 255),
    "gold": (255, 215, 0),
    "goldenrod": (218, 165, 32),
    "gray": (128, 128, 128),
    "green": (0, 128, 0),
    "greenyellow_css": (173, 255, 47),
    "grey": (128, 128, 128),
    "honeydew": (240, 255, 240),
    "hotpink_css": (255, 105, 180),
    "indianred": (205, 92, 92),
    "indigo": (75, 0, 130),
    "ivory": (255, 255, 240),
    "khaki": (240, 230, 140),
    "lavender": (230, 230, 250),
    "lavenderblush": (255, 240, 245),
    "lawngreen": (124, 252, 0),
    "lemonchiffon": (255, 250, 205),
    "lightblue": (173, 216, 230),
    "lightcoral": (240, 128, 128),
    "lightcyan": (224, 255, 255),
    "lightgoldenrodyellow": (250, 250, 210),
    "lightgray": (211, 211, 211),
    "lightgreen": (144, 238, 144),
    "lightgrey": (211, 211, 211),
    "lightpink": (255, 182, 193),
    "lightsalmon": (255, 160, 122),
    "lightseagreen": (32, 178, 170),
    "lightskyblue_css": (135, 206, 250),
    "lightslategray": (119, 136, 153),
    "lightslategrey": (119, 136, 153),
    "lightsteelblue": (176, 196, 222),
    "lightyellow": (255, 255, 224),
    "limegreen": (50, 205, 50),
    "linen": (250, 240, 230),
    "maroon": (128, 0, 0),
    "mediumaquamarine": (102, 205, 170),
    "mediumblue": (0, 0, 205),
    "mediumorchid": (186, 85, 211),
    "mediumpurple": (147, 112, 219),
    "mediumseagreen": (60, 179, 113),
    "mediumslateblue": (123, 104, 238),
    "mediumspringgreen": (0, 250, 154),
    "mediumturquoise": (72, 209, 204),
    "mediumvioletred": (199, 21, 133),
    "midnightblue": (25, 25, 112),
    "mintcream": (245, 255, 250),
    "mistyrose": (255, 228, 225),
    "moccasin": (255, 228, 181),
    "navajowhite": (255, 222, 173),
    "navy": (0, 0, 128),
    "oldlace": (253, 245, 230),
    "olive": (128, 128, 0),
    "olivedrab": (107, 142, 35),
    "orchid": (218, 112, 214),
    "palegoldenrod": (238, 232, 170),
    "palegreen": (152, 251, 152),
    "paleturquoise": (175, 238, 238),
    "palevioletred": (219, 112, 147),
    "papayawhip": (255, 239, 213),
    "peachpuff": (255, 218, 185),
    "peru": (205, 133, 63),
    "pink": (255, 192, 203),
    "plum": (221, 160, 221),
    "powderblue": (176, 224, 230),
    "rosybrown": (188, 143, 143),
    "royalblue": (65, 105, 225),
    "saddlebrown": (139, 69, 19),
    "salmon": (250, 128, 114),
    "sandybrown": (244, 164, 96),
    "seagreen": (46, 139, 87),
    "seashell": (255, 245, 238),
    "sienna": (160, 82, 45),
    "silver": (192, 192, 192),
    "slateblue": (106, 90, 205),
    "slategray": (112, 128, 144),
    "slategrey": (112, 128, 144),
    "snow": (255, 250, 250),
    "steelblue": (70, 130, 180),
    "tan": (210, 180, 140),
    "teal": (0, 128, 128),
    "thistle": (216, 191, 216),
    "csstomato": (255, 99, 71),
    "turquoise": (64, 224, 208),
    "violet_css": (238, 130, 238),
    "wheat": (245, 222, 179),
    "white": (255, 255, 255),
    "whitesmoke": (245, 245, 245),
    "yellowgreen": (154, 205, 50),
    "bright_black": (45, 45, 45),
    "bright_red": (210, 0, 0),
    "bright_green": (0, 210, 0),
    "bright_yellow": (210, 210, 0),
    "bright_blue": (0, 0, 210),
    "bright_magenta": (210, 0, 210),
    "bright_cyan": (0, 210, 210),
    "bright_white": (210, 210, 210),
    "grey0": (0, 0, 0),
    "navy_blue": (0, 0, 95),
    "dark_blue": (0, 0, 135),
    "blue3": (0, 0, 215),
    "dark_green": (0, 95, 0),
    "deep_sky_blue4": (0, 95, 175),
    "dodger_blue3": (0, 95, 215),
    "green4": (0, 135, 0),
    "spring_green4": (0, 135, 95),
    "turquoise4": (0, 135, 135),
    "deep_sky_blue3": (0, 135, 215),
    "dark_cyan": (0, 175, 135),
    "light_sea_green": (0, 175, 175),
    "deep_sky_blue2": (0, 175, 215),
    "green3": (0, 215, 0),
    "spring_green3": (0, 215, 95),
    "cyan3": (0, 215, 175),
    "dark_turquoise": (0, 215, 215),
    "turquoise2": (0, 215, 255),
    "spring_green2": (0, 255, 95),
    "cyan2": (0, 255, 215),
    "purple4": (95, 0, 175),
    "purple3": (95, 0, 215),
    "grey37": (95, 95, 95),
    "medium_purple4": (95, 95, 135),
    "slate_blue3": (95, 95, 215),
    "royal_blue1": (95, 95, 255),
    "chartreuse4": (95, 135, 0),
    "pale_turquoise4": (95, 135, 135),
    "steel_blue": (95, 135, 175),
    "steel_blue3": (95, 135, 215),
    "cornflower_blue": (95, 135, 255),
    "dark_sea_green4": (95, 175, 95),
    "cadet_blue": (95, 175, 175),
    "sky_blue3": (95, 175, 215),
    "chartreuse3": (95, 215, 0),
    "sea_green3": (95, 215, 135),
    "aquamarine3": (95, 215, 175),
    "medium_turquoise": (95, 215, 215),
    "steel_blue1": (95, 215, 255),
    "sea_green2": (95, 255, 95),
    "sea_green1": (95, 255, 175),
    "dark_slate_gray2": (95, 255, 255),
    "dark_red": (135, 0, 0),
    "dark_magenta": (135, 0, 175),
    "orange4": (135, 95, 0),
    "light_pink4": (135, 95, 95),
    "plum4": (135, 95, 135),
    "medium_purple3": (135, 95, 215),
    "slate_blue1": (135, 95, 255),
    "wheat4": (135, 135, 95),
    "grey53": (135, 135, 135),
    "light_slate_grey": (135, 135, 175),
    "medium_purple": (135, 135, 215),
    "light_slate_blue": (135, 135, 255),
    "yellow4": (135, 175, 0),
    "dark_sea_green": (135, 175, 135),
    "light_sky_blue3": (135, 175, 215),
    "sky_blue2": (135, 175, 255),
    "chartreuse2": (135, 215, 0),
    "pale_green3": (135, 215, 135),
    "dark_slate_gray3": (135, 215, 215),
    "sky_blue1": (135, 215, 255),
    "light_green": (135, 255, 135),
    "aquamarine1": (135, 255, 215),
    "dark_slate_gray1": (135, 255, 255),
    "deep_pink4": (175, 0, 95),
    "medium_violet_red": (175, 0, 135),
    "dark_violet": (175, 0, 215),
    "medium_orchid3": (175, 95, 175),
    "medium_orchid": (175, 95, 215),
    "dark_goldenrod": (175, 135, 0),
    "rosy_brown": (175, 135, 135),
    "grey63": (175, 135, 175),
    "medium_purple2": (175, 135, 215),
    "medium_purple1": (175, 135, 255),
    "dark_khaki": (175, 175, 95),
    "navajo_white3": (175, 175, 135),
    "grey69": (175, 175, 175),
    "light_steel_blue3": (175, 175, 215),
    "light_steel_blue": (175, 175, 255),
    "dark_olive_green3": (175, 215, 95),
    "dark_sea_green3": (175, 215, 135),
    "light_cyan3": (175, 215, 215),
    "light_sky_blue1": (175, 215, 255),
    "dark_olive_green2": (175, 255, 95),
    "pale_green1": (175, 255, 135),
    "dark_sea_green2": (175, 255, 175),
    "pale_turquoise1": (175, 255, 255),
    "red3": (215, 0, 0),
    "deep_pink3": (215, 0, 135),
    "magenta3": (215, 0, 215),
    "dark_orange3": (215, 95, 0),
    "indian_red": (215, 95, 95),
    "hot_pink3": (215, 95, 135),
    "hot_pink2": (215, 95, 175),
    "orange3": (215, 135, 0),
    "light_salmon3": (215, 135, 95),
    "light_pink3": (215, 135, 135),
    "pink3": (215, 135, 175),
    "plum3": (215, 135, 215),
    "gold3": (215, 175, 0),
    "light_goldenrod3": (215, 175, 95),
    "misty_rose3": (215, 175, 175),
    "thistle3": (215, 175, 215),
    "plum2": (215, 175, 255),
    "yellow3": (215, 215, 0),
    "khaki3": (215, 215, 95),
    "light_yellow3": (215, 215, 175),
    "grey84": (215, 215, 215),
    "light_steel_blue1": (215, 215, 255),
    "yellow2": (215, 255, 0),
    "dark_olive_green1": (215, 255, 135),
    "dark_sea_green1": (215, 255, 175),
    "honeydew2": (215, 255, 215),
    "light_cyan1": (215, 255, 255),
    "magenta2": (255, 0, 215),
    "indian_red1": (255, 95, 135),
    "hot_pink": (255, 95, 215),
    "medium_orchid1": (255, 95, 255),
    "dark_orange": (255, 135, 0),
    "salmon1": (255, 135, 95),
    "light_coral": (255, 135, 135),
    "pale_violet_red1": (255, 135, 175),
    "orchid2": (255, 135, 215),
    "orchid1": (255, 135, 255),
    "sandy_brown": (255, 175, 95),
    "light_salmon1": (255, 175, 135),
    "light_pink1": (255, 175, 175),
    "pink1": (255, 175, 215),
    "plum1": (255, 175, 255),
    "gold1": (255, 215, 0),
    "light_goldenrod2": (255, 215, 135),
    "navajo_white1": (255, 215, 175),
    "misty_rose1": (255, 215, 215),
    "thistle1": (255, 215, 255),
    "light_goldenrod1": (255, 255, 95),
    "khaki1": (255, 255, 135),
    "wheat1": (255, 255, 175),
    "cornsilk1": (255, 255, 215),
    "grey100": (255, 255, 255),
    "grey3": (8, 8, 8),
    "grey7": (18, 18, 18),
    "grey11": (28, 28, 28),
    "grey15": (38, 38, 38),
    "grey19": (48, 48, 48),
    "grey23": (58, 58, 58),
    "grey27": (68, 68, 68),
    "grey30": (78, 78, 78),
    "grey35": (88, 88, 88),
    "grey39": (98, 98, 98),
    "grey42": (108, 108, 108),
    "grey46": (118, 118, 118),
    "grey50": (128, 128, 128),
    "grey54": (138, 138, 138),
    "grey58": (148, 148, 148),
    "grey62": (158, 158, 158),
    "grey66": (168, 168, 168),
    "grey70": (178, 178, 178),
    "grey74": (188, 188, 188),
    "grey78": (198, 198, 198),
    "grey82": (208, 208, 208),
    "grey85": (218, 218, 218),
    "grey89": (228, 228, 228),
    "grey93": (238, 238, 238),
}

COLORS_BY_VALUE = {v: k for k, v in COLORS_BY_NAME.items()}


if __name__ == "__main__":  # pragma: no cover
    Color.example(record=True)
