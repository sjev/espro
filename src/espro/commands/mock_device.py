from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

import aioesphomeapi.api_pb2  # type: ignore[import-untyped]

pb: Any = cast(Any, aioesphomeapi.api_pb2)

if TYPE_CHECKING:
    from asyncio import StreamReader, StreamWriter

logger = logging.getLogger(__name__)

MSG_HELLO_REQUEST = 1
MSG_HELLO_RESPONSE = 2
MSG_AUTH_REQUEST = 3
MSG_DISCONNECT_REQUEST = 5
MSG_DISCONNECT_RESPONSE = 6
MSG_PING_REQUEST = 7
MSG_PING_RESPONSE = 8
MSG_DEVICE_INFO_REQUEST = 9
MSG_DEVICE_INFO_RESPONSE = 10
MSG_LIST_ENTITIES_REQUEST = 11
MSG_LIST_ENTITIES_SWITCH_RESPONSE = 17
MSG_LIST_ENTITIES_DONE_RESPONSE = 19
MSG_SUBSCRIBE_STATES_REQUEST = 20
MSG_SWITCH_STATE_RESPONSE = 26
MSG_SUBSCRIBE_LOGS_REQUEST = 28
MSG_SUBSCRIBE_LOGS_RESPONSE = 29
MSG_SWITCH_COMMAND_REQUEST = 33

LOG_LEVEL_INFO = 3
LOG_LEVEL_DEBUG = 5


def encode_varint(value: int) -> bytes:
    result = bytearray()
    while value > 127:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    result = 0
    shift = 0
    pos = offset
    while pos < len(data):
        byte = data[pos]
        result |= (byte & 0x7F) << shift
        pos += 1
        if (byte & 0x80) == 0:
            return result, pos - offset
        shift += 7
    raise ValueError("Incomplete varint")


def make_frame(msg_type: int, payload: bytes) -> bytes:
    return b"\x00" + encode_varint(len(payload)) + encode_varint(msg_type) + payload


def parse_frames(data: bytes) -> list[tuple[int, bytes, int]]:
    frames = []
    offset = 0
    while offset < len(data):
        if data[offset] != 0x00:
            break
        offset += 1

        try:
            length, consumed = decode_varint(data, offset)
            offset += consumed
            msg_type, consumed = decode_varint(data, offset)
            offset += consumed
        except ValueError:
            break

        if offset + length > len(data):
            break

        payload = data[offset : offset + length]
        offset += length
        frames.append((msg_type, payload, offset))

    return frames


@dataclass
class MockESPHomeDevice:
    name: str = "mock-switch-1"
    friendly_name: str = "Mock Switch 1"
    mac_address: str = "AA:BB:CC:DD:EE:FF"
    model: str = "ESP32"
    esphome_version: str = "2024.12.0"
    port: int = 6053

    switch_state: bool = False
    switch_key: int = 1
    switch_name: str = "Relay"
    switch_object_id: str = "relay"

    _server: asyncio.Server | None = field(default=None, repr=False)
    _subscribers: set["StreamWriter"] = field(default_factory=set, repr=False)
    _log_subscribers: set["StreamWriter"] = field(default_factory=set, repr=False)
    _log_task: asyncio.Task[None] | None = field(default=None, repr=False)

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client, "0.0.0.0", self.port
        )
        logger.info("Mock device '%s' listening on port %d", self.name, self.port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Mock device '%s' stopped", self.name)

    async def run_forever(self) -> None:
        await self.start()
        if self._server:
            await self._server.serve_forever()

    async def _handle_client(
        self, reader: "StreamReader", writer: "StreamWriter"
    ) -> None:
        addr = writer.get_extra_info("peername")
        logger.info("Client connected: %s", addr)
        buffer = bytearray()

        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break

                buffer.extend(data)
                frames = parse_frames(bytes(buffer))

                for msg_type, payload, consumed in frames:
                    buffer = buffer[consumed:]
                    await self._handle_message(msg_type, payload, writer)

        except (ConnectionResetError, BrokenPipeError):
            logger.debug("Client disconnected: %s", addr)
        finally:
            self._subscribers.discard(writer)
            self._log_subscribers.discard(writer)
            writer.close()
            await writer.wait_closed()

    async def _handle_message(
        self, msg_type: int, payload: bytes, writer: "StreamWriter"
    ) -> None:
        logger.debug("Received message type %d", msg_type)

        if msg_type == MSG_HELLO_REQUEST:
            await self._send_hello_response(writer)
        elif msg_type == MSG_AUTH_REQUEST:
            pass
        elif msg_type == MSG_PING_REQUEST:
            await self._send_ping_response(writer)
        elif msg_type == MSG_DEVICE_INFO_REQUEST:
            await self._send_device_info(writer)
        elif msg_type == MSG_LIST_ENTITIES_REQUEST:
            await self._send_entities(writer)
        elif msg_type == MSG_SUBSCRIBE_STATES_REQUEST:
            self._subscribers.add(writer)
            await self._send_switch_state(writer)
        elif msg_type == MSG_SWITCH_COMMAND_REQUEST:
            await self._handle_switch_command(payload, writer)
        elif msg_type == MSG_SUBSCRIBE_LOGS_REQUEST:
            await self._handle_subscribe_logs(writer)
        elif msg_type == MSG_DISCONNECT_REQUEST:
            await self._send_disconnect_response(writer)
            writer.close()

    async def _send(self, msg_type: int, msg: object, writer: "StreamWriter") -> None:
        payload = msg.SerializeToString()  # type: ignore[attr-defined]
        frame = make_frame(msg_type, payload)
        writer.write(frame)
        await writer.drain()

    async def _send_hello_response(self, writer: "StreamWriter") -> None:
        msg = pb.HelloResponse()
        msg.api_version_major = 1
        msg.api_version_minor = 14
        msg.name = self.name
        msg.server_info = "MockESPHomeDevice"
        await self._send(MSG_HELLO_RESPONSE, msg, writer)

    async def _send_ping_response(self, writer: "StreamWriter") -> None:
        await self._send(MSG_PING_RESPONSE, pb.PingResponse(), writer)

    async def _send_device_info(self, writer: "StreamWriter") -> None:
        msg = pb.DeviceInfoResponse()
        msg.name = self.name
        msg.friendly_name = self.friendly_name
        msg.mac_address = self.mac_address
        msg.model = self.model
        msg.esphome_version = self.esphome_version
        await self._send(MSG_DEVICE_INFO_RESPONSE, msg, writer)

    async def _send_entities(self, writer: "StreamWriter") -> None:
        switch = pb.ListEntitiesSwitchResponse()
        switch.object_id = self.switch_object_id
        switch.key = self.switch_key
        switch.name = self.switch_name
        switch.assumed_state = False
        switch.device_id = 0
        await self._send(MSG_LIST_ENTITIES_SWITCH_RESPONSE, switch, writer)

        await self._send(
            MSG_LIST_ENTITIES_DONE_RESPONSE, pb.ListEntitiesDoneResponse(), writer
        )

    async def _send_switch_state(self, writer: "StreamWriter") -> None:
        msg = pb.SwitchStateResponse()
        msg.key = self.switch_key
        msg.state = self.switch_state
        msg.device_id = 0
        await self._send(MSG_SWITCH_STATE_RESPONSE, msg, writer)

    async def _handle_switch_command(
        self, payload: bytes, writer: "StreamWriter"
    ) -> None:
        cmd = pb.SwitchCommandRequest()
        cmd.ParseFromString(payload)

        if cmd.key == self.switch_key:
            self.switch_state = cmd.state
            logger.info("Switch state changed to: %s", self.switch_state)

            state_str = "ON" if self.switch_state else "OFF"
            await self._broadcast_log(
                LOG_LEVEL_INFO,
                f"[{self.name}] Switch '{self.switch_name}' turned {state_str}",
            )

            for subscriber in list(self._subscribers):
                try:
                    await self._send_switch_state(subscriber)
                except (ConnectionResetError, BrokenPipeError):
                    self._subscribers.discard(subscriber)

    async def _send_disconnect_response(self, writer: "StreamWriter") -> None:
        await self._send(MSG_DISCONNECT_RESPONSE, pb.DisconnectResponse(), writer)

    async def _handle_subscribe_logs(self, writer: "StreamWriter") -> None:
        self._log_subscribers.add(writer)
        await self._send_log(
            writer, LOG_LEVEL_INFO, f"[{self.name}] Log streaming started"
        )

        if self._log_task is None or self._log_task.done():
            self._log_task = asyncio.create_task(self._emit_periodic_logs())

    async def _send_log(self, writer: "StreamWriter", level: int, message: str) -> None:
        msg = pb.SubscribeLogsResponse()
        msg.level = level
        msg.message = message.encode("utf-8")
        await self._send(MSG_SUBSCRIBE_LOGS_RESPONSE, msg, writer)

    async def _broadcast_log(self, level: int, message: str) -> None:
        for subscriber in list(self._log_subscribers):
            try:
                await self._send_log(subscriber, level, message)
            except (ConnectionResetError, BrokenPipeError):
                self._log_subscribers.discard(subscriber)

    async def _emit_periodic_logs(self) -> None:
        counter = 0
        while self._log_subscribers:
            await asyncio.sleep(3.0)
            if self._log_subscribers:
                counter += 1
                await self._broadcast_log(
                    LOG_LEVEL_DEBUG,
                    f"[{self.name}] Heartbeat #{counter}, switch={'ON' if self.switch_state else 'OFF'}",
                )


async def run_mock_device(
    name: str = "mock-switch-1",
    port: int = 6053,
    friendly_name: str | None = None,
    mac_address: str = "AA:BB:CC:DD:EE:FF",
) -> None:
    device = MockESPHomeDevice(
        name=name,
        friendly_name=friendly_name or name.replace("-", " ").title(),
        mac_address=mac_address,
        port=port,
    )
    await device.run_forever()
