import os
import sys
import pandas as pd
import sqlite3
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

read about following commands: new, info, solve, again, decide, restart, go

all commands available:
"""
    cmd = 'tactics'
    table_name = 'lichess_puzzle'
    @classmethod
    def create_puzzles_db(cls, source_path):
        if not os.path.exists(cls.puzzles_db_path):
            print("creating puzzles database")
            con = sqlite3.connect(cls.puzzles_db_path)
            con.execute("PRAGMA journal_mode=OFF;")
            con.execute(f"DROP TABLE IF EXISTS {cls.table_name};")
            for chunk in pd.read_csv(source_path, chunksize=100000):
                chunk.to_sql(name=cls.table_name, con=con, if_exists='append')
                sys.stdout.write('.')
                sys.stdout.flush()
            con.execute(f"CREATE INDEX puzzle_search_index ON {cls.table_name}(PuzzleId, Rating, Popularity, NbPlays)")
            con.commit()
            con.close()

    def __init__(self, main_app=None):
        PosLab.__init__(self, main_app)
        if main_app is not None:
            main_app.copy_attrs(self)

        if not hasattr(self, 'ratings') or self.ratings is None:
            self.ratings = [1400, 1500, 1700, 2000]

        if not hasattr(self, 'probs') or self.probs is None:
            self.probs = [0.5, 0.2, 0.2, 0.1]

        if not hasattr(self, 'pp') or self.pp is None:
            self.create_puzzle_provider()

        if not hasattr(self, 'puzzle') or self.puzzle is None:
            self.puzzle = None
            self.next_puzzle()

        self.flipped = self.puzzle.flipped
        self.fen = self.puzzle.fen
        self.board = self.puzzle.board

    def create_puzzle_provider(self):
        con = sqlite3.connect(self.puzzles_db_path)
        training_sets = [PuzzleProvider.create_set_from_sqlite(con, table_name=self.table_name, rating=rating) for rating in self.ratings]
        con.close()
        if len(self.ratings) != len(self.probs):
            raise Exception("there must be the same ratings as probs")
        self.pp = PuzzleProvider(training_sets=training_sets, weights=self.probs)
        self.pp.rnd_flipped = True

    def next_puzzle(self):
        con = sqlite3.connect(self.puzzles_db_path)
        self.puzzle = self.pp.next_puzzle(con, self.table_name)
        con.close()

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
        self.next_puzzle()
        self.flipped = self.puzzle.flipped
        yield from self._info()
        yield from PosLab._fen(self, self.puzzle.board.fen())

    def _solve(self):
        """
Show solution as provided by lichess.org.
"""
        yield Payload.text(self.puzzle.title)
        yield Payload.text(self.puzzle.solution())
