import os
import random

import chess
from chesslab.engine import ChesslabEngine
from chesslab.apps import MainApp, Payload

from chess import Move, Outcome, Termination
from chess.engine import Limit, Cp, Mate, Score, PovScore
import chess.polyglot
from chess import Board


class Node:
    MATE_SCORE_VALUE = 0xffffffff

    def __init__(self, turn):
        self.children = {}
        self.lines = []
        self.turn = turn
        self.human_success = False
        self.parent = None
        self.outcome = None
        self.eval_score = None
        self.bookmark = False
        self.fen = None

    def get_score_from_lines_copy(self):
        index = 0
        for line in self.lines:
            key = line.key()
            if key in self.children:
                child_node = self.children[key]
                if child_node.human_success:
                    index += 1
                    continue
                else:
                    break

        if index == len(self.lines):
            index = 0

        move = None
        if self.lines[index].moves:
            move = self.lines[index].moves[0]

        return self.lines[index].score.relative.score(mate_score=Node.MATE_SCORE_VALUE), move

    def get_score_from_lines(self):
        move = None
        score = float("-inf")
        for line in self.lines:
            key = line.key()
            if key in self.children:
                child_node = self.children[key]
                if child_node.human_success:
                    continue

            if line.moves:
                move = line.moves[0]
                score = line.score.relative.score(mate_score=Node.MATE_SCORE_VALUE)
                break

        return score, move

    def eval(self, engine_color):
        if self.eval_score is not None:
            return self.eval_score

        if self.outcome is not None:
            if self.outcome.winner is None:
                self.eval_score = 0
            elif self.outcome.winner == engine_color:
                self.eval_score = Node.MATE_SCORE_VALUE
            elif self.outcome.winner == (not engine_color):
                self.eval_score = - 2 * Node.MATE_SCORE_VALUE

            return self.eval_score

        if self.turn == engine_color:
            assert(len(self.lines) > 0)
            children_scores = [self.children[key].eval(engine_color) for key in self.children if self.children[key].human_success]
            if children_scores:
                max_children_score = max(children_scores)
                score, _ = self.get_score_from_lines()
                self.eval_score = max(score, max_children_score)
            else:
                self.eval_score, _ = self.get_score_from_lines()

        else:
            assert (len(self.children) > 0)
            children_scores = [self.children[key].eval(engine_color) for key in self.children if self.children[key].human_success]
            self.eval_score = min(children_scores)

        return self.eval_score

    # Simple version
    # def choose_move(self):
    #     _, move = self.get_score_from_lines()
    #     return move

    def choose_move(self, engine_color):
        """
        Fix problem it does not traverse all important variants
        """
        evaluated_score = self.eval(engine_color)
        score, move = self.get_score_from_lines()

        if move is not None and score >= evaluated_score:
            return move

        for key in self.children:
            child = self.children[key]
            if child.human_success:
                if child.eval(engine_color) >= evaluated_score:
                    move = Move.from_uci(key)
                    return move

        # shouldn't be here
        assert False

    def clear_evals(self):
        self.eval_score = None
        for key in self.children:
            child = self.children[key]
            if child.human_success:
                child.clear_evals()


class PosLab(MainApp):
    """
PosLab

An application to practice winning position by
playing different variations against the engine.
For the first time engine plays optimally
and then remembers lost variations.
When you play again, it deviates from the previous variations
to test your play.
Human player always has first move regardless of color.

read about following commands: again, decide, bookmark, go

all commands available:"""

    cmd = "poslab"

    def __init__(self, main_app=None):
        MainApp.__init__(self)
        if main_app is not None:
            main_app.copy_attrs(self)

        self.engine_color = None
        self.current_node = None
        self.board_node = None
        if not hasattr(self, 'limit') or self.limit is None:
            self.limit = Limit(time=1)
        self.fen = self.board.fen()
        self.set_fen()
        self.initialise()
        self.human_moved = False
        self.book = True

    def start(self):
        yield self.payload(f"PosLab\n{MainApp.copyright_str}")

    def initialise(self, engine_color=None):
        if engine_color is None:
            self.engine_color = (not self.board.turn)
        else:
            self.engine_color = engine_color
        self.current_node = Node(self.board.turn)
        self.current_node.fen = self.board.fen()
        self.board_node = self.current_node
        self.human_moved = False

    def make_move(self, move):
        self.board.push(move)
        key = move.uci()
        if key in self.current_node.children:
            node = self.current_node.children[key]
        else:
            node = Node(self.board.turn)
            node.parent = self.current_node
            if node.outcome is None:
                node.outcome = self.fixed_outcome()
            self.current_node.children[key] = node

        self.current_node = node
        self.current_node.fen = self.board.fen()
        self.board_node = self.current_node

    def bookmark_info_string(self):
        if self.current_node.bookmark:
            yield Payload.text("POSITION BOOKMARKED")

    def go(self, move):
        text = None
        if self.current_node.outcome is None:
            if move is not None:
                if self.engine_color == self.board.turn:
                    yield Payload.text('Engine is on move now.\nType go for engine to move')
                    return
                self.make_move(move)
                self.human_moved = True
                yield from self.send_pos_status()
                yield self.payload(self.get_current_outcome_str())
            else:
                if self.engine_color != self.board.turn:
                    yield Payload.text('waiting for your move')
                    return

            if self.current_node.outcome is None:
                book_move = self.book_move()

                if book_move is not None:
                    engine_move = book_move
                    yield Payload.text('book')
                else:
                    engine_move = self.choose_engine_move()

                san_str = self.board.san(engine_move)
                self.make_move(engine_move)
                yield from self.send_move_to_bt(engine_move.uci())
                yield Payload.text(san_str)
                yield from self.send_pos_status()
            else:
                yield Payload.text(self.current_node.outcome.result())
                yield from self.bookmark_info_string()
                return
        else:
            yield from self.send_pos_status()
            yield self.payload(self.current_node.outcome.result())
            yield from self.bookmark_info_string()
            return

        yield self.payload(self.get_current_outcome_str())
        yield from self.bookmark_info_string()


    def choose_engine_move(self):
        if self.current_node.turn != self.engine_color:
            raise Exception("not engine move")
        if self.board.turn != self.engine_color:
            raise Exception("not engine move")

        if len(self.current_node.lines) == 0:
            with ChesslabEngine(self.engine_path) as engine:
                self.current_node.lines = engine.analyse(self.board, self.limit, self.lines)

        move = self.current_node.choose_move(self.engine_color)

        return move

    def rewind_and_back_propagate_outcome(self):
        if self.current_node.outcome is not None:
        # determine if this is human success
            if self.current_node.outcome.winner is None:
                self.current_node.human_success = True
            if self.current_node.outcome.winner == (not self.engine_color):
                self.current_node.human_success = True

        human_success = self.current_node.human_success

        bookmarked_node = None
        # back propagate human success
        while self.current_node.parent is not None:
            self.current_node = self.current_node.parent
            if bookmarked_node is None and self.current_node.bookmark:
                bookmarked_node = self.current_node
            if human_success:
                self.current_node.human_success = True

        self.current_node.eval_score = 0
        self.current_node.clear_evals()
        if bookmarked_node is not None:
            self.current_node = bookmarked_node
            # self.current_node.bookmark = False

    def _bookmark(self, value: str = None):
        if value is None:
            self.current_node.bookmark = True
        else:
            self.current_node.bookmark = False

    def _again(self):
        """
Play the position again against the engine.
Your previous variations are remembered and used to choose different variations to play."""
        if self.human_moved and self.current_node.outcome is None:
            yield Payload.text("Can't start again with unknown outcome")
            return
        self.rewind_and_back_propagate_outcome()
        while id(self.current_node) != id(self.board_node):
            self.board_node = self.board_node.parent
            self.board.pop()
        self.human_moved = False
        yield self.payload()

    def _fen(self, value: str = None):
        """
Set borad position in Forsyth–Edwards Notation (FEN).

fen <arg: str>

e.g. fen rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"""
        if value is None:
            raise Exception("missing argument")

        yield from MainApp._fen(self, value)
        self.initialise()

    def _restart(self, engine_color: str = None):
        """
Delete all memory from played variations and start again

restart - you plays first
restart white - engine plays as white
restart black - engine plays as black
"""
        yield from MainApp._fen(self, self.fen)
        if engine_color is None:
            self.initialise()
        else:
            self.initialise(engine_color == 'white')

    def _onmove(self):
        """
Print who is on move """

        if self.board.turn == self.engine_color:
            yield Payload.text("engine")
        else:
            yield Payload.text("you")

    def _go(self):
        """
Triggers engine to move if engine has first move."""

        if self.board.turn == self.engine_color:
            yield from self.go(move=None)
        else:
            yield Payload.text("You are on move now.\nType your move")

    def _new(self):
        """
Set the board in an initial position of game of chess."""
        yield from MainApp._new(self)
        self.initialise()

    def _time(self, value: int):
        """
Set the time as an argument in seconds, how long engine will think on its move

time <arg: int>

e.g. time 10
"""
        self.limit = Limit(time=value)

    def _limit(self, arg_name: str = 'time', value=1.0):
        """
Limit engine player strength

limit <arg_name: str> <value>

e.g.
limit time 5
limit nodes 100
limit nodes 2.5k
limit nodes 3.1m"""
        self.limit = self.parse_limit(arg_name, value)

    def _rating(self, value: int):
        """
Set engine strength limit based on rating

rating <value: int>

e.g.
rating 1300"""
        self.limit = Limit(nodes=self.rating2nodes(value))

    def _back(self):
        yield self.payload("Can't take back during serious game.")

    def _decide(self, value: str):
        """
Make an arbitrary decision what is the outcome of the reached position.

decide white-wins|black-wins|draw
"""
        # if self.current_node.parent is not None:
        #     parent = self.current_node.parent
        #     if value == "white-wins":
        #         parent.outcome = Outcome(winner=chess.WHITE, termination=Termination.VARIANT_WIN)
        #     elif value == "black-wins":
        #         parent.outcome = Outcome(winner=chess.BLACK, termination=Termination.VARIANT_LOSS)
        #     elif value == "draw":
        #         parent.outcome = Outcome(winner=None, termination=Termination.VARIANT_DRAW)
        #     self.current_node.outcome = parent.outcome

        if self.current_node.outcome is None:
            node = self.current_node
            if value == "white-wins":
                node.outcome = Outcome(winner=chess.WHITE, termination=Termination.VARIANT_WIN)
            elif value == "black-wins":
                node.outcome = Outcome(winner=chess.BLACK, termination=Termination.VARIANT_LOSS)
            elif value == "draw":
                node.outcome = Outcome(winner=None, termination=Termination.VARIANT_DRAW)
            yield Payload.text(self.current_node.outcome.result())
        else:
            yield Payload.text("Can't decide outcome at root position.")