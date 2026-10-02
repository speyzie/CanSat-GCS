"""Tracks whether uplinked commands were received.

A command is acknowledged when the addressed device reports it in CMD_ECHO
*and* its COMMAND_COUNT has grown since the command was sent, so an old echo
of an identical command is not mistaken for a new acknowledgement. Commands
without an echo within the timeout are marked as unanswered."""

import time
from dataclasses import dataclass, field
from enum import Enum

from gcs.commands import Command
from gcs.telemetry import Device

ACK_TIMEOUT_SECONDS = 3.0
HISTORY_LENGTH = 6


class CommandStatus(Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    NO_ECHO = "no echo"


@dataclass
class CommandRecord:
    command: Command
    sent_at: float = field(default_factory=time.monotonic)
    command_count_at_send: int | None = None
    status: CommandStatus = CommandStatus.PENDING
    response_seconds: float | None = None


class CommandTracker:
    def __init__(self) -> None:
        self._records: list[CommandRecord] = []

    @property
    def records(self) -> list[CommandRecord]:
        """Most recent first."""
        return list(reversed(self._records))

    def sent(self, command: Command, current_command_count: int | None) -> None:
        self._records.append(CommandRecord(command, command_count_at_send=current_command_count))
        del self._records[:-HISTORY_LENGTH]

    def echo_received(self, device: Device, cmd_echo: str, command_count: int) -> bool:
        """Marks the newest matching pending command as acknowledged."""
        for record in reversed(self._records):
            if (record.status is CommandStatus.PENDING and record.command.target is device
                    and record.command.echo == cmd_echo
                    and (record.command_count_at_send is None or command_count > record.command_count_at_send)):
                record.status = CommandStatus.ACKNOWLEDGED
                record.response_seconds = time.monotonic() - record.sent_at
                return True
        return False

    def expire(self) -> list[CommandRecord]:
        """Marks overdue commands as unanswered and returns them."""
        now = time.monotonic()
        expired = [record for record in self._records
                   if record.status is CommandStatus.PENDING and now - record.sent_at > ACK_TIMEOUT_SECONDS]
        for record in expired:
            record.status = CommandStatus.NO_ECHO
        return expired

    def clear(self) -> None:
        self._records.clear()
