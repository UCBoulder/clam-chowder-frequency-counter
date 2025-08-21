import tkinter as tk
from layout import Layout
from counter import Counter
from controller import Controller

def main():
    root = tk.Tk()
    root.title("Claw Chowder Frequency Counter")
    layout = Layout(master=root)
    counter = Counter()
    Controller(layout, counter)
    root.mainloop()

if __name__ == "__main__":
    main()