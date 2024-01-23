import os
import sys
import shutil
import sqlite3
import pandas as pd
from setuptools import setup, find_packages

chesslab_home = os.path.join(os.path.expanduser('~'), '.chesslab')
puzzles_db_path = os.path.join(chesslab_home, 'puzzles_db')
table_name = 'lichess_puzzle'


# def create_puzzles_db():
#     if not os.path.exists(puzzles_db_path):
#         print("creating puzzles database")
#         con = sqlite3.connect(puzzles_db_path)
#         con.execute("PRAGMA journal_mode=OFF;")
#         con.execute(f"DROP TABLE IF EXISTS {table_name};")
#         for chunk in pd.read_csv(os.path.join('data', 'lichess_db_puzzle.csv.zst'), chunksize=100000):
#             chunk.to_sql(name=table_name, con=con, if_exists='append')
#             sys.stdout.write('.')
#             sys.stdout.flush()
#         # con.execute(f"CREATE INDEX puzzle_search_index ON {cls.table_name}(Rating, Popularity, NbPlays)")
#         con.commit()
#         sys.stdout.write('\n')


if not os.path.isdir(chesslab_home):
    os.mkdir(chesslab_home)


#shutil.copy(os.path.join('data', 'lichess_db_puzzle.csv.zst'), os.path.join(chesslab_home, 'lichess_db_puzzle.csv.zst'))
shutil.copy(os.path.join('data', 'book', 'book.bin'), os.path.join(chesslab_home, 'book.bin'))

setup(
    name='chesslab',
    version='',
    packages=find_packages(),
    url='',
    license='Copyright (c) 2023 Warp Dynamics Limited. All rights reserved.',
    author='Michal Wojcik',
    author_email='wojcik@warpdynamics.co.uk',
    description='',
    scripts=['chesslab/scripts/chessui.py'],
    entry_points={
            'console_scripts': [
                'chesslab = chesslab.scripts.chessui:main'
            ]}
)

from chesslab.apps.tactics import TacticsLab
TacticsLab.create_puzzles_db(os.path.join('data', 'lichess_db_puzzle.csv.zst'))

