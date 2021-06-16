
from time import time

# ? Main loop ------------------------------------------------------------------------------------->


class Timer:
	def __init__(self, update_ms):
		self.timestamp: float = time()
		self.return_zero = False
		self.update_ms = update_ms

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

