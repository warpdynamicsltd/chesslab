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

    return res

