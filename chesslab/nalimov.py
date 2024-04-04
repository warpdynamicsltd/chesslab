# based on https://github.com/lichess-org/lila-tablebase#http-api

import requests


def tablebase_api(fen):
    _fen = "_".join(fen.split())
    res = requests.get(f"https://tablebase.lichess.ovh/standard?fen={_fen}")
    return res.json()