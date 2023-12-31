import time
import io
import sys
import traceback

import cairosvg
import chess
import chess.svg
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext, font
import subprocess
from multiprocessing import Process, Queue
from queue import Empty
from chesslab.apps import MainApp, Payload
from chesslab.apps.poslab import PosLab


def convert_svg_to_png(svg_string):
    output = io.BytesIO()
    cairosvg.svg2png(bytestring=svg_string, write_to=output)
    return output


apps = {
    'poslab': PosLab
}


def processor(in_queue, out_queue):
    app = PosLab.app()

    out_queue.put(app.start())

    while True:
        command = in_queue.get()
        out_queue.put(Payload(command))
        a = command.split(" ", 1)
        if len(a) == 1:
            cmd, value = a[0], None
        else:
            cmd, value = a

        if cmd == '__exit__':
            print("saving")
            app.save()
            return

        if cmd in apps:
            app = apps[cmd](app)
            out_queue.put(app.start())
            out_queue.put(Payload.terminal())
            continue

        if cmd == 'exit':
            app = app.exit()
            out_queue.put(app.start())
            out_queue.put(Payload.terminal())
            continue

        try:
            for output in app.execute(cmd, value):
                out_queue.put(output)
        except Exception as e:
            if app.debug:
                output = Payload.terminal(text=traceback.format_exc())
            else:
                output = Payload.terminal(text=repr(e))

            out_queue.put(output)


# Create the main window
def main():
    in_queue = Queue()
    out_queue = Queue()
    p = Process(target=processor, args=(in_queue, out_queue))
    p.start()

    # root = tk.Tk()
    # root.title("Custom Terminal")
    #
    # # Create a scrolled text area
    # text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD)
    # text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    #
    # # Create an entry box for typing commands
    # entry = tk.Entry(root)
    # entry.pack(side=tk.BOTTOM, padx=10, pady=10, fill=tk.X)

    root = tk.Tk()
    root.title("Chesslab")
    custom_font = font.Font(family="Courier New", size=10)

    # Create the terminal frame on the left
    terminal_frame = tk.Frame(root)
    terminal_frame.grid(row=0, column=0, sticky="nsew")

    text_area = scrolledtext.ScrolledText(terminal_frame, wrap=tk.WORD, font=custom_font)
    text_area.pack(expand=True, fill=tk.BOTH)

    entry = tk.Entry(terminal_frame, font=custom_font)
    entry.pack(fill=tk.X)
    entry.bind("<Return>", lambda event: execute_command())

    # Create the image label on the right
    image_label = tk.Label(root)
    image_label.grid(row=0, column=1, sticky="nsew")

    # Configure grid weights so that resizing works properly
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)

    payload = out_queue.get()

    image = tk.PhotoImage(data=payload.img_data)
    image_label.config(image=image)

    text_area.insert(tk.INSERT, f"{payload.text}\n")

    def execute_command():
        command = entry.get()
        in_queue.put(command)
        entry.config(state=tk.DISABLED)

    time_step = 50

    def receiver():
        try:
            payload = out_queue.get(block=False)
        except Empty as e:
            payload = None

        if payload is not None:
            if payload.text is not None:
                text_area.insert(tk.INSERT, f"{payload.text}\n")
                text_area.see(tk.END)
            if payload.img_data is not None:
                image = tk.PhotoImage(data=payload.img_data)
                image_label.config(image=image)
                image_label.image = image

            if payload.last:
                entry.config(state=tk.NORMAL)
                entry.delete(0, tk.END)

        root.after(time_step, receiver)

    entry.bind("<Return>", lambda event: execute_command())

    root.after(0, receiver)

    # Run the application
    root.mainloop()
    in_queue.put('__exit__')
    # p.terminate()
    p.join()


if __name__ == "__main__":
    main()
