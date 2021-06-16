from random import randint

import urllib.request

import logging

import subprocess

from shutil import which

from math import ceil, floor

import tty

import termios

import threading

from time import sleep

from typing import Dict, List, Union

from bpytop.bpytop_widgets import NetBox
from bpytop.collectors import Cpucollector, NetCollector, ProcCollector
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
from engine.universe.terminal.terminal_engine import Draw, create_box
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


class Menu:
	'''Holds all menus'''
	active: bool = False
	close: bool = False
	resized: bool = True
	menus: Dict[str, Dict[str, str]] = {}
	menu_length: Dict[str, int] = {}
	background: str = ""
	for name, menu in MENUS.items():
		menu_length[name] = len(menu["normal"][0])
		menus[name] = {}
		for sel in ["normal", "selected"]:
			menus[name][sel] = ""
			for i in range(len(menu[sel])):
				menus[name][sel] += Fx.trans(f'{Color.fg(MENU_COLORS[sel][i])}{menu[sel][i]}')
				if i < len(menu[sel]) - 1: menus[name][sel] += f'{CursorChar.d(1)}{CursorChar.l(len(menu[sel][i]))}'

	@classmethod
	def main(cls):
		out: str = ""
		banner: str = ""
		redraw: bool = True
		key: str = ""
		mx: int = 0
		my: int = 0
		skip: bool = False
		mouse_over: bool = False
		mouse_items: Dict[str, Dict[str, int]] = {}
		cls.active = True
		cls.resized = True
		menu_names: List[str] = list(cls.menus.keys())
		menu_index: int = 0
		menu_current: str = menu_names[0]
		cls.background = f'{THEME.inactive_fg}' + Fx.uncolor(f'{Draw.saved_buffer()}') + f'{term.fg}'

		while not cls.close:
			key = ""
			if cls.resized:
				banner = (f'{Banner.draw(term.height // 2 - 10, center=True)}{CursorChar.d(1)}{CursorChar.l(46)}{Colors.black_bg}{Colors.default}{Fx.b}← esc'
					f'{CursorChar.r(30)}{Fx.i}Version: {VERSION}{Fx.ui}{Fx.ub}{term.bg}{term.fg}')
				if UpdateChecker.version != VERSION:
					banner += f'{CursorChar.to(term.height, 1)}{Fx.b}{THEME.title}New release {UpdateChecker.version} available at https://github.com/aristocratos/bpytop{Fx.ub}{term.fg}'
				cy = 0
				for name, menu in cls.menus.items():
					ypos = term.height // 2 - 2 + cy
					xpos = term.width // 2 - (cls.menu_length[name] // 2)
					mouse_items[name] = { "x1" : xpos, "x2" : xpos + cls.menu_length[name] - 1, "y1" : ypos, "y2" : ypos + 2 }
					cy += 3
				redraw = True
				cls.resized = False

			if redraw:
				out = ""
				for name, menu in cls.menus.items():
					out += f'{CursorChar.to(mouse_items[name]["y1"], mouse_items[name]["x1"])}{menu["selected" if name == menu_current else "normal"]}'

			if skip and redraw:
				Draw.now(out)
			elif not skip:
				Draw.now(f'{cls.background}{banner}{out}')
			skip = redraw = False

			if controller.input_wait(timer.left(), mouse=True):
				if controller.mouse_moved():
					mx, my = controller.get_mouse()
					for name, pos in mouse_items.items():
						if mx >= pos["x1"] and mx <= pos["x2"] and my >= pos["y1"] and my <= pos["y2"]:
							mouse_over = True
							if name != menu_current:
								menu_current = name
								menu_index = menu_names.index(name)
								redraw = True
							break
					else:
						mouse_over = False
				else:
					key = controller.get()

				if key == "mouse_click" and not mouse_over:
					key = "M"

				if key == "q":
					clean_quit()
				elif key in ["escape", "M"]:
					cls.close = True
					break
				elif key in ["up", "mouse_scroll_up", "shift_tab"]:
					menu_index -= 1
					if menu_index < 0: menu_index = len(menu_names) - 1
					menu_current = menu_names[menu_index]
					redraw = True
				elif key in ["down", "mouse_scroll_down", "tab"]:
					menu_index += 1
					if menu_index > len(menu_names) - 1: menu_index = 0
					menu_current = menu_names[menu_index]
					redraw = True
				elif key == "enter" or (key == "mouse_click" and mouse_over):
					if menu_current == "quit":
						clean_quit()
					elif menu_current == "options":
						cls.options()
						cls.resized = True
					elif menu_current == "help":
						cls.help()
						cls.resized = True

			if timer.not_zero() and not cls.resized:
				skip = True
			else:
				collector.collect()
				collector.collect_done.wait(2)
				if CONFIG.background_update: cls.background = f'{THEME.inactive_fg}' + Fx.uncolor(f'{Draw.saved_buffer()}') + f'{term.fg}'
				timer.stamp()


		Draw.now(f'{Draw.saved_buffer()}')
		cls.background = ""
		cls.active = False
		cls.close = False

	@classmethod
	def help(cls):
		out: str = ""
		out_misc : str = ""
		redraw: bool = True
		key: str = ""
		skip: bool = False
		main_active: bool = True if cls.active else False
		cls.active = True
		cls.resized = True
		if not cls.background:
			cls.background = f'{THEME.inactive_fg}' + Fx.uncolor(f'{Draw.saved_buffer()}') + f'{term.fg}'
		help_items: Dict[str, str] = {
			"(Mouse 1)" : "Clicks buttons and selects in process list.",
			"Selected (Mouse 1)" : "Show detailed information for selected process.",
			"(Mouse scroll)" : "Scrolls any scrollable list/text under cursor.",
			"(Esc, shift+m)" : "Toggles main menu.",
			"(m)" : "Change current view mode, order full->proc->stat.",
			"(F2, o)" : "Shows options.",
			"(F1, h)" : "Shows this window.",
			"(ctrl+z)" : "Sleep program and put in background.",
			"(ctrl+c, q)" : "Quits program.",
			"(+) / (-)" : "Add/Subtract 100ms to/from update timer.",
			"(Up) (Down)" : "Select in process list.",
			"(Enter)" : "Show detailed information for selected process.",
			"(Spacebar)" : "Expand/collapse the selected process in tree view.",
			"(Pg Up) (Pg Down)" : "Jump 1 page in process list.",
			"(Home) (End)" : "Jump to first or last page in process list.",
			"(Left) (Right)" : "Select previous/next sorting column.",
			"(b) (n)" : "Select previous/next network device.",
			"(z)" : "Toggle totals reset for current network device",
			"(a)" : "Toggle auto scaling for the network graphs.",
			"(y)" : "Toggle synced scaling mode for network graphs.",
			"(f)" : "Input a string to filter processes with.",
			"(c)" : "Toggle per-core cpu usage of processes.",
			"(r)" : "Reverse sorting order in processes box.",
			"(e)" : "Toggle processes tree view.",
			"(delete)" : "Clear any entered filter.",
			"Selected (T, t)" : "Terminate selected process with SIGTERM - 15.",
			"Selected (K, k)" : "Kill selected process with SIGKILL - 9.",
			"Selected (I, i)" : "Interrupt selected process with SIGINT - 2.",
			"_1" : " ",
			"_2" : "For bug reporting and project updates, visit:",
			"_3" : "https://github.com/aristocratos/bpytop",
		}

		while not cls.close:
			key = ""
			if cls.resized:
				y = 8 if term.height < len(help_items) + 10 else term.height // 2 - len(help_items) // 2 + 4
				out_misc = (f'{Banner.draw(y-7, center=True)}{CursorChar.d(1)}{CursorChar.l(46)}{Colors.black_bg}{Colors.default}{Fx.b}← esc'
					f'{CursorChar.r(30)}{Fx.i}Version: {VERSION}{Fx.ui}{Fx.ub}{term.bg}{term.fg}')
				x = term.width//2-36
				h, w = term.height-2-y, 72
				if len(help_items) > h:
					pages = ceil(len(help_items) / h)
				else:
					h = len(help_items)
					pages = 0
				page = 1
				out_misc += create_box(x, y, w, h+3, "help", line_color=THEME.div_line)
				redraw = True
				cls.resized = False

			if redraw:
				out = ""
				cy = 0
				if pages:
					out += (f'{CursorChar.to(y, x + 56)}{THEME.div_line(Symbol.title_left)}{Fx.b}{THEME.title("pg")}{Fx.ub}{THEME.main_fg(Symbol.up)} {Fx.b}{THEME.title}{page}/{pages} '
					f'pg{Fx.ub}{THEME.main_fg(Symbol.down)}{THEME.div_line(Symbol.title_right)}')
				out += f'{CursorChar.to(y + 1, x + 1)}{THEME.title}{Fx.b}{"Keys:":^20}Description:{THEME.main_fg}'
				for n, (keys, desc) in enumerate(help_items.items()):
					if pages and n < (page - 1) * h: continue
					out += f'{CursorChar.to(y + 2 + cy, x + 1)}{Fx.b}{("" if keys.startswith("_") else keys):^20.20}{Fx.ub}{desc:50.50}'
					cy += 1
					if cy == h: break
				if cy < h:
					for i in range(h-cy):
						out += f'{CursorChar.to(y + 2 + cy + i, x + 1)}{" " * (w - 2)}'

			if skip and redraw:
				Draw.now(out)
			elif not skip:
				Draw.now(f'{cls.background}{out_misc}{out}')
			skip = redraw = False

			if key.input_wait(timer.left()):
				key = key.get()

				if key == "mouse_click":
					mx, my = key.get_mouse()
					if mx >= x and mx < x + w and my >= y and my < y + h + 3:
						if pages and my == y and mx > x + 56 and mx < x + 61:
							key = "up"
						elif pages and my == y and mx > x + 63 and mx < x + 68:
							key = "down"
					else:
						key = "escape"

				if key == "q":
					clean_quit()
				elif key in ["escape", "M", "enter", "backspace", "h", "f1"]:
					cls.close = True
					break
				elif key in ["up", "mouse_scroll_up", "page_up"] and pages:
					page -= 1
					if page < 1: page = pages
					redraw = True
				elif key in ["down", "mouse_scroll_down", "page_down"] and pages:
					page += 1
					if page > pages: page = 1
					redraw = True

			if timer.not_zero() and not cls.resized:
				skip = True
			else:
				collector.collect()
				collector.collect_done.wait(2)
				if CONFIG.background_update: cls.background = f'{THEME.inactive_fg}' + Fx.uncolor(f'{Draw.saved_buffer()}') + f'{term.fg}'
				timer.stamp()

		if main_active:
			cls.close = False
			return
		Draw.now(f'{Draw.saved_buffer()}')
		cls.background = ""
		cls.active = False
		cls.close = False

	@classmethod
	def options(cls):
		out: str = ""
		out_misc : str = ""
		redraw: bool = True
		key: str = ""
		skip: bool = False
		main_active: bool = True if cls.active else False
		cls.active = True
		cls.resized = True
		d_quote: str
		inputting: bool = False
		input_val: str = ""
		global ARG_MODE
		Theme.refresh()
		if not cls.background:
			cls.background = f'{THEME.inactive_fg}' + Fx.uncolor(f'{Draw.saved_buffer()}') + f'{term.fg}'
		option_items: Dict[str, List[str]] = {
			"color_theme" : [
				'Set color theme.',
				'',
				'Choose from all theme files in',
				'"/usr/[local/]share/bpytop/themes" and',
				'"~/.config/bpytop/themes".',
				'',
				'"Default" for builtin default theme.',
				'User themes are prefixed by a plus sign "+".',
				'',
				'For theme updates see:',
				'https://github.com/aristocratos/bpytop'],
			"theme_background" : [
				'If the theme set background should be shown.',
				'',
				'Set to False if you want terminal background',
				'transparency.'],
			"view_mode" : [
				'Set bpytop view mode.',
				'',
				'"full" for everything shown.',
				'"proc" for cpu stats and processes.',
				'"stat" for cpu, mem, disks and net stats shown.'],
			"update_ms" : [
				'Update time in milliseconds.',
				'',
				'Recommended 2000 ms or above for better sample',
				'times for graphs.',
				'',
				'Min value: 100 ms',
				'Max value: 86400000 ms = 24 hours.'],
			"proc_sorting" : [
				'Processes sorting option.',
				'',
				'Possible values: "pid", "program", "arguments",',
				'"threads", "user", "memory", "cpu lazy" and',
				'"cpu responsive".',
				'',
				'"cpu lazy" updates top process over time,',
				'"cpu responsive" updates top process directly.'],
			"proc_reversed" : [
				'Reverse processes sorting order.',
				'',
				'True or False.'],
			"proc_tree" : [
				'Processes tree view.',
				'',
				'Set true to show processes grouped by parents,',
				'with lines drawn between parent and child',
				'process.'],
			"tree_depth" : [
				'Process tree auto collapse depth.',
				'',
				'Sets the depth were the tree view will auto',
				'collapse processes at.'],
			"proc_colors" : [
				'Enable colors in process view.',
				'',
				'Uses the cpu graph gradient colors.'],
			"proc_gradient" : [
				'Enable process view gradient fade.',
				'',
				'Fades from top or current selection.',
				'Max fade value is equal to current themes',
				'"inactive_fg" color value.'],
			"proc_per_core" : [
				'Process usage per core.',
				'',
				'If process cpu usage should be of the core',
				'it\'s running on or usage of the total',
				'available cpu power.',
				'',
				'If true and process is multithreaded',
				'cpu usage can reach over 100%.'],
			"proc_mem_bytes" : [
				'Show memory as bytes in process list.',
				' ',
				'True or False.'
			],
			"check_temp" : [
				'Enable cpu temperature reporting.',
				'',
				'True or False.'],
			"cpu_sensor" : [
				'Cpu temperature sensor',
				'',
				'Select the sensor that corresponds to',
				'your cpu temperature.',
				'Set to "Auto" for auto detection.'],
			"draw_clock" : [
				'Draw a clock at top of screen.',
				'',
				'Formatting according to strftime, empty',
				'string to disable.',
				'',
				'Custom formatting options:',
				'"/host" = hostname',
				'"/user" = username',
				'',
				'Examples of strftime formats:',
				'"%X" = locale HH:MM:SS',
				'"%H" = 24h hour, "%I" = 12h hour',
				'"%M" = minute, "%S" = second',
				'"%d" = day, "%m" = month, "%y" = year'],
			"background_update" : [
				'Update main ui when menus are showing.',
				'',
				'True or False.',
				'',
				'Set this to false if the menus is flickering',
				'too much for a comfortable experience.'],
			"custom_cpu_name" : [
				'Custom cpu model name in cpu percentage box.',
				'',
				'Empty string to disable.'],
			"disks_filter" : [
				'Optional filter for shown disks.',
				'',
				'Should be last folder in path of a mountpoint,',
				'"root" replaces "/", separate multiple values',
				'with a comma.',
				'Begin line with "exclude=" to change to exclude',
				'filter.',
				'Oterwise defaults to "most include" filter.',
				'',
				'Example: disks_filter="exclude=boot, home"'],
			"mem_graphs" : [
				'Show graphs for memory values.',
				'',
				'True or False.'],
			"show_swap" : [
				'If swap memory should be shown in memory box.',
				'',
				'True or False.'],
			"swap_disk" : [
				'Show swap as a disk.',
				'',
				'Ignores show_swap value above.',
				'Inserts itself after first disk.'],
			"show_disks" : [
				'Split memory box to also show disks.',
				'',
				'True or False.'],
			"net_download" : [
				'Fixed network graph download value.',
				'',
				'Default "10M" = 10 MibiBytes.',
				'Possible units:',
				'"K" (KiB), "M" (MiB), "G" (GiB).',
				'',
				'Append "bit" for bits instead of bytes,',
				'i.e "100Mbit"',
				'',
				'Can be toggled with auto button.'],
			"net_upload" : [
				'Fixed network graph upload value.',
				'',
				'Default "10M" = 10 MibiBytes.',
				'Possible units:',
				'"K" (KiB), "M" (MiB), "G" (GiB).',
				'',
				'Append "bit" for bits instead of bytes,',
				'i.e "100Mbit"',
				'',
				'Can be toggled with auto button.'],
			"net_auto" : [
				'Start in network graphs auto rescaling mode.',
				'',
				'Ignores any values set above at start and',
				'rescales down to 10KibiBytes at the lowest.',
				'',
				'True or False.'],
			"net_sync" : [
				'Network scale sync.',
				'',
				'Syncs the scaling for download and upload to',
				'whichever currently has the highest scale.',
				'',
				'True or False.'],
			"net_color_fixed" : [
				'Set network graphs color gradient to fixed.',
				'',
				'If True the network graphs color is based',
				'on the total bandwidth usage instead of',
				'the current autoscaling.',
				'',
				'The bandwidth usage is based on the',
				'"net_download" and "net_upload" values set',
				'above.'],
			"show_battery" : [
				'Show battery stats.',
				'',
				'Show battery stats in the top right corner',
				'if a battery is present.'],
			"show_init" : [
				'Show init screen at startup.',
				'',
				'The init screen is purely cosmetical and',
				'slows down start to show status messages.'],
			"update_check" : [
				'Check for updates at start.',
				'',
				'Checks for latest version from:',
				'https://github.com/aristocratos/bpytop'],
			"log_level" : [
				'Set loglevel for error.log',
				'',
				'Levels are: "ERROR" "WARNING" "INFO" "DEBUG".',
				'The level set includes all lower levels,',
				'i.e. "DEBUG" will show all logging info.']
			}
		option_len: int = len(option_items) * 2
		sorting_i: int = CONFIG.sorting_options.index(CONFIG.proc_sorting)
		loglevel_i: int = CONFIG.log_levels.index(CONFIG.log_level)
		view_mode_i: int = CONFIG.view_modes.index(CONFIG.view_mode)
		cpu_sensor_i: int = CONFIG.cpu_sensors.index(CONFIG.cpu_sensor)
		color_i: int
		while not cls.close:
			key = ""
			if cls.resized:
				y = 9 if term.height < option_len + 10 else term.height // 2 - option_len // 2 + 4
				out_misc = (f'{Banner.draw(y-7, center=True)}{CursorChar.d(1)}{CursorChar.l(46)}{Colors.black_bg}{Colors.default}{Fx.b}← esc'
					f'{CursorChar.r(30)}{Fx.i}Version: {VERSION}{Fx.ui}{Fx.ub}{term.bg}{term.fg}')
				x = term.width//2-38
				x2 = x + 27
				h, w, w2 = term.height-2-y, 26, 50
				h -= h % 2
				color_i = list(Theme.themes).index(THEME.current)
				if option_len > h:
					pages = ceil(option_len / h)
				else:
					h = option_len
					pages = 0
				page = 1
				selected_int = 0
				out_misc += create_box(x, y, w, h+2, "options", line_color=THEME.div_line)
				redraw = True
				cls.resized = False

			if redraw:
				out = ""
				cy = 0

				selected = list(option_items)[selected_int]
				if pages:
					out += (f'{CursorChar.to(y + h + 1, x + 11)}{THEME.div_line(Symbol.title_left)}{Fx.b}{THEME.title("pg")}{Fx.ub}{THEME.main_fg(Symbol.up)} {Fx.b}{THEME.title}{page}/{pages} '
					f'pg{Fx.ub}{THEME.main_fg(Symbol.down)}{THEME.div_line(Symbol.title_right)}')
				#out += f'{Mv.to(y+1, x+1)}{THEME.title}{Fx.b}{"Keys:":^20}Description:{THEME.main_fg}'
				for n, opt in enumerate(option_items):
					if pages and n < (page - 1) * ceil(h / 2): continue
					value = getattr(CONFIG, opt)
					t_color = f'{THEME.selected_bg}{THEME.selected_fg}' if opt == selected else f'{THEME.title}'
					v_color	= "" if opt == selected else f'{THEME.title}'
					d_quote = '"' if isinstance(value, str) else ""
					if opt == "color_theme":
						counter = f' {color_i + 1}/{len(Theme.themes)}'
					elif opt == "proc_sorting":
						counter = f' {sorting_i + 1}/{len(CONFIG.sorting_options)}'
					elif opt == "log_level":
						counter = f' {loglevel_i + 1}/{len(CONFIG.log_levels)}'
					elif opt == "view_mode":
						counter = f' {view_mode_i + 1}/{len(CONFIG.view_modes)}'
					elif opt == "cpu_sensor":
						counter = f' {cpu_sensor_i + 1}/{len(CONFIG.cpu_sensors)}'
					else:
						counter = ""
					out += f'{CursorChar.to(y + 1 + cy, x + 1)}{t_color}{Fx.b}{opt.replace("_", " ").capitalize() + counter:^24.24}{Fx.ub}{CursorChar.to(y + 2 + cy, x + 1)}{v_color}'
					if opt == selected:
						if isinstance(value, bool) or opt in ["color_theme", "proc_sorting", "log_level", "view_mode", "cpu_sensor"]:
							out += f'{t_color} {Symbol.left}{v_color}{d_quote + str(value) + d_quote:^20.20}{t_color}{Symbol.right} '
						elif inputting:
							out += f'{str(input_val)[-17:] + Fx.bl + "█" + Fx.ubl + "" + Symbol.enter:^33.33}'
						else:
							out += ((f'{t_color} {Symbol.left}{v_color}' if type(value) is int else "  ") +
							f'{str(value) + " " + Symbol.enter:^20.20}' + (f'{t_color}{Symbol.right} ' if type(value) is int else "  "))
					else:
						out += f'{d_quote + str(value) + d_quote:^24.24}'
					out += f'{term.bg}'
					if opt == selected:
						h2 = len(option_items[opt]) + 2
						y2 = y + (selected_int * 2) - ((page-1) * h)
						if y2 + h2 > term.height: y2 = term.height - h2
						out += f'{create_box(x2, y2, w2, h2, "description", line_color=THEME.div_line)}{THEME.main_fg}'
						for n, desc in enumerate(option_items[opt]):
							out += f'{CursorChar.to(y2 + 1 + n, x2 + 2)}{desc:.48}'
					cy += 2
					if cy >= h: break
				if cy < h:
					for i in range(h-cy):
						out += f'{CursorChar.to(y + 1 + cy + i, x + 1)}{" " * (w - 2)}'


			if not skip or redraw:
				Draw.now(f'{cls.background}{out_misc}{out}')
			skip = redraw = False

			if key.input_wait(timer.left()):
				key = key.get()
				redraw = True
				has_sel = False
				if key == "mouse_click" and not inputting:
					mx, my = key.get_mouse()
					if mx > x and mx < x + w and my > y and my < y + h + 2:
						mouse_sel = ceil((my - y) / 2) - 1 + ceil((page-1) * (h / 2))
						if pages and my == y+h+1 and mx > x+11 and mx < x+16:
							key = "page_up"
						elif pages and my == y+h+1 and mx > x+19 and mx < x+24:
							key = "page_down"
						elif my == y+h+1:
							pass
						elif mouse_sel == selected_int:
							if mx < x + 6:
								key = "left"
							elif mx > x + 19:
								key = "right"
							else:
								key = "enter"
						elif mouse_sel < len(option_items):
							selected_int = mouse_sel
							has_sel = True
					else:
						key = "escape"
				if inputting:
					if key in ["escape", "mouse_click"]:
						inputting = False
					elif key == "enter":
						inputting = False
						if str(getattr(CONFIG, selected)) != input_val:
							if selected == "update_ms":
								if not input_val or int(input_val) < 100:
									CONFIG.update_ms = 100
								elif int(input_val) > 86399900:
									CONFIG.update_ms = 86399900
								else:
									CONFIG.update_ms = int(input_val)
							elif selected == "tree_depth":
								if not input_val or int(input_val) < 0:
									CONFIG.tree_depth = 0
								else:
									CONFIG.tree_depth = int(input_val)
								ProcCollector.collapsed = {}
							elif isinstance(getattr(CONFIG, selected), str):
								setattr(CONFIG, selected, input_val)
								if selected.startswith("net_"):
									NetCollector.net_min = {"download" : -1, "upload" : -1}
								elif selected == "draw_clock":
									Box.clock_on = True if len(CONFIG.draw_clock) > 0 else False
									if not Box.clock_on:
										Draw.clear("clock", saved=True)
							term.refresh(force=True)
							cls.resized = False
					elif key == "backspace" and len(input_val) > 0:
						input_val = input_val[:-1]
					elif key == "delete":
							input_val = ""
					elif isinstance(getattr(CONFIG, selected), str) and len(key) == 1:
						input_val += key
					elif isinstance(getattr(CONFIG, selected), int) and key.isdigit():
						input_val += key
				elif key == "q":
					clean_quit()
				elif key in ["escape", "o", "M", "f2"]:
					cls.close = True
					break
				elif key == "enter" and selected in ["update_ms", "disks_filter", "custom_cpu_name", "net_download", "net_upload", "draw_clock", "tree_depth"]:
					inputting = True
					input_val = str(getattr(CONFIG, selected))
				elif key == "left" and selected == "update_ms" and CONFIG.update_ms - 100 >= 100:
					CONFIG.update_ms -= 100
					Box.draw_update_ms()
				elif key == "right" and selected == "update_ms" and CONFIG.update_ms + 100 <= 86399900:
					CONFIG.update_ms += 100
					Box.draw_update_ms()
				elif key == "left" and selected == "tree_depth" and CONFIG.tree_depth > 0:
					CONFIG.tree_depth -= 1
					ProcCollector.collapsed = {}
				elif key == "right" and selected == "tree_depth":
					CONFIG.tree_depth += 1
					ProcCollector.collapsed = {}
				elif key in ["left", "right"] and isinstance(getattr(CONFIG, selected), bool):
					setattr(CONFIG, selected, not getattr(CONFIG, selected))
					if selected == "check_temp":
						if CONFIG.check_temp:
							Cpucollector.get_sensors()
						else:
							Cpucollector.sensor_method = ""
							Cpucollector.got_sensors = False
					if selected in ["net_auto", "net_color_fixed", "net_sync"]:
						if selected == "net_auto": NetCollector.auto_min = CONFIG.net_auto
						NetBox.redraw = True
					if selected == "theme_background":
						term.bg = THEME.main_bg if CONFIG.theme_background else "\033[49m"
						Draw.now(term.bg)
					if selected == "show_battery":
						Draw.clear("battery", saved=True)
					term.refresh(force=True)
					cls.resized = False
				elif key in ["left", "right"] and selected == "color_theme" and len(Theme.themes) > 1:
					if key == "left":
						color_i -= 1
						if color_i < 0: color_i = len(Theme.themes) - 1
					elif key == "right":
						color_i += 1
						if color_i > len(Theme.themes) - 1: color_i = 0
					collector.collect_idle.wait()
					CONFIG.color_theme = list(Theme.themes)[color_i]
					THEME(CONFIG.color_theme)
					term.refresh(force=True)
					timer.finish()
					self.controller.break_wait()
				elif key in ["left", "right"] and selected == "proc_sorting":
					ProcCollector.sorting(key)
				elif key in ["left", "right"] and selected == "log_level":
					if key == "left":
						loglevel_i -= 1
						if loglevel_i < 0: loglevel_i = len(CONFIG.log_levels) - 1
					elif key == "right":
						loglevel_i += 1
						if loglevel_i > len(CONFIG.log_levels) - 1: loglevel_i = 0
					CONFIG.log_level = CONFIG.log_levels[loglevel_i]
					errlog.setLevel(getattr(logging, CONFIG.log_level))
					errlog.info(f'Loglevel set to {CONFIG.log_level}')
				elif key in ["left", "right"] and selected == "cpu_sensor" and len(CONFIG.cpu_sensors) > 1:
					if key == "left":
						cpu_sensor_i -= 1
						if cpu_sensor_i < 0: cpu_sensor_i = len(CONFIG.cpu_sensors) - 1
					elif key == "right":
						cpu_sensor_i += 1
						if cpu_sensor_i > len(CONFIG.cpu_sensors) - 1: cpu_sensor_i = 0
					collector.collect_idle.wait()
					CONFIG.cpu_sensor = CONFIG.cpu_sensors[cpu_sensor_i]
					if CONFIG.check_temp and (
						Cpucollector.sensor_method != "psutil" or CONFIG.cpu_sensor == "Auto"):
						Cpucollector.get_sensors()
						term.refresh(force=True)
						cls.resized = False
				elif key in ["left", "right"] and selected == "view_mode":
					if key == "left":
						view_mode_i -= 1
						if view_mode_i < 0: view_mode_i = len(CONFIG.view_modes) - 1
					elif key == "right":
						view_mode_i += 1
						if view_mode_i > len(CONFIG.view_modes) - 1: view_mode_i = 0
					CONFIG.view_mode = CONFIG.view_modes[view_mode_i]
					Box.proc_mode = True if CONFIG.view_mode == "proc" else False
					Box.stat_mode = True if CONFIG.view_mode == "stat" else False
					if ARG_MODE:
						ARG_MODE = ""
					Draw.clear(saved=True)
					term.refresh(force=True)
					cls.resized = False
				elif key == "up":
					selected_int -= 1
					if selected_int < 0: selected_int = len(option_items) - 1
					page = floor(selected_int * 2 / h) + 1
				elif key == "down":
					selected_int += 1
					if selected_int > len(option_items) - 1: selected_int = 0
					page = floor(selected_int * 2 / h) + 1
				elif key in ["mouse_scroll_up", "page_up"] and pages:
					page -= 1
					if page < 1: page = pages
					selected_int = (page-1) * ceil(h / 2)
				elif key in ["mouse_scroll_down", "page_down"] and pages:
					page += 1
					if page > pages: page = 1
					selected_int = (page-1) * ceil(h / 2)
				elif has_sel:
					pass
				else:
					redraw = False

			if timer.not_zero() and not cls.resized:
				skip = True
			else:
				collector.collect()
				collector.collect_done.wait(2)
				if CONFIG.background_update: cls.background = f'{THEME.inactive_fg}' + Fx.uncolor(f'{Draw.saved_buffer()}') + f'{term.fg}'
				timer.stamp()

		if main_active:
			cls.close = False
			return
		Draw.now(f'{Draw.saved_buffer()}')
		cls.background = ""
		cls.active = False
		cls.close = False





class UpdateChecker:
	version: str = VERSION
	thread: threading.Thread

	@classmethod
	def run(cls):
		cls.thread = threading.Thread(target=cls._checker)
		cls.thread.start()

	@classmethod
	def _checker(cls):
		try:
			with urllib.request.urlopen("https://github.com/aristocratos/bpytop/raw/master/bpytop.py", timeout=5) as source: # type: ignore
				for line in source:
					line = line.decode("utf-8")
					if line.startswith("VERSION: str ="):
						cls.version = line[(line.index("=")+1):].strip('" \n')
						break
		except Exception as e:
			errlog.exception(f'{e}')
		else:
			if cls.version != VERSION and which("notify-send"):
				try:
					subprocess.run(["notify-send", "-u", "normal", "BpyTop Update!",
						f'New version of BpyTop available!\nCurrent version: {VERSION}\nNew version: {cls.version}\nDownload at github.com/aristocratos/bpytop',
						"-i", "update-notifier", "-t", "10000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
				except Exception as e:
					errlog.exception(f'{e}')


class FullScreenWidget:
	pass


class Init(FullScreenWidget):
	def __init__(self):
		self.running: bool = True
		self.initbg_colors: List[str] = []
		self.initbg_data: List[int]
		self.initbg_up: Graph
		self.initbg_down: Graph
		self.resized = False
		self.is_showing = False

		Draw.buffer("init", z=1)
		Draw.buffer("initbg", z=10)
		for i in range(51):
			for _ in range(2): self.initbg_colors.append(Color.fg(i, i, i))
		Draw.buffer("banner", (
			f'{Banner.draw(term.height // 2 - 10, center=True)}{CursorChar.d(1)}{CursorChar.l(11)}{Colors.black_bg}{Colors.default}'
			f'{Fx.b}{Fx.i}Version: {VERSION}{Fx.ui}{Fx.ub}{term.bg}{term.fg}{Color.fg("#50")}'
		), z=2)
		for _i in range(7):
			perc = f'{str(round((_i + 1) * 14 + 2)) + "%":>5}'
			Draw.buffer("+banner", f'{CursorChar.to(term.height // 2 - 2 + _i, term.width // 2 - 28)}{Fx.trans(perc)}{Symbol.v_line}')

		Draw.buffer("+init!", f'{Color.fg("#cc")}{Fx.b}{CursorChar.to(term.height // 2 - 2, term.width // 2 - 21)}{CursorChar.save}')

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
			Draw.buffer(
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
			Draw.now(terminal.clear)
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
		Draw.buffer(
			"+init",
			f'{CursorChar.restore}{Fx.trans(line_text)}{CursorChar.save}',
		)
		if self.is_showing and not self.resized:
			# prevent showing during resizing
			Draw.out("init")

