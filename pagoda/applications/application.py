"""The module containing the PagodaApplication parent class."""

from typing import Any
from abc import ABC, abstractmethod

import pytermgui as ptg

from ..widgets import Header


class PagodaApplication(ABC):
    """The superclass of all Pagoda applications.

    An application has two important methods, `construct_window` and
    `stop`. All registered applications are instantiated at Pagoda class
    instantiation.
    """

    title: str
    """The application's title."""

    active_windows: list[ptg.Window]
    """A list of all active windows. **This is updated & tracked by the Application.**"""

    def __init__(self, manager: ptg.WindowManager) -> None:
        """Initializes the application."""

        self.manager = manager
        self.active_windows = []

    def _get_base_window(self, **attrs: Any) -> ptg.Window:
        """Constructs a base window for this application.

        For the time being, all this does is add a Header with self.title.

        Args:
            **attrs: Arbitrary attributes passed to the window.
        """

        window = ptg.Window(**attrs)
        window += Header("[title]" + self.title)
        return window

    @abstractmethod
    def construct_window(self, **attrs: Any) -> ptg.Window:
        """Constructs and returns a window.

        Args:
            **attrs: Arbitrary attributes passed to the new window.

        Returns:
            An application window.
        """

    def close(self, window: ptg.Window) -> None:
        """Closes given window, while also removing it from our active_windows.

        Args:
            window: The window to close.
        """

        if not window in self.active_windows:
            raise ValueError(f'Window "{window}" is not in {self}\'s active_windows.')

        self.active_windows.remove(window)
        window.close()

    def stop(self) -> None:
        """Closes all application windows.

        If there are any ongoing processes launched by this application,
        those should be terminated here as well.
        """

        for window in self.active_windows:
            if window in self.manager:
                window.close()
