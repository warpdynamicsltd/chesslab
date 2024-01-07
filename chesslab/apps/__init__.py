import time
import pickle
import io
import os
import subprocess

import chess.svg
import chess.pgn
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
    @classmethod
    def text(cls, text):
        return Payload(text, None)

    @classmethod
    def img_data(cls, img_data):
        return Payload(None, img_data)

    @classmethod
    def terminal(cls, text=None, img_data=None):
        payload = Payload(text, img_data)
        payload.last = True
        return payload

    def __init__(self, text=None, img_data=None):
        self.text = text
        self.img_data = img_data
        self.last = None


class MainApp:
    program_data_path = os.path.join(os.path.expanduser('~'), '.chesslab')
    pkl_file_path = os.path.join(program_data_path, 'chesslab.pkl')

    @classmethod
    def app(cls):
        if os.path.isfile(cls.pkl_file_path):
            with open(cls.pkl_file_path, "rb") as f:
                return pickle.load(f)
        else:
            return MainApp()

    @classmethod
    def convert_from(cls, obj):
        app = MainApp()
        app.board = obj.board
        app.size = obj.size
        app.debug = obj.debug
        app.flipped = obj.flipped
        app.coords = obj.coords
        app.fen = obj.fen
        app.engine_path = obj.engine_path
        app.lines = obj.lines
        return app

    def __init__(self, size=600):
        self.board = Board()
        self.size = size
        self.debug = False
        self.flipped = False
        self.coords = True
        self.fen = chess.STARTING_BOARD_FEN
        self.engine_path = None
        self.lines = 5
        # self.load()

    def _status(self, value):
        yield self.payload(str(getattr(self, value)))

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
        return self.payload("Chesslab\nCopyright (c) 2022 Michal Stanislaw Wojcik. All rights reserved.")

    def exit(self):
        return MainApp.convert_from(self)

    def board_png_data(self):
        return convert_svg_to_png(chess.svg.board(self.board,
                                                  size=self.size,
                                                  flipped=self.flipped,
                                                  coordinates=self.coords)).getvalue()

    def payload(self, text=None):
        return Payload(text, self.board_png_data())

    def send_pos_status(self):
        if self.board.is_checkmate():
            yield Payload.text("CHECKMATE")
        if self.board.is_stalemate():
            yield Payload.text("STALEMATE")
        if self.board.is_repetition():
            yield Payload.text("THREEFOLD REPETITION")
        if self.board.is_fivefold_repetition():
            yield Payload.text("FIVEFOLD REPETITION")
        if self.board.is_fifty_moves():
            yield Payload.text("FIFTY MOVES")

        yield self.payload()

    def go(self, move):
        self.board.push(move)
        yield from self.send_pos_status()
        yield Payload.text(self.get_current_outcome_str())

    def get_current_outcome_str(self):
        outcome = self.board.outcome(claim_draw=True)
        if outcome is not None:
            return f"RESULT {outcome.result()}"
        return None

    def command_not_recognized(self):
        yield Payload.text("Command not recognized.")

    def execute(self, cmd, value):
        print(cmd, value)
        res = None
        try:
            move = self.board.parse_san(cmd)
            res = self.go(move)
        except chess.InvalidMoveError as e:
            pass

        if hasattr(self, f'_{cmd}'):
            res = getattr(self, f'_{cmd}')(value)
        elif res is None:
            res = self.command_not_recognized()

        if res is not None:
            yield from res

        yield Payload.terminal()

    def _echo(self, value):
        yield Payload.text(value)

    def _sleep(self, value):
        time.sleep(float(value))

    def _debug(self, value):
        self.debug = True if value == 'on' else False
        yield Payload.text(f"debug mode {'on' if self.debug else 'off'}")

    def _size(self, value):
        self.size = int(value)
        yield self.payload(f"size {value}")

    def _flip(self, value):
        self.flipped = not self.flipped
        yield self.payload()

    def _coords(self, value):
        self.coords = True if value == 'on' else False
        yield self.payload()

    def _back(self, value):
        self.board.pop()
        yield self.payload()

    def _new(self, value):
        self.board.reset()
        self.fen = chess.STARTING_BOARD_FEN
        yield self.payload()

    def _again(self, value):
        self.board = Board(self.fen)
        yield self.payload()

    def _turn(self, value):
        yield Payload.text("white" if self.board.turn else 'black')

    def set_fen(self):
        self.board = Board(self.fen)

    def _fen(self, value):
        self.fen = value
        self.set_fen()
        yield self.payload()

    def _engine_path(self, path):
        if path[0] in {'"', "'"} and path[-1] in {'"', "'"}:
            path = eval(path)

        self.engine_path = path

    def _lines(self, n):
        self.lines = int(n)

    def _analyse(self, t):
        if t is None:
            t = str(1)
        if self.engine_path is None:
            yield self.payload("no engine")
            return
        with ChesslabEngine(self.engine_path) as engine:
            lines = engine.analyse(self.board, Limit(int(t)), self.lines)
            text = f'analysis [{t} sec] <<\n'
            for i, line in enumerate(lines):
                text += f"{i + 1}. ({line.score_str()}) {line.png(self.board)}\n"
            text += ">>"
        yield Payload.text(text)

    def _pgn(self, value):
        game = chess.pgn.Game()
        game.setup(self.fen)
        game.add_line(self.board.move_stack)
        outcome = self.board.outcome(claim_draw=True)
        if outcome is not None:
            game.headers['Result'] = outcome.result()

        exporter = chess.pgn.StringExporter(headers=False, variations=True, comments=False)
        pgn_string = game.accept(exporter)
        yield Payload.text(pgn_string)
