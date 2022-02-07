"""The runtime component of the Pagoda client."""

from __future__ import annotations

import pytermgui as ptg

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

    Button:
        chars:
            delimiter: ["[ ", " ]"]

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

    application_managers = applications.list_applications()

    # TODO: This could be useful? But I'm not sure how well a global
    #       error handler like this would work.
    # applications.ErrorHandler(),

    def __init__(self, remaining_args: list[str], app_id: str | None = None) -> None:
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
                    lambda *_, app=app: (self.add(app.construct_window())),  # type: ignore
                )
                for app in self.applications
            ]
        )

        self.add(self._menubar)

        if app_id is not None:
            arg_app = self._find_app_by_id(app_id)
            arg_app.parse_arguments(remaining_args)

        for starting_app in self.applications:
            starting_app.start()

    def _find_app_by_id(self, app_id: str) -> applications.PagodaApplication:
        """Returns an App by its name.

        Returns:
            The application with the provided ID.

        Raises:
            KeyError: No application with the given ID could be found.
        """

        for app in self.applications:
            if app.app_id == app_id:
                return app

        raise KeyError(f'Could not find application by the id "{app_id}".')

    def error(
        self, caller: applications.PagodaApplication, content: ptg.Container
    ) -> None:
        """Displays an error using the ErrorHandler application."""

        window = ptg.Window(
            vertical_align=ptg.VerticalAlignment.TOP,
            is_modal=True,
            width=80,
        )
        window += widgets.Header(f"[title]An error occured in [bold]{caller.title}.")

        window += ""
        window += content
        window += ""
        window += ptg.Button("Dismiss", lambda *_: window.close())

        self.add(window)

    @staticmethod
    def setup_styles() -> None:
        """Sets up styling. Note: This will support user-configs at some point."""

        def _macro_gradient(base: str, depth: str, item: str) -> str:
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
