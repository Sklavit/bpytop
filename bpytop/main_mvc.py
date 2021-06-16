import fcntl

import termios

import os

from select import select
import sys
import threading
from time import sleep
from typing import Dict, List, Tuple, Union

from bpytop.event_loop import Timer
from bpytop.old_classes import Init, Menu
from bpytop.bpytop_widgets import CpuBox
from bpytop.old_functions import clean_quit
from engine.universe.terminal.terminal_engine import create_box
from bpytop2 import errlog

ESCAPE_CODE = "\033"


class MainWidget:
    def __init__(self):
        self.terminal = Terminal(
            width=os.get_terminal_size().columns, height=os.get_terminal_size().lines,
        )

    def init(self):
        # ? Switch to alternate screen, clear screen, hide cursor, enable mouse reporting and disable input echo
        Draw.now(
            self.terminal.alt_screen,
            self.terminal.clear,
            self.terminal.hide_cursor,
            self.terminal.mouse_on,
            self.terminal.title("BpyTOP"),
        )
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


class Terminal:
    """Terminal info and commands"""

    def __init__(self, width, height):
        self.width: int = width
        self.height: int = height
        self.resized: bool = False
        self._w: int = 0
        self._h: int = 0
        self.fg: str = ""  # * Default foreground color
        self.bg: str = ""  # * Default background color
        self.hide_cursor = "\033[?25l"  # * Hide terminal cursor
        self.show_cursor = "\033[?25h"  # * Show terminal cursor
        self.alt_screen = "\033[?1049h"  # * Switch to alternate screen
        self.normal_screen = "\033[?1049l"  # * Switch to normal screen
        self.clear = "\033[2J\033[0;0f"  # * Clear screen and set cursor to position 0,0
        self.mouse_on = "\033[?1002h\033[?1015h\033[?1006h"  # * Enable reporting of mouse position on click and release
        self.mouse_off = "\033[?1002l"  # * Disable mouse reporting
        self.mouse_direct_on = (
            "\033[?1003h"  # * Enable reporting of mouse position at any movement
        )
        self.mouse_direct_off = "\033[?1003l"  # * Disable direct mouse reporting
        self.winch = threading.Event()

    def refresh(self, *args, force: bool = False):
        """Update width, height and set resized flag if terminal has been resized"""
        if self.resized:
            self.winch.set()
            return

        self._w, self._h = os.get_terminal_size()
        if (self._w, self._h) == (self.width, self.height) and not force:
            return

        if force:
            collector.collect_interrupt = True
        while (self._w, self._h) != (self.width, self.height) or (
            self._w < 80 or self._h < 24
        ):
            if Init.running:
                Init.resized = True
            CpuBox.clock_block = True
            self.resized = True
            collector.collect_interrupt = True
            self.width, self.height = self._w, self._h
            Draw.now(terminal.clear)
            Draw.now(
                f'{create_box(self._w // 2 - 25, self._h // 2 - 2, 50, 3, "resizing", line_color=Colors.green, title_color=Colors.white)}',
                f"{Cursor.r(12)}{Colors.default}{Colors.black_bg}{Fx.b}Width : {self._w}   Height: {self._h}{Fx.ub}{term.bg}{term.fg}",
            )
            if self._w < 80 or self._h < 24:
                while self._w < 80 or self._h < 24:
                    Draw.now(terminal.clear)
                    Draw.now(
                        f'{create_box(self._w // 2 - 25, self._h // 2 - 2, 50, 4, "warning", line_color=Colors.red, title_color=Colors.white)}',
                        f"{Cursor.r(12)}{Colors.default}{Colors.black_bg}{Fx.b}Width: {Colors.red if self._w < 80 else Colors.green}{self._w}   ",
                        f"{Colors.default}Height: {Colors.red if self._h < 24 else Colors.green}{self._h}{term.bg}{term.fg}",
                        f"{Cursor.to(self._h // 2, self._w // 2 - 23)}{Colors.default}{Colors.black_bg}Width and Height needs to be at least 80 x 24 !{Fx.ub}{term.bg}{term.fg}",
                    )
                    self.winch.wait(0.3)
                    self.winch.clear()
                    self._w, self._h = os.get_terminal_size()
            else:
                self.winch.wait(0.3)
                self.winch.clear()
            self._w, self._h = os.get_terminal_size()

        controller.mouse = {}
        Box.calc_sizes()
        if Init.running:
            self.resized = False
            return

        if Menu.active:
            Menu.resized = True

        Box.draw_bg(now=False)
        self.resized = False
        Timer.finish()
        self.controller.break_wait()

    @staticmethod
    def echo(on: bool):
        """Toggle input echo"""
        (iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = termios.tcgetattr(
            sys.stdin.fileno()
        )
        if on:
            lflag |= termios.ECHO  # type: ignore
        else:
            lflag &= ~termios.ECHO  # type: ignore
        new_attr = [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, new_attr)

    @staticmethod
    def title(text: str = "") -> str:
        out: str = f'{os.environ.get("TERMINAL_TITLE", "")}'
        if out and text:
            out += " "
        if text:
            out += f"{text}"
        return f"\033]0;{out}\a"


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
