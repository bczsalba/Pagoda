"""The module containing the Pagoda-builtin Teahaz chatroom application."""

from __future__ import annotations

import os
import inspect
from typing import Callable, Any

import pytermgui as ptg
from teahaz import Teacup, Chatroom, Message, Event, SystemEvent

from ..widgets import Header, get_inputbox
from .application import PagodaApplication


TEMP_DEFAULTS = {
    key.rsplit("_", 1)[-1].lower(): os.environ.get(key)
    for key in [
        "PAGODA_URL",
        "PAGODA_CONV_NAME",
        "PAGODA_USERNAME",
        "PAGODA_PASSWORD",
    ]
}


class TeahazApplication(PagodaApplication):
    """The TeahazApplication class.

    This application controls all of the Teahaz API related work.
    """

    title = "Teaház"

    def __init__(self, manager: ptg.WindowManager) -> None:
        """Initializes the TeahazApplication, and its Teacup instance."""

        self._cup = Teacup()
        self.defaults = TEMP_DEFAULTS

        super().__init__(manager)

    def construct_window(self) -> ptg.Window:
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

            def inner() -> None:
                """Runs the actual flow."""

                self.close(window)
                self._start_flow(method)

            return inner

        window = (
            ptg.Window()
            + "[title]Choose your fighter:"
            + ""
            + ptg.Button("Create a chatroom", _get_runner(self._cup.create_chatroom))
            + ptg.Button("Log into a chatroom", _get_runner(self._cup.login))
        )

        window.select(0)

        self.active_windows.append(window)

        return window

    def _start_flow(self, method: Callable[..., Any]) -> None:
        """Starts a user-flow based on the method provided.

        Args:
            method: The callable to create a window about.
        """

        window = ptg.Window(width=70)
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
                default = self.defaults.get(param.name, "")

            field = ptg.InputField(value=default)
            window += get_inputbox(param.name.title(), field)

            # Mypy cannot infer type, yet providing it doesn't help.
            fields[param.name] = lambda field=field: field.value  # type: ignore

        # Create submission button
        # TODO: This should open a loader modal.
        threaded = self._cup.threaded(
            method, lambda chat: self._handle_output(chat, window)
        )
        window += ptg.Button(
            "Submit!",
            lambda *_: threaded(**{key: value() for key, value in fields.items()}),
        )

        # Finalize
        self.active_windows.append(window)
        self.manager.add(window)

    def _handle_output(self, chatroom: Chatroom | None, caller: ptg.Window) -> None:
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

    def close(self, window: ptg.Window) -> None:
        """Closes given window, while also removing it from our active_windows."""

        if not window in self.active_windows:
            raise ValueError(f'Window "{window}" is not in {self}\'s active_windows.')

        self.active_windows.remove(window)
        window.close()

    def stop(self) -> None:
        """Terminate all cup processes."""

        self._cup.stop()
        super().stop()


class MessageBox(ptg.Container):
    """A message box."""

    overflow = ptg.Overflow.RESIZE

    def __init__(self, message: Message, **attrs: Any) -> None:
        """Initializes message box.
        Args:
            message: The message to display. Can be get/set using
                self.message.
        """

        super().__init__(**attrs)
        self.message = message
        self.relative_width = 0.4

    @property
    def message(self) -> Message:
        """Set the currently displayed message.
        Args:
            new: The new message to display.
        Returns:
            The current message.
        """

        return self._message

    @message.setter
    def message(self, new: Message) -> None:
        """Set a new message."""

        self._message = new

        if new.message_type == "system":
            assert isinstance(new.data, SystemEvent)
            self._add_widget(ptg.Label("[245 italic]-- " + new.data.event_type + " --"))
            return

        # Just to calm mypy down.
        assert isinstance(new.data, str)

        assert new.username

        self._widgets = []
        self._add_widget(
            ptg.Label("[157 bold]" + new.username, parent_align=self.parent_align)
        )
        self._add_widget("")
        self._add_widget(ptg.Label(new.data, parent_align=self.parent_align))
        self._add_widget("")
        self._add_widget(ptg.Label(str(new.send_time), parent_align=self.parent_align))
        self.get_lines()


# TODO: Refactor this. We can do better!
#       This and `MessageBox` should both be
#       moved under a separate module inside
#       this application.
class ChatroomWindow(ptg.Window):  # pylint: disable=too-many-instance-attributes
    """The Pagoda Chatroom window."""

    cup: Teacup
    chatroom: Chatroom

    is_dirty = True
    overflow = ptg.Overflow.HIDE

    def __init__(self, chatroom: Chatroom, cup: Teacup, **attrs: Any) -> None:
        """Initialize a chatroom window.
        This method creates our Teacup for managing the API,
        sets up its bindings and does some other things that I
        cannot think of at the moment."""

        self.chatroom = chatroom
        self.chatroom.subscribe(Event.MSG_NEW, self.add_message)
        self.chatroom.subscribe(Event.MSG_SENT, self._add_sent_message)

        self.cup = cup
        self._send_threaded = self.cup.threaded(self.chatroom.send)

        self._conv_box = ptg.Container(
            height=25, overflow=ptg.Overflow.SCROLL, vertical_align=0
        )
        self._conv_box.box = ptg.boxes.Box(
            [
                "   ",
                "x",
                "   ",
            ]
        )

        super().__init__(**attrs)
        self.box = ptg.boxes.DOUBLE
        self.width = 100

        # Messages that have been sent, but not yet received back
        self._sent_messages: list[tuple[str, MessageBox]] = []

        self._old_size = (self.width, self.height)
        self._old_height_sum = self._get_height_sum()

        self._add_widget(Header(str(self.chatroom.name)))
        self._add_widget(self._conv_box)

        field = ptg.InputField()
        field.bind(ptg.keys.RETURN, self._send_field_value)

        self._add_widget(get_inputbox("Message", field=field))
        self.height = 30

        self.chatroom.send("hello world!")

    def _send_field_value(self, field: ptg.InputField, _: str) -> None:
        """Sends the input field's value.
        This method uses self._send_threaded to send the message under a thread.
        Args:
            field: The field whose value should be sent.
        """

        self._send_threaded(field.value)
        field.value = ""

    def _get_height_sum(self) -> int:
        """Calculates the sum of non-self._convbox widget heights."""

        return sum(
            widget.height for widget in self._widgets if widget is not self._conv_box
        )

    def _add_sent_message(self, message: Message) -> None:
        """Adds a message to the window.
        This is called as a callback for self.cup.
        Args:
            message: The teahaz Message instance.
        """

        box = MessageBox(
            message,
            parent_align=(2 if message.username == self.chatroom.username else 0),
        )

        style = ptg.MarkupFormatter("[240]{item}")
        box.set_style("border", style)
        box.set_style("corner", style)

        self._conv_box += box
        self._sent_messages.append((message.uid, box))

    def add_message(self, message: Message) -> None:
        """Adds a message to the window.
        This is called as a callback for self.cup.
        Args:
            message: The teahaz Message instance.
        """

        box = MessageBox(
            message,
            parent_align=(2 if message.username == self.chatroom.username else 0),
        )

        for i, (uid, sent_box) in enumerate(self._sent_messages):
            if uid == message.uid:
                self._conv_box.remove(sent_box)
                self._sent_messages.pop(i)

        self._conv_box += box

    def get_lines(self) -> list[str]:
        """ "Updates self._conv_box size before returning super().get_lines()."""

        height_sum = self._get_height_sum()
        if (
            not height_sum == self._old_height_sum
            or not (self.width, self.height) == self._old_size
        ):
            self._conv_box.height = self.height - 2 - height_sum
            self._old_size = (self.width, self.height)

        return super().get_lines()
