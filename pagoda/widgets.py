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

        chars = ptg.boxes.SINGLE.borders.copy()
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


class ToggleSection(ptg.Container):
    """A toggleable "section"."""

    chars = {
        "indicator_open": "▼ ",
        "indicator_closed": "▶ ",
    }

    parent_align = ptg.HorizontalAlignment.LEFT

    def __init__(self, title: str | ptg.Widget, **attrs) -> None:
        """Initializes a ToggleSection.

        Args:
            title: The title that will be visible regardless of toggle
                state.
        """

        self._is_expanded = False
        self._ignore_mouse = False

        super().__init__(**attrs)

        self.title = title
        self._add_widget(title)
        self._widgets.insert(0, self._widgets.pop())

    @property
    def sidelength(self) -> int:
        """Returns 0."""

        return 0

    def __iadd__(self, other: object) -> ToggleSection:
        """Adds other, returns self."""

        super().__iadd__(other)
        return self

    def toggle(self) -> None:
        """Toggles self._is_expanded."""

        self._is_expanded = not self._is_expanded

    def get_lines(self) -> list[str]:
        """Gets a list of lines depending on self._is_expanded."""

        if len(self._widgets) == 0:
            return []

        char = self._get_char(
            "indicator_" + ("open" if self._is_expanded else "closed")
        )
        assert isinstance(char, str)

        title = self._widgets[0]
        assert isinstance(title, ptg.Label), (title, type(title))

        self._update_width(title)

        old_value = title.value
        title.value = char + old_value

        align, _ = self._get_aligners(title, ("", ""))
        lines = [align(line) for line in self._widgets[0].get_lines()]
        title.value = old_value

        if self._is_expanded:
            for widget in self._widgets[1:]:
                align, offset = self._get_aligners(widget, ("", ""))
                self._update_width(widget)

                widget.pos = self.pos[0] + offset, self.pos[1] + len(lines)
                for line in widget.get_lines():
                    lines.append(align(line))

        self.height = len(lines)

        return lines

    def handle_mouse(self, event: ptg.MouseEvent) -> bool:
        """Handles a mouse event.

        Clicking on the title will toggle the widgets contained within,
        and interacting anywhere else will be passed to the children.

        Args:
            event: The event to handle.
        """

        if (
            event.action is ptg.MouseAction.LEFT_CLICK
            and event.position[1] == self.pos[1]
        ):
            self.toggle()
            self._ignore_mouse = True
            return False

        if self._ignore_mouse or not self._is_expanded:
            self._ignore_mouse = False
            return False

        return super().handle_mouse(event)


def from_signature(
    method: Callable[..., Any],
    handle_output: Callable[..., Any] | None = None,
    **attrs: Any
) -> ptg.Window:
    """Creates a window from a function signature.

    Args:
        method: The method to generate window from.
        handle_output: The output handler. Its signature depends on the method given.

    Returns:
        A window with InputFields for all parameters for the method.
    """

    window = ptg.Window(width=70, **attrs)
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

        field = ptg.InputField(value=str(default or ""))
        window += get_inputbox(param.name.title(), field)

        # Mypy cannot infer type, yet providing it doesn't help.
        fields[param.name] = lambda field=field: field.value  # type: ignore

    # Create submission button
    # TODO: This should open a loader modal.
    threaded = Teacup.threaded(
        method,
        lambda *args, **kwargs: handle_output(window, *args, **kwargs)
        if handle_output
        else None,
    )

    window += ""

    window += ptg.Button(
        "Submit!",
        lambda *_: threaded(**{key: value() for key, value in fields.items()}),
    )

    return window
