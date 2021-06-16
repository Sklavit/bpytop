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