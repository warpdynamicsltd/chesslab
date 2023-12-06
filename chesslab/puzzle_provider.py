import random
from chesslab.puzzle import Puzzle


class PuzzleProvider:
    def __init__(self, training_sets, weights):
        self.training_sets = training_sets
        self.weights = weights

        self.rnd_flipped = False

    def next_puzzle(self, display=None, size=400):
        training_set, = random.choices(self.training_sets, weights=self.weights, k=1)
        sample = training_set.sample()
        fen = sample['FEN'].values[0]
        moves = sample['Moves'].values[0]
        rating = sample['Rating'].values[0]
        puzzle = Puzzle(fen=fen, uci_moves_string=moves, title=rating)
        flipped = False if not self.rnd_flipped else random.choice([False, True])
        if display is not None:
            puzzle.jupyter_dsp(display, size=size, flipped=flipped)
        return puzzle

