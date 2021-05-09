import threading

from typing import Dict, Iterable, Tuple

from bpytop.config import errlog


class Cursor:
	"""
	Class with collection of cursor movement functions:
	.t[o](line, column) | .r[ight](columns) | .l[eft](columns) | .u[p](lines) | .d[own](lines)
	| .save() | .restore()
	"""
	@staticmethod
	def to(line: int, col: int) -> str:
		return f'\033[{line};{col}f'	#* Move cursor to line, column
	@staticmethod
	def right(x: int) -> str:			#* Move cursor right x columns
		return f'\033[{x}C'
	@staticmethod
	def left(x: int) -> str:			#* Move cursor left x columns
		return f'\033[{x}D'
	@staticmethod
	def up(x: int) -> str:				#* Move cursor up x lines
		return f'\033[{x}A'
	@staticmethod
	def down(x: int) -> str:			#* Move cursor down x lines
		return f'\033[{x}B'

	save: str = "\033[s" 				#* Save cursor position
	restore: str = "\033[u" 			#* Restore saved cursor postion
	t = to
	r = right
	l = left
	u = up
	d = down


class Draw:
	"""Holds the draw buffer and manages IO blocking queue
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
		'''Wait for input reader and self to be idle then print to screen'''
		key.idle.wait()
		cls.idle.wait()
		cls.idle.clear()
		try:
			print(*args, sep="", end="", flush=True)
		except BlockingIOError:
			pass
			key.idle.wait()
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
		if not name in cls.z_order or z != 100: cls.z_order[name] = z
		if args: string = "".join(args)
		if only_save:
			if name not in cls.saved or not append: cls.saved[name] = ""
			cls.saved[name] += string
		else:
			if name not in cls.strings or not append: cls.strings[name] = ""
			cls.strings[name] += string
			if now:
				cls.out(name)

	@classmethod
	def out(cls, *names: str, clear = False):
		out: str = ""
		if not cls.strings: return
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


class Color:
	'''Holds representations for a 24-bit color value
	__init__(color, depth="fg", default=False)
	-- color accepts 6 digit hexadecimal: string "#RRGGBB", 2 digit hexadecimal: string "#FF" or decimal RGB "255 255 255" as a string.
	-- depth accepts "fg" or "bg"
	__call__(*args) joins str arguments to a string and apply color
	__str__ returns escape sequence to set color
	__iter__ returns iteration over red, green and blue in integer values of 0-255.
	* Values:  .hexa: str  |  .dec: Tuple[int, int, int]  |  .red: int  |  .green: int  |  .blue: int  |  .depth: str  |  .escape: str
	'''
	hexa: str; dec: Tuple[int, int, int]; red: int; green: int; blue: int; depth: str; escape: str; default: bool

	def __init__(self, color: str, depth: str = "fg", default: bool = False):
		self.depth = depth
		self.default = default
		try:
			if not color:
				self.dec = (-1, -1, -1)
				self.hexa = ""
				self.red = self.green = self.blue = -1
				self.escape = "\033[49m" if depth == "bg" and default else ""
				return

			elif color.startswith("#"):
				self.hexa = color
				if len(self.hexa) == 3:
					self.hexa += self.hexa[1:3] + self.hexa[1:3]
					c = int(self.hexa[1:3], base=16)
					self.dec = (c, c, c)
				elif len(self.hexa) == 7:
					self.dec = (int(self.hexa[1:3], base=16), int(self.hexa[3:5], base=16), int(self.hexa[5:7], base=16))
				else:
					raise ValueError(f'Incorrectly formatted hexadecimal rgb string: {self.hexa}')

			else:
				c_t = tuple(map(int, color.split(" ")))
				if len(c_t) == 3:
					self.dec = c_t #type: ignore
				else:
					raise ValueError(f'RGB dec should be "0-255 0-255 0-255"')

			ct = self.dec[0] + self.dec[1] + self.dec[2]
			if ct > 255*3 or ct < 0:
				raise ValueError(f'RGB values out of range: {color}')
		except Exception as e:
			errlog.exception(str(e))
			self.escape = ""
			return

		if self.dec and not self.hexa: self.hexa = f'{hex(self.dec[0]).lstrip("0x").zfill(2)}{hex(self.dec[1]).lstrip("0x").zfill(2)}{hex(self.dec[2]).lstrip("0x").zfill(2)}'

		if self.dec and self.hexa:
			self.red, self.green, self.blue = self.dec
			self.escape = f'\033[{38 if self.depth == "fg" else 48};2;{";".join(str(c) for c in self.dec)}m'

	def __str__(self) -> str:
		return self.escape

	def __repr__(self) -> str:
		return repr(self.escape)

	def __iter__(self) -> Iterable:
		for c in self.dec: yield c

	def __call__(self, *args: str) -> str:
		if len(args) < 1:
			return ""
		return f'{self.escape}{"".join(args)}{getattr(term, self.depth)}'

	@staticmethod
	def escape_color(hexa: str = "", r: int = 0, g: int = 0, b: int = 0, depth: str = "fg") -> str:
		"""Returns escape sequence to set color
		* accepts either 6 digit hexadecimal hexa="#RRGGBB", 2 digit hexadecimal: hexa="#FF"
		* or decimal RGB: r=0-255, g=0-255, b=0-255
		* depth="fg" or "bg"
		"""
		dint: int = 38 if depth == "fg" else 48
		color: str = ""
		if hexa:
			try:
				if len(hexa) == 3:
					c = int(hexa[1:], base=16)
					color = f'\033[{dint};2;{c};{c};{c}m'
				elif len(hexa) == 7:
					color = f'\033[{dint};2;{int(hexa[1:3], base=16)};{int(hexa[3:5], base=16)};{int(hexa[5:7], base=16)}m'
			except ValueError as e:
				errlog.exception(f'{e}')
		else:
			color = f'\033[{dint};2;{r};{g};{b}m'
		return color

	@classmethod
	def fg(cls, *args) -> str:
		if len(args) > 2: return cls.escape_color(r=args[0], g=args[1], b=args[2], depth="fg")
		else: return cls.escape_color(hexa=args[0], depth="fg")

	@classmethod
	def bg(cls, *args) -> str:
		if len(args) > 2: return cls.escape_color(r=args[0], g=args[1], b=args[2], depth="bg")
		else: return cls.escape_color(hexa=args[0], depth="bg")


class Colors:
	'''Standard colors for menus and dialogs'''
	default = Color("#cc")
	white = Color("#ff")
	red = Color("#bf3636")
	green = Color("#68bf36")
	blue = Color("#0fd7ff")
	yellow = Color("#db8b00")
	black_bg = Color("#00", depth="bg")
	null = Color("")