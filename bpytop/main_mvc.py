import fcntl

import os

from select import select
import sys
import threading
from time import sleep
from typing import Dict, List, Tuple, Union

from bpytop.old_classes import Menu
from bpytop.old_functions import clean_quit
from engine.universe.terminal.base import Terminal
from bpytop2 import errlog

ESCAPE_CODE = "\033"


class MainWidget:
    def __init__(self):
        pass

    def init(self):
        Draw.now(
            self.terminal.alt_screen,  # Switch to alternate screen
            self.terminal.clear,  # clear screen, reset cursor
            self.terminal.hide_cursor,  # hide cursor
            self.terminal.mouse_on,  # enable mouse reporting
            self.terminal.title("BpyTOP"),
        )
        # disable input echo
        self.terminal.echo(False)
        self.terminal.refresh(force=True)


class Controller:
    """Handles the threaded input reader for keypresses and mouse events."""

    def __init__(self):
        self.events_queue: List[str] = []
        self.mouse: Dict[str, List[List[int]]] = {}
        self.mouse_pos: Tuple[int, int] = (0, 0)
        self.escape: Dict[Union[str, Tuple[str, str]], str] = {
            "\n": "enter",
            ("\x7f", "\x08"): "backspace",
            ("[A", "OA"): "up",
            ("[B", "OB"): "down",
            ("[D", "OD"): "left",
            ("[C", "OC"): "right",
            "[2~": "insert",
            "[3~": "delete",
            "[H": "home",
            "[F": "end",
            "[5~": "page_up",
            "[6~": "page_down",
            "\t": "tab",
            "[Z": "shift_tab",
            "OP": "f1",
            "OQ": "f2",
            "OR": "f3",
            "OS": "f4",
            "[15": "f5",
            "[17": "f6",
            "[18": "f7",
            "[19": "f8",
            "[20": "f9",
            "[21": "f10",
            "[23": "f11",
            "[24": "f12",
        }
        self.new_event = threading.Event()
        self.idle_event = threading.Event()
        self.idle_event.set()

        self.mouse_move = threading.Event()
        self.mouse_report: bool = False
        self.stopping: bool = False
        self.started: bool = False
        self.reader: threading.Thread = None

    def start(self):
        self.stopping = False
        self.reader = threading.Thread(target=self._get_key)
        self.reader.start()
        self.started = True

    def stop(self):
        if self.started and self.reader.is_alive():
            self.stopping = True
            try:
                self.reader.join()
            except:
                pass

    def get(self) -> str:
        return self.events_queue.pop(0) if self.events_queue else ""

    def get_mouse(self) -> Tuple[int, int]:
        if self.new_event.is_set():
            self.new_event.clear()
        return self.mouse_pos

    def mouse_moved(self) -> bool:
        if self.mouse_move.is_set():
            self.mouse_move.clear()
            return True
        else:
            return False

    def has_key(self) -> bool:
        return bool(self.events_queue)

    def clear(self):
        self.events_queue = []

    def input_wait(self, timeout: float = 0.0, mouse: bool = False) -> bool:
        """Returns True if key or mouse is detected else waits out timer and returns False.

		:param timeout: When the timeout argument is present and not None,
			it should be a floating point number
			specifying a timeout for the operation in seconds (or fractions thereof).

		"""
        if self.events_queue:
            return True
        if mouse:
            Draw.now(term.mouse_direct_on)

        self.new_event.wait(timeout if timeout > 0 else 0.0)

        if mouse:
            Draw.now(term.mouse_direct_off, term.mouse_on)

        if self.new_event.is_set():
            self.new_event.clear()
            return True
        else:
            return False

    def break_wait(self):
        self.events_queue.append("_null")
        self.new_event.set()
        sleep(0.01)
        self.new_event.clear()

    def _get_key(self):
        """Get a key or escape sequence from stdin, convert to readable format and save to keys
		list. Meant to be run in it's own thread. """
        input_key: str = ""
        try:
            while not self.stopping:
                with Raw(sys.stdin):
                    if not select([sys.stdin], [], [], 0.1)[0]:
                        # * Wait 100ms for input on stdin then restart loop to check for stop flag
                        continue
                    input_key += sys.stdin.read(
                        1
                    )  # * Read 1 key safely with blocking on
                    if (
                        input_key == ESCAPE_CODE
                    ):  # * If first character is a escape sequence keep reading
                        # * Report IO block in progress to prevent Draw functions from getting a IO Block error
                        self.idle_event.clear()
                        # * Wait for Draw function to finish if busy
                        Draw.idle.wait()
                        # * Set non blocking to prevent read stall
                        with Nonblocking(sys.stdin):
                            input_key += sys.stdin.read(20)
                            if input_key.startswith("\033[<"):
                                _ = sys.stdin.read(1000)
                        self.idle_event.set()  # * Report IO blocking done

                    # errlog.debug(f'{repr(input_key)}')

                    clean_key: str = self.parse_input_key(input_key)

                    if clean_key:
                        # * Store up to 10 keys in input queue for later processing
                        self.events_queue.append(clean_key)
                        if len(self.events_queue) > 10:
                            del self.events_queue[0]

                        # * Set threading event to interrupt main thread sleep
                        self.new_event.set()
                    input_key = ""

        except Exception as e:
            errlog.exception(f"Input thread failed with exception: {e}")
            self.idle_event.set()
            self.events_queue.clear()
            clean_quit(1, thread=True)

    def parse_input_key(self, input_key):
        clean_key: str = ""
        if input_key == ESCAPE_CODE:
            # * Key is "escape" key if only containing \033
            clean_key = "escape"
        elif input_key.startswith(("\033[<0;", "\033[<35;", "\033[<64;", "\033[<65;")):
            # * Detected mouse event
            try:
                self.mouse_pos = (
                    int(input_key.split(";")[1]),
                    int(input_key.split(";")[2].rstrip("mM")),
                )
            except:
                pass
            else:
                if input_key.startswith(
                    "\033[<35;"
                ):  # * Detected mouse move in mouse direct mode
                    self.mouse_move.set()
                    self.new_event.set()
                elif input_key.startswith("\033[<64;"):  # * Detected mouse scroll up
                    clean_key = "mouse_scroll_up"
                elif input_key.startswith("\033[<65;"):  # * Detected mouse scroll down
                    clean_key = "mouse_scroll_down"
                elif input_key.startswith("\033[<0;") and input_key.endswith(
                    "m"
                ):  # * Detected mouse click release
                    if Menu.active:
                        clean_key = "mouse_click"
                    else:
                        for (
                            key_name,
                            positions,
                        ) in (
                            self.mouse.items()
                        ):  # * Check if mouse position is clickable
                            if list(self.mouse_pos) in positions:
                                clean_key = key_name
                                break
                        else:
                            clean_key = "mouse_click"
        elif input_key == "\\":
            clean_key = "\\"  # * Clean up "\" to not return escaped
        else:
            for code in self.escape.keys():
                # * Go trough dict of escape codes to get the cleaned key name
                if input_key.lstrip(ESCAPE_CODE).startswith(code):
                    clean_key = self.escape[code]
                    break
            else:  # * If not found in escape dict and length of key is 1, assume regular character
                if len(input_key) == 1:
                    clean_key = input_key
        return clean_key


class Nonblocking(object):
    """Set nonblocking mode for device"""

    def __init__(self, stream):
        self.stream = stream
        self.fd = self.stream.fileno()

    def __enter__(self):
        self.orig_fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl | os.O_NONBLOCK)

    def __exit__(self, *args):
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl)
