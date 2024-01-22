# Chesslab

Chesslab is an advanced analytical chess program with simple but powerful command line user interface.


### Instalation

1. You should have <i>Python</i> with <i>tkinter</i> module. 
There is a big chance you already have it. If not you need to usually install
this package. E.g. in Ubuntu you can run `sudo apt-get install python3-tk`   
2. Clone this repository by

    ```git clone https://github.com/warpdynamicsltd/chesslab.git```
3. Some functionality requires large data files. To pull them to the repo, 
you need the following steps:  

   1. You need to have installed LFS extension for git
   (you will find information here: https://git-lfs.com/)
   2. Once LFT extension in installed, in `chesslab` root folder execute:
   
      ```git lfs install```

      This will enable extension to use in this local repository
   3. Next `git pull` should download large files.
   
4. Go into `chesslab` directory (e.g. `cd chesslab`)
5. Install required dependencies by

    ```pip -r requrements.txt```
    If you only want to run `chesslab` ui script, minimal requirements are:

    ```pip install chess cairosvg```
6. Install `chesslab` by e.g.:

    ```pip install .```

    If you want to install it for development, use:

    ```pip install -e .```
7. Now, just type `chesslab` in your terminal and gui should start. You should see something like this:

   ![Alt Chesslab Screen](img/chesslab.png)
8. Type `help` in console to read documentation