import sys

import termios

import os

import threading

from bpytop.bpytop_widgets import CpuBox
from bpytop.event_loop import Timer
from bpytop.old_classes import Init, Menu
from engine.universe.terminal.terminal_engine import create_box


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