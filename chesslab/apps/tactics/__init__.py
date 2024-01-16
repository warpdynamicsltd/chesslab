import pandas as pd
import chess
from chesslab.engine import ChesslabEngine
from chesslab.apps import MainApp, Payload
from chesslab.apps.poslab import PosLab

from chesslab.puzzle import Puzzle
from chesslab.puzzle_provider import PuzzleProvider


class TacticsLab(PosLab):
    """
TacticsLab
includes PosLab

An application to solve chess tactics puzzles downloaded from https://database.lichess.org/#puzzles

read about following commands: next, info, solve, again, decide
"""
    cmd = 'tactics'

    def __init__(self, main_app=None):
        PosLab.__init__(self, main_app)
        if main_app is not None:
            main_app.copy_attrs(self)

        if not hasattr(self, 'df') or self.df is None:
            self.df = pd.read_csv('data/lichess_db_puzzle.csv.zst')

        if not hasattr(self, 'ratings') or self.ratings is None:
            self.ratings = [1400, 1500, 1700, 2000]

        if not hasattr(self, 'probs') or self.probs is None:
            self.probs = [0.5, 0.2, 0.2, 0.1]

        self.pp = None
        self.create_puzzle_provider()
        if not hasattr(self, 'puzzle') or self.puzzle is None:
            self.puzzle = self.pp.next_puzzle(size=None, coordinates=None, solution=True)

        self.flipped = self.puzzle.flipped
        self.fen = self.puzzle.fen
        self.board = self.puzzle.board

    def create_puzzle_provider(self):
        training_sets = [PuzzleProvider.create_set(self.df, rating=rating) for rating in self.ratings]
        if len(self.ratings) != len(self.probs):
            raise Exception("there must be the same ratings as probs")
        self.pp = PuzzleProvider(training_sets=training_sets, weights=self.probs)
        self.pp.rnd_flipped = True

    def start(self):
        return self.payload(f"TacticsLab\n{MainApp.copyright_str}")

    def _ratings(self, *args):
        self.ratings = list(map(int, args))
        self.create_puzzle_provider()

    def _probs(self, *args):
        self.probs = list(map(float, args))
        self.create_puzzle_provider()

    def _info(self):
        """
Show information needed to solve a puzzle
"""
        yield Payload.text(self.puzzle.get_first_move_str())
        yield Payload.text(f"{self.puzzle.get_turn_name()} to move")
        yield Payload.text(f"pawns direction {self.puzzle.direction_str()}")

    def _new(self):
        """
Next randomly chosen puzzle from predefined set.
"""
        self.puzzle = self.pp.next_puzzle(size=None, coordinates=None, solution=True)
        self.flipped = self.puzzle.flipped
        yield from self._info()
        yield from PosLab._fen(self, self.puzzle.board.fen())

    def _solve(self):
        """
Show solution as provided by lichess.org.
"""
        yield Payload.text(self.puzzle.title)
        yield Payload.text(self.puzzle.solution())
