from random import randint

import urllib.request

import logging

import subprocess

from shutil import which

from math import ceil, floor

import tty

import termios


from time import sleep

from typing import Dict, List, Union

from bpytop.bpytop_widgets import NetBox
from bpytop.collectors import NetCollector, ProcCollector
from bpytop.old import BANNER_SRC
from bpytop.theme import MENUS, MENU_COLORS, Theme
from bpytop2 import (
	THEME,
	VERSION, errlog,
)
from bpytop.old_functions import (
	clean_quit,
)
from engine.universe.terminal.colors import Color
from engine.universe.terminal.terminal_engine import create_box
from engine.universe.terminal.constants import CursorChar
from engine.universe.terminal.terminal_widgets import Fx, Symbol


class Raw(object):
	"""Set raw input mode for device"""
	def __init__(self, stream):
		self.stream = stream
		self.fd = self.stream.fileno()
	def __enter__(self):
		self.original_stty = termios.tcgetattr(self.stream)
		tty.setcbreak(self.stream)
	def __exit__(self, type, value, traceback):
		termios.tcsetattr(self.stream, termios.TCSANOW, self.original_stty)


class Banner:
	'''Holds the bpytop banner, .draw(line, [col=0], [center=False], [now=False])'''
	out: List[str] = []
	c_color: str = ""
	length: int = 0
	if not out:
		for num, (color, color2, line) in enumerate(BANNER_SRC):
			if len(line) > length: length = len(line)
			out_var = ""
			line_color = Color.fg(color)
			line_color2 = Color.fg(color2)
			line_dark = Color.fg(f'#{80 - num * 6}')
			for n, letter in enumerate(line):
				if letter == "█" and c_color != line_color:
					if n > 5 and n < 25: c_color = line_color2
					else: c_color = line_color
					out_var += c_color
				elif letter == " ":
					letter = f'{CursorChar.r(1)}'
					c_color = ""
				elif letter != "█" and c_color != line_dark:
					c_color = line_dark
					out_var += line_dark
				out_var += letter
			out.append(out_var)

	@classmethod
	def draw(cls, line: int, col: int = 0, center: bool = False, now: bool = False):
		out: str = ""
		if center: col = term.width // 2 - cls.length // 2
		for n, o in enumerate(cls.out):
			out += f'{CursorChar.to(line + n, col)}{o}'
		out += f'{term.fg}'
		if now:
			Draw.out(out)
		else:
			return out


class Graph:
	"""
	Class for creating and adding to graphs
	* __str__ : returns graph as a string
	* add(value: int) : adds a value to graph and returns it as a string
	* __call__ : same as add
	"""
	out: str
	width: int
	height: int
	graphs: Dict[bool, List[str]]
	colors: List[str]
	invert: bool
	max_value: int
	color_max_value: int
	offset: int
	current: bool
	last: int
	symbol: Dict[float, str]

	def __init__(self, width: int, height: int, color: Union[List[str], Color, None], data: List[int], invert: bool = False, max_value: int = 0, offset: int = 0, color_max_value: Union[int, None] = None):
		self.graphs: Dict[bool, List[str]] = {False : [], True : []}
		self.current: bool = True
		self.width = width
		self.height = height
		self.invert = invert
		self.offset = offset
		if not data: data = [0]
		if max_value:
			self.max_value = max_value
			data = [ min(100, (v + offset) * 100 // (max_value + offset)) for v in data ] #* Convert values to percentage values of max_value with max_value as ceiling
		else:
			self.max_value = 0
		if color_max_value:
			self.color_max_value = color_max_value
		else:
			self.color_max_value = self.max_value
		if self.color_max_value and self.max_value:
			color_scale = int(100.0 * self.max_value / self.color_max_value)
		else:
			color_scale = 100
		self.colors: List[str] = []
		if isinstance(color, list) and height > 1:
			for i in range(1, height + 1):
				#* Calculate colors of graph
				self.colors.insert(0, color[min(100, i * color_scale // height)])
			if invert:
				self.colors.reverse()
		elif isinstance(color, Color) and height > 1:
			self.colors = [ f'{color}' for _ in range(height) ]
		else:
			if isinstance(color, list):
				self.colors = color
			elif isinstance(color, Color):
				self.colors = [f'{color}' for _ in range(101)]
		if self.height == 1:
			self.symbol = Symbol.graph_down_small if invert else Symbol.graph_up_small
		else:
			self.symbol = Symbol.graph_down if invert else Symbol.graph_up
		value_width: int = ceil(len(data) / 2)
		filler: str = ""

		if value_width > width:
			# * If the size of given data set is bigger then width of graph, shrink data set
			data = data[-(width*2):]
			value_width = ceil(len(data) / 2)
		elif value_width < width:
			# * If the size of given data set is smaller then width of graph, fill graph with whitespace
			filler = self.symbol[0.0] * (width - value_width)
		if len(data) % 2: data.insert(0, 0)
		for _ in range(height):
			for b in [True, False]:
				self.graphs[b].append(filler)
		self._create(data, new=True)

	def _create(self, data: List[int], new: bool = False):
		h_high: int
		h_low: int
		value: Dict[str, int] = { "left" : 0, "right" : 0 }
		val: int
		side: str

		#* Create the graph
		for h in range(self.height):
			h_high = round(100 * (self.height - h) / self.height) if self.height > 1 else 100
			h_low = round(100 * (self.height - (h + 1)) / self.height) if self.height > 1 else 0
			for v in range(len(data)):
				if new:
					# * Switch between True and False graphs
					self.current = bool(v % 2)
				if new and v == 0:
					self.last = 0
				for val, side in [self.last, "left"], [data[v], "right"]:
					# type: ignore
					if val >= h_high:
						value[side] = 4
					elif val <= h_low:
						value[side] = 0
					else:
						if self.height == 1: value[side] = round(val * 4 / 100 + 0.5)
						else: value[side] = round((val - h_low) * 4 / (h_high - h_low) + 0.1)
				if new:
					self.last = data[v]
				self.graphs[self.current][h] += self.symbol[float(value["left"] + value["right"] / 10)]
		if data:
			self.last = data[-1]
		self.out = ""

		if self.height == 1:
			self.out += f'{"" if not self.colors else self.colors[self.last]}{self.graphs[self.current][0]}'
		elif self.height > 1:
			for h in range(self.height):
				if h > 0: self.out += f'{CursorChar.d(1)}{CursorChar.l(self.width)}'
				self.out += f'{"" if not self.colors else self.colors[h]}{self.graphs[self.current][h if not self.invert else (self.height - 1) - h]}'
		if self.colors:
			self.out += f'{term.fg}'

	def __call__(self, value: Union[int, None] = None) -> str:
		if not isinstance(value, int):
			return self.out
		self.current = not self.current
		if self.height == 1:
			if self.graphs[self.current][0].startswith(self.symbol[0.0]):
				self.graphs[self.current][0] = self.graphs[self.current][0].replace(self.symbol[0.0], "", 1)
			else:
				self.graphs[self.current][0] = self.graphs[self.current][0][1:]
		else:
			for n in range(self.height):
				self.graphs[self.current][n] = self.graphs[self.current][n][1:]
		if self.max_value: value = (value + self.offset) * 100 // (self.max_value + self.offset) if value < self.max_value else 100
		self._create([value])
		return self.out

	def add(self, value: Union[int, None] = None) -> str:
		return self.__call__(value)

	def __str__(self):
		return self.out

	def __repr__(self):
		return repr(self.out)


class Graphs:
	"""Holds all graphs and lists of graphs for dynamically created graphs"""
	cpu: Dict[str, Graph] = {}
	cores: List[Graph] = [NotImplemented] * THREADS
	temps: List[Graph] = [NotImplemented] * (THREADS + 1)
	net: Dict[str, Graph] = {}
	detailed_cpu: Graph = NotImplemented
	detailed_mem: Graph = NotImplemented
	pid_cpu: Dict[int, Graph] = {}


class Meters:
	cpu: Meter
	battery: Meter
	mem: Dict[str, Union[Meter, Graph]] = {}
	swap: Dict[str, Union[Meter, Graph]] = {}
	disks_used: Dict[str, Meter] = {}
	disks_free: Dict[str, Meter] = {}







def checker_for_latest_version():
	version = None
	try:
		with urllib.request.urlopen("https://github.com/aristocratos/bpytop/raw/master/bpytop.py", timeout=5) as source: # type: ignore
			for line in source:
				line = line.decode("utf-8")
				if line.startswith("VERSION: str ="):
					version = line[(line.index("=")+1):].strip('" \n')
					break
	except Exception as e:
		errlog.exception(f'{e}')
	else:
		if version != VERSION and which("notify-send"):
			try:
				subprocess.run(["notify-send", "-u", "normal", "BpyTop Update!",
					f'New version of BpyTop available!\nCurrent version: {VERSION}\nNew version: {version}\nDownload at github.com/aristocratos/bpytop',
					"-i", "update-notifier", "-t", "10000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
			except Exception as e:
				errlog.exception(f'{e}')
	return version


class FullScreenWidget:
	pass


class Init(FullScreenWidget):
	def __init__(self, window):
		self.window = window

		self.running: bool = True
		self.initbg_colors: List[str] = []
		self.initbg_data: List[int]
		self.initbg_up: Graph
		self.initbg_down: Graph
		self.resized = False
		self.is_showing = False

		self.window.view.buffer("init", z=1)
		self.window.view.buffer("initbg", z=10)
		for i in range(51):
			for _ in range(2): self.initbg_colors.append(Color.fg(i, i, i))
		self.window.view.buffer("banner", (
			f'{Banner.draw(term.height // 2 - 10, center=True)}{CursorChar.d(1)}{CursorChar.l(11)}{Colors.black_bg}{Colors.default}'
			f'{Fx.b}{Fx.i}Version: {VERSION}{Fx.ui}{Fx.ub}{term.bg}{term.fg}{Color.fg("#50")}'
		), z=2)
		for _i in range(7):
			perc = f'{str(round((_i + 1) * 14 + 2)) + "%":>5}'
			self.window.view.buffer("+banner", f'{CursorChar.to(term.height // 2 - 2 + _i, term.width // 2 - 28)}{Fx.trans(perc)}{Symbol.v_line}')

		self.window.view.buffer("+init!", f'{Color.fg("#cc")}{Fx.b}{CursorChar.to(term.height // 2 - 2, term.width // 2 - 21)}{CursorChar.save}')

		self.initbg_data = [randint(0, 100) for _ in range(term.width * 2)]
		self.initbg_up = Graph(term.width, term.height // 2, self.initbg_colors, self.initbg_data, invert=True)
		self.initbg_down = Graph(term.width, term.height // 2, self.initbg_colors, self.initbg_data, invert=False)

	def show(self):
		self.is_showing = True
		if not self.resized:
			# prevent showing during resizing
			Draw.out("banner")

	def draw_bg(self, times: int = 5):
		for _ in range(times):
			sleep(0.05)
			x = randint(0, 100)
			self.window.view.buffer(
				"initbg",
				f'{Fx.ub}{CursorChar.to(0, 0)}{self.initbg_up(x)}{CursorChar.to(term.height // 2, 0)}{self.initbg_down(x)}'
			)
			if self.is_showing and not self.resized:
				Draw.out("initbg", "banner", "init")

	def done(self):
		self.running = False
		if not self.is_showing:
			return

		if self.resized:
			self.window.view.draw_soon(terminal.clear)
		else:
			self.draw_bg(10)
		Draw.clear("initbg", "banner", "init", saved=True)
		if self.resized:
			return

		# memory cleanup TODO what for?
		del self.initbg_up
		del self.initbg_down
		del self.initbg_data
		del self.initbg_colors

	def add_line(self, line_text: str):
		"""
		Adds text label and shows it.

		:param str line_text: text to show in label.
		"""
		self.window.view.buffer(
			"+init",
			f'{CursorChar.restore}{Fx.trans(line_text)}{CursorChar.save}',
		)
		if self.is_showing and not self.resized:
			# prevent showing during resizing
			Draw.out("init")

