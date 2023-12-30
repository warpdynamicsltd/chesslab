import time
import chess.pgn
from chess.engine import Limit
from chesslab.game_score import GameScore


class Collection:
    def __init__(self, path):
        self.path = path
        self.games = []
        self.load()

    def load(self):
        with open(self.path) as pgn:
            while True:
                game = chess.pgn.read_game(pgn)
                if game is None:
                    break
                self.games.append(game)

    def compute_scores_and_save(self, engine, limit=Limit(time=0.5), overwrite=False):
        start = time.time()
        for i, game in enumerate(self.games):
            if overwrite or ('WhiteScore' not in game.headers):
                print(f"game {i + 1}")
                gs = GameScore(game, engine, limit)
                score = gs.score()
                game.headers["WhiteScore"] = str(round(score['white'], 2))
                game.headers["BlackScore"] = str(round(score['black'], 2))
                self.save()
                print(f"{round(time.time() - start)} sec")

    def remove_comments_and_variations_for_game(self, original_game):
        clean_game = chess.pgn.Game()

        # Copying game headers (optional, but usually desirable)
        for key, value in original_game.headers.items():
            clean_game.headers[key] = value

        # Node pointer for the new game
        node = clean_game

        # Iterate over the mainline moves of the original game
        for mainline_move in original_game.mainline_moves():
            node = node.add_variation(mainline_move)

        return clean_game

    def remove_comments_and_variations(self):
        clean_games = []
        for game in self.games:
            clean_games.append(self.remove_comments_and_variations_for_game(game))
        self.games = clean_games

    def sort(self, key=lambda game: game.headers['Date']):
        self.games.sort(key=key)

    def add_game(self, game, compute_score_save=True):
        self.games.append(game)
        self.sort()

    def save(self):
        if self.games:
            with open(self.path, "w", encoding="utf-8") as pgn:
                exporter = chess.pgn.FileExporter(pgn)
                for game in self.games:
                    game.accept(exporter)
