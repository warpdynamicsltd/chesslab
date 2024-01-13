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

    def __init__(self, main_app):
        PosLab.__init__(self, main_app)
        self.__dict__ = main_app.__dict__

        if self.df is None:
            self.df = pd.read_csv('data/lichess_db_puzzle.csv.zst')
        self.easy_rating = 1400
        self.medium_rating = 1500
        self.hard_rating = 1700
        self.extreme_rating = 2000

        self.df_easy = PuzzleProvider.create_set(self.df, rating=self.easy_rating)
        self.df_medium = PuzzleProvider.create_set(self.df, rating=self.medium_rating)
        self.df_hard = PuzzleProvider.create_set(self.df, rating=self.hard_rating)
        self.df_extreme = PuzzleProvider.create_set(self.df, rating=self.extreme_rating)

        self.pp = PuzzleProvider(training_sets=[self.df_easy, self.df_medium, self.df_hard, self.df_extreme], weights=[0.5, 0.2, 0.2, 0.1])
        self.pp.rnd_flipped = True
        self.puzzle = None

    def start(self):
        return self.payload(f"TacticsLab\n{MainApp.copyright_str}")

    def _info(self):
        """
Show information needed to solve a puzzle
"""
        yield Payload.text(self.puzzle.get_first_move_str())
        yield Payload.text(f"{self.puzzle.get_turn_name()} to move")
        yield Payload.text(f"pawns direction {self.puzzle.direction_str()}")

    def _next(self):
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
