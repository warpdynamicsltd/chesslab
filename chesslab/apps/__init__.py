import time
import pickle
import io
import os
import subprocess

import chess.svg
import chess
import cairosvg
from chess import Board, Move, Color
from chess.engine import SimpleEngine, Limit, PovScore

from chesslab.engine import ChesslabEngine


def convert_svg_to_png(svg_string):
    output = io.BytesIO()
    cairosvg.svg2png(bytestring=svg_string, write_to=output)
    return output


class Payload:
    def __init__(self, text, img_data=None):
        self.text = text
        self.img_data = img_data


class MainApp:
    Null = Payload(None, None)
    program_data_path = os.path.join(os.path.expanduser('~'), '.chessio')
    pkl_file_path = os.path.join(program_data_path, 'chessio.pkl')

    def __init__(self, size=600):
        self.board = Board()
        self.size = size
        self.debug = False
        self.flipped = False
        self.coords = True
        self.fen = chess.STARTING_BOARD_FEN
        self.engine_path = None
        self.lines = 5
        self.load()

    def _status(self, value):
        return self.payload(str(getattr(self, value)))

    def save(self):
        if not os.path.isdir(self.program_data_path):
            os.mkdir(self.program_data_path)

        with open(self.pkl_file_path, "wb") as f:
            pickle.dump(self, f)

    def load(self):
        if os.path.isfile(self.pkl_file_path):
            with open(self.pkl_file_path, "rb") as f:
                obj = pickle.load(f)
                self.__dict__ = obj.__dict__

    def start(self):
        return Payload(
            "Chessio\nCopyright (c) 2022 Michal Stanislaw Wojcik. All rights reserved.",
            self.board_png_data())

    def board_png_data(self):
        return convert_svg_to_png(chess.svg.board(self.board,
                                                  size=self.size,
                                                  flipped=self.flipped,
                                                  coordinates=self.coords)).getvalue()

    def payload(self, text=None):
        return Payload(text, self.board_png_data())

    def move(self, move):
        self.board.push(move)
        info = ""
        if self.board.is_checkmate():
            info += "checkmate\n"
        if self.board.is_stalemate():
            info += "stalmate\n"
        if self.board.is_repetition():
            info += "treefold repetition\n"
        if self.board.is_fivefold_repetition():
            info += "fivefold repetition\n"
        if self.board.is_fifty_moves():
            info += "fifty moves\n"

        if info != "":
            return self.payload(info[:-1])
        else:
            return self.payload()

    def execute(self, cmd, value):
        try:
            move = self.board.parse_san(cmd)
            return self.move(move)
        except chess.InvalidMoveError as e:
            pass

        if hasattr(self, f'_{cmd}'):
            payload = getattr(self, f'_{cmd}')(value)
            if payload is None:
                payload = Payload(None, None)
            return payload
        else:
            return None

    def _echo(self, value):
        return Payload(value, None)

    def _sleep(self, value):
        time.sleep(float(value))

    def _debug(self, value):
        self.debug = True if value == 'on' else False
        return Payload(f"debug mode {'on' if self.debug else 'off'}")

    def _size(self, value):
        self.size = int(value)
        return self.payload(f"size {value}")

    def _flip(self, value):
        self.flipped = not self.flipped
        return self.payload()

    def _coords(self, value):
        self.coords = True if value == 'on' else False
        return self.payload()

    def _back(self, value):
        self.board.pop()
        return self.payload()

    def _new(self, value):
        self.board.reset()
        self.fen = chess.STARTING_BOARD_FEN
        return self.payload()

    def _again(self, value):
        self.board = Board(self.fen)
        return self.payload()

    def _turn(self, value):
        return Payload("white" if self.board.turn else 'black')

    def _fen(self, value):
        self.fen = value
        self.board = Board(self.fen)
        return self.payload()

    def _engine(self, path):
        if path[0] in {'"', "'"} and path[-1] in {'"', "'"}:
            path = eval(path)

        self.engine_path = path

    def _lines(self, n):
        self.lines = int(n)

    def _analyse(self, t):
        if t is None:
            t = str(1)
        if self.engine_path is None:
            return self.payload("no engine")
        with ChesslabEngine(self.engine_path) as engine:
            lines = engine.analyse(self.board, Limit(int(t)), self.lines)
            text = f'analysis [{t} sec] <<\n'
            for i, line in enumerate(lines):
                text += f"{i + 1}. ({line.score_str()}) {line.png(self.board)}\n"
            text += ">>\n"
        return self.payload(text)
