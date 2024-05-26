import asyncio
import traceback
import queue
import bleak
from bleak import BleakScanner
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from chesslab.apps import Payload, EcbCommand
from chesslab.command import ChesslabCommand

""" Constant used in the program"""
# When the board is first connected it is necessary to send it a three byte initialisation code:
INITIALIZASION_CODE = b'\x21\x01\x00'
# The board will then send back a three byte confirmation code:
CONFIRMATION_CHARACTERISTICS = b'\x21\x01\x00'
# The signals from the board consist of a sequence of 38 bytes. The first two are:
HEAD_BUFFER = b'\x01\x24'
#  Communications using BLE
WRITECHARACTERISTICS = '1B7E8272-2877-41C3-B46E-CF057C562023'
READCONFIRMATION = '1B7E8273-2877-41C3-B46E-CF057C562023'
READDATA = '1B7E8262-2877-41C3-B46E-CF057C562023'

# Within each byte the lower 4 bits represent the
# first square and the higher 4 bits represent the
# second square
MASKLOW = 0b00001111

PIECES = {
    1: 'q',
    2: 'k',
    3: 'b',
    4: 'p',
    5: 'n',
    6: 'R',
    7: 'P',
    8: 'r',
    9: 'B',
    0xa: 'N',
    0xb: 'Q',
    0xc: 'K'
}


class Action:
    def __init__(self, direction, piece, square, color):
        self.direction = direction
        self.piece = piece
        self.square = square
        self.color = color

    def __repr__(self):
        return f"{self.direction} {self.piece} {self.square} {self.color}"


class ECB:
    def __init__(self, ec_in_queue, in_queue, out_queue):
        self.ec_in_queue = ec_in_queue
        self.in_queue = in_queue
        self.out_queue = out_queue

        self.devices = {}
        self.client = None
        self.device = None
        self.prev_data = None

        self.actions = asyncio.Queue()
        self.led = bytearray([0x0A, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

        self.send_disabled = False

    def available(self):
        return self.client is not None and self.client.is_connected

    async def light_led(self, square):
        i = 7 - ord(square[0]) + ord('a')
        j = 8 - int(square[1])
        self.led[2 + j] |= (1 << i)
        if self.available():
            await self.client.write_gatt_char(WRITECHARACTERISTICS, self.led)

    async def all_led_off(self):
        self.led = bytearray([0x0A, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        if self.available():
            await self.client.write_gatt_char(WRITECHARACTERISTICS, self.led)

    async def discover(self):
        self.devices = {}
        devices = await BleakScanner.discover(timeout=5.0)
        if devices:
            for i, device in enumerate(devices):
                key = str(i + 1)
                msg = f"{key}. {str(device.name).strip()} {device.address}"
                self.devices[key] = device
                self.out_queue.put(Payload.text(msg))
        else:
            self.out_queue.put(Payload.text("no devices"))

    def send_move(self, uci_move):
        # print('MOVE', uci_move)
        if not self.send_disabled:
            self.in_queue.put(ChesslabCommand('ecb', uci_move))

    async def piece_up(self, piece, square, color):
        action = Action('UP', piece, square, color)
        # print(action)
        await self.light_led(action.square)
        await self.actions.put(action)

    async def piece_down(self,  piece, square, color):
        action = Action('DOWN', piece, square, color)
        # print(action)
        await self.light_led(action.square)
        await self.actions.put(action)

    async def notification_handler(self, characteristic, data):
        if self.prev_data is not None:
            for b in range(0, 32):
                for k in range(0, 2):
                    i = 2*b + k
                    square = chr(ord('a') + 7 - (i % 8)) + str(8 - i // 8)

                    prev_fig = 0b1111 & (self.prev_data[b + 2] >> (4*k))
                    fig = 0b1111 & (data[b + 2] >> (4*k))

                    if prev_fig != 0 and fig == 0:
                        fig_sym = PIECES[prev_fig]
                        await self.piece_up(fig_sym, square, fig_sym.isupper())

                    if prev_fig == 0 and fig != 0:
                        fig_sym = PIECES[fig]
                        await self.piece_down(fig_sym, square, fig_sym.isupper())

        # print(data.hex())
        self.prev_data = data

        # led = bytearray([0x0A, 0x08, 0x1, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        # await self.client.write_gatt_char(WRITECHARACTERISTICS, led)

    def disconnect_handler(self, client):
        print("disconnected")
        self.prev_data = None

    async def connect(self, key):
        await self.disconnect()
        # print("*** connecting ***")
        self.device = self.devices[key]
        self.client = BleakClient(self.device, disconnected_callback=self.disconnect_handler)
        await self.client.connect()
        await self.client.start_notify(READDATA, self.notification_handler)  # start the notification handler
        await self.client.write_gatt_char(WRITECHARACTERISTICS, INITIALIZASION_CODE)

    async def status(self):
        if self.client is not None and self.client.is_connected:
            msg = f"connected {str(self.device.name).strip()} {self.client.address}"
        else:
            msg = 'disconnected'
        self.out_queue.put(Payload.text(msg))

    async def disconnect(self):
        if self.client is not None and self.client.is_connected:
            await self.client.stop_notify(READDATA)
            await self.client.disconnect()
        self.client = None
        self.device = None

    async def absorb_move(self, move):
        if self.available():
            self.send_disabled = True
            await self.light_led(move[:2])
            await self.light_led(move[2:4])
        # print(f"absorbing {move}")

    async def clean_move_parser(self):
        self.prev_data = None
        if self.available():
            await self.actions.put(None)
            self.send_disabled = False

    async def get_action(self):
        action = await self.actions.get()
        return action

    async def parse_move(self):
        first_up = await self.get_action()
        if first_up is None:
            return None
        await self.light_led(first_up.square)

        if first_up.direction != 'UP':
            return None

        action_down = await self.get_action()
        if action_down is None:
            return None

        if action_down.direction != 'DOWN':
            action = action_down

            action_down = await self.get_action()
            if action_down is None:
                return None

            if action_down.direction != 'DOWN':
                return None
            else:
                if first_up.color != action_down.color:
                    first_up = action

        if action_down.color == first_up.color:
            if first_up.piece == action_down.piece:
                # castling
                if (first_up.piece == 'K' and first_up.square == 'e1' and action_down.square in {'c1', 'g1'}) or \
                        (first_up.piece == 'k' and first_up.square == 'e8' and action_down.square in {'c8', 'g8'}):
                    rook_up = await self.get_action()
                    if rook_up is None:
                        return
                    rook_down = await self.get_action()
                    if rook_down is None:
                        return

                    return first_up.square + rook_up.square

                return first_up.square + action_down.square
            else:
                return first_up.square + action_down.square + action_down.piece.lower()

        return None

    async def actions_loop(self):
        while True:
            move = await self.parse_move()
            await asyncio.sleep(0.3)
            await self.all_led_off()
            if move is not None:
                # print('MOVE', move)
                self.send_move(move)
            self.send_disabled = False

    async def command_loop(self):
        while True:
            while True:
                try:
                    ecb_command = self.ec_in_queue.get(block=False)
                    break
                except queue.Empty:
                    await asyncio.sleep(0.01)
            try:
                if ecb_command.cmd == 'discover':
                    await self.discover()
                elif ecb_command.cmd == 'connect':
                    await self.connect(ecb_command.content)
                    self.out_queue.put(Payload.text('connected'))
                elif ecb_command.cmd == 'disconnect':
                    await self.disconnect()
                    self.out_queue.put(Payload.text('disconnected'))
                elif ecb_command.cmd == 'status':
                    await self.status()
                elif ecb_command.cmd == 'clean':
                    await self.clean_move_parser()
                    #self.clear_action_stack()
                elif ecb_command.cmd == 'move':
                    await self.absorb_move(ecb_command.content)
                self.out_queue.put(Payload.terminal())
            except Exception as e:
                traceback.print_exc()
                self.out_queue.put(Payload.text("bluetooth error"))
                # self.out_queue.put(Payload.text(f"{type(e).__name__} {str(e)}"))
                self.out_queue.put(Payload.text(repr(e)))
                self.out_queue.put(Payload.terminal())

    # async def main(self):
    #     await asyncio.gather(self.command_loop(), self.actions_loop())
