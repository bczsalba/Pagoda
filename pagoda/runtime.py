"""The runtime component of the Pagoda client."""

from typing import Any, Callable

import pytermgui as ptg
from requests import Response
from teahaz import Teacup, Chatroom, Event

from . import widgets
from . import windows

#: This is temporary
CONFIG = """\
config:
    Splitter:
        chars:
            separator: " "

    InputField:
        styles:
            fill: "[field-text]{item}"

    Window:
        styles:
            border: &border "[!gradient(60:{depth})]{item}"
            corner: *border

    Container:
        styles:
            border: *border
            corner: *border

    Header:
        styles:
            border: "[60]{item}"

markup:
    title: 210 bold
    field-text: '245'
    error-title: 210 bold
    error-key: 72 bold
    error-value: 157 italic
"""


class App(ptg.WindowManager):
    """The Pagoda Application class.

    If for some reason you would want to use this manually,
    you can use the context manager syntax:

    ```python3
    from pagoda.runtime import App

    with App() as app:
        app.run()
    ```

    This ensures errors are dealt with cleanly, and all open
    files are closed.
    """

    cup: Teacup
    """The Teacup used for API operations."""

    def __init__(self) -> None:
        """Initialize application."""

        super().__init__()

        self.setup_styles()

        self.cup = Teacup()
        self.cup.subscribe_all(Event.ERROR, self._display_error)
        self.bind("*", lambda *_: self.show_targets())
        self.bind(
            ptg.keys.CTRL_W, lambda *_: self.focused.close() if self.focused else None
        )

        menubar = ptg.Window(
            is_static=True, is_noresize=True, is_noblur=True
        ) + widgets.Menubar(
            self._get_menubar_button(self.cup.create_chatroom),
            self._get_menubar_button(self.cup.login),
        )
        menubar.box = ptg.boxes.EMPTY
        self.add(menubar)

    def _get_menubar_button(self, func: Callable[..., Any]) -> ptg.Button:
        """Gets a button with callback creating teahazwindow"""

        return ptg.Button(
            "[!title]" + func.__name__,
            lambda *_: self.add(windows.TeahazWindow(self.cup).from_signature(func)),
        )

    def _display_error(
        self, response: Response, method: str, req_kwargs: dict[str, Any]
    ) -> None:
        """Creates a modal window to show the error."""

        if response.status_code == 200:
            return

        modal = (
            ptg.Window(is_modal=True, width=70, is_resizable=False)
            + "[error-title]An error occured!"
            + ""
            + {"[error-key]Method:": "[error-value]" + method.upper()}
            + {"[error-key]Error:": "[error-value]" + str(response.json())}
        )

        modal += ptg.Label("[72 bold]request_arguments[/] = {", parent_align=0)
        for key, value in {**req_kwargs, "url": response.url}.items():
            modal += ptg.Label(f"    [italic 243]{key}: [157]{value}", parent_align=0)
        modal += ptg.Label("}", parent_align=0)

        modal += ""
        modal += ["Close!", lambda *_: modal.close()]

        self.add(modal)

    @staticmethod
    def setup_styles() -> None:
        """Sets up styling. Note: This will support user-configs at some point."""

        def _macro_gradient(base, depth, item) -> str:
            if not base.isdigit():
                raise ValueError(f"Gradient base has to be digit, not {type(base)}.")

            return ptg.markup.parse(f"[{int(base) + int(depth) * 36}]{item}")

        ptg.markup.define("gradient", _macro_gradient)
        ptg.markup.define("title", lambda item: item.title().replace("_", " "))

        loader = ptg.YamlLoader()
        loader.register(widgets.Header)
        loader.load(CONFIG)

    def add_chatroom(self, chatroom: Chatroom) -> None:
        """Adds a chatroom."""

        self.add(windows.ChatroomWindow(chatroom, self.cup))

    def add(self, window: ptg.Window) -> ptg.WindowManager:
        """Adds a window, and centers it."""

        if not window.is_static:
            window.center()

        return super().add(window)

    def exit(self):
        """Gracefully stops all Teacup threads before exiting program."""

        self.cup.stop()
        super().exit()
