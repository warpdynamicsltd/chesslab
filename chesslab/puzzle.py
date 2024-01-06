import chess
import chess.pgn
from chess import Board, Move, Color


class Puzzle:
    def __init__(self, fen, uci_moves_string, title=str()):
        self.title=title
        uci_moves = uci_moves_string.split()
        self.moves = [Move.from_uci(move) for move in uci_moves]
        self.fen = fen
        self.board = Board(fen)
        self.first_move = self.moves[0]

        self.moves_san = self.moves_to_san()
        self.first_move_san = self.moves_san[0]

        self.board.push(self.first_move)

    def get_turn_name(self):
        return 'white' if self.board.turn else 'black'

    def get_last_move_san(self):
        return self.first_move_san

    def get_first_move_str(self):
        game = chess.pgn.Game()
        game.setup(self.fen)
        game.add_line(self.moves[:1])

        exporter = chess.pgn.StringExporter(headers=False, variations=True, comments=False)
        pgn_string = game.accept(exporter)
        return pgn_string

    def check_solution(self, move_san):
        return self.board.parse_san(move_san) == self.moves[1]

    def moves_to_san(self):
        moves_san = []
        board = Board(self.fen)
        for move in self.moves:
            moves_san.append(board.san(move))
            board.push(move)

        return moves_san

    def solution(self):
        game = chess.pgn.Game()
        game.setup(self.fen)
        game.add_line(self.moves)

        exporter = chess.pgn.StringExporter(headers=False, variations=True, comments=False)
        pgn_string = game.accept(exporter)
        return pgn_string

    def jupyter_dsp(self, display, size=400, flipped=False, show_title=False, coordinates=False):
        if show_title:
            print(self.title)
        print(self.get_first_move_str())
        display(chess.svg.board(self.board, size=size, flipped=flipped, coordinates=coordinates))
        print("\u2191" if (self.board.turn and not flipped) or (not self.board.turn and flipped) else "\u2193")
        print(f"{self.get_turn_name()} to move")




