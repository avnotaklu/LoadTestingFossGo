from typing import Tuple
import threading
from time import sleep
from pysgf import SGF


class Action:
    def __init__(self, callback, col):
        self.callback = callback
        self.col = col


class Reader:
    def __init__(self):
        self.root = SGF.parse_file("DRKCCHFCDK.sgf")
        self.move_ptr = self.root.children
        self.lock = threading.Lock()
        self.actions = []

    def add_callback(self, action: Action):
        if len(list(filter(lambda x: x.col == action.col, self.actions))) != 0:
            return

        if len(self.actions) < 2:
            print("Added move: ", action.col)
            self.actions.append(action)
        if len(self.actions) == 2:
            self.do_moves()
            self.actions = []

    def do_moves(self):  # -> Tuple[str, str]:

        with self.lock:
            self.actions.sort(key=lambda a: a.col != "B")

            print(list(map(lambda a: a.col, self.actions)))

            for action in self.actions:
                pos = self.__pop()
                a, b = list(pos[0])
                x, y = (ord(a) - ord("a"), ord(b) - ord("a"))

                action.callback(x, y)

    def __pop(self) -> list:
        self.move = self.move_ptr
        self.move_ptr = self.move_ptr[0].children

        _notation: dict = next(map(lambda x: x.sgf_properties(), self.move))
        result = _notation["B"] if _notation.__contains__("B") else _notation["W"]

        return result


r = Reader()


def main():
    r.add_callback(Action(col="B", callback=lambda x: x))
    r.add_callback(Action(col="A", callback=lambda x: x))


if __name__ == "__main__":
    main()
