import time
import random
import glob
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
        self.colors = {
            'square dark': "#858383",
            'square light': "#d9d7d7"
        }

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
        return self.payload(f"Chesslab\n{MainApp.copyright_str}")

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

    def execute(self, cmd, value):
        # print(cmd, value)
        res = None
        try:
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
        self.board.reset()

        if self.chess960:
            self.board = Board(chess960=True)
            self.board.set_chess960_pos(random.randint(0, 959))
            self.fen = self.board.fen()
        else:
            self.fen = chess.STARTING_FEN
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

        exporter = chess.pgn.StringExporter(headers=False, variations=True, comments=False)
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
