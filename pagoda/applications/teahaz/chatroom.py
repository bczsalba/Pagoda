"""The module containing the Teahaz application's Chatroom window."""

from __future__ import annotations

import json
from typing import Any
from datetime import datetime
from dataclasses import asdict

import pytermgui as ptg
from teahaz import Teacup, Chatroom, Message, Event, Invite

from ... import widgets


class MessageBox(ptg.Container):
    """A message box."""

    # TODO: Currently, once messages are grouped together there
    #       is no way to ungroup them. This should be fine, but
    #       we shall see.

    is_unsent = False
    """Shows that this message has not yet been sent."""

    def __init__(self, *messages: Message, **attrs) -> None:
        """Initializes a MessageBox.

        This widget only calculates changes if its size changed
        or new messages were added for perfomance reasons.

        It also assumes all messages come from the same author,
        and within a certain amount of time. This is handled by
        ChatroomWindow.

        Args:
            *messages: The messages this box will display.
        """

        self._cached_lines: list[str] = []

        super().__init__(**attrs)

        self.relative_width = 0.4
        self.box = ptg.boxes.EMPTY

        self._messages = []
        for message in messages:
            self._messages.append(message)

        self.update()

    def add_message(self, message: Message, do_update: bool = True) -> None:
        """Adds a new message.

        Args:
            do_update: Determines whether self.update() should be called
                after adding a message.
        """

        self._messages.append(message)
        self._messages.sort(key=lambda msg: msg.send_time)

        if do_update:
            self.update()

    def update(self) -> None:
        """Updates box content."""

        self._widgets = []
        total = len(self._messages)

        for i, message in enumerate(self._messages):
            # This shouldn't happen
            if message.message_type.startswith("system"):
                continue

            if i > 0:
                self._add_widget("")

            show_name = i == 0 and not self.is_unsent
            show_time = i == total - 1 and not self.is_unsent

            if show_name:
                self._add_widget(
                    ptg.Label(
                        "[teahaz-default_username]" + str(message.username),
                        parent_align=self.parent_align,
                    )
                )

            data = "<file>" if not isinstance(message.data, str) else message.data

            if self.is_unsent:
                self._add_widget("")
                data = "[teahaz-unsent_message]" + data
            else:
                data = "[teahaz-message]" + data

            if i == self.selected_index:
                data = "[inverse]" + data

            self._add_widget(ptg.Label(data, parent_align=self.parent_align))

            if show_time:
                time = datetime.fromtimestamp(message.send_time).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                self._add_widget(
                    ptg.Label(
                        "[teahaz-timestamp]" + time, parent_align=self.parent_align
                    )
                )

        self._cached_lines = super().get_lines()

    def get_lines(self) -> list[str]:
        """Returns cached lines when possible, only updates content when size was changed."""

        return self._cached_lines


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

        self.conv_box = ptg.Container(
            height=25, overflow=ptg.Overflow.SCROLL, vertical_align=0
        )
        self.conv_box.box = ptg.boxes.Box(
            [
                "   ",
                " x ",
                "   ",
            ]
        )

        super().__init__(**attrs)
        self.box = ptg.boxes.DOUBLE
        self.width = 100

        # Messages that have been sent, but not yet received back
        self._sent_messages: list[tuple[str, MessageBox]] = []

        self._previous_msg: Message | None = None
        self._previous_msg_box: MessageBox | None = None

        self._old_size = (self.width, self.height)
        self._old_height_sum = self._get_height_sum()

        self._header = widgets.Header(
            "[teahaz-chatroom_name]" + str(self.chatroom.name)
        )
        self._add_widget(self._header)
        self._add_widget(self.conv_box)

        field = ptg.InputField()
        field.bind(ptg.keys.RETURN, self._send_field_value)

        self._add_widget(widgets.get_inputbox("Message", field=field))
        self.height = int(4 * ptg.terminal.height / 5)

    def _write_invite(self, caller: ptg.Window, invite: Invite | None) -> None:
        """Writes the invite to a file."""

        file_dialog: ptg.Window

        def _write(name: str) -> None:
            """Writes the invite."""

            with open(name, "w", encoding="utf-8") as file:
                json.dump(asdict(invite), file, indent=2)

            file_dialog.close()
            caller.close()

        if invite is None:
            return

        if self.chatroom.name is None:
            default = "invite.inv"
        else:
            default = self.chatroom.name.replace(" ", "_") + ".inv"

        field = ptg.InputField(value=default)

        file_dialog = (
            ptg.Window(is_modal=True, width=50)
            + "[title]Invite created!"
            + ""
            + widgets.get_inputbox("Save invite as", field)
            + ""
            + ptg.Button("Save!", lambda *_: _write(field.value))
        )

        assert self.manager is not None
        self.manager.add(file_dialog)

    def _send_field_value(self, field: ptg.InputField, _: str) -> None:
        """Sends the input field's value.
        This method uses self._send_threaded to send the message under a thread.
        Args:
            field: The field whose value should be sent.
        """

        if field.value == "":
            return

        self._send_threaded(field.value)
        field.value = ""

    def _get_height_sum(self) -> int:
        """Calculates the sum of non-self._convbox widget heights."""

        return sum(
            widget.height for widget in self._widgets if widget is not self.conv_box
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
            is_unsent=True,
        )

        style = ptg.MarkupFormatter("[240]{item}")
        box.set_style("border", style)
        box.set_style("corner", style)

        self.conv_box += box
        box.update()
        self._sent_messages.append((message.uid, box))

    def add_message(self, message: Message, do_update: bool = True) -> None:
        """Adds a message to the window.
        This is called as a callback for self.cup.
        Args:
            message: The teahaz Message instance.
        """

        for i, (uid, sent_box) in enumerate(self._sent_messages):
            if uid == message.uid:
                self.conv_box.remove(sent_box)
                self._sent_messages.pop(i)

        prev = self._previous_msg
        self._previous_msg = message

        should_group = (
            prev is not None
            and prev.username == message.username
            and message.send_time - prev.send_time < 600
        )

        if should_group and self._previous_msg_box is not None:
            self._previous_msg_box.add_message(message, do_update)
            return

        box = MessageBox(
            message,
            parent_align=(2 if message.username == self.chatroom.username else 0),
        )

        self.conv_box += ""
        self.conv_box += ""
        self.conv_box += box

        self._previous_msg_box = box
        return

    def get_lines(self) -> list[str]:
        """ "Updates self.conv_box size before returning super().get_lines()."""

        height_sum = self._get_height_sum()
        if (
            not height_sum == self._old_height_sum
            or not (self.width, self.height) == self._old_size
        ):
            self.conv_box.height = self.height - 2 - height_sum
            self._old_size = (self.width, self.height)

        return super().get_lines()
