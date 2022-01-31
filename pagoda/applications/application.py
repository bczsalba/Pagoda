"""The module containing the PagodaApplication parent class."""

from abc import ABC, abstractmethod

import pytermgui as ptg


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

    @abstractmethod
    def construct_window(self) -> ptg.Window:
        """Constructs and returns a window."""

    def stop(self) -> None:
        """Closes all application windows.

        If there are any ongoing processes launched by this application,
        those should be terminated here as well.
        """

        for window in self.active_windows:
            if window in self.manager:
                window.close()
