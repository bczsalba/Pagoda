"""Pagoda's general widget module."""

from __future__ import annotations

import os
import inspect
from typing import Any, Callable

import pytermgui as ptg
from teahaz import Teacup


TEMP_DEFAULTS = {
    key.rsplit("_", 1)[-1].lower(): os.environ.get(key)
    for key in [
        "PAGODA_URL",
        "PAGODA_CONV_NAME",
        "PAGODA_USERNAME",
        "PAGODA_PASSWORD",
    ]
}


def get_inputbox(
    title: str, field: ptg.InputField | None = None, **field_attrs: Any
) -> ptg.Container:
    """Gets an inputbox."""

    box = ptg.Container()

    box.box = ptg.boxes.SINGLE
    chars = list(box.chars["corner"]).copy()
    chars[0] += " " + title + " "
    box.set_char("corner", chars)

    if field is None:
        field = ptg.InputField(**field_attrs)

    box += field

    return box


class Menubar(ptg.Container):
    """A menubar to hoist at the top of the screen."""

    parent_align = ptg.HorizontalAlignment.LEFT

    def __init__(self, *buttons, **attrs) -> None:
        """Initialize menubar."""

        super().__init__(**attrs)

        self.width = ptg.terminal.width

        for button in buttons:
            if not isinstance(button, ptg.Widget):
                button = ptg.Widget.from_data(button)
                assert button is not None

            line = button.get_lines()[0]
            button.width = ptg.real_length(line)
            self._add_widget(button)

    def close(self) -> None:
        """Do not close this window."""

    def get_lines(self) -> list[str]:
        """Does magic"""

        lines: list[str] = []
        line = ""
        for widget in self._widgets:
            widget.pos = (self.pos[0] + ptg.real_length(line), self.pos[1] + len(lines))
            line += widget.get_lines()[0]

        lines.append(line)
        return lines


class Header(ptg.Container):
    """A simple header bar widget to use inside of Windows."""

    styles = ptg.Container.styles.copy()

    def __init__(self, label: str, **attrs) -> None:
        """Initializes a Header widget."""

        super().__init__(**attrs)

        self._label = ptg.Label(label)
        self._add_widget(self._label)

        chars = list(self._get_char("border"))
        chars[0] = ""
        chars[1] = ""
        chars[2] = ""

        self.set_char("corner", [""] * 4)
        self.set_char("border", chars)

    @property
    def label(self) -> str:
        """The string this header will display.

        Args:
            new: The new value for the header label.

        Returns:
            The current header string.
        """

        return self._label.value

    @label.setter
    def label(self, new: str) -> None:
        """Sets a new label. See the property definiton for
        more information."""

        self._label.value = new


def from_signature(
    method: Callable[..., Any], handle_output: Callable[..., Any]
) -> ptg.Window:
    """Creates a window from a function signature.

    Args:
        method: The method to generate window from.
        handle_output: The output handler. Its signature depends on the method given.

    Returns:
        A window with InputFields for all parameters for the method.
    """

    window = ptg.Window(width=70)
    window += Header("[title]" + method.__name__.title().replace("_", " "))
    window += ""

    # Add documentation's first line if it is found
    if method.__doc__ is not None:
        doc = method.__doc__
        window += ptg.Label("[245 italic] > " + doc.splitlines()[0], parent_align=0)

    window += ""

    # Construct widgets based on method signature
    fields: dict[str, Callable[[], str]] = {}
    for param in inspect.signature(method).parameters.values():
        default = param.default

        if param.default == inspect.Signature.empty:
            default = TEMP_DEFAULTS.get(param.name, "")

        field = ptg.InputField(value=default or "")
        window += get_inputbox(param.name.title(), field)

        # Mypy cannot infer type, yet providing it doesn't help.
        fields[param.name] = lambda field=field: field.value  # type: ignore

    # Create submission button
    # TODO: This should open a loader modal.
    threaded = Teacup.threaded(
        method, lambda *args, **kwargs: handle_output(window, *args, **kwargs)
    )
    window += ptg.Button(
        "Submit!",
        lambda *_: threaded(**{key: value() for key, value in fields.items()}),
    )

    return window
