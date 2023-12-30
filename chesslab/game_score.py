import time
import sys
import numpy as np


def score_to_numeric(score, mate_score=1000):
    if score.is_mate():
        if score.mate() > 0:
            value = mate_score
        else:
            value = -mate_score
    else:
        value = max(min(score.score(), mate_score), -mate_score)

    return value


def cmp_score(best_score, score, mate_score=1000):
    best_value = score_to_numeric(best_score, mate_score)
    value = score_to_numeric(score, mate_score)
    return min(value - best_value, 0)


class GameScore:
    def __init__(self, game, engine, limit):
        self.engine = engine
        self.game = game
        self.board = game.board()
        self.limit = limit

    def evaluate(self):
        self.board = self.game.board()
        res = {'white': [], 'black': []}
        for i, move in enumerate(self.game.mainline_moves()):
            color = 'white' if self.board.turn else 'black'
            r = self.diff(move)
            res[color].append(r)
            self.board.push(move)
            sys.stdout.write('.')
        print("")
        return res

    def score(self):
        res = self.evaluate()
        return {'white': np.mean([k for k in res['white'] if k is not None]),
                'black': np.mean([k for k in res['black'] if k is not None])}

    def diff(self, move):
        res = self.engine.analyse(self.board, self.limit)
        best_move = res['pv'][0]
        color = self.board.turn
        self.board.push(best_move)
        res_best = self.engine.analyse(self.board, self.limit)
        best_score = res_best['score'].pov(color)
        self.board.pop()
        self.board.push(move)
        res = self.engine.analyse(self.board, self.limit)
        score = res['score'].pov(color)
        self.board.pop()
        return cmp_score(best_score, score)
