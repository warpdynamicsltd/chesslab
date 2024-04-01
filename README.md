# Chesslab

Chesslab is an advanced analytical chess program with simple but powerful command line user interface.


### Installation

1. You should have <i>Python</i> with <i>tkinter</i> module. 
There is a big chance you already have it. If not you need to usually install
this package. E.g. in Ubuntu you can run `sudo apt-get install python3-tk`   
2. Clone this repository by running the following in your terminal 

    ```git clone https://github.com/warpdynamicsltd/chesslab.git```
3. Some functionality requires large data files. To pull them to the repo, 
you need the following steps:  

   1. You need to have installed LFS extension for git
   (you will find information here: https://git-lfs.com/)
   2. Once LFT extension in installed, in `chesslab` root folder execute:
   
      ```git lfs install```

      This will enable extension to use in this local repository
   3. Next `git pull` should download large files.
   
4. Go into the root directory of this repository, i.e. `chesslab` directory (e.g. `cd chesslab`)
5. Install required dependencies by

    ```pip -r requrements.txt```
    If you only want to run `chesslab` ui script, minimal requirements are:

    ```pip install chess cairosvg zstandard pandas```
6. Install `chesslab` by e.g.:

    ```pip install .```

    If you want to install it for development, use:

    ```pip install -e .```

   Installation can take up to a few minutes because puzzles database is being created during installation. 
   
7. Now, run Chesslab by executing `chesslab` in your terminal. 
   You should see something like this:

      ![Alt Chesslab Screen](img/chesslab.png)
8. You need to set chess engine path by executing
   ```chess_engine <absolute path to chess engine binary>```
   in Chesslab text console.
9. You can use `help` command in console and then to read documentation.
10. Applications available by commands:
    1. chesslab
    2. poslab
    3. tactics
    4. chessworld