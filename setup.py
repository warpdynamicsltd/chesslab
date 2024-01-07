from setuptools import setup, find_packages

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
