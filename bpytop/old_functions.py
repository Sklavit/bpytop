import psutil
from time import time

from datetime import timedelta

from _thread import interrupt_main

import signal

import os

import re

import subprocess

from typing import Dict, List, Tuple, Union

from bpytop.env import SYSTEM
# from bpytop.old_classes import (
# 	Graphs, Menu,
# )
# from bpytop.collectors import Memcollector, Netcollector, Proccollector
# from bpytop.terminal_widgets import Box, Fx, Symbol
# from bpytop.bpytop_widgets import ProcBox
# from bpytop.terminal_engine import Color, Cursor, Draw
# from bpytop2 import CONFIG, THEME, errlog
# from bpytop.old_consts import UNITS
from bpytop.main_mvc import Controller
from bpytop.old_classes import Menu

THREAD_ERROR: int = 0


def get_cpu_name() -> str:
	'''Fetch a suitable CPU identifier from the CPU model name string'''
	name: str = ""
	nlist: List = []
	command: str = ""
	cmd_out: str = ""
	rem_line: str = ""
	if SYSTEM == "Linux":
		command = "cat /proc/cpuinfo"
		rem_line = "model name"
	elif SYSTEM == "MacOS":
		command ="sysctl -n machdep.cpu.brand_string"
	elif SYSTEM == "BSD":
		command ="sysctl hw.model"
		rem_line = "hw.model"

	try:
		cmd_out = subprocess.check_output("LANG=C " + command, shell=True, universal_newlines=True)
	except:
		pass
	if rem_line:
		for line in cmd_out.split("\n"):
			if rem_line in line:
				name = re.sub( ".*" + rem_line + ".*:", "", line,1).lstrip()
	else:
		name = cmd_out
	nlist = name.split(" ")
	try:
		if "Xeon" in name and "CPU" in name:
			name = nlist[nlist.index("CPU")+(-1 if name.endswith(("CPU", "z")) else 1)]
		elif "Ryzen" in name:
			name = " ".join(nlist[nlist.index("Ryzen"):nlist.index("Ryzen")+3])
		elif "Duo" in name and "@" in name:
			name = " ".join(nlist[:nlist.index("@")])
		elif "CPU" in name and not nlist[0] == "CPU" and not nlist[nlist.index("CPU")-1].isdigit():
			name = nlist[nlist.index("CPU")-1]
	except:
		pass

	name = name.replace("Processor", "").replace("CPU", "").replace("(R)", "").replace("(TM)", "").replace("Intel", "")
	name = re.sub(r"\d?\.?\d+[mMgG][hH][zZ]", "", name)
	name = " ".join(name.split())

	return name


def now_sleeping(signum, frame):
	"""Reset terminal settings and stop background input read before putting to sleep"""
	key.stop()
	collector.stop()
	Draw.now(term.clear, term.normal_screen, term.show_cursor, term.mouse_off, term.mouse_direct_off, term.title())
	term.echo(True)
	os.kill(os.getpid(), signal.SIGSTOP)


def now_awake(signum, frame):
	"""Set terminal settings and restart background input read.

	Used on STOP interruption signal.
	"""
	Draw.now(term.alt_screen, term.clear, term.hide_cursor, term.mouse_on, term.title("BpyTOP"))
	term.echo(False)
	controller.start()
	term.refresh()
	Box.calc_sizes()
	Box.draw_bg()
	collector.start()


def quit_sigint(signum, frame):
	"""SIGINT redirection to clean_quit()"""
	clean_quit()


def clean_quit(errcode: int = 0, errmsg: str = "", thread: bool = False):
	"""Stop background input read, save current config and reset terminal settings before quitting"""
	global THREAD_ERROR
	if thread:
		THREAD_ERROR = errcode
		interrupt_main()
		return
	if THREAD_ERROR: errcode = THREAD_ERROR
	controller.stop()
	collector.stop()
	if not errcode: CONFIG.save_config()
	Draw.now(term.clear, term.normal_screen, term.show_cursor, term.mouse_off, term.mouse_direct_off, term.title())
	term.echo(True)
	if errcode == 0:
		errlog.info(f'Exiting. Runtime {timedelta(seconds=round(time() - SELF_START, 0))} \n')
	else:
		errlog.warning(f'Exiting with errorcode ({errcode}). Runtime {timedelta(seconds=round(time() - SELF_START, 0))} \n')
		if not errmsg: errmsg = f'Bpytop exited with errorcode ({errcode}). See {CONFIG_DIR}/error.log for more information!'
	if errmsg: print(errmsg)

	raise SystemExit(errcode)


def floating_humanizer(value: Union[float, int], bit: bool = False, per_second: bool = False, start: int = 0, short: bool = False) -> str:
	'''Scales up in steps of 1024 to highest possible unit and returns string with unit suffixed
	* bit=True or defaults to bytes
	* start=int to set 1024 multiplier starting unit
	* short=True always returns 0 decimals and shortens unit to 1 character
	'''
	out: str = ""
	mult: int = 8 if bit else 1
	selector: int = start
	unit: Tuple[str, ...] = UNITS["bit"] if bit else UNITS["byte"]

	if isinstance(value, float): value = round(value * 100 * mult)
	elif value > 0: value *= 100 * mult
	else: value = 0

	while len(f'{value}') > 5 and value >= 102400:
		value >>= 10
		if value < 100:
			out = f'{value}'
			break
		selector += 1
	else:
		if len(f'{value}') == 4 and selector > 0:
			out = f'{value}'[:-2] + "." + f'{value}'[-2]
		elif len(f'{value}') == 3 and selector > 0:
			out = f'{value}'[:-2] + "." + f'{value}'[-2:]
		elif len(f'{value}') >= 2:
			out = f'{value}'[:-2]
		else:
			out = f'{value}'


	if short:
		if "." in out:
			out = f'{round(float(out))}'
		if len(out) > 3:
			out = f'{int(out[0]) + 1}'
			selector += 1
	out += f'{"" if short else " "}{unit[selector][0] if short else unit[selector]}'
	if per_second: out += "ps" if bit else "/s"

	return out


def units_to_bytes(value: str) -> int:
	if not value: return 0
	out: int = 0
	mult: int = 0
	bit: bool = False
	value_i: int = 0
	units: Dict[str, int] = {"k" : 1, "m" : 2, "g" : 3}
	try:
		if value.lower().endswith("s"):
			value = value[:-1]
		if value.lower().endswith("bit"):
			bit = True
			value = value[:-3]
		elif value.lower().endswith("byte"):
			value = value[:-4]

		if value[-1].lower() in units:
			mult = units[value[-1].lower()]
			value = value[:-1]

		if "." in value and value.replace(".", "").isdigit():
			if mult > 0:
				value_i = round(float(value) * 1024)
				mult -= 1
			else:
				value_i = round(float(value))
		elif value.isdigit():
			value_i = int(value)

		if bit: value_i = round(value_i / 8)
		out = int(value_i) << (10 * mult)
	except ValueError:
		out = 0
	return out


def min_max(value: int, min_value: int=0, max_value: int=100) -> int:
	return max(min_value, min(value, max_value))


def readfile(file: str, default: str = "") -> str:
	out: Union[str, None] = None
	if os.path.isfile(file):
		try:
			with open(file, "r") as f:
				out = f.read().strip()
		except:
			pass
	return default if out is None else out


def process_keys(controller: Controller, latest_version):
	mouse_pos: Tuple[int, int] = (0, 0)
	filtered: bool = False
	global ARG_MODE

	while controller.has_key():
		key = controller.get()
		if key in ["mouse_scroll_up", "mouse_scroll_down", "mouse_click"]:
			mouse_pos = controller.get_mouse()
			if mouse_pos[0] >= ProcBox.x and mouse_pos[1] >= ProcBox.current_y + 1 and mouse_pos[1] < ProcBox.current_y + ProcBox.current_h - 1:
				pass
			elif key == "mouse_click":
				key = "mouse_unselect"
			else:
				key = "_null"

		if ProcBox.filtering:
			if key in ["enter", "mouse_click", "mouse_unselect"]:
				ProcBox.filtering = False
				collector.collect(Proccollector, redraw=True, only_draw=True)
				continue
			elif key in ["escape", "delete"]:
				Proccollector.search_filter = ""
				ProcBox.filtering = False
			elif len(key) == 1:
				Proccollector.search_filter += key
			elif key == "backspace" and len(Proccollector.search_filter) > 0:
				Proccollector.search_filter = Proccollector.search_filter[:-1]
			else:
				continue
			collector.collect(Proccollector, proc_interrupt=True, redraw=True)
			if filtered: collector.collect_done.wait(0.1)
			filtered = True
			continue


		if key == "_null":
			continue
		elif key == "q":
			clean_quit()
		elif key == "+" and CONFIG.update_ms + 100 <= 86399900:
			CONFIG.update_ms += 100
			Box.draw_update_ms()
		elif key == "-" and CONFIG.update_ms - 100 >= 100:
			CONFIG.update_ms -= 100
			Box.draw_update_ms()
		elif key in ["b", "n"]:
			Netcollector.switch(key)
		elif key in ["M", "escape"]:
			Menu.main_menu.show(latest_version)
		elif key in ["o", "f2"]:
			Menu.options_menu.show()
		elif key in ["h", "f1"]:
			Menu.help_menu.show()
		elif key == "z":
			Netcollector.reset = not Netcollector.reset
			collector.collect(Netcollector, redraw=True)
		elif key == "y":
			CONFIG.net_sync = not CONFIG.net_sync
			collector.collect(Netcollector, redraw=True)
		elif key == "a":
			Netcollector.auto_min = not Netcollector.auto_min
			Netcollector.net_min = {"download" : -1, "upload" : -1}
			collector.collect(Netcollector, redraw=True)
		elif key in ["left", "right"]:
			Proccollector.sorting(key)
		elif key == " " and CONFIG.proc_tree and ProcBox.selected > 0:
			if ProcBox.selected_pid in Proccollector.collapsed:
				Proccollector.collapsed[ProcBox.selected_pid] = not Proccollector.collapsed[
					ProcBox.selected_pid]
			collector.collect(Proccollector, interrupt=True, redraw=True)
		elif key == "e":
			CONFIG.proc_tree = not CONFIG.proc_tree
			collector.collect(Proccollector, interrupt=True, redraw=True)
		elif key == "r":
			CONFIG.proc_reversed = not CONFIG.proc_reversed
			collector.collect(Proccollector, interrupt=True, redraw=True)
		elif key == "c":
			CONFIG.proc_per_core = not CONFIG.proc_per_core
			collector.collect(Proccollector, interrupt=True, redraw=True)
		elif key == "g":
			CONFIG.mem_graphs = not CONFIG.mem_graphs
			collector.collect(Memcollector, interrupt=True, redraw=True)
		elif key == "s":
			collector.collect_idle.wait()
			CONFIG.swap_disk = not CONFIG.swap_disk
			collector.collect(Memcollector, interrupt=True, redraw=True)
		elif key == "f":
			ProcBox.filtering = True
			if not Proccollector.search_filter: ProcBox.start = 0
			collector.collect(Proccollector, redraw=True, only_draw=True)
		elif key == "m":
			if ARG_MODE:
				ARG_MODE = ""
			elif CONFIG.view_modes.index(CONFIG.view_mode) + 1 > len(CONFIG.view_modes) - 1:
				CONFIG.view_mode = CONFIG.view_modes[0]
			else:
				CONFIG.view_mode = CONFIG.view_modes[(CONFIG.view_modes.index(CONFIG.view_mode) + 1)]
			Box.proc_mode = True if CONFIG.view_mode == "proc" else False
			Box.stat_mode = True if CONFIG.view_mode == "stat" else False
			Draw.clear(saved=True)
			term.refresh(force=True)
		elif key.lower() in ["t", "k", "i"] and (ProcBox.selected > 0 or Proccollector.detailed):
			pid: int = ProcBox.selected_pid if ProcBox.selected > 0 else Proccollector.detailed_pid # type: ignore
			if psutil.pid_exists(pid):
				if key.lower() == "t": sig = signal.SIGTERM
				elif key.lower() == "k": sig = signal.SIGKILL
				elif key.lower() == "i": sig = signal.SIGINT
				try:
					os.kill(pid, sig)
				except Exception as e:
					errlog.error(f'Exception when sending signal {sig} to pid {pid}')
					errlog.exception(f'{e}')
		elif key == "delete" and Proccollector.search_filter:
			Proccollector.search_filter = ""
			collector.collect(Proccollector, proc_interrupt=True, redraw=True)
		elif key == "enter":
			if ProcBox.selected > 0 and Proccollector.detailed_pid != ProcBox.selected_pid and psutil.pid_exists(
				ProcBox.selected_pid):
				Proccollector.detailed = True
				ProcBox.last_selection = ProcBox.selected
				ProcBox.selected = 0
				Proccollector.detailed_pid = ProcBox.selected_pid
				ProcBox.resized = True
			elif Proccollector.detailed:
				ProcBox.selected = ProcBox.last_selection
				ProcBox.last_selection = 0
				Proccollector.detailed = False
				Proccollector.detailed_pid = None
				ProcBox.resized = True
			else:
				continue
			Proccollector.details = {}
			Proccollector.details_cpu = []
			Proccollector.details_mem = []
			Graphs.detailed_cpu = NotImplemented
			Graphs.detailed_mem = NotImplemented
			collector.collect(Proccollector, proc_interrupt=True, redraw=True)

		elif key in ["up", "down", "mouse_scroll_up", "mouse_scroll_down", "page_up", "page_down", "home", "end", "mouse_click", "mouse_unselect"]:
			ProcBox.selector(key, mouse_pos)
