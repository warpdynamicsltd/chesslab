from chesslab.evaluator import evaluate, Selector


class Automaton:
    def __init__(self, engine, limit, selector: Selector):
        self.engine = engine
        self.limit = limit
        self.selector = selector

    def move(self, board):
        evaluation = evaluate(board, self.engine, self.limit)
        mov = self.selector.select_move(evaluation)
        board.push(mov)
        return board
