import subprocess
from collections import defaultdict
import chess.pgn
from chess.engine import SimpleEngine, Limit, PovScore, Info


class Line:
    def __init__(self, info):
        self.score = info['score']
        if 'pv' in info:
            self.moves = info['pv']
        else:
            self.moves = []

    def key(self):
        if self.moves:
            return self.moves[0].uci()

        return None

    def sans(self, board):
        res = []
        for move in self.moves:
            res.append(board.san(move))
            board.push(move)

        for _ in range(len(self.moves)):
            board.pop()

        return res

    def png(self, board):
        game = chess.pgn.Game()
        game.setup(board.fen())
        game.add_line(self.moves)

        exporter = chess.pgn.StringExporter(columns=None, headers=False, variations=True, comments=False)
        pgn_string = game.accept(exporter)
        return pgn_string

    def score_str(self):
        score_rw = self.score.white()
        if score_rw.is_mate():
            mate = score_rw.mate()
            return f"#{mate}"
        else:
            return f"{score_rw.score()/100:.2f}"


class ChesslabEngine:
    def __init__(self, path):
        self.engine = SimpleEngine.popen_uci(path)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.engine.quit()

    def analysis(self, board, limit):
        return self.engine.analysis(board, limit)

    def analyse(self, board, limit, multipv):
        res = []
        analysis = self.engine.analyse(board, limit=limit, multipv=multipv)
        for info in analysis:
            res.append(Line(info))

        return res


