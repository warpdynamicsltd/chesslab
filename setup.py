import os
import shutil
from setuptools import setup, find_packages

chesslab_home = os.path.join(os.path.expanduser('~'), '.chesslab')

if not os.path.isdir(chesslab_home):
    os.mkdir(chesslab_home)

shutil.copy(os.path.join('data', 'lichess_db_puzzle.csv.zst'), os.path.join(chesslab_home, 'lichess_db_puzzle.csv.zst'))

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
