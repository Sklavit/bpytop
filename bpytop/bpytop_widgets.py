import os

from math import ceil
import psutil
from typing import Dict, List, Tuple, Union

from bpytop.old_classes import (
	Graph, Graphs, Menu, Meters,
)
from bpytop.collectors import Cpucollector, Memcollector, Netcollector, Proccollector
from bpytop.old_functions import floating_humanizer, min_max, readfile
from engine.universe.terminal.terminal_engine import CursorChar, Draw, create_box
from engine.universe.terminal.terminal_widgets import Box, Fx, Meter, SubBox, Symbol
from bpytop2 import CPU_NAME, THEME


class CpuBox(Box, SubBox):
	name = "cpu"
	x = 1
	y = 1
	height_p = 32
	width_p = 100
	resized: bool = True
	redraw: bool = False
	buffer: str = "cpu"
	battery_percent: int = 1000
	battery_secs: int = 0
	battery_status: str = "Unknown"
	old_battery_pos = 0
	old_battery_len = 0
	battery_path: Union[str, None] = ""
	battery_clear: bool = False
	clock_block: bool = True
	Box.buffers.append(buffer)

	@classmethod
	def _calc_size(cls):
		cpu = Cpucollector
		height_p: int
		if cls.proc_mode: height_p = 20
		else: height_p = cls.height_p
		cls.width = round(term.width * cls.width_p / 100)
		cls.height = round(term.height * height_p / 100)
		if cls.height < 8: cls.height = 8
		Box._b_cpu_h = cls.height
		#THREADS = 64
		cls.box_columns = ceil((THREADS + 1) / (cls.height - 5))
		if cls.box_columns * (20 + 13 if cpu.got_sensors else 21) < cls.width - (cls.width // 3):
			cls.column_size = 2
			cls.box_width = (20 + 13 if cpu.got_sensors else 21) * cls.box_columns - ((cls.box_columns - 1) * 1)
		elif cls.box_columns * (15 + 6 if cpu.got_sensors else 15) < cls.width - (cls.width // 3):
			cls.column_size = 1
			cls.box_width = (15 + 6 if cpu.got_sensors else 15) * cls.box_columns - ((cls.box_columns - 1) * 1)
		elif cls.box_columns * (8 + 6 if cpu.got_sensors else 8) < cls.width - (cls.width // 3):
			cls.column_size = 0
		else:
			cls.box_columns = (cls.width - cls.width // 3) // (8 + 6 if cpu.got_sensors else 8); cls.column_size = 0

		if cls.column_size == 0: cls.box_width = (8 + 6 if cpu.got_sensors else 8) * cls.box_columns + 1

		cls.box_height = ceil(THREADS / cls.box_columns) + 4

		if cls.box_height > cls.height - 2: cls.box_height = cls.height - 2
		cls.box_x = (cls.width - 1) - cls.box_width
		cls.box_y = cls.y + ceil((cls.height - 2) / 2) - ceil(cls.box_height / 2) + 1

	@classmethod
	def _draw_bg(cls) -> str:
		if not "M" in key.mouse:
			key.mouse["M"] = [[cls.x + 10 + i, cls.y] for i in range(6)]
		return (f'{create_box(box=cls, line_color=THEME.cpu_box)}'
		f'{CursorChar.to(cls.y, cls.x + 10)}{THEME.cpu_box(Symbol.title_left)}{Fx.b}{THEME.hi_fg("M")}{THEME.title("enu")}{Fx.ub}{THEME.cpu_box(Symbol.title_right)}'
		f'{create_box(x=cls.box_x, y=cls.box_y, width=cls.box_width, height=cls.box_height, line_color=THEME.div_line, fill=False, title=CPU_NAME[:cls.box_width - 14] if not CONFIG.custom_cpu_name else CONFIG.custom_cpu_name[:cls.box_width - 14])}')

	@classmethod
	def battery_activity(cls) -> bool:
		if not hasattr(psutil, "sensors_battery") or psutil.sensors_battery() == None:
			if cls.battery_percent != 1000:
				cls.battery_clear = True
			return False

		if cls.battery_path == "":
			cls.battery_path = None
			if os.path.isdir("/sys/class/power_supply"):
				for directory in sorted(os.listdir("/sys/class/power_supply")):
					if directory.startswith('BAT') or 'battery' in directory.lower():
						cls.battery_path = f'/sys/class/power_supply/{directory}/'
						break

		return_true: bool = False
		percent: int = ceil(getattr(psutil.sensors_battery(), "percent", 0))
		if percent != cls.battery_percent:
			cls.battery_percent = percent
			return_true = True

		seconds: int = getattr(psutil.sensors_battery(), "secsleft", 0)
		if seconds != cls.battery_secs:
			cls.battery_secs = seconds
			return_true = True

		status: str = "not_set"
		if cls.battery_path:
			status = readfile(cls.battery_path + "status", default="not_set")
		if status == "not_set" and getattr(psutil.sensors_battery(), "power_plugged", None) == True:
			status = "Charging" if cls.battery_percent < 100 else "Full"
		elif status == "not_set" and getattr(psutil.sensors_battery(), "power_plugged", None) == False:
			status = "Discharging"
		elif status == "not_set":
			status = "Unknown"
		if status != cls.battery_status:
			cls.battery_status = status
			return_true = True

		if return_true or cls.resized or cls.redraw or Menu.active:
			return True
		else:
			return False

	@classmethod
	def _draw_fg(cls):
		cpu = Cpucollector
		if cpu.redraw: cls.redraw = True
		out: str = ""
		out_misc: str = ""
		lavg: str = ""
		x, y, w, h = cls.x + 1, cls.y + 1, cls.width - 2, cls.height - 2
		bx, by, bw, bh = cls.box_x + 1, cls.box_y + 1, cls.box_width - 2, cls.box_height - 2
		hh: int = ceil(h / 2)

		if cls.resized or cls.redraw:
			if not "m" in key.mouse:
				key.mouse["m"] = [[cls.x + 16 + i, cls.y] for i in range(12)]
			out_misc += f'{CursorChar.to(cls.y, cls.x + 16)}{THEME.cpu_box(Symbol.title_left)}{Fx.b}{THEME.hi_fg("m")}{THEME.title}ode:{ARG_MODE or CONFIG.view_mode}{Fx.ub}{THEME.cpu_box(Symbol.title_right)}'
			Graphs.cpu["up"] = Graph(w - bw - 3, hh, THEME.gradient["cpu"], cpu.cpu_usage[0])
			Graphs.cpu["down"] = Graph(w - bw - 3, h - hh, THEME.gradient["cpu"], cpu.cpu_usage[0], invert=True)
			Meters.cpu = Meter(cpu.cpu_usage[0][-1], bw - (21 if cpu.got_sensors else 9), "cpu")
			if cls.column_size > 0:
				for n in range(THREADS):
					Graphs.cores[n] = Graph(5 * cls.column_size, 1, None, cpu.cpu_usage[n + 1])
			if cpu.got_sensors:
				Graphs.temps[0] = Graph(5, 1, None, cpu.cpu_temp[0], max_value=cpu.cpu_temp_crit, offset=-23)
				if cls.column_size > 1:
					for n in range(1, THREADS + 1):
						Graphs.temps[n] = Graph(5, 1, None, cpu.cpu_temp[n], max_value=cpu.cpu_temp_crit, offset=-23)
			Draw.buffer("cpu_misc", out_misc, only_save=True)

		if CONFIG.show_battery and cls.battery_activity():
			bat_out: str = ""
			if cls.battery_secs > 0:
				battery_time: str = f' {cls.battery_secs // 3600:02}:{(cls.battery_secs % 3600) // 60:02}'
			else:
				battery_time = ""
			if not hasattr(Meters, "battery") or cls.resized:
				Meters.battery = Meter(cls.battery_percent, 10, "cpu", invert=True)
			if cls.battery_status == "Charging":
				battery_symbol: str = "▲"
			elif cls.battery_status == "Discharging":
				battery_symbol = "▼"
			elif cls.battery_status in ["Full", "Not charging"]:
				battery_symbol = "■"
			else:
				battery_symbol = "○"
			battery_len: int = len(f'{CONFIG.update_ms}') + (11 if cls.width >= 100 else 0) + len(battery_time) + len(f'{cls.battery_percent}')
			battery_pos = cls.width - battery_len - 17
			if (battery_pos != cls.old_battery_pos or battery_len != cls.old_battery_len) and cls.old_battery_pos > 0 and not cls.resized:
				bat_out += f'{CursorChar.to(y - 1, cls.old_battery_pos)}{THEME.cpu_box(Symbol.h_line * (cls.old_battery_len + 4))}'
			cls.old_battery_pos, cls.old_battery_len = battery_pos, battery_len
			bat_out += (f'{CursorChar.to(y - 1, battery_pos)}{THEME.cpu_box(Symbol.title_left)}{Fx.b}{THEME.title}BAT{battery_symbol} {cls.battery_percent}%' +
						("" if cls.width < 100 else f' {Fx.ub}{Meters.battery(cls.battery_percent)}{Fx.b}') +
				f'{THEME.title}{battery_time}{Fx.ub}{THEME.cpu_box(Symbol.title_right)}')
			Draw.buffer("battery", f'{bat_out}{term.fg}', only_save=Menu.active)
		elif cls.battery_clear:
			out += f'{CursorChar.to(y - 1, cls.old_battery_pos)}{THEME.cpu_box(Symbol.h_line * (cls.old_battery_len + 4))}'
			cls.battery_clear = False
			cls.battery_percent = 1000
			cls.battery_secs = 0
			cls.battery_status = "Unknown"
			cls.old_battery_pos = 0
			cls.old_battery_len = 0
			cls.battery_path = ""
			Draw.clear("battery", saved=True)

		cx = cy = cc = 0
		ccw = (bw + 1) // cls.box_columns
		if cpu.cpu_freq:
			freq: str = f'{cpu.cpu_freq} Mhz' if cpu.cpu_freq < 1000 else f'{float(cpu.cpu_freq / 1000):.1f} GHz'
			out += f'{CursorChar.to(by - 1, bx + bw - 9)}{THEME.div_line(Symbol.title_left)}{Fx.b}{THEME.title(freq)}{Fx.ub}{THEME.div_line(Symbol.title_right)}'
		out += (f'{CursorChar.to(y, x)}{Graphs.cpu["up"](None if cls.resized else cpu.cpu_usage[0][-1])}{CursorChar.to(y + hh, x)}{Graphs.cpu["down"](None if cls.resized else cpu.cpu_usage[0][-1])}'
				f'{THEME.main_fg}{CursorChar.to(by + cy, bx + cx)}{Fx.b}{"CPU "}{Fx.ub}{Meters.cpu(cpu.cpu_usage[0][-1])}'
				f'{THEME.gradient["cpu"][cpu.cpu_usage[0][-1]]}{cpu.cpu_usage[0][-1]:>4}{THEME.main_fg}%')
		if cpu.got_sensors:
				out += (f'{THEME.inactive_fg} ⡀⡀⡀⡀⡀{CursorChar.l(5)}{THEME.gradient["temp"][min_max(cpu.cpu_temp[0][-1], 0, cpu.cpu_temp_crit) * 100 // cpu.cpu_temp_crit]}{Graphs.temps[0](None if cls.resized else cpu.cpu_temp[0][-1])}'
						f'{cpu.cpu_temp[0][-1]:>4}{THEME.main_fg}°C')

		cy += 1
		for n in range(1, THREADS + 1):
			out += f'{THEME.main_fg}{CursorChar.to(by + cy, bx + cx)}{Fx.b + "C" + Fx.ub if THREADS < 100 else ""}{str(n):<{2 if cls.column_size == 0 else 3}}'
			if cls.column_size > 0:
				out += f'{THEME.inactive_fg}{"⡀" * (5 * cls.column_size)}{CursorChar.l(5 * cls.column_size)}{THEME.gradient["cpu"][cpu.cpu_usage[n][-1]]}{Graphs.cores[n - 1](None if cls.resized else cpu.cpu_usage[n][-1])}'
			else:
				out += f'{THEME.gradient["cpu"][cpu.cpu_usage[n][-1]]}'
			out += f'{cpu.cpu_usage[n][-1]:>{3 if cls.column_size < 2 else 4}}{THEME.main_fg}%'
			if cpu.got_sensors:
				if cls.column_size > 1:
					out += f'{THEME.inactive_fg} ⡀⡀⡀⡀⡀{CursorChar.l(5)}{THEME.gradient["temp"][100 if cpu.cpu_temp[n][-1] >= cpu.cpu_temp_crit else (cpu.cpu_temp[n][-1] * 100 // cpu.cpu_temp_crit)]}{Graphs.temps[n](None if cls.resized else cpu.cpu_temp[n][-1])}'
				else:
					out += f'{THEME.gradient["temp"][100 if cpu.cpu_temp[n][-1] >= cpu.cpu_temp_crit else (cpu.cpu_temp[n][-1] * 100 // cpu.cpu_temp_crit)]}'
				out += f'{cpu.cpu_temp[n][-1]:>4}{THEME.main_fg}°C'
			out += f'{THEME.div_line(Symbol.v_line)}'
			cy += 1
			if cy > ceil(THREADS/cls.box_columns) and n != THREADS:
				cc += 1; cy = 1; cx = ccw * cc
				if cc == cls.box_columns: break

		if cy < bh - 1: cy = bh - 1

		if cy < bh and cc < cls.box_columns:
			if cls.column_size == 2 and cpu.got_sensors:
				lavg = f' Load AVG:  {"   ".join(str(l) for l in cpu.load_avg):^19.19}'
			elif cls.column_size == 2 or (cls.column_size == 1 and cpu.got_sensors):
				lavg = f'LAV: {" ".join(str(l) for l in cpu.load_avg):^14.14}'
			elif cls.column_size == 1 or (cls.column_size == 0 and cpu.got_sensors):
				lavg = f'L {" ".join(str(round(l, 1)) for l in cpu.load_avg):^11.11}'
			else:
				lavg = f'{" ".join(str(round(l, 1)) for l in cpu.load_avg[:2]):^7.7}'
			out += f'{CursorChar.to(by + cy, bx + cx)}{THEME.main_fg}{lavg}{THEME.div_line(Symbol.v_line)}'

		out += f'{CursorChar.to(y + h - 1, x + 1)}{THEME.graph_text}up {cpu.uptime}'


		Draw.buffer(cls.buffer, f'{out_misc}{out}{term.fg}', only_save=Menu.active)
		cls.resized = cls.redraw = cls.clock_block = False


class MemBox(Box):
	name = "mem"
	height_p = 38
	width_p = 45
	x = 1
	y = 1
	mem_meter: int = 0
	mem_size: int = 0
	disk_meter: int = 0
	divider: int = 0
	mem_width: int = 0
	disks_width: int = 0
	graph_height: int
	resized: bool = True
	redraw: bool = False
	buffer: str = "mem"
	swap_on: bool = CONFIG.show_swap
	Box.buffers.append(buffer)
	mem_names: List[str] = ["used", "available", "cached", "free"]
	swap_names: List[str] = ["used", "free"]

	@classmethod
	def _calc_size(cls):
		width_p: int; height_p: int
		if cls.stat_mode:
			width_p, height_p = 100, cls.height_p
		else:
			width_p, height_p = cls.width_p, cls.height_p
		cls.width = round(term.width * width_p / 100)
		cls.height = round(term.height * height_p / 100) + 1
		Box._b_mem_h = cls.height
		cls.y = Box._b_cpu_h + 1
		if CONFIG.show_disks:
			cls.mem_width = ceil((cls.width - 3) / 2)
			cls.disks_width = cls.width - cls.mem_width - 3
			if cls.mem_width + cls.disks_width < cls.width - 2: cls.mem_width += 1
			cls.divider = cls.x + cls.mem_width
		else:
			cls.mem_width = cls.width - 1

		item_height: int = 6 if cls.swap_on and not CONFIG.swap_disk else 4
		if cls.height - (3 if cls.swap_on and not CONFIG.swap_disk else 2) > 2 * item_height: cls.mem_size = 3
		elif cls.mem_width > 25: cls.mem_size = 2
		else: cls.mem_size = 1

		cls.mem_meter = cls.width - (cls.disks_width if CONFIG.show_disks else 0) - (9 if cls.mem_size > 2 else 20)
		if cls.mem_size == 1: cls.mem_meter += 6
		if cls.mem_meter < 1: cls.mem_meter = 0

		if CONFIG.mem_graphs:
			cls.graph_height = round(((cls.height - (2 if cls.swap_on and not CONFIG.swap_disk else 1)) - (2 if cls.mem_size == 3 else 1) * item_height) / item_height)
			if cls.graph_height == 0: cls.graph_height = 1
			if cls.graph_height > 1: cls.mem_meter += 6
		else:
			cls.graph_height = 0

		if CONFIG.show_disks:
			cls.disk_meter = cls.width - cls.mem_width - 23
			if cls.disks_width < 25:
				cls.disk_meter += 10
			if cls.disk_meter < 1: cls.disk_meter = 0

	@classmethod
	def _draw_bg(cls) -> str:
		if cls.proc_mode: return ""
		out: str = ""
		out += f'{create_box(box=cls, line_color=THEME.mem_box)}'
		if CONFIG.show_disks:
			out += (f'{CursorChar.to(cls.y, cls.divider + 2)}{THEME.mem_box(Symbol.title_left)}{Fx.b}{THEME.title("disks")}{Fx.ub}{THEME.mem_box(Symbol.title_right)}'
					f'{CursorChar.to(cls.y, cls.divider)}{THEME.mem_box(Symbol.div_up)}'
					f'{CursorChar.to(cls.y + cls.height - 1, cls.divider)}{THEME.mem_box(Symbol.div_down)}{THEME.div_line}'
					f'{"".join(f"{CursorChar.to(cls.y + i, cls.divider)}{Symbol.v_line}" for i in range(1, cls.height - 1))}')
		return out

	@classmethod
	def _draw_fg(cls):
		if cls.proc_mode: return
		mem = Memcollector
		if mem.redraw: cls.redraw = True
		out: str = ""
		out_misc: str = ""
		gbg: str = ""
		gmv: str = ""
		gli: str = ""
		x, y, w, h = cls.x + 1, cls.y + 1, cls.width - 2, cls.height - 2
		if cls.resized or cls.redraw:
			cls._calc_size()
			out_misc += cls._draw_bg()
			Meters.mem = {}
			Meters.swap = {}
			Meters.disks_used = {}
			Meters.disks_free = {}
			if cls.mem_meter > 0:
				for name in cls.mem_names:
					if CONFIG.mem_graphs:
						Meters.mem[name] = Graph(cls.mem_meter, cls.graph_height, THEME.gradient[name], mem.vlist[name])
					else:
						Meters.mem[name] = Meter(mem.percent[name], cls.mem_meter, name)
				if cls.swap_on:
					for name in cls.swap_names:
						if CONFIG.mem_graphs and not CONFIG.swap_disk:
							Meters.swap[name] = Graph(cls.mem_meter, cls.graph_height, THEME.gradient[name], mem.swap_vlist[name])
						elif CONFIG.swap_disk and CONFIG.show_disks:
							Meters.disks_used["__swap"] = Meter(mem.swap_percent["used"], cls.disk_meter, "used")
							if len(mem.disks) * 3 <= h + 1:
								Meters.disks_free["__swap"] = Meter(mem.swap_percent["free"], cls.disk_meter, "free")
							break
						else:
							Meters.swap[name] = Meter(mem.swap_percent[name], cls.mem_meter, name)
			if cls.disk_meter > 0:
				for n, name in enumerate(mem.disks.keys()):
					if n * 2 > h: break
					Meters.disks_used[name] = Meter(mem.disks[name]["used_percent"], cls.disk_meter, "used")
					if len(mem.disks) * 3 <= h + 1:
						Meters.disks_free[name] = Meter(mem.disks[name]["free_percent"], cls.disk_meter, "free")
			if not "g" in key.mouse:
				key.mouse["g"] = [[x + cls.mem_width - 8 + i, y-1] for i in range(5)]
			out_misc += (f'{CursorChar.to(y - 1, x + cls.mem_width - 9)}{THEME.mem_box(Symbol.title_left)}{Fx.b if CONFIG.mem_graphs else ""}'
				f'{THEME.hi_fg("g")}{THEME.title("raph")}{Fx.ub}{THEME.mem_box(Symbol.title_right)}')
			if CONFIG.show_disks:
				if not "s" in key.mouse:
					key.mouse["s"] = [[x + w - 6 + i, y-1] for i in range(4)]
				out_misc += (f'{CursorChar.to(y - 1, x + w - 7)}{THEME.mem_box(Symbol.title_left)}{Fx.b if CONFIG.swap_disk else ""}'
				f'{THEME.hi_fg("s")}{THEME.title("wap")}{Fx.ub}{THEME.mem_box(Symbol.title_right)}')

			if collector.collect_interrupt: return
			Draw.buffer("mem_misc", out_misc, only_save=True)
		try:
			#* Mem
			cx = 1; cy = 1

			out += f'{CursorChar.to(y, x + 1)}{THEME.title}{Fx.b}Total:{mem.string["total"]:>{cls.mem_width - 9}}{Fx.ub}{THEME.main_fg}'
			if cls.graph_height > 0:
				gli = f'{CursorChar.l(2)}{THEME.mem_box(Symbol.title_right)}{THEME.div_line}{Symbol.h_line * (cls.mem_width - 1)}{"" if CONFIG.show_disks else THEME.mem_box}{Symbol.title_left}{CursorChar.l(cls.mem_width - 1)}{THEME.title}'
			if cls.graph_height >= 2:
				gbg = f'{CursorChar.l(1)}'
				gmv = f'{CursorChar.l(cls.mem_width - 2)}{CursorChar.u(cls.graph_height - 1)}'

			big_mem: bool = True if cls.mem_width > 21 else False
			for name in cls.mem_names:
				if collector.collect_interrupt: return
				if cls.mem_size > 2:
					out += (f'{CursorChar.to(y + cy, x + cx)}{gli}{name.capitalize()[:None if big_mem else 5] + ":":<{1 if big_mem else 6.6}}{CursorChar.to(y + cy, x + cx + cls.mem_width - 3 - (len(mem.string[name])))}{Fx.trans(mem.string[name])}'
							f'{CursorChar.to(y + cy + 1, x + cx)}{gbg}{Meters.mem[name](None if cls.resized else mem.percent[name])}{gmv}{str(mem.percent[name]) + "%":>4}')
					cy += 2 if not cls.graph_height else cls.graph_height + 1
				else:
					out += f'{CursorChar.to(y + cy, x + cx)}{name.capitalize():{5.5 if cls.mem_size > 1 else 1.1}} {gbg}{Meters.mem[name](None if cls.resized else mem.percent[name])}{mem.string[name][:None if cls.mem_size > 1 else -2]:>{9 if cls.mem_size > 1 else 7}}'
					cy += 1 if not cls.graph_height else cls.graph_height
			#* Swap
			if cls.swap_on and CONFIG.show_swap and not CONFIG.swap_disk and mem.swap_string:
				if h - cy > 5:
					if cls.graph_height > 0: out += f'{CursorChar.to(y + cy, x + cx)}{gli}'
					cy += 1

				out += f'{CursorChar.to(y + cy, x + cx)}{THEME.title}{Fx.b}Swap:{mem.swap_string["total"]:>{cls.mem_width - 8}}{Fx.ub}{THEME.main_fg}'
				cy += 1
				for name in cls.swap_names:
					if collector.collect_interrupt: return
					if cls.mem_size > 2:
						out += (f'{CursorChar.to(y + cy, x + cx)}{gli}{name.capitalize()[:None if big_mem else 5] + ":":<{1 if big_mem else 6.6}}{CursorChar.to(y + cy, x + cx + cls.mem_width - 3 - (len(mem.swap_string[name])))}{Fx.trans(mem.swap_string[name])}'
								f'{CursorChar.to(y + cy + 1, x + cx)}{gbg}{Meters.swap[name](None if cls.resized else mem.swap_percent[name])}{gmv}{str(mem.swap_percent[name]) + "%":>4}')
						cy += 2 if not cls.graph_height else cls.graph_height + 1
					else:
						out += f'{CursorChar.to(y + cy, x + cx)}{name.capitalize():{5.5 if cls.mem_size > 1 else 1.1}} {gbg}{Meters.swap[name](None if cls.resized else mem.swap_percent[name])}{mem.swap_string[name][:None if cls.mem_size > 1 else -2]:>{9 if cls.mem_size > 1 else 7}}'; cy += 1 if not cls.graph_height else cls.graph_height

			if cls.graph_height > 0 and not cy == h: out += f'{CursorChar.to(y + cy, x + cx)}{gli}'

			#* Disks
			if CONFIG.show_disks and mem.disks:
				cx = x + cls.mem_width - 1; cy = 0
				big_disk: bool = True if cls.disks_width >= 25 else False
				gli = f'{CursorChar.l(2)}{THEME.div_line}{Symbol.title_right}{Symbol.h_line * cls.disks_width}{THEME.mem_box}{Symbol.title_left}{CursorChar.l(cls.disks_width - 1)}'
				for name, item in mem.disks.items():
					if collector.collect_interrupt: return
					if not name in Meters.disks_used:
						continue
					if cy > h - 2: break
					out += Fx.trans(f'{CursorChar.to(y + cy, x + cx)}{gli}{THEME.title}{Fx.b}{item["name"]:{cls.disks_width - 2}.12}{CursorChar.to(y + cy, x + cx + cls.disks_width - 11)}{item["total"][:None if big_disk else -2]:>9}')
					out += f'{CursorChar.to(y + cy, x + cx + (cls.disks_width // 2) - (len(item["io"]) // 2) - 2)}{Fx.ub}{THEME.main_fg}{item["io"]}{Fx.ub}{THEME.main_fg}{CursorChar.to(y + cy + 1, x + cx)}'
					out += f'Used:{str(item["used_percent"]) + "%":>4} ' if big_disk else "U "
					out += f'{Meters.disks_used[name]}{item["used"][:None if big_disk else -2]:>{9 if big_disk else 7}}'
					cy += 2

					if len(mem.disks) * 3 <= h + 1:
						if cy > h - 1: break
						out += CursorChar.to(y + cy, x + cx)
						out += f'Free:{str(item["free_percent"]) + "%":>4} ' if big_disk else f'{"F "}'
						out += f'{Meters.disks_free[name]}{item["free"][:None if big_disk else -2]:>{9 if big_disk else 7}}'
						cy += 1
						if len(mem.disks) * 4 <= h + 1: cy += 1
		except (keyError, TypeError):
			return
		Draw.buffer(cls.buffer, f'{out_misc}{out}{term.fg}', only_save=Menu.active)
		cls.resized = cls.redraw = False


class NetBox(Box, SubBox):
	name = "net"
	height_p = 30
	width_p = 45
	x = 1
	y = 1
	resized: bool = True
	redraw: bool = True
	graph_height: Dict[str, int] = {}
	symbols: Dict[str, str] = {"download" : "▼", "upload" : "▲"}
	buffer: str = "net"

	Box.buffers.append(buffer)

	@classmethod
	def _calc_size(cls):
		width_p: int
		if cls.stat_mode:
			width_p = 100
		else:
			width_p = cls.width_p
		cls.width = round(term.width * width_p / 100)
		cls.height = term.height - Box._b_cpu_h - Box._b_mem_h
		cls.y = term.height - cls.height + 1
		cls.box_width = 27 if cls.width > 45 else 19
		cls.box_height = 9 if cls.height > 10 else cls.height - 2
		cls.box_x = cls.width - cls.box_width - 1
		cls.box_y = cls.y + ((cls.height - 2) // 2) - cls.box_height // 2 + 1
		cls.graph_height["download"] = round((cls.height - 2) / 2)
		cls.graph_height["upload"] = cls.height - 2 - cls.graph_height["download"]
		cls.redraw = True

	@classmethod
	def _draw_bg(cls) -> str:
		if cls.proc_mode: return ""
		return f'{create_box(box=cls, line_color=THEME.net_box)}\
		{create_box(x=cls.box_x, y=cls.box_y, width=cls.box_width, height=cls.box_height, line_color=THEME.div_line, fill=False, title="Download", title2="Upload")}'

	@classmethod
	def _draw_fg(cls):
		if cls.proc_mode: return
		net = Netcollector
		if net.redraw: cls.redraw = True
		if not net.nic: return
		out: str = ""
		out_misc: str = ""
		x, y, w, h = cls.x + 1, cls.y + 1, cls.width - 2, cls.height - 2
		bx, by, bw, bh = cls.box_x + 1, cls.box_y + 1, cls.box_width - 2, cls.box_height - 2
		reset: bool = bool(net.stats[net.nic]["download"]["offset"])

		if cls.resized or cls.redraw:
			out_misc += cls._draw_bg()
			if not "b" in key.mouse:
				key.mouse["b"] = [[x+w - len(net.nic[:10]) - 9 + i, y-1] for i in range(4)]
				key.mouse["n"] = [[x+w - 5 + i, y-1] for i in range(4)]
				key.mouse["z"] = [[x+w - len(net.nic[:10]) - 14 + i, y-1] for i in range(4)]


			out_misc += (f'{CursorChar.to(y - 1, x + w - 25)}{THEME.net_box}{Symbol.h_line * (10 - len(net.nic[:10]))}{Symbol.title_left}{Fx.b if reset else ""}{THEME.hi_fg("z")}{THEME.title("ero")}'
				f'{Fx.ub}{THEME.net_box(Symbol.title_right)}{term.fg}'
				f'{THEME.net_box}{Symbol.title_left}{Fx.b}{THEME.hi_fg("<b")} {THEME.title(net.nic[:10])} {THEME.hi_fg("n>")}{Fx.ub}{THEME.net_box(Symbol.title_right)}{term.fg}')
			if w - len(net.nic[:10]) - 20 > 6:
				if not "a" in key.mouse: key.mouse["a"] = [[x+w - 20 - len(net.nic[:10]) + i, y-1] for i in range(4)]
				out_misc += (f'{CursorChar.to(y - 1, x + w - 21 - len(net.nic[:10]))}{THEME.net_box(Symbol.title_left)}{Fx.b if net.auto_min else ""}{THEME.hi_fg("a")}{THEME.title("uto")}'
				f'{Fx.ub}{THEME.net_box(Symbol.title_right)}{term.fg}')
			if w - len(net.nic[:10]) - 20 > 13:
				if not "y" in key.mouse: key.mouse["y"] = [[x+w - 26 - len(net.nic[:10]) + i, y-1] for i in range(4)]
				out_misc += (f'{CursorChar.to(y - 1, x + w - 27 - len(net.nic[:10]))}{THEME.net_box(Symbol.title_left)}{Fx.b if CONFIG.net_sync else ""}{THEME.title("s")}{THEME.hi_fg("y")}{THEME.title("nc")}'
				f'{Fx.ub}{THEME.net_box(Symbol.title_right)}{term.fg}')
			Draw.buffer("net_misc", out_misc, only_save=True)

		cy = 0
		for direction in ["download", "upload"]:
			strings = net.strings[net.nic][direction]
			stats = net.stats[net.nic][direction]
			if cls.redraw: stats["redraw"] = True
			if stats["redraw"] or cls.resized:
				Graphs.net[direction] = Graph(w - bw - 3, cls.graph_height[direction], THEME.gradient[direction], stats["speed"], max_value=net.sync_top if CONFIG.net_sync else stats["graph_top"],
					invert=False if direction == "download" else True, color_max_value=net.net_min.get(direction) if CONFIG.net_color_fixed else None)
			out += f'{CursorChar.to(y if direction == "download" else y + cls.graph_height["download"], x)}{Graphs.net[direction](None if stats["redraw"] else stats["speed"][-1])}'

			out += (f'{CursorChar.to(by + cy, bx)}{THEME.main_fg}{cls.symbols[direction]} {strings["byte_ps"]:<10.10}' +
					("" if bw < 20 else f'{CursorChar.to(by + cy, bx + bw - 12)}{"(" + strings["bit_ps"] + ")":>12.12}'))
			cy += 1 if bh != 3 else 2
			if bh >= 6:
				out += f'{CursorChar.to(by + cy, bx)}{cls.symbols[direction]} {"Top:"}{CursorChar.to(by + cy, bx + bw - 12)}{"(" + strings["top"] + ")":>12.12}'
				cy += 1
			if bh >= 4:
				out += f'{CursorChar.to(by + cy, bx)}{cls.symbols[direction]} {"Total:"}{CursorChar.to(by + cy, bx + bw - 10)}{strings["total"]:>10.10}'
				if bh > 2 and bh % 2: cy += 2
				else: cy += 1
			stats["redraw"] = False

		out += (f'{CursorChar.to(y, x)}{THEME.graph_text(net.sync_string if CONFIG.net_sync else net.strings[net.nic]["download"]["graph_top"])}'
				f'{CursorChar.to(y + h - 1, x)}{THEME.graph_text(net.sync_string if CONFIG.net_sync else net.strings[net.nic]["upload"]["graph_top"])}')

		Draw.buffer(cls.buffer, f'{out_misc}{out}{term.fg}', only_save=Menu.active)
		cls.redraw = cls.resized = False


class ProcBox(Box):
	name = "proc"
	height_p = 68
	width_p = 55
	x = 1
	y = 1
	current_y: int = 0
	current_h: int = 0
	select_max: int = 0
	selected: int = 0
	selected_pid: int = 0
	last_selection: int = 0
	filtering: bool = False
	moved: bool = False
	start: int = 1
	count: int = 0
	s_len: int = 0
	detailed: bool = False
	detailed_x: int = 0
	detailed_y: int = 0
	detailed_width: int = 0
	detailed_height: int = 8
	resized: bool = True
	redraw: bool = True
	buffer: str = "proc"
	pid_counter: Dict[int, int] = {}
	Box.buffers.append(buffer)

	@classmethod
	def _calc_size(cls):
		width_p: int; height_p: int
		if cls.proc_mode:
			width_p, height_p = 100, 80
		else:
			width_p, height_p = cls.width_p, cls.height_p
		cls.width = round(term.width * width_p / 100)
		cls.height = round(term.height * height_p / 100)
		if cls.height + Box._b_cpu_h > term.height: cls.height = term.height - Box._b_cpu_h
		cls.x = term.width - cls.width + 1
		cls.y = Box._b_cpu_h + 1
		cls.current_y = cls.y
		cls.current_h = cls.height
		cls.select_max = cls.height - 3
		cls.redraw = True
		cls.resized = True

	@classmethod
	def _draw_bg(cls) -> str:
		if cls.stat_mode: return ""
		return create_box(box=cls, line_color=THEME.proc_box)

	@classmethod
	def selector(cls, key: str, mouse_pos: Tuple[int, int] = (0, 0)):
		old: Tuple[int, int] = (cls.start, cls.selected)
		new_sel: int
		if key == "up":
			if cls.selected == 1 and cls.start > 1:
				cls.start -= 1
			elif cls.selected == 1:
				cls.selected = 0
			elif cls.selected > 1:
				cls.selected -= 1
		elif key == "down":
			if cls.selected == 0 and Proccollector.detailed and cls.last_selection:
				cls.selected = cls.last_selection
				cls.last_selection = 0
			if cls.selected == cls.select_max and cls.start < Proccollector.num_procs - cls.select_max + 1:
				cls.start += 1
			elif cls.selected < cls.select_max:
				cls.selected += 1
		elif key == "mouse_scroll_up" and cls.start > 1:
			cls.start -= 5
		elif key == "mouse_scroll_down" and cls.start < Proccollector.num_procs - cls.select_max + 1:
			cls.start += 5
		elif key == "page_up" and cls.start > 1:
			cls.start -= cls.select_max
		elif key == "page_down" and cls.start < Proccollector.num_procs - cls.select_max + 1:
			cls.start += cls.select_max
		elif key == "home":
			if cls.start > 1: cls.start = 1
			elif cls.selected > 0: cls.selected = 0
		elif key == "end":
			if cls.start < Proccollector.num_procs - cls.select_max + 1: cls.start = Proccollector.num_procs - cls.select_max + 1
			elif cls.selected < cls.select_max: cls.selected = cls.select_max
		elif key == "mouse_click":
			if mouse_pos[0] > cls.x + cls.width - 4 and mouse_pos[1] > cls.current_y + 1 and mouse_pos[1] < cls.current_y + 1 + cls.select_max + 1:
				if mouse_pos[1] == cls.current_y + 2:
					cls.start = 1
				elif mouse_pos[1] == cls.current_y + 1 + cls.select_max:
					cls.start = Proccollector.num_procs - cls.select_max + 1
				else:
					cls.start = round((mouse_pos[1] - cls.current_y) * ((Proccollector.num_procs - cls.select_max - 2) / (cls.select_max - 2)))
			else:
				new_sel = mouse_pos[1] - cls.current_y - 1 if mouse_pos[1] >= cls.current_y - 1 else 0
				if new_sel > 0 and new_sel == cls.selected:
					key.list.insert(0, "enter")
					return
				elif new_sel > 0 and new_sel != cls.selected:
					if cls.last_selection: cls.last_selection = 0
					cls.selected = new_sel
		elif key == "mouse_unselect":
			cls.selected = 0

		if cls.start > Proccollector.num_procs - cls.select_max + 1 and Proccollector.num_procs > cls.select_max: cls.start = Proccollector.num_procs - cls.select_max + 1
		elif cls.start > Proccollector.num_procs: cls.start = Proccollector.num_procs
		if cls.start < 1: cls.start = 1
		if cls.selected > Proccollector.num_procs and Proccollector.num_procs < cls.select_max: cls.selected = Proccollector.num_procs
		elif cls.selected > cls.select_max: cls.selected = cls.select_max
		if cls.selected < 0: cls.selected = 0

		if old != (cls.start, cls.selected):
			cls.moved = True
			collector.collect(Proccollector, proc_interrupt=True, redraw=True, only_draw=True)


	@classmethod
	def _draw_fg(cls):
		if cls.stat_mode: return
		proc = Proccollector
		if proc.proc_interrupt: return
		if proc.redraw: cls.redraw = True
		out: str = ""
		out_misc: str = ""
		n: int = 0
		x, y, w, h = cls.x + 1, cls.current_y + 1, cls.width - 2, cls.current_h - 2
		prog_len: int; arg_len: int; val: int; c_color: str; m_color: str; t_color: str; sort_pos: int; tree_len: int; is_selected: bool; calc: int
		dgx: int; dgw: int; dx: int; dw: int; dy: int
		l_count: int = 0
		scroll_pos: int = 0
		killed: bool = True
		indent: str = ""
		offset: int = 0
		tr_show: bool = True
		usr_show: bool = True
		vals: List[str]
		g_color: str = ""
		s_len: int = 0
		if proc.search_filter: s_len = len(proc.search_filter[:10])
		loc_string: str = f'{cls.start + cls.selected - 1}/{proc.num_procs}'
		end: str = ""

		if proc.detailed:
			dgx, dgw = x, w // 3
			dw = w - dgw - 1
			if dw > 120:
				dw = 120
				dgw = w - 121
			dx = x + dgw + 2
			dy = cls.y + 1

		if w > 67:
			arg_len = w - 53 - (1 if proc.num_procs > cls.select_max else 0)
			prog_len = 15
		else:
			arg_len = 0
			prog_len = w - 38 - (1 if proc.num_procs > cls.select_max else 0)
			if prog_len < 15:
				tr_show = False
				prog_len += 5
			if prog_len < 12:
				usr_show = False
				prog_len += 9

		if CONFIG.proc_tree:
			tree_len = arg_len + prog_len + 6
			arg_len = 0

		#* Buttons and titles only redrawn if needed
		if cls.resized or cls.redraw:
			s_len += len(CONFIG.proc_sorting)
			if cls.resized or s_len != cls.s_len or proc.detailed:
				cls.s_len = s_len
				for k in ["e", "r", "c", "t", "k", "i", "enter", "left", " ", "f", "delete"]:
					if k in key.mouse: del key.mouse[k]
			if proc.detailed:
				killed = proc.details["killed"]
				main = THEME.main_fg if cls.selected == 0 and not killed else THEME.inactive_fg
				hi = THEME.hi_fg if cls.selected == 0 and not killed else THEME.inactive_fg
				title = THEME.title if cls.selected == 0 and not killed else THEME.inactive_fg
				if cls.current_y != cls.y + 8 or cls.resized or Graphs.detailed_cpu is NotImplemented:
					cls.current_y = cls.y + 8
					cls.current_h = cls.height - 8
					for i in range(7): out_misc += f'{CursorChar.to(dy + i, x)}{" " * w}'
					out_misc += (f'{CursorChar.to(dy + 7, x - 1)}{THEME.proc_box}{Symbol.title_right}{Symbol.h_line * w}{Symbol.title_left}'
					f'{CursorChar.to(dy + 7, x + 1)}{THEME.proc_box(Symbol.title_left)}{Fx.b}{THEME.title(cls.name)}{Fx.ub}{THEME.proc_box(Symbol.title_right)}{THEME.div_line}')
					for i in range(7):
						out_misc += f'{CursorChar.to(dy + i, dgx + dgw + 1)}{Symbol.v_line}'

				out_misc += (f'{CursorChar.to(dy - 1, x - 1)}{THEME.proc_box}{Symbol.left_up}{Symbol.h_line * w}{Symbol.right_up}'
					f'{CursorChar.to(dy - 1, dgx + dgw + 1)}{Symbol.div_up}'
					f'{CursorChar.to(dy - 1, x + 1)}{THEME.proc_box(Symbol.title_left)}{Fx.b}{THEME.title(str(proc.details["pid"]))}{Fx.ub}{THEME.proc_box(Symbol.title_right)}'
					f'{THEME.proc_box(Symbol.title_left)}{Fx.b}{THEME.title(proc.details["name"][:(dgw - 11)])}{Fx.ub}{THEME.proc_box(Symbol.title_right)}')

				if cls.selected == 0:
					key.mouse["enter"] = [[dx+dw-10 + i, dy-1] for i in range(7)]
				if cls.selected == 0 and not killed:
					key.mouse["t"] = [[dx+2 + i, dy-1] for i in range(9)]

				out_misc += (f'{CursorChar.to(dy - 1, dx + dw - 11)}{THEME.proc_box(Symbol.title_left)}{Fx.b}{title if cls.selected > 0 else THEME.title}close{Fx.ub} {main if cls.selected > 0 else THEME.main_fg}{Symbol.enter}{THEME.proc_box(Symbol.title_right)}'
					f'{CursorChar.to(dy - 1, dx + 1)}{THEME.proc_box(Symbol.title_left)}{Fx.b}{hi}t{title}erminate{Fx.ub}{THEME.proc_box(Symbol.title_right)}')
				if dw > 28:
					if cls.selected == 0 and not killed and not "k" in key.mouse: key.mouse["k"] = [[dx + 13 + i, dy-1] for i in range(4)]
					out_misc += f'{THEME.proc_box(Symbol.title_left)}{Fx.b}{hi}k{title}ill{Fx.ub}{THEME.proc_box(Symbol.title_right)}'
				if dw > 39:
					if cls.selected == 0 and not killed and not "i" in key.mouse: key.mouse["i"] = [[dx + 19 + i, dy-1] for i in range(9)]
					out_misc += f'{THEME.proc_box(Symbol.title_left)}{Fx.b}{hi}i{title}nterrupt{Fx.ub}{THEME.proc_box(Symbol.title_right)}'

				if Graphs.detailed_cpu is NotImplemented or cls.resized:
					Graphs.detailed_cpu = Graph(dgw+1, 7, THEME.gradient["cpu"], proc.details_cpu)
					Graphs.detailed_mem = Graph(dw // 3, 1, None, proc.details_mem)

				cls.select_max = cls.height - 11
				y = cls.y + 9
				h = cls.height - 10

			else:
				if cls.current_y != cls.y or cls.resized:
					cls.current_y = cls.y
					cls.current_h = cls.height
					y, h = cls.y + 1, cls.height - 2
					out_misc += (f'{CursorChar.to(y - 1, x - 1)}{THEME.proc_box}{Symbol.left_up}{Symbol.h_line * w}{Symbol.right_up}'
						f'{CursorChar.to(y - 1, x + 1)}{THEME.proc_box(Symbol.title_left)}{Fx.b}{THEME.title(cls.name)}{Fx.ub}{THEME.proc_box(Symbol.title_right)}'
						f'{CursorChar.to(y + 7, x - 1)}{THEME.proc_box(Symbol.v_line)}{CursorChar.r(w)}{THEME.proc_box(Symbol.v_line)}')
				cls.select_max = cls.height - 3


			sort_pos = x + w - len(CONFIG.proc_sorting) - 7
			if not "left" in key.mouse:
				key.mouse["left"] = [[sort_pos + i, y-1] for i in range(3)]
				key.mouse["right"] = [[sort_pos + len(CONFIG.proc_sorting) + 3 + i, y-1] for i in range(3)]


			out_misc += (f'{CursorChar.to(y - 1, x + 8)}{THEME.proc_box(Symbol.h_line * (w - 9))}' +
						 ("" if not proc.detailed else f"{CursorChar.to(dy + 7, dgx + dgw + 1)}{THEME.proc_box(Symbol.div_down)}") +
				f'{CursorChar.to(y - 1, sort_pos)}{THEME.proc_box(Symbol.title_left)}{Fx.b}{THEME.hi_fg("<")} {THEME.title(CONFIG.proc_sorting)} '
				f'{THEME.hi_fg(">")}{Fx.ub}{THEME.proc_box(Symbol.title_right)}')


			if w > 29 + s_len:
				if not "e" in key.mouse: key.mouse["e"] = [[sort_pos - 5 + i, y-1] for i in range(4)]
				out_misc += (f'{CursorChar.to(y - 1, sort_pos - 6)}{THEME.proc_box(Symbol.title_left)}{Fx.b if CONFIG.proc_tree else ""}'
					f'{THEME.title("tre")}{THEME.hi_fg("e")}{Fx.ub}{THEME.proc_box(Symbol.title_right)}')
			if w > 37 + s_len:
				if not "r" in key.mouse: key.mouse["r"] = [[sort_pos - 14 + i, y-1] for i in range(7)]
				out_misc += (f'{CursorChar.to(y - 1, sort_pos - 15)}{THEME.proc_box(Symbol.title_left)}{Fx.b if CONFIG.proc_reversed else ""}'
					f'{THEME.hi_fg("r")}{THEME.title("everse")}{Fx.ub}{THEME.proc_box(Symbol.title_right)}')
			if w > 47 + s_len:
				if not "c" in key.mouse: key.mouse["c"] = [[sort_pos - 24 + i, y-1] for i in range(8)]
				out_misc += (f'{CursorChar.to(y - 1, sort_pos - 25)}{THEME.proc_box(Symbol.title_left)}{Fx.b if CONFIG.proc_per_core else ""}'
					f'{THEME.title("per-")}{THEME.hi_fg("c")}{THEME.title("ore")}{Fx.ub}{THEME.proc_box(Symbol.title_right)}')

			if not "f" in key.mouse or cls.resized: key.mouse["f"] = [[x+5 + i, y-1] for i in range(6 if not proc.search_filter else 2 + len(proc.search_filter[-10:]))]
			if proc.search_filter:
				if not "delete" in key.mouse: key.mouse["delete"] = [[x+11 + len(proc.search_filter[-10:]) + i, y-1] for i in range(3)]
			elif "delete" in key.mouse:
				del key.mouse["delete"]
			out_misc += (f'{CursorChar.to(y - 1, x + 7)}{THEME.proc_box(Symbol.title_left)}{Fx.b if cls.filtering or proc.search_filter else ""}{THEME.hi_fg("f")}{THEME.title}' +
						 ("ilter" if not proc.search_filter and not cls.filtering else f' {proc.search_filter[-(10 if w < 83 else w - 74):]}{(Fx.bl + "█" + Fx.ubl) if cls.filtering else THEME.hi_fg(" del")}') +
				f'{THEME.proc_box(Symbol.title_right)}')

			main = THEME.inactive_fg if cls.selected == 0 else THEME.main_fg
			hi = THEME.inactive_fg if cls.selected == 0 else THEME.hi_fg
			title = THEME.inactive_fg if cls.selected == 0 else THEME.title
			out_misc += (f'{CursorChar.to(y + h, x + 1)}{THEME.proc_box}{Symbol.h_line * (w - 4)}'
					f'{CursorChar.to(y + h, x + 1)}{THEME.proc_box(Symbol.title_left)}{main}{Symbol.up} {Fx.b}{THEME.main_fg("select")} {Fx.ub}'
					f'{THEME.inactive_fg if cls.selected == cls.select_max else THEME.main_fg}{Symbol.down}{THEME.proc_box(Symbol.title_right)}'
					f'{THEME.proc_box(Symbol.title_left)}{title}{Fx.b}info {Fx.ub}{main}{Symbol.enter}{THEME.proc_box(Symbol.title_right)}')
			if not "enter" in key.mouse: key.mouse["enter"] = [[x + 14 + i, y+h] for i in range(6)]
			if w - len(loc_string) > 34:
				if not "t" in key.mouse: key.mouse["t"] = [[x + 22 + i, y+h] for i in range(9)]
				out_misc += f'{THEME.proc_box(Symbol.title_left)}{Fx.b}{hi}t{title}erminate{Fx.ub}{THEME.proc_box(Symbol.title_right)}'
			if w - len(loc_string) > 40:
				if not "k" in key.mouse: key.mouse["k"] = [[x + 33 + i, y+h] for i in range(4)]
				out_misc += f'{THEME.proc_box(Symbol.title_left)}{Fx.b}{hi}k{title}ill{Fx.ub}{THEME.proc_box(Symbol.title_right)}'
			if w - len(loc_string) > 51:
				if not "i" in key.mouse: key.mouse["i"] = [[x + 39 + i, y+h] for i in range(9)]
				out_misc += f'{THEME.proc_box(Symbol.title_left)}{Fx.b}{hi}i{title}nterrupt{Fx.ub}{THEME.proc_box(Symbol.title_right)}'
			if CONFIG.proc_tree and w - len(loc_string) > 65:
				if not " " in key.mouse: key.mouse[" "] = [[x + 50 + i, y+h] for i in range(12)]
				out_misc += f'{THEME.proc_box(Symbol.title_left)}{Fx.b}{hi}spc {title}collapse{Fx.ub}{THEME.proc_box(Symbol.title_right)}'

			#* Processes labels
			selected: str = CONFIG.proc_sorting
			label: str
			if selected == "memory": selected = "mem"
			if selected == "threads" and not CONFIG.proc_tree and not arg_len: selected = "tr"
			if CONFIG.proc_tree:
				label = (f'{THEME.title}{Fx.b}{CursorChar.to(y, x)}{" Tree:":<{tree_len - 2}}' + (f'{"Threads: ":<9}' if tr_show else " " * 4) + (f'{"User:":<9}' if usr_show else "") + f'Mem%{"Cpu%":>11}{Fx.ub}{THEME.main_fg} ' +
						 (" " if proc.num_procs > cls.select_max else ""))
				if selected in ["pid", "program", "arguments"]: selected = "tree"
			else:
				label = (f'{THEME.title}{Fx.b}{CursorChar.to(y, x)}{"Pid:":>7} {"Program:" if prog_len > 8 else "Prg:":<{prog_len}}' + (f'{"Arguments:":<{arg_len - 4}}' if arg_len else "") +
						 ((f'{"Threads:":<9}' if arg_len else f'{"Tr:":^5}') if tr_show else "") + (f'{"User:":<9}' if usr_show else "") + f'Mem%{"Cpu%":>11}{Fx.ub}{THEME.main_fg} ' +
						 (" " if proc.num_procs > cls.select_max else ""))
				if selected == "program" and prog_len <= 8: selected = "prg"
			selected = selected.split(" ")[0].capitalize()
			if CONFIG.proc_mem_bytes: label = label.replace("Mem%", "MemB")
			label = label.replace(selected, f'{Fx.u}{selected}{Fx.uu}')
			out_misc += label

			Draw.buffer("proc_misc", out_misc, only_save=True)

		#* Detailed box draw
		if proc.detailed:
			if proc.details["status"] == psutil.STATUS_RUNNING: stat_color = Fx.b
			elif proc.details["status"] in [psutil.STATUS_DEAD, psutil.STATUS_STOPPED, psutil.STATUS_ZOMBIE]: stat_color = THEME.inactive_fg
			else: stat_color = ""
			expand = proc.expand
			iw = (dw - 3) // (4 + expand)
			iw2 = iw - 1
			out += (f'{CursorChar.to(dy, dgx)}{Graphs.detailed_cpu(None if cls.moved or proc.details["killed"] else proc.details_cpu[-1])}'
					f'{CursorChar.to(dy, dgx)}{THEME.title}{Fx.b}{0 if proc.details["killed"] else proc.details["cpu_percent"]}%{CursorChar.r(1)}{"" if SYSTEM == "MacOS" else (("C" if dgw < 20 else "Core") + str(proc.details["cpu_num"]))}')
			for i, l in enumerate(["C", "P", "U"]):
				out += f'{CursorChar.to(dy + 2 + i, dgx)}{l}'
			for i, l in enumerate(["C", "M", "D"]):
				out += f'{CursorChar.to(dy + 4 + i, dx + 1)}{l}'
			out += (f'{CursorChar.to(dy, dx + 1)} {"Status:":^{iw}.{iw2}}{"Elapsed:":^{iw}.{iw2}}' +
					(f'{"Parent:":^{iw}.{iw2}}' if dw > 28 else "") + (f'{"User:":^{iw}.{iw2}}' if dw > 38 else "") +
					(f'{"Threads:":^{iw}.{iw2}}' if expand > 0 else "") + (f'{"Nice:":^{iw}.{iw2}}' if expand > 1 else "") +
					(f'{"IO Read:":^{iw}.{iw2}}' if expand > 2 else "") + (f'{"IO Write:":^{iw}.{iw2}}' if expand > 3 else "") +
					(f'{"TTY:":^{iw}.{iw2}}' if expand > 4 else "") +
					f'{CursorChar.to(dy + 1, dx + 1)}{Fx.ub}{THEME.main_fg}{stat_color}{proc.details["status"]:^{iw}.{iw2}}{Fx.ub}{THEME.main_fg}{proc.details["uptime"]:^{iw}.{iw2}} ' +
					(f'{proc.details["parent_name"]:^{iw}.{iw2}}' if dw > 28 else "") + (f'{proc.details["username"]:^{iw}.{iw2}}' if dw > 38 else "") +
					(f'{proc.details["threads"]:^{iw}.{iw2}}' if expand > 0 else "") + (f'{proc.details["nice"]:^{iw}.{iw2}}' if expand > 1 else "") +
					(f'{proc.details["io_read"]:^{iw}.{iw2}}' if expand > 2 else "") + (f'{proc.details["io_write"]:^{iw}.{iw2}}' if expand > 3 else "") +
					(f'{proc.details["terminal"][-(iw2):]:^{iw}.{iw2}}' if expand > 4 else "") +
					f'{CursorChar.to(dy + 3, dx)}{THEME.title}{Fx.b}{("Memory: " if dw > 42 else "M:") + str(round(proc.details["memory_percent"], 1)) + "%":>{dw // 3 - 1}}{Fx.ub} {THEME.inactive_fg}{"⡀" * (dw // 3)}'
					f'{CursorChar.l(dw // 3)}{THEME.proc_misc}{Graphs.detailed_mem(None if cls.moved else proc.details_mem[-1])} '
					f'{THEME.title}{Fx.b}{proc.details["memory_bytes"]:.{dw//3 - 2}}{THEME.main_fg}{Fx.ub}')
			cy = dy + (4 if len(proc.details["cmdline"]) > dw - 5 else 5)
			for i in range(ceil(len(proc.details["cmdline"]) / (dw - 5))):
				out += f'{CursorChar.to(cy + i, dx + 3)}{proc.details["cmdline"][((dw - 5) * i):][:(dw - 5)]:{"^" if i == 0 else "<"}{dw - 5}}'
				if i == 2: break

		#* Checking for selection out of bounds
		if cls.start > proc.num_procs - cls.select_max + 1 and proc.num_procs > cls.select_max: cls.start = proc.num_procs - cls.select_max + 1
		elif cls.start > proc.num_procs: cls.start = proc.num_procs
		if cls.start < 1: cls.start = 1
		if cls.selected > proc.num_procs and proc.num_procs < cls.select_max: cls.selected = proc.num_procs
		elif cls.selected > cls.select_max: cls.selected = cls.select_max
		if cls.selected < 0: cls.selected = 0

		#* Start iteration over all processes and info
		cy = 1
		for n, (pid, items) in enumerate(proc.processes.items(), start=1):
			if n < cls.start: continue
			l_count += 1
			if l_count == cls.selected:
				is_selected = True
				cls.selected_pid = pid
			else: is_selected = False

			indent, name, cmd, threads, username, mem, mem_b, cpu = [items.get(v, d) for v, d in [("indent", ""), ("name", ""), ("cmd", ""), ("threads", 0), ("username", "?"), ("mem", 0.0), ("mem_b", 0), ("cpu", 0.0)]]

			if CONFIG.proc_tree:
				arg_len = 0
				offset = tree_len - len(f'{indent}{pid}')
				if offset < 1: offset = 0
				indent = f'{indent:.{tree_len - len(str(pid))}}'
				if offset - len(name) > 12:
					cmd = cmd.split(" ")[0].split("/")[-1]
					if not cmd.startswith(name):
						offset = len(name)
						arg_len = tree_len - len(f'{indent}{pid} {name} ') + 2
						cmd = f'({cmd[:(arg_len-4)]})'
			else:
				offset = prog_len - 1
			if cpu > 1.0 or pid in Graphs.pid_cpu:
				if pid not in Graphs.pid_cpu:
					Graphs.pid_cpu[pid] = Graph(5, 1, None, [0])
					cls.pid_counter[pid] = 0
				elif cpu < 1.0:
					cls.pid_counter[pid] += 1
					if cls.pid_counter[pid] > 10:
						del cls.pid_counter[pid], Graphs.pid_cpu[pid]
				else:
					cls.pid_counter[pid] = 0

			end = f'{THEME.main_fg}{Fx.ub}' if CONFIG.proc_colors else Fx.ub
			if cls.selected > cy: calc = cls.selected - cy
			elif cls.selected > 0 and cls.selected <= cy: calc = cy - cls.selected
			else: calc = cy
			if CONFIG.proc_colors and not is_selected:
				vals = []
				for v in [int(cpu), int(mem), int(threads // 3)]:
					if CONFIG.proc_gradient:
						val = ((v if v <= 100 else 100) + 100) - calc * 100 // cls.select_max
						vals += [f'{THEME.gradient["proc_color" if val < 100 else "process"][val if val < 100 else val - 100]}']
					else:
						vals += [f'{THEME.gradient["process"][v if v <= 100 else 100]}']
				c_color, m_color, t_color = vals
			else:
				c_color = m_color = t_color = Fx.b
			if CONFIG.proc_gradient and not is_selected:
				g_color = f'{THEME.gradient["proc"][calc * 100 // cls.select_max]}'
			if is_selected:
				c_color = m_color = t_color = g_color = end = ""
				out += f'{THEME.selected_bg}{THEME.selected_fg}{Fx.b}'

			#* Creates one line for a process with all gathered information
			out += (f'{CursorChar.to(y + cy, x)}{g_color}{indent}{pid:>{(1 if CONFIG.proc_tree else 7)}} ' +
				f'{c_color}{name:<{offset}.{offset}} {end}' +
					(f'{g_color}{cmd:<{arg_len}.{arg_len-1}}' if arg_len else "") +
					(t_color + (f'{threads:>4} ' if threads < 1000 else "999> ") + end if tr_show else "") +
					(g_color + (f'{username:<9.9}' if len(username) < 10 else f'{username[:8]:<8}+') if usr_show else "") +
					m_color + ((f'{mem:>4.1f}' if mem < 100 else f'{mem:>4.0f} ') if not CONFIG.proc_mem_bytes else f'{floating_humanizer(mem_b, short=True):>4.4}') + end +
				f' {THEME.inactive_fg}{"⡀"*5}{THEME.main_fg}{g_color}{c_color}' + (f' {cpu:>4.1f} ' if cpu < 100 else f'{cpu:>5.0f} ') + end +
					(" " if proc.num_procs > cls.select_max else ""))

			#* Draw small cpu graph for process if cpu usage was above 1% in the last 10 updates
			if pid in Graphs.pid_cpu:
				out += f'{CursorChar.to(y + cy, x + w - (12 if proc.num_procs > cls.select_max else 11))}{c_color if CONFIG.proc_colors else THEME.proc_misc}{Graphs.pid_cpu[pid](None if cls.moved else round(cpu))}{THEME.main_fg}'

			if is_selected: out += f'{Fx.ub}{term.fg}{term.bg}{CursorChar.to(y + cy, x + w - 1)}{" " if proc.num_procs > cls.select_max else ""}'

			cy += 1
			if cy == h: break
		if cy < h:
			for i in range(h-cy):
				out += f'{CursorChar.to(y + cy + i, x)}{" " * w}'

		#* Draw scrollbar if needed
		if proc.num_procs > cls.select_max:
			if cls.resized:
				key.mouse["mouse_scroll_up"] = [[x+w-2+i, y] for i in range(3)]
				key.mouse["mouse_scroll_down"] = [[x+w-2+i, y+h-1] for i in range(3)]
			scroll_pos = round(cls.start * (cls.select_max - 2) / (proc.num_procs - (cls.select_max - 2)))
			if scroll_pos < 0 or cls.start == 1: scroll_pos = 0
			elif scroll_pos > h - 3 or cls.start >= proc.num_procs - cls.select_max: scroll_pos = h - 3
			out += (f'{CursorChar.to(y, x + w - 1)}{Fx.b}{THEME.main_fg}↑{CursorChar.to(y + h - 1, x + w - 1)}↓{Fx.ub}'
					f'{CursorChar.to(y + 1 + scroll_pos, x + w - 1)}█')
		elif "scroll_up" in key.mouse:
			del key.mouse["scroll_up"], key.mouse["scroll_down"]

		#* Draw current selection and number of processes
		out += (f'{CursorChar.to(y + h, x + w - 3 - len(loc_string))}{THEME.proc_box}{Symbol.title_left}{THEME.title}'
					f'{Fx.b}{loc_string}{Fx.ub}{THEME.proc_box(Symbol.title_right)}')

		#* Clean up dead processes graphs and counters
		cls.count += 1
		if cls.count == 100:
			cls.count == 0
			for p in list(cls.pid_counter):
				if not psutil.pid_exists(p):
					del cls.pid_counter[p], Graphs.pid_cpu[p]

		Draw.buffer(cls.buffer, f'{out_misc}{out}{term.fg}', only_save=Menu.active)
		cls.redraw = cls.resized = cls.moved = False