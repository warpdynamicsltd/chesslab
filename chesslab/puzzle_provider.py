import random
from chesslab.puzzle import Puzzle


class PuzzleProvider:
    @classmethod
    def create_set(cls, df, rating, min_popularity=60, min_nbplays=25):
        return df[(df.Rating > rating - 50) & (df.Rating < rating + 50) & (df.Popularity > min_popularity) & (df.NbPlays > min_nbplays)]

    def __init__(self, training_sets, weights):
        self.training_sets = training_sets
        self.weights = weights

        self.rnd_flipped = False

    def next_puzzle(self, display=None, size=400, show_title=False, coordinates=True, solution=False):
        training_set, = random.choices(self.training_sets, weights=self.weights, k=1)
        sample = training_set.sample()
        fen = sample['FEN'].values[0]
        moves = sample['Moves'].values[0]
        rating = sample['Rating'].values[0]
        url = sample['GameUrl'].values[0]
        title = f"{url} ({rating})"
        puzzle = Puzzle(fen=fen, uci_moves_string=moves, title=title)
        puzzle.flipped = False if not self.rnd_flipped else random.choice([False, True])
        if display is not None:
            puzzle.jupyter_dsp(display, size=size, flipped=puzzle.flipped, show_title=show_title, coordinates=coordinates)
            if solution:
                print(puzzle.solution())
        return puzzle

