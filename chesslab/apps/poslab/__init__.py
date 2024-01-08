import chess
from chesslab.engine import ChesslabEngine
from chesslab.apps import MainApp, Payload

from chess import Move, Outcome, Termination
from chess.engine import Limit, Cp, Mate, Score, PovScore
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
            if node.outcome is None:
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
                yield Payload.text(self.current_node.outcome.result())
                return
        else:
            yield Payload.text(self.current_node.outcome.result())
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

        move = self.current_node.choose_move(self.engine_color)

        return move

    def rewind_and_back_propagate_outcome(self):
        assert(self.current_node.outcome is not None)

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

        self.current_node.eval_score = 0
        self.current_node.clear_evals()

    def _again(self, value):
        if self.current_node.outcome is None:
            yield Payload.text("Can't start again with unknown outcome")
            return
        self.rewind_and_back_propagate_outcome()
        yield from MainApp._again(self, value)

    def _fen(self, value):
        yield from MainApp._fen(self, value)
        self.initialise()

    def _restart(self, value):
        yield from self._fen(self.fen)

    def _new(self, value):
        yield from MainApp._new(self, value)
        self.initialise()

    def _time(self, value):
        self.limit = Limit(time=int(value))

    def _back(self, value):
        yield self.payload("Can't take back during serious game.")

    def _decide(self, value):
        if self.current_node.parent is not None:
            parent = self.current_node.parent
            if value == "white wins":
                parent.outcome = Outcome(winner=chess.WHITE, termination=Termination.VARIANT_WIN)
            elif value == "black wins":
                parent.outcome = Outcome(winner=chess.BLACK, termination=Termination.VARIANT_LOSS)
            elif value == "draw":
                parent.outcome = Outcome(winner=None, termination=Termination.VARIANT_DRAW)
            self.current_node.outcome = parent.outcome
            yield Payload.text(self.current_node.outcome.result())
        else:
            yield Payload.text("Can't decide outcome at root position.")
