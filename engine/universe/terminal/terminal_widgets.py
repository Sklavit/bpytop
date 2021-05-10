import pwd
from time import strftime

import os
import psutil
import re

from typing import Any, Dict, List, Union

from bpytop.bpytop_widgets import CpuBox
from bpytop.config import CONFIG
from bpytop.old_classes import Menu

from bpytop.terminal_engine import Color, Cursor, Draw
from bpytop2 import THEME


class Meter:
	"""
	Creates a percentage meter
	__init__(value, width, theme, gradient_name) to create new meter
	__call__(value) to set value and return meter as a string
	__str__ returns last set meter as a string
	"""
	out: str
	color_gradient: List[str]
	color_inactive: Color
	gradient_name: str
	width: int
	invert: bool
	saved: Dict[int, str]

	def __init__(self, value: int, width: int, gradient_name: str, invert: bool = False):
		self.gradient_name = gradient_name
		self.color_gradient = THEME.gradient[gradient_name]
		self.color_inactive = THEME.meter_bg
		self.width = width
		self.saved = {}
		self.invert = invert
		self.out = self._create(value)

	def __call__(self, value: Union[int, None]) -> str:
		if not isinstance(value, int):
			return self.out
		if value > 100:
			value = 100
		elif value < 0:
			value = 100
		if value in self.saved:
			self.out = self.saved[value]
		else:
			self.out = self._create(value)
		return self.out

	def __str__(self) -> str:
		return self.out

	def __repr__(self):
		return repr(self.out)

	def _create(self, value: int) -> str:
		if value > 100:
			value = 100
		elif value < 0:
			value = 100
		out: str = ""
		for i in range(1, self.width + 1):
			if value >= round(i * 100 / self.width):
				out += f'{self.color_gradient[round(i * 100 / self.width) if not self.invert else round(100 - (i * 100 / self.width))]}{Symbol.meter}'
			else:
				out += self.color_inactive(Symbol.meter * (self.width + 1 - i))
				break
		else:
			out += f'{term.fg}'
		if not value in self.saved:
			self.saved[value] = out
		return out


class Fx:
	"""Text effects
	* trans(string: str): Replace whitespace with escape move right to not overwrite background behind whitespace.
	* uncolor(string: str) : Removes all 24-bit color and returns string ."""
	start					= "\033["			#* Escape sequence start
	sep						= ";"				#* Escape sequence separator
	end						= "m"				#* Escape sequence end
	reset = rs				= "\033[0m"			#* Reset foreground/background color and text effects
	bold = b				= "\033[1m"			#* Bold on
	unbold = ub				= "\033[22m"		#* Bold off
	dark = d				= "\033[2m"			#* Dark on
	undark = ud				= "\033[22m"		#* Dark off
	italic = i				= "\033[3m"			#* Italic on
	unitalic = ui			= "\033[23m"		#* Italic off
	underline = u			= "\033[4m"			#* Underline on
	ununderline = uu		= "\033[24m"		#* Underline off
	blink = bl 				= "\033[5m"			#* Blink on
	unblink = ubl			= "\033[25m"		#* Blink off
	strike = s 				= "\033[9m"			#* Strike / crossed-out on
	unstrike = us			= "\033[29m"		#* Strike / crossed-out off

	#* Precompiled regex for finding a 24-bit color escape sequence in a string
	color_re = re.compile(r"\033\[\d+;\d?;?\d*;?\d*;?\d*m")

	@staticmethod
	def trans(string: str):
		return string.replace(" ", "\033[1C")

	@classmethod
	def uncolor(cls, string: str) -> str:
		return f'{cls.color_re.sub("", string)}'


class Symbol:
	h_line: str			= "─"
	v_line: str			= "│"
	left_up: str		= "┌"
	right_up: str		= "┐"
	left_down: str		= "└"
	right_down: str		= "┘"
	title_left: str		= "┤"
	title_right: str	= "├"
	div_up: str			= "┬"
	div_down: str		= "┴"
	graph_up: Dict[float, str] = {
	0.0 : " ", 0.1 : "⢀", 0.2 : "⢠", 0.3 : "⢰", 0.4 : "⢸",
	1.0 : "⡀", 1.1 : "⣀", 1.2 : "⣠", 1.3 : "⣰", 1.4 : "⣸",
	2.0 : "⡄", 2.1 : "⣄", 2.2 : "⣤", 2.3 : "⣴", 2.4 : "⣼",
	3.0 : "⡆", 3.1 : "⣆", 3.2 : "⣦", 3.3 : "⣶", 3.4 : "⣾",
	4.0 : "⡇", 4.1 : "⣇", 4.2 : "⣧", 4.3 : "⣷", 4.4 : "⣿"
	}
	graph_up_small = graph_up.copy()
	graph_up_small[0.0] = "\033[1C"

	graph_down: Dict[float, str] = {
	0.0 : " ", 0.1 : "⠈", 0.2 : "⠘", 0.3 : "⠸", 0.4 : "⢸",
	1.0 : "⠁", 1.1 : "⠉", 1.2 : "⠙", 1.3 : "⠹", 1.4 : "⢹",
	2.0 : "⠃", 2.1 : "⠋", 2.2 : "⠛", 2.3 : "⠻", 2.4 : "⢻",
	3.0 : "⠇", 3.1 : "⠏", 3.2 : "⠟", 3.3 : "⠿", 3.4 : "⢿",
	4.0 : "⡇", 4.1 : "⡏", 4.2 : "⡟", 4.3 : "⡿", 4.4 : "⣿"
	}
	graph_down_small = graph_down.copy()
	graph_down_small[0.0] = "\033[1C"
	meter: str = "■"
	up: str = "↑"
	down: str = "↓"
	left: str = "←"
	right: str = "→"
	enter: str = "↲"
	ok: str = f'{Color.fg("#30ff50")}√{Color.fg("#cc")}'
	fail: str = f'{Color.fg("#ff3050")}!{Color.fg("#cc")}'


class Box:
	"""Box class with all needed attributes for create_box() function"""
	name: str
	height_p: int
	width_p: int
	x: int
	y: int
	width: int
	height: int
	proc_mode: bool = True if (CONFIG.view_mode == "proc" and not ARG_MODE) or ARG_MODE == "proc" else False
	stat_mode: bool = True if (CONFIG.view_mode == "stat" and not ARG_MODE) or ARG_MODE == "stat" else False
	out: str
	bg: str
	_b_cpu_h: int
	_b_mem_h: int
	redraw_all: bool
	buffers: List[str] = []
	clock_on: bool = False
	clock: str = ""
	clock_len: int = 0
	resized: bool = False
	clock_custom_format: Dict[str, Any] = {
		"/host" : os.uname()[1],
		"/user" : os.environ.get("USER") or pwd.getpwuid(os.getuid())[0],
		}
	if clock_custom_format["/host"].endswith(".local"):
		clock_custom_format["/host"] = clock_custom_format["/host"].replace(".local", "")

	@classmethod
	def calc_sizes(cls):
		'''Calculate sizes of boxes'''
		for sub in cls.__subclasses__():
			sub._calc_size() # type: ignore
			sub.resized = True # type: ignore

	@classmethod
	def draw_update_ms(cls, now: bool = True):
		update_string: str = f'{CONFIG.update_ms}ms'
		xpos: int = CpuBox.x + CpuBox.width - len(update_string) - 15
		if not "+" in controller.mouse:
			controller.mouse["+"] = [[xpos + 7 + i, CpuBox.y] for i in range(3)]
			controller.mouse["-"] = [[CpuBox.x + CpuBox.width - 4 + i, CpuBox.y] for i in range(3)]
		Draw.buffer("update_ms!" if now and not Menu.active else "update_ms",
			f'{Cursor.to(CpuBox.y, xpos)}{THEME.cpu_box(Symbol.h_line * 7, Symbol.title_left)}{Fx.b}{THEME.hi_fg("+")} ',
			f'{THEME.title(update_string)} {THEME.hi_fg("-")}{Fx.ub}{THEME.cpu_box(Symbol.title_right)}', only_save=Menu.active, once=True)
		if now and not Menu.active:
			Draw.clear("update_ms")
			if CONFIG.show_battery and hasattr(psutil, "sensors_battery") and psutil.sensors_battery():
				Draw.out("battery")

	@classmethod
	def draw_clock(cls, force: bool = False):
		out: str = ""
		if force: pass
		elif not cls.clock_on or terminal.resized or strftime(CONFIG.draw_clock) == cls.clock: return
		clock_string = cls.clock = strftime(CONFIG.draw_clock)
		for custom in cls.clock_custom_format:
			if custom in clock_string:
				clock_string = clock_string.replace(custom, cls.clock_custom_format[custom])
		clock_len = len(clock_string[:(CpuBox.width - 56)])
		if cls.clock_len != clock_len and not CpuBox.resized:
			out = f'{Cursor.to(CpuBox.y, ((CpuBox.width) // 2) - (cls.clock_len // 2))}{Fx.ub}{THEME.cpu_box}{Symbol.h_line * cls.clock_len}'
		cls.clock_len = clock_len
		now: bool = False if Menu.active else not force
		out += (f'{Cursor.to(CpuBox.y, ((CpuBox.width) // 2) - (clock_len // 2))}{Fx.ub}{THEME.cpu_box}'
			f'{Symbol.title_left}{Fx.b}{THEME.title(clock_string[:clock_len])}{Fx.ub}{THEME.cpu_box}{Symbol.title_right}{term.fg}')
		Draw.buffer("clock", out, z=1, now=now, once=not force, only_save=Menu.active)
		if now and not Menu.active:
			if CONFIG.show_battery and hasattr(psutil, "sensors_battery") and psutil.sensors_battery():
				Draw.out("battery")

	@classmethod
	def draw_bg(cls, now: bool = True):
		'''Draw all boxes outlines and titles'''
		Draw.buffer("bg", "".join(sub._draw_bg() for sub in cls.__subclasses__()), now=now, z=1000, only_save=Menu.active, once=True) # type: ignore
		cls.draw_update_ms(now=now)
		if CONFIG.draw_clock: cls.draw_clock(force=True)


class SubBox:
	box_x: int = 0
	box_y: int = 0
	box_width: int = 0
	box_height: int = 0
	box_columns: int = 0
	column_size: int = 0