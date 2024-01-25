import random
import pandas as pd
from chesslab.puzzle import Puzzle


class PuzzleProvider:
    @classmethod
    def create_set(cls, df, rating, min_popularity=60, min_nbplays=25):
        return df[(df.Rating > rating - 50) & (df.Rating < rating + 50) & (df.Popularity > min_popularity) & (df.NbPlays > min_nbplays)]

    @classmethod
    def create_set_from_sqlite(cls, con, table_name, rating, min_popularity=60, min_nbplays=25):
        df = pd.read_sql(f"SELECT PuzzleId FROM {table_name} WHERE Rating > {rating - 50} AND Rating < {rating + 50} AND Popularity > {min_popularity} AND NbPlays > {min_nbplays};", con)
        return df

    def __init__(self, training_sets, weights):
        self.training_sets = training_sets
        self.weights = weights

        self.rnd_flipped = False

    def next_puzzle(self, con, table_name):
        training_set, = random.choices(self.training_sets, weights=self.weights, k=1)
        sample = training_set.sample()
        puzzle_id = sample['PuzzleId'].values[0]
        return self.get_puzzle(con, table_name, puzzle_id)

    def get_puzzle(self, con, table_name, puzzle_id):
        sample = pd.read_sql(f"SELECT * FROM {table_name} WHERE PuzzleId = '{puzzle_id}'", con)
        fen = sample['FEN'].values[0]
        moves = sample['Moves'].values[0]
        rating = sample['Rating'].values[0]
        url = sample['GameUrl'].values[0]
        title = f"{url} ({rating})"
        puzzle = Puzzle(puzzle_id=puzzle_id, fen=fen, uci_moves_string=moves, title=title)
        puzzle.flipped = False if not self.rnd_flipped else random.choice([False, True])
        return puzzle

