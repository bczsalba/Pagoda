"""Pagoda's general widget module."""

from __future__ import annotations

from typing import Any
import pytermgui as ptg


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


class Menubar(ptg.Window):
    """A menubar to hoist at the top of the screen."""

    pos = ptg.terminal.origin
    is_noblur = True
    is_static = True
    is_noresize = True

    def __init__(self, *buttons, **attrs) -> None:
        """Initialize menubar."""

        super().__init__(**attrs)

        self.width = ptg.terminal.width

        for button in buttons:
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
