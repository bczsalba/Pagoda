"""The runtime component of the Pagoda client."""

from typing import Any, Type

import pytermgui as ptg
from requests import Response

from . import widgets
from . import applications

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


class Pagoda(ptg.WindowManager):
    """The Pagoda class.

    If for some reason you would want to use this manually,
    you can use the context manager syntax:

    ```python3
    from pagoda.runtime import Pagoda

    with Pagoda() as pagoda:
        pagoda.run()
    ```

    This ensures errors are dealt with cleanly, and all open
    files are closed.
    """

    application_managers: list[Type[applications.PagodaApplication]] = [
        applications.TeahazApplication,
        # TODO: This could be useful? But I'm not sure how well a global
        #       error handler like this would work.
        # applications.ErrorHandler(),
    ]

    def __init__(self) -> None:
        """Initialize application."""

        super().__init__()

        self.applications: list[applications.PagodaApplication] = []

        for app in self.application_managers:
            self.applications.append(app(self))

        self.setup_styles()

        self.bind("*", lambda *_: self.show_targets())
        self.bind(ptg.keys.CTRL_W, self.close_window)

        self._menubar = ptg.Window(is_static=True, is_noresize=True, is_noblur=True)
        self._menubar.box = ptg.boxes.EMPTY

        self._menubar += widgets.Menubar(
            *[
                ptg.Button(
                    app.title,
                    lambda app=app: (self.add(app.construct_window())),  # type: ignore
                )
                for app in self.applications
            ]
        )

        self.add(self._menubar)

    # TODO: Move this to ErrorHandler app, others can interface with it using
    #       manager.error()
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

    def close_window(self, *_: ptg.WindowManager) -> None:
        """Closes the currently focused window, so long as it is not our menubar."""

        if self.focused is None or self.focused is self._menubar:
            return

        self.focused.close()

    def add(self, window: ptg.Window) -> ptg.WindowManager:
        """Adds a window, and centers it."""

        if not window.is_static:
            window.center()

        return super().add(window)

    def exit(self):
        """Gracefully stops all Teacup threads before exiting program."""

        for app in self.applications:
            app.stop()

        super().exit()
