import chess
from chesslab.engine import ChesslabEngine
from chesslab.apps import MainApp, Payload

from chess.engine import Limit
from chess import Board


class Node:
    def __init__(self, turn):
        self.children = {}
        self.lines = []
        self.turn = turn
        self.human_success = False
        self.parent = None
        self.outcome = None


class PosLab(MainApp):
    def __init__(self, main_app):
        MainApp.__init__(self)
        self.__dict__ = main_app.__dict__
        self.engine_color = None
        self.current_node = None
        self.limit = Limit(time=1)
        self.fen = self.board.fen()
        self.set_fen()
        self.initialise()

    def start(self):
        return self.payload("PosLab\nCopyright (c) 2022 Michal Stanislaw Wojcik. All rights reserved.")

    def initialise(self):
        self.engine_color = (not self.board.turn)
        self.current_node = Node(self.board.turn)

    def make_move(self, move):
        self.board.push(move)
        key = move.uci()
        if key in self.current_node.children:
            node = self.current_node.children[key]
        else:
            node = Node(self.board.turn)
            node.parent = self.current_node
            node.outcome = self.board.outcome(claim_draw=True)
            self.current_node.children[key] = node

        self.current_node = node

    def go(self, move):
        print('*')
        text = None
        if self.current_node.outcome is None:
            self.make_move(move)
            yield from self.send_pos_status()
            yield self.payload(self.get_current_outcome_str())

            if self.current_node.outcome is None:
                engine_move = self.choose_engine_move()
                san_str = self.board.san(engine_move)
                self.make_move(engine_move)
                yield Payload.text(san_str)
                yield from self.send_pos_status()
            else:
                return

        yield self.payload(self.get_current_outcome_str())

    def choose_engine_move(self):
        print('engine_color', self.engine_color)
        if self.current_node.turn != self.engine_color:
            raise Exception("not engine move")
        if self.board.turn != self.engine_color:
            raise Exception("not engine move")

        if len(self.current_node.lines) == 0:
            with ChesslabEngine(self.engine_path) as engine:
                self.current_node.lines = engine.analyse(self.board, self.limit, self.lines)

        index = 0
        for line in self.current_node.lines:
            key = line.key()
            if key in self.current_node.children:
                child_node = self.current_node.children[key]
                if child_node.human_success:
                    index += 1
                    continue
                else:
                    break

        if index == len(self.current_node.lines):
            index = 0

        move = self.current_node.lines[index].moves[0]

        return move

    def rewind_and_back_propagate_outcome(self):
        if self.current_node.outcome is not None:

            # determine if this is human success
            if self.current_node.outcome.winner is None:
                self.current_node.human_success = True
            if self.current_node.outcome.winner == (not self.engine_color):
                self.current_node.human_success = True

            human_success = self.current_node.human_success
            # back propagate human success
            while self.current_node.parent is not None:
                self.current_node = self.current_node.parent
                if human_success:
                    self.current_node.human_success = True

    def _again(self, value):
        self.rewind_and_back_propagate_outcome()
        yield from MainApp._again(self, value)

    def _fen(self, value):
        yield from MainApp._fen(self, value)
        self.initialise()

    def _reset(self, value):
        yield from self._fen(self.fen)

    def _new(self, value):
        yield from MainApp._new(self, value)
        self.initialise()

    def _time(self, value):
        self.limit = Limit(time=int(value))

    def _back(self, value):
        yield self.payload("Can't take back during serious game")