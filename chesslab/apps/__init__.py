import time
import random
import glob
import math
import pickle
import io
import os
import shlex
import datetime
import subprocess
import inspect
from inspect import signature
from pathlib import Path

import chess.svg
import chess.pgn
import chess
import cairosvg
from chess import Board, Move, Color
from chess.engine import SimpleEngine, Limit, PovScore

from chesslab.engine import ChesslabEngine

# black knight replacement from https://github.com/lichess-org/lila/blob/master/public/piece/merida/bN.svg
chess.svg.PIECES["n"] = r"""<g id="black-knight" class="black knight" clip-rule="evenodd" fill-rule="evenodd" height="50mm" image-rendering="optimizeQuality" shape-rendering="geometricPrecision" text-rendering="geometricPrecision" viewBox="0 0 50 50" width="50mm" transform="translate(0.5, 0.7) scale(0.84)"><linearGradient id="a" gradientUnits="userSpaceOnUse" x1="21.253" x2="77.641" y1="37.592" y2="37.469"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient><path d="M26.178 9.395c2.6.17 5.004.838 7.222 2.015 2.21 1.169 4.098 2.676 5.656 4.513 1.092 1.287 2.117 2.845 3.082 4.665a28.684 28.684 0 0 1 2.32 5.774 36.511 36.511 0 0 1 1.253 7.46c.177 2.599.262 5.012.262 7.23v5.402H15.468c-.153 0-.22-.407-.212-1.21.009-.814.06-1.466.16-1.965.06-.398.221-.957.467-1.685.254-.728.66-1.609 1.244-2.65.263-.534.89-1.304 1.88-2.32.999-1.016 2.133-2.201 3.429-3.539.745-.762 1.32-1.719 1.744-2.879.423-1.151.601-2.201.533-3.15a8.37 8.37 0 0 1-2.006 1.22c-3.505 1.253-6.045 3.073-7.612 5.452-.118.153-.49.822-1.117 2.015-.33.627-.618 1.059-.847 1.287-.313.314-.77.491-1.363.525-.923.043-1.643-.398-2.16-1.346-.693.203-1.312.288-1.862.254-.923-.347-1.592-.72-2.006-1.117-.847-.847-1.389-1.685-1.651-2.532a9.43 9.43 0 0 1-.381-2.726c0-1.389.855-3.226 2.582-5.512 2.015-2.625 3.09-4.631 3.217-6.003 0-.593.06-1.261.178-2.007a4.198 4.198 0 0 1 .618-1.49c.22-.33.364-.558.432-.677.076-.127.212-.313.415-.559.144-.203.27-.355.372-.457.093-.11.22-.254.373-.44.178-.212.406-.457.694-.745a18.06 18.06 0 0 1-1.067-7.46c3.285 1.169 6.054 3.015 8.28 5.53.551-1.872 1.626-3.387 3.226-4.539 1.321.923 2.371 2.15 3.15 3.666z" fill="#1f1a17"/><path d="M15.688 17.786l.542-.28c.5-.194.652-.559.474-1.092-.195-.491-.576-.66-1.143-.491-1.947.711-3.294 2.015-4.039 3.92-.118.542.076.914.593 1.118.516.16.864-.017 1.041-.55.136-.28.229-.466.297-.543.186.144.423.246.72.297 1.007.16 1.6-.28 1.76-1.338a1.498 1.498 0 0 0-.245-1.041zM11.573 34.55c.06-.153.17-.373.322-.67.28-.693.415-1.108.415-1.244-.026-.457-.271-.694-.72-.694-.33 0-.711.474-1.16 1.414a.97.97 0 0 1-.296.347c-.449.466-.381.855.194 1.168.534.314.94.212 1.245-.321zm14.63-9.204c1.16-1.524 1.728-3.217 1.71-5.08-.067-.55-.38-.82-.94-.82-.761 0-1.057.279-.897.837.051.915-.033 1.668-.27 2.261-.382.94-.805 1.643-1.262 2.108-.254.5-.102.864.449 1.092.525.246.931.119 1.21-.398zM19.726 13.24a6.798 6.798 0 0 1 .051-1.93c-.99.194-1.922.66-2.802 1.388-.525.28-.652.67-.373 1.169.28.508.67.592 1.169.245.347-.186.669-.355.956-.508.288-.16.618-.28 1-.364zm23.25 31.454c-.017 0 0-.449.042-1.346.131-3.108.096-6.221.076-9.33a26.837 26.837 0 0 0-.889-6.613c-.84-3.31-2.124-6.485-4.072-9.297-2.634-3.845-6.814-6.033-11.286-6.976.126.766.033 1.54.076 2.311a25.82 25.82 0 0 1 4.538 2.032c4.241 2.555 6.414 7.276 7.197 11.93 1.272 6.154.453 11.557.813 17.289zM9.439 30.139c.475-.34.525-.729.144-1.194-.398-.381-.83-.415-1.312-.102-1.007.66-1.55 1.533-1.617 2.608.017.542.347.804.974.77.592-.05.88-.355.863-.922.136-.525.449-.915.948-1.16z" fill="url(#a)"/></g>"""
# white knight replacement from https://github.com/lichess-org/lila/blob/master/public/piece/merida/wN.svg?short_path=f43fec4
chess.svg.PIECES["N"] = r"""<g id="white-knight" class="white knight" clip-rule="evenodd" fill-rule="evenodd" height="50mm" image-rendering="optimizeQuality" shape-rendering="geometricPrecision" text-rendering="geometricPrecision" viewBox="0 0 50 50" width="50mm" transform="translate(0.5, 0.7) scale(0.84)" ><linearGradient id="a" gradientUnits="userSpaceOnUse" x1="21.405" x2="77.641" y1="37.346" y2="37.346"><stop offset="0" stop-color="#000"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient><path d="M26.178 9.395c2.6.17 5.004.838 7.222 2.015 2.21 1.169 4.098 2.676 5.656 4.513 1.092 1.287 2.117 2.845 3.082 4.665a28.684 28.684 0 0 1 2.32 5.774 36.511 36.511 0 0 1 1.253 7.46c.177 2.599.262 5.012.262 7.23v5.402H15.468c-.153 0-.22-.407-.212-1.21.009-.814.06-1.466.16-1.965.06-.398.221-.957.467-1.685.254-.728.66-1.609 1.244-2.65.263-.534.89-1.304 1.88-2.32.999-1.016 2.133-2.201 3.429-3.539.745-.762 1.32-1.719 1.744-2.879.423-1.151.601-2.201.533-3.15a8.37 8.37 0 0 1-2.006 1.22c-3.505 1.253-6.045 3.073-7.612 5.452-.118.153-.49.822-1.117 2.015-.33.627-.618 1.059-.847 1.287-.313.314-.77.491-1.363.525-.923.043-1.643-.398-2.16-1.346-.693.203-1.312.288-1.862.254-.923-.347-1.592-.72-2.006-1.117-.847-.847-1.389-1.685-1.651-2.532a9.43 9.43 0 0 1-.381-2.726c0-1.389.855-3.226 2.582-5.512 2.015-2.625 3.09-4.631 3.217-6.003 0-.593.06-1.261.178-2.007a4.198 4.198 0 0 1 .618-1.49c.22-.33.364-.558.432-.677.076-.127.212-.313.415-.559.144-.203.27-.355.372-.457.093-.11.22-.254.373-.44.178-.212.406-.457.694-.745a18.06 18.06 0 0 1-1.067-7.46c3.285 1.169 6.054 3.015 8.28 5.53.551-1.872 1.626-3.387 3.226-4.539 1.321.923 2.371 2.15 3.15 3.666z" fill="#1f1a17"/><path d="M42.976 44.693c-.017 0 0-.449.042-1.346.051-.906.076-1.88.076-2.921.017-2.066.017-4.2 0-6.41a26.837 26.837 0 0 0-.889-6.612c-.567-2.117-1.185-3.92-1.862-5.419-.678-1.498-1.414-2.785-2.21-3.878-1.185-1.786-2.811-3.302-4.86-4.538-2.049-1.244-4.19-2.057-6.426-2.438.152.813.22 1.609.203 2.387-.034.593-.313.89-.847.89-.61 0-.88-.297-.82-.89.05-2.184-.729-4.055-2.33-5.604-1.252 1.32-1.938 2.853-2.031 4.605-.034.585-.33.839-.898.77-.525-.016-.787-.32-.787-.914 0 0 .017-.067.042-.203-.677.22-1.388.525-2.133.923-.474.33-.864.246-1.16-.245-.297-.5-.17-.89.398-1.169.71-.364 1.244-.635 1.608-.821a17.634 17.634 0 0 0-4.86-3.522 17.31 17.31 0 0 0 1.889 6.528c.279.423.211.804-.204 1.134-.465.364-.855.313-1.168-.17a8.87 8.87 0 0 1-.491-.897c-.347.347-.584.61-.694.77-.119.153-.322.483-.61.991-.288.517-.5.94-.635 1.27-.144.415-.212.745-.186 1.008.025.254.05.533.067.855a7.61 7.61 0 0 1-1.007 2.752 133.71 133.71 0 0 1-1.998 3.15 127.607 127.607 0 0 1-1.787 2.675c-.415.601-.728 1.354-.94 2.286-.152.559-.152 1.244 0 2.04.144.805.475 1.431.966 1.88.762.77 1.498 1.126 2.21 1.067.228 0 .541-.093.93-.28.39-.178.687-.525.907-1.041.423-.94.779-1.414 1.067-1.414.406 0 .635.237.668.694 0 .102-.135.517-.397 1.245-.153.33-.348.677-.593 1.041-.322.432-.457.61-.423.542.262.948.702 1.11 1.312.5.178-.178.39-.525.618-1.016.237-.5.601-1.169 1.092-2.007.584-.982 1.202-1.77 1.863-2.388.66-.61 1.244-1.109 1.76-1.481.297-.22.661-.466 1.093-.745.432-.288 1.008-.576 1.736-.872.576-.229 1.219-.517 1.922-.856s1.329-.77 1.87-1.303c.763-.745 1.347-1.66 1.762-2.752.22-.61.296-1.363.245-2.26-.144-.56.136-.839.847-.839.533 0 .83.271.898.821 0 1.863-.534 3.565-1.592 5.106.347 1.058.44 2.218.27 3.471-.143 1.008-.499 2.091-1.05 3.243-.558 1.143-1.676 2.421-3.36 3.827-3.43 2.845-5.046 5.774-4.86 8.78h12.175zM9.338 29.613c-.483.297-.77.695-.872 1.194.017.542-.237.839-.762.89-.584.067-.88-.178-.898-.746.068-1.092.55-1.955 1.465-2.599.432-.347.83-.322 1.194.093.364.449.322.838-.127 1.169zm7.366-11.827c.212.33.296.677.245 1.041-.16 1.058-.753 1.499-1.76 1.338a1.596 1.596 0 0 1-.72-.296c-.06.076-.161.262-.297.541-.178.534-.525.712-1.041.55-.508-.202-.711-.575-.593-1.117.745-1.905 2.091-3.209 4.039-3.92.567-.17.94 0 1.117.491.204.534.051.898-.448 1.092a2.745 2.745 0 0 1-.271.136c-.085.042-.17.093-.271.144z" fill="#fff"/></g>"""


def convert_svg_to_png(svg_string):
    output = io.BytesIO()
    cairosvg.svg2png(bytestring=svg_string, write_to=output)
    return output


class EcbCommand:
    def __init__(self, cmd, content):
        self.cmd = cmd
        self.content = content


class Payload:
    @classmethod
    def text(cls, text):
        return Payload(text, None)

    @classmethod
    def img_data(cls, img_data):
        return Payload(None, img_data)

    @classmethod
    def ecb_data(cls, cmd, content=None):
        return Payload(None, None, EcbCommand(cmd, content))

    @classmethod
    def terminal(cls, text=None, img_data=None):
        payload = Payload(text, img_data)
        payload.last = True
        return payload

    def __init__(self, text=None, img_data=None, ecb_data=None):
        self.text = text
        self.img_data = img_data
        self.last = None
        self.ecb_data = ecb_data


class MainApp:
    cmd = None
    copyright_str = f"Copyright (c) Michal Stanislaw Wojcik 2023."
    program_data_path = os.path.join(os.path.expanduser('~'), '.chesslab')
    snapshot_dir = os.path.join(program_data_path, 'snapshots')
    pkl_file_path = os.path.join(program_data_path, 'chesslab.pkl')
    puzzles_db_path = os.path.join(program_data_path, 'puzzles_db')

    attrs_to_copy = [
        'board',
        'size',
        'debug',
        'flipped',
        'coords',
        'fen',
        'engine_path',
        'lines',
        'puzzle',
        'probs',
        'ratings',
        'rating',
        'my_rating',
        'rating_old',
        'my_rating_old',
        'engine_color',
        'current_node',
        'board_node',
        'limit',
        'human_moved',
        'resigned',
        'book',
        'my',
        'chess960',
        'ecb_enabled',
        'apps'
    ]

    def __getstate__(self):
        state = self.__dict__
        if 'pp' in state:
            del state['pp']
        return state

    @classmethod
    def app(cls):
        if os.path.isfile(cls.pkl_file_path):
            with open(cls.pkl_file_path, "rb") as f:
                return pickle.load(f)
        else:
            return MainApp()

    @classmethod
    def load_snapshot(cls, name):
        with open(os.path.join(cls.snapshot_dir, name + '.pkl'), "rb") as f:
            return pickle.load(f)

    @classmethod
    def create_from(cls, obj):
        app = cls()
        obj.copy_attrs(app)
        return app

    def __init__(self, size=600):
        self.can_exist = True
        self.board = Board()
        self.size = size
        self.debug = False
        self.flipped = False
        self.coords = True
        self.fen = chess.STARTING_BOARD_FEN
        self.engine_path = None
        self.lines = 5
        self.puzzle = None
        self.apps = None
        self.refresh = True
        self.book = False
        self.limit = None
        self.rating = None
        self.my = None
        self.my_rating = None
        self.my_rating_old = None
        self.rating_old = None
        self.resigned = False
        self.chess960 = False
        self.engine_color = True
        self.ecb_enabled = True
        self.colors = {
            'square dark': "#858383",
            'square light': "#d9d7d7"
        }

    def rating2nodes(self, r):
        # formula approximates more or less the plot given in https://www.melonimarco.it/en/2021/03/08/stockfish-and-lc0-test-at-different-number-of-nodes/
        return round(math.pow(10, 1.7 * math.tan(math.pi * (r - 2250) / 4500) + 3.7))

    def copy_attrs(self, target):
        for attr_name in MainApp.attrs_to_copy:
            if hasattr(self, attr_name) and hasattr(target, attr_name):
                setattr(target, attr_name, getattr(self, attr_name))

    def _status(self, value):
        """
Return a status of given attribute.

status <arg>

e.g. status chess_engine

status fen
shows stored FEN not FEN of current position to get current FEN type: current fen

"""

        yield self.payload(str(getattr(self, value)))

    def save(self):
        if not os.path.isdir(self.program_data_path):
            os.mkdir(self.program_data_path)

        with open(self.pkl_file_path, "wb") as f:
            pickle.dump(self, f)

    def save_snapshot(self, name):
        if not os.path.isdir(self.snapshot_dir):
            os.mkdir(self.snapshot_dir)

        with open(os.path.join(self.snapshot_dir, name + '.pkl'), "wb") as f:
            pickle.dump(self, f)

    def _app(self):
        yield self.start()

    def _save(self, name: str):
        """
Save snapshot of a current application.

save <snapshot_name: str>

e.g. save snapshot1"""
        self.save_snapshot(name)
        yield Payload.text("saved")

    def _list(self):
        """
List all snapshots which you can load using load command.
        """
        for path in glob.glob(os.path.join(self.snapshot_dir, "*.pkl")):
            yield Payload.text(Path(path).name[:-4])

    def load(self):
        if os.path.isfile(self.pkl_file_path):
            with open(self.pkl_file_path, "rb") as f:
                obj = pickle.load(f)
                self.__dict__ = obj.__dict__

    def _load(self, value: str):
        """
Load snapshot of an application.

load  <snapshot_name: str>

e.g. load snapshot1"""
        # load command is overwrote globally. This one is here just for docs
        pass

    def start(self):
        yield self.payload(f"Chesslab\n{MainApp.copyright_str}")

    def exit(self):
        return MainApp.create_from(self)

    def board_png_data(self):
        return convert_svg_to_png(chess.svg.board(self.board,
                                                  size=self.size,
                                                  flipped=self.flipped,
                                                  coordinates=self.coords,
                                                  colors=self.colors)).getvalue()

    def payload(self, text=None):
        if self.refresh:
            return Payload(text, self.board_png_data())
        else:
            return Payload.text(text)

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
        if self.board.is_insufficient_material():
            yield Payload.text("INSUFFICIENT MATERIAL")

        yield self.payload()

    def fixed_outcome(self):
        if self.board.outcome() is not None:
            return self.board.outcome()

        if self.board.is_repetition():
            return chess.Outcome(chess.Termination.THREEFOLD_REPETITION, winner=None)

        if self.board.is_fifty_moves():
            return chess.Outcome(chess.Termination.FIFTY_MOVES, winner=None)

        if self.board.is_stalemate():
            return chess.Outcome(chess.Termination.STALEMATE, winner=None)

        if self.board.is_insufficient_material():
            return chess.Outcome(chess.Termination.INSUFFICIENT_MATERIAL, winner=None)

        return None

    def go(self, move):
        self.board.push(move)
        yield from self.send_pos_status()
        yield Payload.text(self.get_current_outcome_str())

    def get_current_outcome_str(self):
        outcome = self.fixed_outcome()
        if outcome is not None:
            return f"RESULT {outcome.result()}"
        return None

    def command_not_recognized(self):
        yield Payload.text("Command not recognized.")

    def convert_arguments(self, method, args):
        new_args = []

        for i, key in enumerate(signature(method).parameters):
            param = signature(method).parameters[key]
            if param.name == 'args':
                return args
            if i < len(args):
                if param.annotation is not inspect._empty:
                    arg = param.annotation(args[i])
                else:
                    arg = args[i]
            else:
                arg = param.default

            new_args.append(arg)

        if len(args) > len(signature(method).parameters):
            raise Exception("too many arguments")

        return new_args

    def arg_to_str_if_needed(self, value):
        if value[0] in {'"', "'"} and value[-1] in {'"', "'"}:
            return eval(value)
        else:
            return value

    def execute(self, cmd, value, mode=None):
        # print(cmd, value)
        res = None

        try:
            if mode == "ecb":
                if self.ecb_enabled:
                    move = self.board.parse_uci(cmd)
                    san_str = self.board.san(move)
                    yield Payload.text(san_str)
                    res = self.go(move)
                else:
                    yield Payload.terminal()
                    return
        except chess.InvalidMoveError as e:
            pass

        try:
            if mode == "term":
                move = self.board.parse_san(cmd)
                res = self.go(move)
        except chess.InvalidMoveError as e:
            pass

        if hasattr(self, f'_{cmd}'):
            # args = value.split()
            # args = [self.arg_to_str_if_needed(arg) for arg in args]
            s = shlex.shlex(value, posix=True)
            s.whitespace_split = True
            s.commenters = []
            s.escape = []
            args = list(s)
            method = getattr(self, f'_{cmd}')
            args = self.convert_arguments(method, args)
            res = method(*args)
        elif res is None:
            res = self.command_not_recognized()

        if res is not None:
            yield from res

        if cmd != 'bt':
            yield Payload.terminal()

    def book_move(self):
        if not self.book:
            return None

        try:
            with chess.polyglot.open_reader(os.path.join(self.program_data_path, 'book.bin')) as reader:
                board = Board(self.board.fen())
                # for entry in reader.find_all(board):
                #     print(entry.move, entry.weight, entry.learn)
                entry = reader.choice(board, random=random.Random())
                return entry.move
        except IndexError as e:
            return None

    def _echo(self, value: str):
        """
Print argument in console.

echo <arg>"""
        yield Payload.text(value)

    def _sleep(self, value: float):
        """
Sleep for time given as an argument in seconds.

sleep <time: float>"""
        time.sleep(value)

    def _debug(self, value: str):
        """
Turn on or off debug mode.

debug on|off"""
        self.debug = True if value == 'on' else False
        yield Payload.text(f"debug mode {'on' if self.debug else 'off'}")

    def _size(self, value: int):
        """
Set the board size.

size <arg: int>

e.g. size 400"""
        self.size = value
        yield self.payload()

    def _flip(self):
        """
Flip the board."""

        self.flipped = not self.flipped
        yield self.payload()

    def _coords(self, value: str):
        """
Show or hide coordinates.

coords on|off"""
        self.coords = True if value == 'on' else False
        yield self.payload()

    def _back(self):
        """
Take the last move back."""
        self.board.pop()
        yield self.payload()

    def _chess960(self, value: str):
        """
Turn on and off Fisher random chess variation, known also as Chess960

chess960 on|off
"""
        if value == 'on':
            self.chess960 = True
        else:
            self.chess960 = False

    def _new(self):
        """
Set the board in an initial position of game of chess."""
        if self.chess960:
            self.board = Board(chess960=True)
            self.board.set_chess960_pos(random.randint(0, 959))
        else:
            self.board = Board()

        self.fen = self.board.fen()
        yield self.payload()

    def _again(self):
        """
Return to set fen position."""
        self.board = Board(self.fen)
        yield self.payload()

    def _turn(self):
        """
Show which side is on move."""
        yield Payload.text("white" if self.board.turn else 'black')

    def set_fen(self):
        self.board = Board(self.fen)

    def _fen(self, value: str):
        """
Set borad position in Forsyth–Edwards Notation (FEN).

fen <arg: str>

e.g. fen "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" """
        if value is None:
            raise Exception("missing argument")
        self.fen = value
        self.set_fen()
        yield self.payload()

    def _engine_path(self, path: str):
        """
Set engine path.

engine_path <arg:str>

e.g. engine_path "C:\My Engines\best_engine.exe" """
        self.engine_path = path

    def _lines(self, n: int):
        """
Set how many lines of analysis you want to see.

lines <arg: int>

e.g. lines 5"""
        if n > 0:
            self.lines = n

    def parse_limit(self, arg_name, value):
        if arg_name == 'nodes' and type(value) is str:
            if value[-1] == 'k':
                value = 1000 * float(str(value[:-1]))
            elif value[-1] == 'm':
                value = 1000000 * float(str(value[:-1]))

        if arg_name == 'time':
            value = float(value)

        if arg_name == 'depth':
            value = int(value)

        if arg_name == 'mate':
            value = int(value)

        return Limit(**{arg_name: value})

    def _analyse(self, arg_name: str = 'time', value=1.0):
        """
Analyse given position for a time given as an argument in seconds.

analyse <arg_name: str> <value>

e.g.
analyse time 5
analyse nodes 100
analyse nodes 2.5k
analyse nodes 3.1m"""

        if self.engine_path is None:
            yield self.payload("no engine")
            return
        with ChesslabEngine(self.engine_path) as engine:
            limit = self.parse_limit(arg_name, value)
            lines = engine.analyse(self.board, limit, self.lines)
            text = f'analysis [{limit}] <<\n'
            for i, line in enumerate(lines):
                text += f"{i + 1}. ({line.score_str()}) {line.png(self.board)} | nodes={line.nodes}\n"
            text += ">>"
        yield Payload.text(text)

    def _score(self, t: int = 1):
        """
Analyse given position for a time given as an argument in seconds
and displays score.

score <time: int>

e.g. score 5"""
        if self.engine_path is None:
            yield self.payload("no engine")
            return
        with ChesslabEngine(self.engine_path) as engine:
            lines = engine.analyse(self.board, Limit(int(t)), self.lines)
            text = f'analysis [{t} sec] <<\n'
            for i, line in enumerate(lines):
                text = line.score_str()
                yield Payload.text(text)
                break

    def _pgn(self):
        """
Print sequence of moves in console."""
        game = chess.pgn.Game()
        game.setup(self.fen)
        game.add_line(self.board.move_stack)
        outcome = self.fixed_outcome()
        if outcome is not None:
            game.headers['Result'] = outcome.result()

        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=False)
        pgn_string = game.accept(exporter)
        yield Payload.text(pgn_string)

    def _color(self, key: str, value: str):
        """
Change color of a given board element.

color <key: str> <value: str>

Possible keys are square light, square dark, square light lastmove, square dark lastmove, margin, coord, inner border, outer border, arrow green, arrow blue, arrow red, and arrow yellow. Values should look like #ffce9e (opaque), or #15781B80 (transparent)"""
        self.colors[key] = value
        yield self.payload()

    def _refresh(self, value: str):
        """
Turn on and off refreshing chessboard. Use for blindfold chess training.

refresh on|off
        """
        if value == "on":
            self.refresh = True
            yield self.payload()
        else:
            self.refresh = False

    def _current(self, key: str):
        """
Show current values:

current fen
"""
        if key == 'fen':
            yield Payload.text(self.board.fen())
            return

    def _book(self, value: str):
        """
Turning on and off opening book.

book on|off
"""
        self.book = (value == 'on')

    def send_move_to_bt(self, uci_move):
        yield Payload.ecb_data("move", uci_move)

    def _bt(self, *args):
        """
Managing electronic chessboard via bluetooth.

List all bluetooth devices:
bt
bt discover

Connect to chosen device:
bt connect <device number on list>

Check device status:
bt status

Clean chessboard buffer:
bt clean

Board sending (not sending) moves to application
bt ecb on|off

Disconnect device:
bt disconnect
"""
        if args:
            cmd = args[0]
            if cmd == 'discover':
                yield Payload.ecb_data('discover')
                return
            if cmd == 'connect':
                key = args[1]
                yield Payload.ecb_data('connect', key)
                return
            if cmd == 'disconnect':
                yield Payload.ecb_data('disconnect')
                return
            if cmd == 'status':
                yield Payload.ecb_data('status')
                return
            if cmd == 'clean':
                yield Payload.ecb_data('clean')
                return
            if cmd == 'ecb' and args[1] == 'on':
                self.ecb_enabled = True
                yield Payload.text("ecb on")
                yield Payload.terminal()
                return
            if cmd == 'ecb' and args[1] == 'off':
                self.ecb_enabled = False
                yield Payload.text("ecb off")
                yield Payload.terminal()
                return
        else:
            yield Payload.ecb_data('discover')
            return

        yield Payload.terminal()

    def _help(self, value: str = None):
        """
Print documentation in the console.

help [<function_name: str>]

e.g.
help
help fen"""
        if value is None:
            doc = f"""
Chesslab - base Chesslab application

applications available:

{self.apps}

commands available: """
            res = str()
            obj_class = type(self)
            methods = inspect.getmembers(obj_class, predicate=inspect.isfunction)

            if obj_class.__name__ != 'MainApp':
                yield Payload.text(f"{obj_class.__doc__}\n")
            else:
                yield Payload.text(f"{doc}\n")
            names = [k[0] for k in methods]
            names.sort()

            for name in names:
                if name[0:1] == '_' and name[0:2] != '__':
                    res += f'{name[1:]}\n'

            yield Payload.text(res)
        else:
            method = getattr(self, f"_{value}")
            yield Payload.text(method.__doc__)
