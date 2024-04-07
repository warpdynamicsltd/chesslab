import asyncio
import traceback
import queue
import bleak
from bleak import BleakScanner
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from chesslab.apps import Payload, EcbCommand
import chesslab.scripts.chessui

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


class ECB:
    def __init__(self, ec_in_queue, in_queue, out_queue):
        self.ec_in_queue = ec_in_queue
        self.in_queue = in_queue
        self.out_queue = out_queue

        self.devices = {}
        self.client = None
        self.device = None
        self.prev_data = None

        self.action_stack = []
        self.castling = False
        self.promoting = False
        self.capturing = False

    async def discover(self):
        self.devices = {}
        devices = await BleakScanner.discover()
        if devices:
            for i, device in enumerate(devices):
                key = str(i + 1)
                msg = f"{key}. {str(device.name).strip()} {device.address}"
                self.devices[key] = device
                self.out_queue.put(Payload.text(msg))
        else:
            self.out_queue.put(Payload.text("no devices"))

    def send_move(self, uci_move):
        print('MOVE', uci_move)
        self.in_queue.put(chesslab.scripts.chessui.ChesslabCommand('term', uci_move))

    def clear_action_stack(self):
        self.action_stack = []
        self.castling = False
        self.promoting = False
        self.capturing = False

    def interpret_action_stack(self):
        if self.capturing and len(self.action_stack) == 3:
            if self.action_stack[2].direction == 'DOWN':
                if self.action_stack[2].color == self.action_stack[0].color:
                    del self.action_stack[1]
                elif self.action_stack[2].color == self.action_stack[1].color:
                    del self.action_stack[0]
                self.capturing = False

        if self.castling and len(self.action_stack) == 3:
            if self.action_stack[2].direction == 'UP' and self.action_stack[2].piece in {'R', 'r'}:
                return
            self.clear_action_stack()
            return

        if self.castling and len(self.action_stack) == 4:
            if self.action_stack[3].direction == 'DOWN' and self.action_stack[3].piece in {'R', 'r'}:
                move = self.action_stack[0].square + self.action_stack[1].square
                self.send_move(move)
                self.clear_action_stack()
                return

        if self.promoting and len(self.action_stack) == 2:
            if self.action_stack[1].direction == 'DOWN':
                piece = self.action_stack[1].piece.lower()
                move = self.action_stack[0].square + self.action_stack[1].square + piece
                self.send_move(move)
            self.clear_action_stack()
            return

        if len(self.action_stack) == 1:
            # white promotion
            if self.action_stack[0].direction == 'UP' and self.action_stack[0].piece == 'P' and self.action_stack[0].square[1] == '7':
                self.promoting = True
                return

            # black promotion
            if self.action_stack[0].direction == 'UP' and self.action_stack[0].piece == 'p' and self.action_stack[0].square[1] == '2':
                self.promoting = True
                return

            if self.action_stack[0].direction == 'DOWN':
                self.clear_action_stack()
                return

            return

        if len(self.action_stack) == 2:
            first_color = self.action_stack[0].color

            # white promotion
            if self.action_stack[1].direction == 'UP' and self.action_stack[1].piece == 'P' and self.action_stack[1].square[1] == '7':
                self.promoting = True

            # black promotion
            if self.action_stack[1].direction == 'UP' and self.action_stack[1].piece == 'p' and self.action_stack[1].square[1] == '2':
                self.promoting = True

            # eliminate capturing
            if self.action_stack[0].direction == 'UP' and self.action_stack[1].direction == 'UP' and self.action_stack[1].color != first_color:
                self.capturing = True
                return

            if self.action_stack[0].direction == 'UP' and self.action_stack[1].direction == 'DOWN' and self.action_stack[1].color == first_color:

                # eliminate first move of white castle
                if self.action_stack[0].piece == 'K' and self.action_stack[1].piece == 'K' and self.action_stack[0].square == 'e1':
                    if self.action_stack[1].square == 'c1' or self.action_stack[1].square == 'g1':
                        self.castling = True
                        return

                # eliminate first move of white castle
                if self.action_stack[0].piece == 'k' and self.action_stack[1].piece == 'k' and self.action_stack[0].square == 'e8':
                    if self.action_stack[1].square == 'c8' or self.action_stack[1].square == 'g8':
                        self.castling = True
                        return

                move = self.action_stack[0].square + self.action_stack[1].square
                self.send_move(move)
                self.clear_action_stack()
                return

        self.clear_action_stack()

    def piece_up(self, piece, square, color):
        print('UP', piece, square, color)
        self.action_stack.append(Action('UP', piece, square, color))
        self.interpret_action_stack()

    def piece_down(self,  piece, square, color):
        print('DOWN', piece, square, color)
        self.action_stack.append(Action('DOWN', piece, square, color))
        self.interpret_action_stack()

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
                        self.piece_up(fig_sym, square, fig_sym.isupper())

                    if prev_fig == 0 and fig != 0:
                        fig_sym = PIECES[fig]
                        self.piece_down(fig_sym, square, fig_sym.isupper())

        # print(data.hex())
        self.prev_data = data



        # led = bytearray([0x0A, 0x08, 0x1, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        # await self.client.write_gatt_char(WRITECHARACTERISTICS, led)

    async def connect(self, key):
        await self.disconnect()
        print("*** connecting ***")
        self.device = self.devices[key]
        self.client = BleakClient(self.device)
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

    async def main(self):
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
                    self.clear_action_stack()
                self.out_queue.put(Payload.terminal())
            except Exception as e:
                traceback.print_exc()
                self.out_queue.put(Payload.text("bluetooth error"))
                # self.out_queue.put(Payload.text(f"{type(e).__name__} {str(e)}"))
                self.out_queue.put(Payload.text(repr(e)))
                self.out_queue.put(Payload.terminal())
