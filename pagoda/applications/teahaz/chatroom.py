"""The module containing the Teahaz application's Chatroom window."""

from __future__ import annotations

from typing import Any
from datetime import datetime

import pytermgui as ptg
from teahaz import threaded, Chatroom, Message, Event, Channel

from ... import widgets


class MessageButton(ptg.Button):
    """A clickable message."""

    def __init__(self, content: Message, **attrs) -> None:
        """Initializes a messagebutton.

        Args:
            content: The message associated with this button.
        """

        super().__init__(**attrs)

        self.set_style("label", ptg.MarkupFormatter("[teahaz-message]{item}"))
        self.set_style(
            "highlight", ptg.MarkupFormatter("[teahaz-message_selected]{item}")
        )
        self.set_char("delimiter", ["", ""])

        self.content = content
        self.label = ""

    def get_lines(self) -> list[str]:
        """Assigns label from self.content & returns super().get_lines()."""

        if self.content.message_type == "system":
            # TODO: This is not yet implemented due to the soon-changing API.
            return []

        label = str(self.content.data)
        if isinstance(self.content.data, bytes) and self.content.message_type == "file":
            label = "<file>"

        if not self.content.is_delivered:
            label = "[teahaz-message_unsent]" + label

        self.label = label

        width = self.width
        lines = super().get_lines()
        self.width = width

        broken = list(ptg.break_line(" ".join(lines), self.width))
        self.height = len(broken)
        return broken


class MessageBox(ptg.Container):
    """A message box."""

    # TODO: Currently, once messages are grouped together there
    #       is no way to ungroup them. This should be fine, but
    #       we shall see.

    is_unsent = False
    """Shows that this message has not yet been sent."""

    def __init__(self, *messages: Message, **attrs) -> None:
        """Initializes a MessageBox.

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

        self._previous_pos: tuple[int, int] = self.pos
        self.update()

    def __contains__(self, other: object) -> bool:
        """Determines whether other is contained within self._messages."""

        return other in self._messages

    def remove_msg(self, msg: Message) -> None:
        """Removes a message from self._messages."""

        self._messages.remove(msg)
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

    def update(self, run_getlines: bool = True) -> None:
        """Updates box content."""

        self._widgets = []
        total = len(self._messages)

        for i, message in enumerate(self._messages):
            if i > 0:
                self._add_widget("", run_getlines)

            show_name = i == 0 and not self.is_unsent
            show_time = i == total - 1 and not self.is_unsent

            if show_name:
                self._add_widget(
                    ptg.Label(
                        "[teahaz-default_username]" + str(message.username),
                        parent_align=self.parent_align,
                    ),
                    run_getlines,
                )

            self._add_widget(
                MessageButton(message, parent_align=self.parent_align), run_getlines
            )

            if show_time:
                time = datetime.fromtimestamp(message.send_time).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                self._add_widget(
                    ptg.Label(
                        "[teahaz-timestamp]" + time, parent_align=self.parent_align
                    ),
                    run_getlines,
                )


# Refactoring further will just ruin readability. 8/7 ain't too bad anyway.
class ChatroomWindow(ptg.Window):  # pylint: disable=too-many-instance-attributes
    """A window displaying a single chatroom."""

    overflow = ptg.Overflow.HIDE
    is_dirty = False
    """Force constant updates."""

    def __init__(self, chatroom: Chatroom, **attrs: Any) -> None:
        """Initializes a ChatroomWindow."""

        super().__init__(width=100, **attrs)

        self.chatroom = chatroom
        self.chatroom.subscribe(Event.MSG_NEW, self.add_message)
        self.chatroom.subscribe(Event.MSG_SENT, self.add_message)

        self._old_size_info = 0, (self.width, self.height)

        self._sent_messages: dict[str, tuple[Message, MessageBox]] = {}
        self._previous_box: MessageBox | None = None
        self._previous_message: Message | None = None

        self.header = widgets.Header("This is a header")
        self._add_widget(self.header)
        self._update_header()

        self.conv_box = ptg.Container(overflow=ptg.Overflow.SCROLL, vertical_align=0)
        self.conv_box.box = ptg.boxes.EMPTY
        self.conv_box.height = 30
        self._add_widget(self.conv_box)

        field = ptg.InputField()
        field.bind(ptg.keys.ENTER, self._send_message)
        self._add_widget(widgets.get_inputbox("Message", field))

        self.height = 40

        self.bind(ptg.keys.TAB, self._add_util_window)
        self._switch_channel(self.chatroom.channels[0])

    def _add_util_window(self, _: ptg.Window, __: str) -> None:
        """Adds a Chatroom utility window."""

        def _execute_switch(caller: ptg.Window, channel: Channel) -> None:
            """Switches to new channel and closes caller window."""

            caller.close()
            self._switch_channel(channel)

        def _confirm_switch(caller: ptg.Window, channel: Channel) -> None:
            """Confirms user wanting to switch to newly created channel."""

            caller.close()
            window: ptg.Window

            window = ptg.Window(
                widgets.Header("[title]New chatroom created!"),
                "",
                "Would you like to switch to it?",
                "",
                ptg.Splitter(
                    ["Yes!", lambda *_: _execute_switch(window, channel)],
                    ["No", lambda *_: window.close()],
                ),
                is_modal=True,
            )

            assert self.manager is not None
            self.manager.add(window)

        def _create_channel(_: ptg.Window) -> None:
            """Creates a channel."""

            window = widgets.from_signature(
                self.chatroom.create_channel, _confirm_switch, is_modal=True
            )

            assert self.manager is not None
            self.manager.add(window)

        window = ptg.Window(
            widgets.Header("[title]Chatroom utilities"),
            "",
            width=ptg.terminal.width // 2,
            is_modal=True,
        )

        body = ptg.Container(
            overflow=ptg.Overflow.SCROLL,
            height=15,
            vertical_align=ptg.VerticalAlignment.TOP,
        )

        body.box = ptg.boxes.EMPTY

        window += body

        channels = widgets.ToggleSection("[title]Channels")
        channels.toggle()
        for channel in self.chatroom.channels:
            prefix = "[72]" if self.chatroom.active_channel is channel else ""
            # TODO: These would be much cleaner as clickable text
            channels += {
                (prefix + channel.name): [
                    "Switch",
                    lambda *_, window=window, channel=channel: _execute_switch(
                        window, channel
                    ),
                ]
            }

        channels += ["Create...", _create_channel]
        body += channels + ""

        assert self.manager is not None
        self.manager.add(window)

    def _update_header(self) -> None:
        """Updates header value."""

        self.header.label = "[teahaz-chatroom_name]" + str(self.chatroom.name) + "[/]: "
        if self.chatroom.active_channel is not None:
            self.header.label += (
                "[teahaz-channel_name]" + self.chatroom.active_channel.name
            )

    def _switch_channel(self, channel: Channel) -> None:
        """Switches to a different channel & load new messages."""

        if channel is None:
            return

        self.chatroom.active_channel = channel

        self._sent_messages = {}
        self._previous_box = None
        self._previous_message = None

        self.conv_box.set_widgets([])
        for message in channel.messages:
            self.add_message(message)

        self._update_header()

    def _send_message(self, field: ptg.InputField, _: str) -> None:
        """Sends message as field's content."""

        if field.value == "":
            return

        threaded(self.chatroom.send)(field.value)
        field.value = ""

    def add_message(self, message: Message, do_update: bool = True) -> None:
        """Adds a message to the conversation box."""

        if message.uid in self._sent_messages:
            sent, box = self._sent_messages[message.uid]
            box.remove_msg(sent)
            box.update()

            del self._sent_messages[message.uid]

        prev = self._previous_message

        align = 2 if message.username == self.chatroom.username else 0

        if prev is not None:
            if (
                message.username == prev.username
                and message.send_time - prev.send_time < 600
            ):
                assert self._previous_box is not None
                self._previous_box.add_message(message, do_update)

        else:
            self._previous_box = MessageBox(message, parent_align=align)
            if len(self.conv_box) > 0:
                self.conv_box += ""
                self.conv_box += ""

            self.conv_box += self._previous_box

        assert self._previous_box is not None
        self._previous_message = message

        if not message.is_delivered:
            self._sent_messages[message.uid] = (message, self._previous_box)

        if do_update:
            self._previous_box.update()
            self.conv_box.scroll_end(-1)

        self.select(self.selectables_length - 1)

    def get_lines(self) -> list[str]:
        """Updates self.conv_box size before returning super().get_lines()."""

        def _calculate_height_sum() -> int:
            """Calculates sum of non-convbox widgets."""

            if not hasattr(self, "conv_box"):
                return 0

            return sum(
                widget.height for widget in self._widgets if widget is not self.conv_box
            )

        height_sum = _calculate_height_sum()
        old_sum, old_size = self._old_size_info

        if not height_sum == old_sum or not (self.width, self.height) == old_size:
            self.conv_box.height = self.height - 2 - height_sum
            self._old_size_info = height_sum, (self.width, self.height)
            for box in self.conv_box:
                if not isinstance(box, MessageBox):
                    continue
                box.update()

        return super().get_lines()
