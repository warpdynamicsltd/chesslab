from chesslab.automaton import Automaton
from chess import Color


class Game:
    def __init__(self, board, automaton, automaton_color: Color):
        self.board = board
        self.automaton = automaton
        self.automaton_color = automaton_color

    def present_board(self):
        if self.board.turn == self.automaton_color:
            return self.automaton.go(self.board)
        else:
            return self.board

    def move(self, algebraic):
        if self.board.turn == self.automaton_color:
            return self.board
        else:
            self.board.push_san(algebraic)
            return self.board