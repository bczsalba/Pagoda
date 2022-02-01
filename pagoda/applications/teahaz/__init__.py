"""The module containing the Pagoda-builtin Teahaz chatroom application."""

from __future__ import annotations

from typing import Callable, Any

import pytermgui as ptg
from teahaz import Teacup, Chatroom, Message, Event, SystemEvent

from ... import widgets
from ..application import PagodaApplication
from .chatroom import ChatroomWindow


class TeahazApplication(PagodaApplication):
    """The TeahazApplication class.

    This application controls all of the Teahaz API related work.
    """

    title = "Teaház"

    def __init__(self, manager: ptg.WindowManager) -> None:
        """Initializes the TeahazApplication, and its Teacup instance."""

        self._cup = Teacup()

        super().__init__(manager)

    def construct_window(self, **attrs: Any) -> ptg.Window:
        """Constructs a picker for the various ways one can sign into Teahaz."""

        window: ptg.Window

        def _get_runner(method: Callable[..., Any]) -> Callable[..., Any]:
            """Returns a flowrunner for given method.

            Sideeffects:
                This runner also closes the constructed window.

            Returns:
                A new lambda function that runs `self._start_flow` with given
                method.
            """

            def inner(_: ptg.Button) -> None:
                """Runs the actual flow."""

                self._start_flow(method)
                self.close(window)

            return inner

        window = (
            self._get_base_window(**attrs)
            + ""
            + ptg.Button("Choose from logged-in chatrooms")
            + ptg.Button("Create a chatroom", _get_runner(self._cup.create_chatroom))
            + ptg.Button("Log into a chatroom", _get_runner(self._cup.login))
            + ""
        )

        self.active_windows.append(window)

        return window

    def _start_flow(self, method: Callable[..., Any]) -> None:
        """Starts a user-flow based on the method provided.

        Args:
            method: The callable to create a window about.
        """

        def _go_back(window: ptg.Window, _: str) -> None:
            """Aborts current window and goes back to the selector."""

            self.manager.add(self.construct_window())
            self.close(window)

        window = widgets.from_signature(method, self._handle_output)

        window.bind(ptg.keys.ESC, _go_back)

        self.active_windows.append(window)
        self.manager.add(window)

    def _handle_output(self, caller: ptg.Window, chatroom: Chatroom | None) -> None:
        """Handles the response.

        Args:
            chatroom: The result of trying to log in.
            caller: The window who called this method. Will be closed once ChatroomWindow
                has been constructed.
        """

        if chatroom is None:
            return

        self.manager.add(ChatroomWindow(chatroom, self._cup))
        self.close(caller)

    def stop(self) -> None:
        """Terminate all cup processes."""

        self._cup.stop()
        super().stop()
