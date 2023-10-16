import random
from abc import ABC, abstractmethod
from chess import Board, Move, Color


class Evaluation:
    def __init__(self, color, res_eval):
        self.color_on_move = color
        self.eval_res = res_eval


def evaluate(board, engine, limit):
    res = {}
    for mov in board.legal_moves:
        board.push(mov)
        key = mov.uci()
        res[key] = {}
        analysis = engine.analysis(board, limit)
        for info in analysis:
            if 'depth' in info and 'score' in info:
                res[key][info['depth']] = info['score']

        board.pop()

    return Evaluation(board.turn, res)


class Selector(ABC):
    @abstractmethod
    def select_move(self, evaluation):
        pass


class SimpleSelector(Selector):
    def select_move(self, evaluation):
        eval_res = evaluation.eval_res
        move_list = []
        for move_key in eval_res:
            depths = list(eval_res[move_key].keys())
            depths.sort()
            max_depth = depths[-1]
            score = eval_res[move_key][max_depth].pov(evaluation.color_on_move)
            move_list.append((move_key, score))

        move_list.sort(key=lambda k: k[1])
        return Move.from_uci(move_list[-1][0])


class RandomSelector(Selector):
    def __init__(self, tolerance=100):
        self.tolerance = tolerance

    def select_move(self, evaluation):
        eval_res = evaluation.eval_res
        move_list = []
        for move_key in eval_res:
            depths = list(eval_res[move_key].keys())
            depths.sort()
            max_depth = depths[-1]
            score = eval_res[move_key][max_depth].pov(evaluation.color_on_move)
            move_list.append((move_key, score))

        move_list.sort(key=lambda k: k[1])
        max_score = move_list[-1][1]
        max_score_v = max_score.score()
        if max_score.is_mate():
            return Move.from_uci(move_list[-1][0])

        moves = []
        for m, score in move_list:
            if not score.is_mate():
                if max_score_v - score.score() <= self.tolerance:
                    moves.append(m)

        m = random.choice(moves)
        return Move.from_uci(m)


