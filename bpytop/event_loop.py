
from time import time

# ? Main loop ------------------------------------------------------------------------------------->
from bpytop.old_functions import process_keys


class Timer:
	def __init__(self, update_ms, controller):
		self.timestamp: float = time()
		self.return_zero = False
		self.update_ms = update_ms
		self.controller = controller

	def stamp(self):
		self.timestamp = time()

	def not_zero(self) -> bool:
		if self.return_zero:
			self.return_zero = False
			return False
		return self.timestamp + (self.update_ms / 1000) > time()

	def left(self) -> float:
		return self.timestamp + (self.update_ms / 1000) - time()

	def finish(self):
		self.return_zero = True
		self.timestamp = time() - (self.update_ms / 1000)
		self.controller.break_wait()


def run_event_loop(term, timer, key, collector):
	while not False:
		term.refresh()
		timer.stamp()

		while timer.not_zero():
			if key.input_wait(timer.left()):
				process_keys()

		collector.collect()
