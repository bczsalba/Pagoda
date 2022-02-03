"""The module containing the Pagoda-builtin Teahaz chatroom application."""

from __future__ import annotations

import json
from argparse import ArgumentParser
from typing import Callable, Any, TYPE_CHECKING

import pytermgui as ptg
from requests import Response
from teahaz import Teacup, Chatroom, Message, Event, SystemEvent, Invite

from ... import widgets
from ..application import PagodaApplication
from .chatroom import ChatroomWindow

if TYPE_CHECKING:
    from ...runtime import Pagoda


class TeahazApplication(PagodaApplication):
    """The TeahazApplication class.

    This application controls all of the Teahaz API related work.
    """

    manager: Pagoda

    title = "Teaház"
    app_id = "teahaz"

    def __init__(self, manager: Pagoda) -> None:
        """Initializes the TeahazApplication, and its Teacup instance."""

        ptg.markup.alias("teahaz-chatroom_name", "bold 210")
        ptg.markup.alias("teahaz-channel_name", "202")
        ptg.markup.alias("teahaz-default_username", "210 bold")
        ptg.markup.alias("teahaz-message", "")
        ptg.markup.alias("teahaz-unsent_message", "240")
        ptg.markup.alias("teahaz-timestamp", "bold 72")

        self._cup = Teacup()
        self._cup.subscribe_all(Event.ERROR, self._error)

        super().__init__(manager)

    def _error(
        self, response: Response, method: str, req_kwargs: dict[str, Any]
    ) -> None:
        """Passes information to ErrorHandler application."""

        content = ptg.Container(
            {
                "[error-key]Error:": "[error-value]" + str(response.json()),
            },
            {
                "[error-key]Method:": "[error-value]" + method.upper(),
            },
        )

        content.box = ptg.boxes.SINGLE

        content += ptg.Label("[72 bold]request_arguments[/] = {", parent_align=0)
        for key, value in {**req_kwargs, "url": response.url}.items():
            content += ptg.Label(f"    [italic 243]{key}: [157]{value}", parent_align=0)
        content += ptg.Label("}", parent_align=0)

        self.manager.error(self, content)

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
            + ""
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

    def parse_arguments(self, args: list[str]) -> None:
        """Parses given arguments."""

        def _use_invite(invite: Invite, username: str, password: str) -> None:
            """Uses an invite."""

            chatroom = self._cup.use_invite(invite, username, password)
            if chatroom is None:
                return

            window = ChatroomWindow(chatroom, self._cup)
            self.active_windows.append(window)
            self.manager.add(window)

        parser = ArgumentParser(
            prog="Teaház", description="The Pagoda Teaház application."
        )

        parser.add_argument(
            "-i",
            "--invite",
            metavar=("file"),
            help="Consumes an invite from the given file path.",
        )

        namespace = parser.parse_args(args)

        if namespace.invite is None:
            return

        with open(namespace.invite, "r", encoding="utf-8") as inv_file:
            invite = Invite.from_dict(json.load(inv_file))

        username_field = ptg.InputField()
        password_field = ptg.InputField()
        self.manager.add(
            self._get_base_window()
            + ""
            + "[title]Register to a new chatroom!"
            + ""
            + widgets.get_inputbox("Username", username_field)
            + widgets.get_inputbox("Password", password_field)
            + ""
            + [
                "Submit!",
                lambda *_: _use_invite(
                    invite, username_field.value, password_field.value
                ),
            ]
        )
