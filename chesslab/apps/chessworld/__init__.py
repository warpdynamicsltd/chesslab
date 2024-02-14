import os
import random
import math
from datetime import datetime

import chess
import chess.pgn
from chesslab.engine import ChesslabEngine, Limit
from chesslab.apps import MainApp, Payload


class ChessWorld(MainApp):
    """
ChessWorld

an application to simulate games, tournaments and players with specific ratings
    """
    cmd = "chessworld"

    def __init__(self, main_app=None):
        MainApp.__init__(self)
        if main_app is not None:
            main_app.copy_attrs(self)

        self.engine_color = chess.WHITE

        if not hasattr(self, 'rating') or self.rating is None:
            self.rating = 1600

        if not hasattr(self, 'my_rating') or self.my_rating is None:
            self.my_rating = 1600

        if not hasattr(self, 'rating_old') or self.rating_old is None:
            self.rating_old = self.rating

        if not hasattr(self, 'my_rating_old') or self.my_rating_old is None:
            self.my_rating = self.my_rating_old

        if not hasattr(self, 'limit') or self.limit is None:
            self.limit = Limit(nodes=self.rating2nodes(self.rating))

        if not hasattr(self, 'my') or self.my is None:
            self.my = 'white'

        self.resigned = False
        self.my_rating_old = self.my_rating
        self.rating_old = self.rating_old

    def fixed_outcome(self):
        outcome = MainApp.fixed_outcome(self)
        if outcome is None and self.resigned:
            outcome = chess.Outcome(chess.Termination.VARIANT_LOSS, winner=self.engine_color)
        return outcome

    def update_my_rating(self, outcome):
        k = 16
        E_a = 1/(1 + 10**((self.rating - self.my_rating)/400))
        if outcome.winner == self.engine_color:
            S_a = 0
        elif outcome.winner == (not self.engine_color):
            S_a = 1
        else:
            S_a = 0.5

        self.my_rating += k*(S_a - E_a)
        self.my_rating = round(self.my_rating)

    def rating2nodes(self, r):
        # formula approximates more or less the plot given in https://www.melonimarco.it/en/2021/03/08/stockfish-and-lc0-test-at-different-number-of-nodes/
        return round(math.pow(10, 1.7 * math.tan(math.pi * (r - 2250) / 4500) + 3.7))

    def choose_engine_move(self):
        with ChesslabEngine(self.engine_path) as engine:
            lines = engine.analyse(self.board, self.limit, self.lines)

        return lines[0].moves[0]

    def choose_automatic_move(self):
        move = self.book_move()
        if move is not None:
            return move
        return self.choose_engine_move()

    def make_move(self, move):
        self.board.push(move)

    def start(self):
        return self.payload(f"ChessWorld\n{MainApp.copyright_str}")

    def _rating(self, value: int):
        """
Set opponent rating

e.g. rating 1600
"""
        self.rating = value

    def _my(self, value: str):
        """
Set color you play

my white|black|random|alter
"""
        self.my = value

    def choose_engine_color(self):
        if self.my == 'white':
            self.engine_color = chess.BLACK
            return
        if self.my == 'black':
            self.engine_color = chess.WHITE
            return
        if self.my == 'alter':
            self.engine_color = not self.engine_color
            return
        if self.my == 'random':
            self.engine_color = random.choice([True, False])
            return

        return

    def _resign(self):
        if not self.resigned:
            self.resigned = True
            outcome = self.fixed_outcome()
            self.update_my_rating(outcome)
            yield from self.game_info()

    def get_ratings(self):
        white_rating = self.rating if self.engine_color else self.my_rating
        black_rating = self.rating if not self.engine_color else self.my_rating
        return white_rating, black_rating

    def get_ratings_old(self):
        white_rating = self.rating if self.engine_color else self.my_rating_old
        black_rating = self.rating if not self.engine_color else self.my_rating_old
        return white_rating, black_rating

    def rating_info(self):
        white_rating, black_rating = self.get_ratings()
        yield self.payload(f"WHITE {white_rating} ELO")
        yield self.payload(f"BLACK {black_rating} ELO")

    def _pgn(self):
        """
Print sequence of moves in console."""
        game = chess.pgn.Game()
        game.setup(self.fen)
        game.add_line(self.board.move_stack)
        outcome = self.fixed_outcome()
        if outcome is not None:
            game.headers['Result'] = outcome.result()

        if self.engine_color == chess.BLACK:
            game.headers['White'] = "Player"
            game.headers['Black'] = "Chesslab Engine"
        else:
            game.headers['White'] = "Chesslab Engine"
            game.headers['Black'] = "Player"

        white_rating, black_rating = self.get_ratings_old()
        game.headers['WhiteElo'] = str(white_rating)
        game.headers['BlackElo'] = str(black_rating)

        game.headers['Date'] = datetime.now().strftime("%Y.%m.%d")
        game.headers['Site'] = 'Chesslab'
        game.headers['Event'] = 'Chesslab Rated Game'

        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=False)
        pgn_string = game.accept(exporter)
        yield Payload.text(pgn_string)

    def _new(self):
        """
Start new serious game """
        outcome = self.fixed_outcome()
        if outcome is None:
            yield self.payload("game is not finished")
            return

        yield from MainApp._new(self)
        self.my_rating_old = self.my_rating
        self.resigned = False
        self.choose_engine_color()

        if self.engine_color == chess.WHITE:
            move = self.choose_automatic_move()
            self.make_move(move)
            yield self.payload()

        color = 'white' if self.engine_color else 'black'

        self.rating = max(1000, round(random.gauss(self.my_rating, 100)))
        yield from self.rating_info()

        self.limit = Limit(nodes=self.rating2nodes(self.rating))
        self.flipped = self.engine_color

        yield self.payload(f"engine plays {color}")

    def game_info(self):
        yield from self.send_pos_status()
        if self.resigned:
            yield self.payload("RESIGNED")
        yield self.payload(self.get_current_outcome_str())

    def _info(self):
        yield from self.rating_info()

    def _outcome(self):
        """
Display game outcome
"""
        outcome = self.fixed_outcome()
        if outcome is None:
            yield self.payload("game is not finished")
        else:
            yield from self.game_info()

    def go(self, move):
        if move is not None:
            outcome = self.fixed_outcome()
            if outcome is None:
                self.make_move(move)
                yield self.payload()
                outcome = self.fixed_outcome()
                if outcome is not None:
                    self.update_my_rating(outcome)
                    yield from self.game_info()
                else:
                    engine_move = self.choose_automatic_move()
                    san_str = self.board.san(engine_move)
                    self.make_move(engine_move)
                    yield Payload.text(san_str)
                    outcome = self.fixed_outcome()
                    if outcome is not None:
                        self.update_my_rating(outcome)
                        yield from self.game_info()
                    else:
                        yield self.payload()
            else:
                yield self.payload("game is already finished")
                yield from self.game_info()



