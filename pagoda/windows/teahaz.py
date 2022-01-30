"""Pagoda's Teahaz window generator.

TeahazWindow must be instantated with a `teahaz.Teacup` object, after
which `from_signature` can be called with any Callable.

This callable will be assigned to window.callback, and fields are generated
generated from it. When the submit button is pressed, the callback is called
with all given arguments.
"""

from __future__ import annotations

import os
import inspect
from typing import Any, Callable

from teahaz import Teacup, Chatroom
import pytermgui as ptg

from ..widgets import get_inputbox


# This is only going to stay here as long as
# rapid testing of chatroom create / login is
# required.
TEMP_DEFAULTS = {
    key.split("_")[-1].lower(): os.environ.get(key)
    for key in [
        "PAGODA_URL",
        "PAGODA_CONV_NAME",
        "PAGODA_USERNAME",
        "PAGODA_PASSWORD",
    ]
}


class TeahazWindow(ptg.Window):
    """A window with teahaz capabilities."""

    callback: Callable[[], Any] | None
    """The callback assigned to this window."""

    def __init__(
        self, cup: Teacup, defaults: dict[str, Any] | None = None, **args: Any
    ) -> None:
        """Initialize TeahazWindow.

        Args:
            cup: The teacup instance this window will use.
            parent: The parent object that is notified once this window
                completes its lifetime.
        """

        super().__init__(**args)

        self.width = 70
        self.callback = None

        if defaults is None:
            defaults = TEMP_DEFAULTS

        self.defaults = defaults
        self.box = ptg.boxes.DOUBLE

        self._cup = cup
        self._fields: dict[str, Callable[[], Any]] = {}

    def _gather_values(self) -> dict[str, Any]:
        """Gathers the values from self._fields.

        Return:
            A dictionary containing the names and values from this object's fields.
        """

        return {name: get_value() for name, get_value in self._fields.items()}

    def handle_output(self, chatroom: Chatroom | None) -> None:
        """Handles whatever self.callback gave us.

        Args:
            chatroom: Either a chatroom object, or nothing, depending on
                whether the call succeeded.
        """

        if chatroom is not None:
            self.manager.add_chatroom(chatroom)  # type: ignore
            self.close()

    def from_signature(self, func: Callable[..., Any]) -> TeahazWindow:
        """Creates a window from a signature.

        Args:
            func: The callable to generate this window from.

        Returns:
            This window, but now full of content.
        """

        self.callback = func
        threaded_callback = self._cup.threaded(self.callback, self.handle_output)

        self._add_widget("[title]" + func.__name__.title().replace("_", " "))
        self._add_widget("")

        for param in inspect.signature(func).parameters.values():
            if param.default == inspect.Signature.empty:
                default = self.defaults.get(param.name, "")

            if param.annotation == "str":
                field = ptg.InputField(value=default)
                self._add_widget(get_inputbox(param.name.title(), field))

                # Mypy cannot infer type, yet providing it doesn't help.
                get_value = lambda field=field: field.value  # type: ignore

                self._fields[param.name] = get_value
                continue

            raise NotImplementedError(f"Cannot convert {param}.")

        self._add_widget("")
        self._add_widget(
            [
                "Submit!",
                lambda *_: threaded_callback(**self._gather_values()),
            ]
        )

        return self
