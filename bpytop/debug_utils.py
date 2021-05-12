#? Timers for testing and debugging -------------------------------------------------------------->
import logging

from typing import Dict

from time import time

reporter = logging.getLogger("reporter")
errlog = logging.getLogger("ErrorLogger")


def timeit_decorator(func):
	def timed(*args, **kw):
		ts = time()
		out = func(*args, **kw)
		errlog.debug(f'{func.__name__} completed in {time() - ts:.6f} seconds')
		return out
	return timed


class TimeIt:
	timers: Dict[str, float] = {}
	paused: Dict[str, float] = {}

	@classmethod
	def start(cls, name):
		cls.timers[name] = time()

	@classmethod
	def pause(cls, name):
		if name in cls.timers:
			cls.paused[name] = time() - cls.timers[name]
			del cls.timers[name]

	@classmethod
	def stop(cls, name):
		if name in cls.timers:
			total: float = time() - cls.timers[name]
			del cls.timers[name]
			if name in cls.paused:
				total += cls.paused[name]
				del cls.paused[name]
			errlog.debug(f'{name} completed in {total:.6f} seconds')
