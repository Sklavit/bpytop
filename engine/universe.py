import os

from bpytop.main_mvc import Controller
from engine.universe.terminal.base import Terminal
from engine.universe.terminal.terminal_engine import BufferedStdout


class Window:
	def reset(self):
		pass

	def set_title(self, title: str):
		pass


class StdinOutWindow(Window):
	def __init__(self, terminal):
		self.terminal = terminal  # stdin ?
		self.controller = Controller(self.terminal)  # stdin ? processor ? TODO split controllero on stdin and processor
		self.view = BufferedStdout()  # stdout

	@classmethod
	def get_active(cls):
		terminal = Terminal(
			width=os.get_terminal_size().columns, height=os.get_terminal_size().lines,
		)
		return cls(terminal)

	def draw_soon(self, *args):  # previously Draw.now(cls, *args)
		"""Wait for input reader and self to be idle then print to screen"""
		self.controller.idle.wait()
		try:
			self.view.draw_soon(*args)
		except BlockingIOError:
			pass  # TODO why pass here ?
			self.controller.idle.wait()
			self.view.draw_soon(*args)

	def switch_to_alt_screen(self):
		# TODO we should not call self method ! should be from parent class or component ?
		self.draw_soon(
			self.terminal.alt_screen,  # Switch to alternate screen
		)

	def reset(self):
		self.draw_soon(
			self.terminal.clear,  # clear screen, reset cursor
			self.terminal.hide_cursor,  # hide cursor
			self.terminal.mouse_on,  # enable mouse reporting
		)
		# disable input echo
		self.terminal.echo(False)
		self.terminal.refresh(force=True)

	def set_title(self, title: str):
		self.draw_soon(
			self.terminal.title(title),
		)


class Universe:
	def __init__(self):
		pass

	@classmethod
	def get_active_stdinout_window(cls):
		"""
		Return active stdinout window which corresponds to stdin/stdout (terminal).

		:return: StdinOutWindow
		"""
		return StdinOutWindow.get_active()


