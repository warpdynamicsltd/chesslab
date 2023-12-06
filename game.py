import cairosvg
from multiprocessing import Process, Queue
from queue import Empty
import io
import time
import PySimpleGUI as sg

import subprocess

import chess
import chess.svg

import chesslab
from chesslab.evaluator import SimpleSelector, RandomSelector
from chesslab.automaton import Automaton
from chesslab.game import Game

from chess.engine import SimpleEngine, Limit
from chess import Board

# CONFIG
engine = SimpleEngine.popen_uci("engines/stockfish.exe", creationflags=subprocess.CREATE_NO_WINDOW)
selector = RandomSelector(tolerance=200)
limit = Limit(time=1)
# start_fen = chess.STARTING_FEN
start_fen = "5nk1/pp2r2p/2p2p1Q/3p1p1P/3P2P1/2P5/PqBK4/7R b - g3 0 1"
automaton_color = chess.WHITE

automaton = Automaton(engine, limit, selector)
board = Board(fen=start_fen)
game = Game(board, automaton, automaton_color)

##


def convert_svg_to_png(svg_string):
    output = io.BytesIO()
    cairosvg.svg2png(bytestring=svg_string, write_to=output)
    return output


def gui(in_queue, out_queue):
    cmd, data = in_queue.get()

    layout = [
        [sg.Text('Enter something')],
        [sg.InputText(key='-INPUT-')],
        [sg.Image(data=data, key='-IMAGE-')],
        [sg.Button('Play'), sg.Button('Exit')]
    ]

    window = sg.Window('Input Field Demo', layout)

    while True:
        event, values = window.read(timeout=25)

        if event == sg.WINDOW_CLOSE_ATTEMPTED_EVENT or event == 'Exit':
            time.sleep(0.5)
            break
        if event == 'Play':
            algebraic = values['-INPUT-']
            out_queue.put(('MOV', algebraic))

        try:
            cmd, data = in_queue.get(block=False)
            if cmd == 'BOARD_IMG':
                print('BOARD_IMG')
                window['-IMAGE-'].update(data=data)
        except Empty:
            pass

    window.close()


def main():
    in_queue = Queue()
    out_queue = Queue()
    in_queue.put(('BOARD_IMG', convert_svg_to_png(chess.svg.board(board)).getvalue()))
    p = Process(target=gui, args=(in_queue, out_queue))
    p.start()
    while not board.is_game_over():
        cmd, data = out_queue.get()
        if cmd == 'MOV':
            print('MOV')
            game.move(data)
            in_queue.put(('BOARD_IMG', convert_svg_to_png(chess.svg.board(board)).getvalue()))
            print("put image into query")
            game.present_board()
            in_queue.put(('BOARD_IMG', convert_svg_to_png(chess.svg.board(board)).getvalue()))
            print("put image into query")

    print(board.outcome())

    p.join()


if __name__ == '__main__':
    main()
