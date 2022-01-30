"""The module containing the chatroom window type"""

from typing import Any

import pytermgui as ptg
from teahaz import Teacup, Chatroom, Message, Event, SystemEvent

from .. import widgets


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

        assert new.username
        assert isinstance(new.data, str)

        self._widgets = []
        self._add_widget(
            ptg.Label("[157 bold]" + new.username, parent_align=self.parent_align)
        )
        self._add_widget("")
        self._add_widget(ptg.Label(new.data, parent_align=self.parent_align))
        self._add_widget("")
        self._add_widget(ptg.Label(str(new.send_time), parent_align=self.parent_align))
        self.get_lines()


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

        self._add_widget(widgets.Header(str(self.chatroom.name)))
        self._add_widget(self._conv_box)

        field = ptg.InputField()
        field.set_style("value", lambda _, item: item)
        field.bind(ptg.keys.RETURN, self._send_field_value)

        self._add_widget(widgets.get_inputbox("Message", field=field))
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
