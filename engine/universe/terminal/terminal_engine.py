import logging

import threading

from typing import Dict, Tuple

from engine.universe.terminal.colors import Color

reporter = logging.getLogger("reporter")
errlog = logging.getLogger("ErrorLogger")


class CursorChar:
	"""
	Class with collection of cursor movement functions:
	.t[o](line, column) | .r[ight](columns) | .l[eft](columns) | .u[p](lines) | .d[own](lines)
	| .save() | .restore()
	"""
	@staticmethod
	def to(line: int, col: int) -> str:
		# * Move cursor to line, column
		return f'\033[{line};{col}f'
	@staticmethod
	def right(x: int) -> str:
		"""Move cursor right x columns."""
		return f'\033[{x}C'
	@staticmethod
	def left(x: int) -> str:
		"""Move cursor left x columns"""
		return f'\033[{x}D'
	@staticmethod
	def up(x: int) -> str:
		"""Move cursor up x lines"""
		return f'\033[{x}A'
	@staticmethod
	def down(x: int) -> str:
		"""Move cursor down x lines"""
		return f'\033[{x}B'

	save: str = "\033[s" 				#* Save cursor position
	restore: str = "\033[u" 			#* Restore saved cursor postion
	t = to
	r = right
	l = left
	u = up
	d = down


class Draw:
	"""
	Holds the draw buffer and manages IO blocking queue
	* .buffer([+]name[!], *args, append=False, now=False, z=100) : Add *args to buffer
	* - Adding "+" prefix to name sets append to True and appends to name's current string
	* - Adding "!" suffix to name sets now to True and print name's current string
	* .out(clear=False) : Print all strings in buffer, clear=True clear all buffers after
	* .now(*args) : Prints all arguments as a string
	* .clear(*names) : Clear named buffers, all if no argument
	* .last_screen() : Prints all saved buffers
	"""
	strings: Dict[str, str] = {}
	z_order: Dict[str, int] = {}
	saved: Dict[str, str] = {}
	save: Dict[str, bool] = {}
	once: Dict[str, bool] = {}
	idle = threading.Event()
	idle.set()

	@classmethod
	def now(cls, *args):
		"""Wait for input reader and self to be idle then print to screen"""
		controller.idle.wait()
		cls.idle.wait()
		cls.idle.clear()
		try:
			print(*args, sep="", end="", flush=True)
		except BlockingIOError:
			pass
			controller.idle.wait()
			print(*args, sep="", end="", flush=True)
		cls.idle.set()

	@classmethod
	def buffer(cls, name: str, *args: str, append: bool = False, now: bool = False, z: int = 100, only_save: bool = False, no_save: bool = False, once: bool = False):
		string: str = ""
		if name.startswith("+"):
			name = name.lstrip("+")
			append = True
		if name.endswith("!"):
			name = name.rstrip("!")
			now = True
		cls.save[name] = not no_save
		cls.once[name] = once
		if not name in cls.z_order or z != 100:
			cls.z_order[name] = z
		if args:
			string = "".join(args)
		if only_save:
			if name not in cls.saved or not append:
				cls.saved[name] = ""
			cls.saved[name] += string
		else:
			if name not in cls.strings or not append:
				cls.strings[name] = ""
			cls.strings[name] += string
			if now:
				cls.out(name)

	@classmethod
	def out(cls, *names: str, clear=False):
		out: str = ""
		if not cls.strings:
			return
		if names:
			for name in sorted(cls.z_order, key=cls.z_order.get, reverse=True):
				if name in names and name in cls.strings:
					out += cls.strings[name]
					if cls.save[name]:
						cls.saved[name] = cls.strings[name]
					if clear or cls.once[name]:
						cls.clear(name)
			cls.now(out)
		else:
			for name in sorted(cls.z_order, key=cls.z_order.get, reverse=True):
				if name in cls.strings:
					out += cls.strings[name]
					if cls.save[name]:
						cls.saved[name] = cls.strings[name]
					if cls.once[name] and not clear:
						cls.clear(name)
			if clear:
				cls.clear()
			cls.now(out)

	@classmethod
	def saved_buffer(cls) -> str:
		out: str = ""
		for name in sorted(cls.z_order, key=cls.z_order.get, reverse=True):
			if name in cls.saved:
				out += cls.saved[name]
		return out


	@classmethod
	def clear(cls, *names, saved: bool = False):
		if names:
			for name in names:
				if name in cls.strings:
					del cls.strings[name]
				if name in cls.save:
					del cls.save[name]
				if name in cls.once:
					del cls.once[name]
				if saved:
					if name in cls.saved:
						del cls.saved[name]
					if name in cls.z_order:
						del cls.z_order[name]
		else:
			cls.strings = {}
			cls.save = {}
			cls.once = {}
			if saved:
				cls.saved = {}
				cls.z_order = {}


def create_box(x: int = 0, y: int = 0, width: int = 0, height: int = 0, title: str = "", title2: str = "", line_color: Color = None, title_color: Color = None, fill: bool = True, box = None) -> str:
	'''Create a box from a box object or by given arguments'''
	out: str = f'{term.fg}{term.bg}'
	if not line_color: line_color = THEME.div_line
	if not title_color: title_color = THEME.title

	#* Get values from box class if given
	if box:
		x = box.x
		y = box.y
		width = box.width
		height =box.height
		title = box.name
	hlines: Tuple[int, int] = (y, y + height - 1)

	out += f'{line_color}'

	#* Draw all horizontal lines
	for hpos in hlines:
		out += f'{Cursor.to(hpos, x)}{Symbol.h_line * (width - 1)}'

	#* Draw all vertical lines and fill if enabled
	for hpos in range(hlines[0]+1, hlines[1]):
		out += f'{Cursor.to(hpos, x)}{Symbol.v_line}{" " * (width - 2) if fill else Cursor.r(width - 2)}{Symbol.v_line}'

	#* Draw corners
	out += f'{Cursor.to(y, x)}{Symbol.left_up}\
	{Cursor.to(y, x + width - 1)}{Symbol.right_up}\
	{Cursor.to(y + height - 1, x)}{Symbol.left_down}\
	{Cursor.to(y + height - 1, x + width - 1)}{Symbol.right_down}'

	#* Draw titles if enabled
	if title:
		out += f'{Cursor.to(y, x + 2)}{Symbol.title_left}{title_color}{Fx.b}{title}{Fx.ub}{line_color}{Symbol.title_right}'
	if title2:
		out += f'{Cursor.to(hlines[1], x + 2)}{Symbol.title_left}{title_color}{Fx.b}{title2}{Fx.ub}{line_color}{Symbol.title_right}'

	return f'{out}{term.fg}{Cursor.to(y + 1, x + 1)}'