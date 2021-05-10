from collections import defaultdict

from time import time

from datetime import timedelta

import os

import psutil
import subprocess

from shutil import which

from typing import Any, Dict, List, Tuple, Union

import threading

from bpytop.bpytop_widgets import CpuBox, MemBox, NetBox, ProcBox
from bpytop.config import errlog
from bpytop.old import THREADS
from bpytop.old_classes import Menu
from bpytop.old_functions import clean_quit, floating_humanizer, units_to_bytes
from bpytop2 import DEBUG


class Collector:
	"""Data collector master class
	* .start(): Starts collector thread
	* .stop(): Stops collector thread
	* .collect(*collectors: Collector, draw_now: bool = True, interrupt: bool = False): queues up collectors to run
	"""
	stopping: bool = False
	started: bool = False
	draw_now: bool = False
	redraw: bool = False
	only_draw: bool = False
	thread: threading.Thread
	collect_run = threading.Event()
	collect_idle = threading.Event()
	collect_idle.set()
	collect_done = threading.Event()
	collect_queue: List = []
	collect_interrupt: bool = False
	proc_interrupt: bool = False
	use_draw_list: bool = False

	@classmethod
	def start(cls):
		cls.stopping = False
		cls.thread = threading.Thread(target=cls._runner, args=())
		cls.thread.start()
		cls.started = True

	@classmethod
	def stop(cls):
		if cls.started and cls.thread.is_alive():
			cls.stopping = True
			cls.started = False
			cls.collect_queue = []
			cls.collect_idle.set()
			cls.collect_done.set()
			try:
				cls.thread.join()
			except:
				pass

	@classmethod
	def _runner(cls):
		'''This is meant to run in it's own thread, collecting and drawing when collect_run is set'''
		draw_buffers: List[str] = []
		debugged: bool = False
		try:
			while not cls.stopping:
				if CONFIG.draw_clock: Box.draw_clock()
				cls.collect_run.wait(0.1)
				if not cls.collect_run.is_set():
					continue
				draw_buffers = []
				cls.collect_interrupt = False
				cls.collect_run.clear()
				cls.collect_idle.clear()
				cls.collect_done.clear()
				if DEBUG and not debugged: TimeIt.start("Collect and draw")
				while cls.collect_queue:
					collector = cls.collect_queue.pop()
					if not cls.only_draw:
						collector._collect()
					collector._draw()
					if cls.use_draw_list: draw_buffers.append(collector.buffer)
					if cls.collect_interrupt: break
				if DEBUG and not debugged: TimeIt.stop("Collect and draw"); debugged = True
				if cls.draw_now and not Menu.active and not cls.collect_interrupt:
					if cls.use_draw_list: Draw.out(*draw_buffers)
					else: Draw.out()
				cls.collect_idle.set()
				cls.collect_done.set()
		except Exception as e:
			errlog.exception(f'Data collection thread failed with exception: {e}')
			cls.collect_idle.set()
			cls.collect_done.set()
			clean_quit(1, thread=True)

	@classmethod
	def collect(cls, *collectors, draw_now: bool = True, interrupt: bool = False, proc_interrupt: bool = False, redraw: bool = False, only_draw: bool = False):
		"""Setup collect queue for _runner"""
		cls.collect_interrupt = interrupt
		cls.proc_interrupt = proc_interrupt
		cls.collect_idle.wait()
		cls.collect_interrupt = False
		cls.proc_interrupt = False
		cls.use_draw_list = False
		cls.draw_now = draw_now
		cls.redraw = redraw
		cls.only_draw = only_draw

		if collectors:
			cls.collect_queue = [*collectors]
			cls.use_draw_list = True

		else:
			cls.collect_queue = list(cls.__subclasses__())

		cls.collect_run.set()


class CpuCollector(Collector):
	'''Collects cpu usage for cpu and cores, cpu frequency, load_avg, uptime and cpu temps'''
	cpu_usage: List[List[int]] = []
	cpu_temp: List[List[int]] = []
	cpu_temp_high: int = 0
	cpu_temp_crit: int = 0
	for _ in range(THREADS + 1):
		cpu_usage.append([])
		cpu_temp.append([])
	freq_error: bool = False
	cpu_freq: int = 0
	load_avg: List[float] = []
	uptime: str = ""
	buffer: str = CpuBox.buffer
	sensor_method: str = ""
	got_sensors: bool = False

	@classmethod
	def get_sensors(cls):
		'''Check if we can get cpu temps and return method of getting temps'''
		cls.sensor_method = ""
		if SYSTEM == "MacOS":
			try:
				if which("coretemp") and subprocess.check_output(["coretemp", "-p"], text=True).strip().replace("-", "").isdigit():
					cls.sensor_method = "coretemp"
				elif which("osx-cpu-temp") and subprocess.check_output("osx-cpu-temp", text=True).rstrip().endswith("°C"):
					cls.sensor_method = "osx-cpu-temp"
			except: pass
		elif CONFIG.cpu_sensor != "Auto" and CONFIG.cpu_sensor in CONFIG.cpu_sensors:
			cls.sensor_method = "psutil"
		elif hasattr(psutil, "sensors_temperatures"):
			try:
				temps = psutil.sensors_temperatures()
				if temps:
					for name, entries in temps.items():
						if name.lower().startswith("cpu"):
							cls.sensor_method = "psutil"
							break
						for entry in entries:
							if entry.label.startswith(("Package", "Core 0", "Tdie", "CPU")):
								cls.sensor_method = "psutil"
								break
			except: pass
		if not cls.sensor_method and SYSTEM == "Linux":
			try:
				if which("vcgencmd") and subprocess.check_output(["vcgencmd", "measure_temp"], text=True).strip().endswith("'C"):
					cls.sensor_method = "vcgencmd"
			except: pass
		cls.got_sensors = True if cls.sensor_method else False

	@classmethod
	def _collect(cls):
		cls.cpu_usage[0].append(round(psutil.cpu_percent(percpu=False)))

		for n, thread in enumerate(psutil.cpu_percent(percpu=True), start=1):
			cls.cpu_usage[n].append(round(thread))
			if len(cls.cpu_usage[n]) > term.width * 2:
				del cls.cpu_usage[n][0]
		try:
			if hasattr(psutil.cpu_freq(), "current"):
				cls.cpu_freq = round(psutil.cpu_freq().current)
		except Exception as e:
			if not cls.freq_error:
				cls.freq_error = True
				errlog.error("Exception while getting cpu frequency!")
				errlog.exception(f'{e}')
			else:
				pass
		cls.load_avg = [round(lavg, 2) for lavg in os.getloadavg()]
		cls.uptime = str(timedelta(seconds=round(time()-psutil.boot_time(),0)))[:-3]

		if CONFIG.check_temp and cls.got_sensors:
			cls._collect_temps()

		report(cpu_usage=cls.cpu_usage[0][-1])


	@classmethod
	def _collect_temps(cls):
		temp: int = 1000
		cores: List[int] = []
		cpu_type: str = ""
		s_name: str = "_-_"
		s_label: str = "_-_"
		if cls.sensor_method == "psutil":
			try:
				for name, entries in psutil.sensors_temperatures().items():
					for num, entry in enumerate(entries, 1):
						if CONFIG.cpu_sensor != "Auto":
							s_name, s_label = CONFIG.cpu_sensor.split(":", 1)
						if temp == 1000 and name == s_name and (entry.label == s_label or str(num) == s_label) and round(entry.current) > 0:
							cpu_type = "other"
							if not cls.cpu_temp_high:
								if hasattr(entry, "high") and entry.high > 1: cls.cpu_temp_high = round(entry.high)
								else: cls.cpu_temp_high = 80
								if hasattr(entry, "critical") and entry.critical > 1: cls.cpu_temp_crit = round(entry.critical)
								else: cls.cpu_temp_crit = 95
							temp = round(entry.current)
						elif temp == 1000 and entry.label.startswith(("Package", "Tdie")) and hasattr(entry, "current") and round(entry.current) > 0:
							cpu_type = "intel" if entry.label.startswith("Package") else "ryzen"
							if not cls.cpu_temp_high:
								if hasattr(entry, "high") and entry.high > 1: cls.cpu_temp_high = round(entry.high)
								else: cls.cpu_temp_high = 80
								if hasattr(entry, "critical") and entry.critical > 1: cls.cpu_temp_crit = round(entry.critical)
								else: cls.cpu_temp_crit = 95
							temp = round(entry.current)
						elif (entry.label.startswith(("Core", "Tccd", "CPU")) or (name.lower().startswith("cpu") and not entry.label)) and hasattr(entry, "current") and round(entry.current) > 0:
							if not cpu_type:
								cpu_type = "other"
								if not cls.cpu_temp_high:
									if hasattr(entry, "high") and entry.high > 1: cls.cpu_temp_high = round(entry.high)
									else: cls.cpu_temp_high = 60 if name == "cpu_thermal" else 80
									if hasattr(entry, "critical") and entry.critical > 1: cls.cpu_temp_crit = round(entry.critical)
									else: cls.cpu_temp_crit = 80 if name == "cpu_thermal" else 95
								temp = round(entry.current)
							cores.append(round(entry.current))
				if len(cores) < THREADS:
					if cpu_type == "intel" or (cpu_type == "other" and len(cores) == THREADS // 2):
						cls.cpu_temp[0].append(temp)
						for n, t in enumerate(cores, start=1):
							try:
								cls.cpu_temp[n].append(t)
								cls.cpu_temp[THREADS // 2 + n].append(t)
							except IndexError:
								break
					elif cpu_type == "ryzen" or cpu_type == "other":
						cls.cpu_temp[0].append(temp)
						if len(cores) < 1: cores.append(temp)
						z = 1
						for t in cores:
							try:
								for i in range(THREADS // len(cores)):
									cls.cpu_temp[z + i].append(t)
								z += i
							except IndexError:
								break
					if cls.cpu_temp[0]:
						for n in range(1, len(cls.cpu_temp)):
							if len(cls.cpu_temp[n]) != len(cls.cpu_temp[n-1]):
								cls.cpu_temp[n] = cls.cpu_temp[n//2].copy()
				else:
					cores.insert(0, temp)
					for n, t in enumerate(cores):
						try:
							cls.cpu_temp[n].append(t)
						except IndexError:
							break
			except Exception as e:
					errlog.exception(f'{e}')
					cls.got_sensors = False
					#CONFIG.check_temp = False
					CpuBox._calc_size()

		else:
			try:
				if cls.sensor_method == "coretemp":
					temp = max(0, int(subprocess.check_output(["coretemp", "-p"], text=True).strip()))
					cores = [max(0, int(x)) for x in subprocess.check_output("coretemp", text=True).split()]
					if len(cores) < THREADS:
						cls.cpu_temp[0].append(temp)
						for n, t in enumerate(cores, start=1):
							try:
								cls.cpu_temp[n].append(t)
								cls.cpu_temp[THREADS // 2 + n].append(t)
							except IndexError:
								break
					else:
						cores.insert(0, temp)
						for n, t in enumerate(cores):
							try:
								cls.cpu_temp[n].append(t)
							except IndexError:
								break
					if not cls.cpu_temp_high:
						cls.cpu_temp_high = 85
						cls.cpu_temp_crit = 100
				elif cls.sensor_method == "osx-cpu-temp":
					temp = max(0, round(float(subprocess.check_output("osx-cpu-temp", text=True).strip()[:-2])))
					if not cls.cpu_temp_high:
						cls.cpu_temp_high = 85
						cls.cpu_temp_crit = 100
				elif cls.sensor_method == "vcgencmd":
					temp = max(0, round(float(subprocess.check_output(["vcgencmd", "measure_temp"], text=True).strip()[5:-2])))
					if not cls.cpu_temp_high:
						cls.cpu_temp_high = 60
						cls.cpu_temp_crit = 80
			except Exception as e:
					errlog.exception(f'{e}')
					cls.got_sensors = False
					CpuBox._calc_size()
			else:
				if not cores:
					for n in range(THREADS + 1):
						cls.cpu_temp[n].append(temp)

		if len(cls.cpu_temp[0]) > 5:
			for n in range(len(cls.cpu_temp)):
				del cls.cpu_temp[n][0]

	@classmethod
	def _draw(cls):
		CpuBox._draw_fg()


class Memcollector(collector):
	'''Collects memory and disks information'''
	values: Dict[str, int] = {}
	vlist: Dict[str, List[int]] = {}
	percent: Dict[str, int] = {}
	string: Dict[str, str] = {}

	swap_values: Dict[str, int] = {}
	swap_vlist: Dict[str, List[int]] = {}
	swap_percent: Dict[str, int] = {}
	swap_string: Dict[str, str] = {}

	disks: Dict[str, Dict]
	disk_hist: Dict[str, Tuple] = {}
	timestamp: float = time()

	io_error: bool = False

	old_disks: List[str] = []

	excludes: List[str] = ["squashfs"]
	if SYSTEM == "BSD": excludes += ["devfs", "tmpfs", "procfs", "linprocfs", "gvfs", "fusefs"]

	buffer: str = MemBox.buffer

	@classmethod
	def _collect(cls):
		#* Collect memory
		mem = psutil.virtual_memory()
		if hasattr(mem, "cached"):
			cls.values["cached"] = mem.cached
		else:
			cls.values["cached"] = mem.active
		cls.values["total"], cls.values["free"], cls.values["available"] = mem.total, mem.free, mem.available
		cls.values["used"] = cls.values["total"] - cls.values["available"]

		for key, value in cls.values.items():
			cls.string[key] = floating_humanizer(value)
			if key == "total": continue
			cls.percent[key] = round(value * 100 / cls.values["total"])
			if CONFIG.mem_graphs:
				if not key in cls.vlist: cls.vlist[key] = []
				cls.vlist[key].append(cls.percent[key])
				if len(cls.vlist[key]) > MemBox.width: del cls.vlist[key][0]

		#* Collect swap
		if CONFIG.show_swap or CONFIG.swap_disk:
			swap = psutil.swap_memory()
			cls.swap_values["total"], cls.swap_values["free"] = swap.total, swap.free
			cls.swap_values["used"] = cls.swap_values["total"] - cls.swap_values["free"]

			if swap.total:
				if not MemBox.swap_on:
					MemBox.redraw = True
				MemBox.swap_on = True
				for key, value in cls.swap_values.items():
					cls.swap_string[key] = floating_humanizer(value)
					if key == "total": continue
					cls.swap_percent[key] = round(value * 100 / cls.swap_values["total"])
					if CONFIG.mem_graphs:
						if not key in cls.swap_vlist: cls.swap_vlist[key] = []
						cls.swap_vlist[key].append(cls.swap_percent[key])
						if len(cls.swap_vlist[key]) > MemBox.width: del cls.swap_vlist[key][0]
			else:
				if MemBox.swap_on:
					MemBox.redraw = True
				MemBox.swap_on = False
		else:
			if MemBox.swap_on:
				MemBox.redraw = True
			MemBox.swap_on = False


		if not CONFIG.show_disks: return
		#* Collect disks usage
		disk_read: int = 0
		disk_write: int = 0
		dev_name: str
		disk_name: str
		filtering: Tuple = ()
		filter_exclude: bool = False
		io_string: str
		u_percent: int
		disk_list: List[str] = []
		cls.disks = {}

		if CONFIG.disks_filter:
			if CONFIG.disks_filter.startswith("exclude="):
				filter_exclude = True
				filtering = tuple(v.strip() for v in CONFIG.disks_filter.replace("exclude=", "").strip().split(","))
			else:
				filtering = tuple(v.strip() for v in CONFIG.disks_filter.strip().split(","))

		try:
			io_counters = psutil.disk_io_counters(perdisk=True if SYSTEM == "Linux" else False, nowrap=True)
		except ValueError as e:
			if not cls.io_error:
				cls.io_error = True
				errlog.error(f'Non fatal error during disk io collection!')
				if psutil.version_info[0] < 5 or (psutil.version_info[0] == 5 and psutil.version_info[1] < 7):
					errlog.error(f'Caused by outdated psutil version.')
				errlog.exception(f'{e}')
			io_counters = None

		for disk in psutil.disk_partitions():
			disk_io = None
			io_string = ""
			disk_name = disk.mountpoint.rsplit('/', 1)[-1] if not disk.mountpoint == "/" else "root"
			while disk_name in disk_list: disk_name += "_"
			disk_list += [disk_name]
			if cls.excludes and disk.fstype in cls.excludes:
				continue
			if filtering and ((not filter_exclude and not disk_name.endswith(filtering)) or (filter_exclude and disk_name.endswith(filtering))):
				continue
			#elif filtering and disk_name.endswith(filtering)
			if SYSTEM == "MacOS" and disk.mountpoint == "/private/var/vm":
				continue
			try:
				disk_u = psutil.disk_usage(disk.mountpoint)
			except:
				pass

			u_percent = round(disk_u.percent)
			cls.disks[disk.device] = { "name" : disk_name, "used_percent" : u_percent, "free_percent" : 100 - u_percent }
			for name in ["total", "used", "free"]:
				cls.disks[disk.device][name] = floating_humanizer(getattr(disk_u, name, 0))

			#* Collect disk io
			if io_counters:
				try:
					if SYSTEM == "Linux":
						dev_name = os.path.realpath(disk.device).rsplit('/', 1)[-1]
						if dev_name.startswith("md"):
							try:
								dev_name = dev_name[:dev_name.index("p")]
							except:
								pass
						disk_io = io_counters[dev_name]
					elif disk.mountpoint == "/":
						disk_io = io_counters
					else:
						raise Exception
					disk_read = round((disk_io.read_bytes - cls.disk_hist[disk.device][0]) / (time() - cls.timestamp))
					disk_write = round((disk_io.write_bytes - cls.disk_hist[disk.device][1]) / (time() - cls.timestamp))
				except:
					disk_read = disk_write = 0
			else:
				disk_read = disk_write = 0

			if disk_io:
				cls.disk_hist[disk.device] = (disk_io.read_bytes, disk_io.write_bytes)
				if MemBox.disks_width > 30:
					if disk_read > 0:
						io_string += f'▲{floating_humanizer(disk_read, short=True)} '
					if disk_write > 0:
						io_string += f'▼{floating_humanizer(disk_write, short=True)}'
				elif disk_read + disk_write > 0:
					io_string += f'▼▲{floating_humanizer(disk_read + disk_write, short=True)}'

			cls.disks[disk.device]["io"] = io_string

		if CONFIG.swap_disk and MemBox.swap_on:
			cls.disks["__swap"] = { "name" : "swap", "used_percent" : cls.swap_percent["used"], "free_percent" : cls.swap_percent["free"], "io" : "" }
			for name in ["total", "used", "free"]:
				cls.disks["__swap"][name] = cls.swap_string[name]
			if len(cls.disks) > 2:
				try:
					new = { list(cls.disks)[0] : cls.disks.pop(list(cls.disks)[0])}
					new["__swap"] = cls.disks.pop("__swap")
					new.update(cls.disks)
					cls.disks = new
				except:
					pass

		if disk_list != cls.old_disks:
			MemBox.redraw = True
			cls.old_disks = disk_list.copy()

		for name, value in cls.string.items():
			report(**cls.string)

		cls.timestamp = time()

	@classmethod
	def _draw(cls):
		MemBox._draw_fg()


class Netcollector(collector):
	'''Collects network stats'''
	buffer: str = NetBox.buffer
	nics: List[str] = []
	nic_i: int = 0
	nic: str = ""
	new_nic: str = ""
	nic_error: bool = False
	reset: bool = False
	graph_raise: Dict[str, int] = {"download" : 5, "upload" : 5}
	graph_lower: Dict[str, int] = {"download" : 5, "upload" : 5}
	#min_top: int = 10<<10
	#* Stats structure = stats[netword device][download, upload][total, last, top, graph_top, offset, speed, redraw, graph_raise, graph_low] = int, List[int], bool
	stats: Dict[str, Dict[str, Dict[str, Any]]] = {}
	#* Strings structure strings[network device][download, upload][total, byte_ps, bit_ps, top, graph_top] = str
	strings: Dict[str, Dict[str, Dict[str, str]]] = {}
	switched: bool = False
	timestamp: float = time()
	net_min: Dict[str, int] = {"download" : -1, "upload" : -1}
	auto_min: bool = CONFIG.net_auto
	sync_top: int = 0
	sync_string: str = ""

	@classmethod
	def _get_nics(cls):
		'''Get a list of all network devices sorted by highest throughput'''
		cls.nic_i = 0
		cls.nic = ""
		try:
			io_all = psutil.net_io_counters(pernic=True)
		except Exception as e:
			if not cls.nic_error:
				cls.nic_error = True
				errlog.exception(f'{e}')
		if not io_all: return
		up_stat = psutil.net_if_stats()
		for nic in sorted(io_all.keys(), key=lambda nic: (getattr(io_all[nic], "bytes_recv", 0) + getattr(io_all[nic], "bytes_sent", 0)), reverse=True):
			if nic not in up_stat or not up_stat[nic].isup:
				continue
			cls.nics.append(nic)
		if not cls.nics: cls.nics = [""]
		cls.nic = cls.nics[cls.nic_i]

	@classmethod
	def switch(cls, key: str):
		if len(cls.nics) < 2: return
		cls.nic_i += +1 if key == "n" else -1
		if cls.nic_i >= len(cls.nics): cls.nic_i = 0
		elif cls.nic_i < 0: cls.nic_i = len(cls.nics) - 1
		cls.new_nic = cls.nics[cls.nic_i]
		cls.switched = True
		collector.collect(Netcollector, redraw=True)

	@classmethod
	def _collect(cls):
		speed: int
		stat: Dict
		up_stat = psutil.net_if_stats()

		if cls.switched:
			cls.nic = cls.new_nic
			cls.switched = False

		if not cls.nic or cls.nic not in up_stat or not up_stat[cls.nic].isup:
			cls._get_nics()
			if not cls.nic: return
		try:
			io_all = psutil.net_io_counters(pernic=True)[cls.nic]
		except keyError:
			pass
			return
		if not cls.nic in cls.stats:
			cls.stats[cls.nic] = {}
			cls.strings[cls.nic] = { "download" : {}, "upload" : {}}
			for direction, value in ["download", io_all.bytes_recv], ["upload", io_all.bytes_sent]:
				cls.stats[cls.nic][direction] = { "total" : value, "last" : value, "top" : 0, "graph_top" : 0, "offset" : 0, "speed" : [], "redraw" : True, "graph_raise" : 0, "graph_lower" : 7 }
				for v in ["total", "byte_ps", "bit_ps", "top", "graph_top"]:
					cls.strings[cls.nic][direction][v] = ""

		cls.stats[cls.nic]["download"]["total"] = io_all.bytes_recv
		cls.stats[cls.nic]["upload"]["total"] = io_all.bytes_sent

		for direction in ["download", "upload"]:
			stat = cls.stats[cls.nic][direction]
			strings = cls.strings[cls.nic][direction]
			#* Calculate current speed
			stat["speed"].append(round((stat["total"] - stat["last"]) / (time() - cls.timestamp)))
			stat["last"] = stat["total"]
			speed = stat["speed"][-1]

			if cls.net_min[direction] == -1:
				cls.net_min[direction] = units_to_bytes(getattr(CONFIG, "net_" + direction))
				stat["graph_top"] = cls.net_min[direction]
				stat["graph_lower"] = 7
				if not cls.auto_min:
					stat["redraw"] = True
					strings["graph_top"] = floating_humanizer(stat["graph_top"], short=True)

			if stat["offset"] and stat["offset"] > stat["total"]:
				cls.reset = True

			if cls.reset:
				if not stat["offset"]:
					stat["offset"] = stat["total"]
				else:
					stat["offset"] = 0
				if direction == "upload":
					cls.reset = False
					NetBox.redraw = True

			if len(stat["speed"]) > NetBox.width * 2:
				del stat["speed"][0]

			strings["total"] = floating_humanizer(stat["total"] - stat["offset"])
			strings["byte_ps"] = floating_humanizer(stat["speed"][-1], per_second=True)
			strings["bit_ps"] = floating_humanizer(stat["speed"][-1], bit=True, per_second=True)

			if speed > stat["top"] or not stat["top"]:
				stat["top"] = speed
				strings["top"] = floating_humanizer(stat["top"], bit=True, per_second=True)

			if cls.auto_min:
				if speed > stat["graph_top"]:
					stat["graph_raise"] += 1
					if stat["graph_lower"] > 0: stat["graph_lower"] -= 1
				elif speed < stat["graph_top"] // 10:
					stat["graph_lower"] += 1
					if stat["graph_raise"] > 0: stat["graph_raise"] -= 1

				if stat["graph_raise"] >= 5 or stat["graph_lower"] >= 5:
					if stat["graph_raise"] >= 5:
						stat["graph_top"] = round(max(stat["speed"][-5:]) / 0.8)
					elif stat["graph_lower"] >= 5:
						stat["graph_top"] = max(10 << 10, max(stat["speed"][-5:]) * 3)
					stat["graph_raise"] = 0
					stat["graph_lower"] = 0
					stat["redraw"] = True
					strings["graph_top"] = floating_humanizer(stat["graph_top"], short=True)

		cls.timestamp = time()

		if CONFIG.net_sync:
			c_max: int = max(cls.stats[cls.nic]["download"]["graph_top"], cls.stats[cls.nic]["upload"]["graph_top"])
			if c_max != cls.sync_top:
				cls.sync_top = c_max
				cls.sync_string = floating_humanizer(cls.sync_top, short=True)
				NetBox.redraw = True

	@classmethod
	def _draw(cls):
		NetBox._draw_fg()


class Proccollector(collector):
	'''Collects process stats'''
	buffer: str = ProcBox.buffer
	search_filter: str = ""
	processes: Dict = {}
	num_procs: int = 0
	det_cpu: float = 0.0
	detailed: bool = False
	detailed_pid: Union[int, None] = None
	details: Dict[str, Any] = {}
	details_cpu: List[int] = []
	details_mem: List[int] = []
	expand: int = 0
	collapsed: Dict = {}
	tree_counter: int = 0
	p_values: List[str] = ["pid", "name", "cmdline", "num_threads", "username", "memory_percent", "cpu_percent", "cpu_times", "create_time"]
	sort_expr: Dict = {}
	sort_expr["pid"] = compile("p.info['pid']", "str", "eval")
	sort_expr["program"] = compile("'' if p.info['name'] == 0.0 else p.info['name']", "str", "eval")
	sort_expr["arguments"] = compile("' '.join(str(p.info['cmdline'])) or ('' if p.info['name'] == 0.0 else p.info['name'])", "str", "eval")
	sort_expr["threads"] = compile("0 if p.info['num_threads'] == 0.0 else p.info['num_threads']", "str", "eval")
	sort_expr["user"] = compile("'' if p.info['username'] == 0.0 else p.info['username']", "str", "eval")
	sort_expr["memory"] = compile("p.info['memory_percent']", "str", "eval")
	sort_expr["cpu lazy"] = compile("(sum(p.info['cpu_times'][:2] if not p.info['cpu_times'] == 0.0 else [0.0, 0.0]) * 1000 / (time() - p.info['create_time']))", "str", "eval")
	sort_expr["cpu responsive"] = compile("(p.info['cpu_percent'] if CONFIG.proc_per_core else (p.info['cpu_percent'] / THREADS))", "str", "eval")

	@classmethod
	def _collect(cls):
		'''List all processess with pid, name, arguments, threads, username, memory percent and cpu percent'''
		if Box.stat_mode: return
		out: Dict = {}
		cls.det_cpu = 0.0
		sorting: str = CONFIG.proc_sorting
		reverse: bool = not CONFIG.proc_reversed
		proc_per_cpu: bool = CONFIG.proc_per_core
		search: str = cls.search_filter
		err: float = 0.0
		n: int = 0

		if CONFIG.proc_tree and sorting == "arguments":
			sorting = "program"

		sort_cmd = cls.sort_expr[sorting]

		if CONFIG.proc_tree:
			cls._tree(sort_cmd=sort_cmd, reverse=reverse, proc_per_cpu=proc_per_cpu, search=search)
		else:
			for p in sorted(psutil.process_iter(cls.p_values + (["memory_info"] if CONFIG.proc_mem_bytes else []), err), key=lambda p: eval(sort_cmd), reverse=reverse):
				if cls.collect_interrupt or cls.proc_interrupt:
					return
				if p.info["name"] == "idle" or p.info["name"] == err or p.info["pid"] == err:
					continue
				if p.info["cmdline"] == err:
					p.info["cmdline"] = ""
				if p.info["username"] == err:
					p.info["username"] = ""
				if p.info["num_threads"] == err:
					p.info["num_threads"] = 0
				if search:
					if cls.detailed and p.info["pid"] == cls.detailed_pid:
						cls.det_cpu = p.info["cpu_percent"]
					for value in [ p.info["name"], " ".join(p.info["cmdline"]), str(p.info["pid"]), p.info["username"] ]:
						for s in search.split(","):
							if s.strip() in value:
								break
						else: continue
						break
					else: continue

				cpu = p.info["cpu_percent"] if proc_per_cpu else round(p.info["cpu_percent"] / THREADS, 2)
				mem = p.info["memory_percent"]
				if CONFIG.proc_mem_bytes and hasattr(p.info["memory_info"], "rss"):
					mem_b = p.info["memory_info"].rss
				else:
					mem_b = 0

				cmd = " ".join(p.info["cmdline"]) or "[" + p.info["name"] + "]"

				out[p.info["pid"]] = {
					"name" : p.info["name"],
					"cmd" : cmd,
					"threads" : p.info["num_threads"],
					"username" : p.info["username"],
					"mem" : mem,
					"mem_b" : mem_b,
					"cpu" : cpu }

				n += 1

			cls.num_procs = n
			cls.processes = out.copy()

		if cls.detailed:
			cls.expand = ((ProcBox.width - 2) - ((ProcBox.width - 2) // 3) - 40) // 10
			if cls.expand > 5: cls.expand = 5
		if cls.detailed and not cls.details.get("killed", False):
			try:
				c_pid = cls.detailed_pid
				det = psutil.Process(c_pid)
			except (psutil.NoSuchProcess, psutil.ZombieProcess):
				cls.details["killed"] = True
				cls.details["status"] = psutil.STATUS_DEAD
				ProcBox.redraw = True
			else:
				attrs: List[str] = ["status", "memory_info", "create_time"]
				if not SYSTEM == "MacOS": attrs.extend(["cpu_num"])
				if cls.expand:
					attrs.extend(["nice", "terminal"])
					if not SYSTEM == "MacOS": attrs.extend(["io_counters"])

				if not c_pid in cls.processes: attrs.extend(["pid", "name", "cmdline", "num_threads", "username", "memory_percent"])

				cls.details = det.as_dict(attrs=attrs, ad_value="")
				if det.parent() != None: cls.details["parent_name"] = det.parent().name()
				else: cls.details["parent_name"] = ""

				cls.details["pid"] = c_pid
				if c_pid in cls.processes:
					cls.details["name"] = cls.processes[c_pid]["name"]
					cls.details["cmdline"] = cls.processes[c_pid]["cmd"]
					cls.details["threads"] = f'{cls.processes[c_pid]["threads"]}'
					cls.details["username"] = cls.processes[c_pid]["username"]
					cls.details["memory_percent"] = cls.processes[c_pid]["mem"]
					cls.details["cpu_percent"] = round(cls.processes[c_pid]["cpu"] * (1 if CONFIG.proc_per_core else THREADS))
				else:
					cls.details["cmdline"] = " ".join(cls.details["cmdline"]) or "[" + cls.details["name"] + "]"
					cls.details["threads"] = f'{cls.details["num_threads"]}'
					cls.details["cpu_percent"] = round(cls.det_cpu)

				cls.details["killed"] = False
				if SYSTEM == "MacOS":
					cls.details["cpu_num"] = -1
					cls.details["io_counters"] = ""


				if hasattr(cls.details["memory_info"], "rss"): cls.details["memory_bytes"] = floating_humanizer(cls.details["memory_info"].rss) # type: ignore
				else: cls.details["memory_bytes"] = "? Bytes"

				if isinstance(cls.details["create_time"], float):
					uptime = timedelta(seconds=round(time()-cls.details["create_time"],0))
					if uptime.days > 0: cls.details["uptime"] = f'{uptime.days}d {str(uptime).split(",")[1][:-3].strip()}'
					else: cls.details["uptime"] = f'{uptime}'
				else: cls.details["uptime"] = "??:??:??"

				if cls.expand:
					if cls.expand > 1 : cls.details["nice"] = f'{cls.details["nice"]}'
					if SYSTEM == "BSD":
						if cls.expand > 2:
							if hasattr(cls.details["io_counters"], "read_count"): cls.details["io_read"] = f'{cls.details["io_counters"].read_count}'
							else: cls.details["io_read"] = "?"
						if cls.expand > 3:
							if hasattr(cls.details["io_counters"], "write_count"): cls.details["io_write"] = f'{cls.details["io_counters"].write_count}'
							else: cls.details["io_write"] = "?"
					else:
						if cls.expand > 2:
							if hasattr(cls.details["io_counters"], "read_bytes"): cls.details["io_read"] = floating_humanizer(cls.details["io_counters"].read_bytes)
							else: cls.details["io_read"] = "?"
						if cls.expand > 3:
							if hasattr(cls.details["io_counters"], "write_bytes"): cls.details["io_write"] = floating_humanizer(cls.details["io_counters"].write_bytes)
							else: cls.details["io_write"] = "?"
					if cls.expand > 4 : cls.details["terminal"] = f'{cls.details["terminal"]}'.replace("/dev/", "")

				cls.details_cpu.append(cls.details["cpu_percent"])
				mem = cls.details["memory_percent"]
				if mem > 80: mem = round(mem)
				elif mem > 60: mem = round(mem * 1.2)
				elif mem > 30: mem = round(mem * 1.5)
				elif mem > 10: mem = round(mem * 2)
				elif mem > 5: mem = round(mem * 10)
				else: mem = round(mem * 20)
				cls.details_mem.append(mem)
				if len(cls.details_cpu) > ProcBox.width: del cls.details_cpu[0]
				if len(cls.details_mem) > ProcBox.width: del cls.details_mem[0]

	@classmethod
	def _tree(cls, sort_cmd, reverse: bool, proc_per_cpu: bool, search: str):
		'''List all processess in a tree view with pid, name, threads, username, memory percent and cpu percent'''
		out: Dict = {}
		err: float = 0.0
		det_cpu: float = 0.0
		infolist: Dict = {}
		cls.tree_counter += 1
		tree = defaultdict(list)
		n: int = 0
		for p in sorted(psutil.process_iter(cls.p_values + (["memory_info"] if CONFIG.proc_mem_bytes else []), err), key=lambda p: eval(sort_cmd), reverse=reverse):
			if cls.collect_interrupt: return
			try:
				tree[p.ppid()].append(p.pid)
			except (psutil.NoSuchProcess, psutil.ZombieProcess):
				pass
			else:
				infolist[p.pid] = p.info
				n += 1
		if 0 in tree and 0 in tree[0]:
			tree[0].remove(0)

		def create_tree(pid: int, tree: defaultdict, indent: str = "", inindent: str = " ", found: bool = False, depth: int = 0, collapse_to: Union[None, int] = None):
			nonlocal infolist, proc_per_cpu, search, out, det_cpu
			name: str; threads: int; username: str; mem: float; cpu: float; collapse: bool = False
			cont: bool = True
			getinfo: Dict = {}
			if cls.collect_interrupt: return
			try:
				name = psutil.Process(pid).name()
				if name == "idle": return
			except psutil.Error:
				pass
				cont = False
				name = ""
			if pid in infolist:
				getinfo = infolist[pid]

			if search and not found:
				if cls.detailed and pid == cls.detailed_pid:
						det_cpu = getinfo["cpu_percent"]
				if "username" in getinfo and isinstance(getinfo["username"], float): getinfo["username"] = ""
				if "cmdline" in getinfo and isinstance(getinfo["cmdline"], float): getinfo["cmdline"] = ""
				for value in [ name, str(pid), getinfo.get("username", ""), " ".join(getinfo.get("cmdline", "")) ]:
					for s in search.split(","):
						if s.strip() in value:
							found = True
							break
					else: continue
					break
				else: cont = False
			if cont:
				if getinfo:
					if getinfo["num_threads"] == err: threads = 0
					else: threads = getinfo["num_threads"]
					if getinfo["username"] == err: username = ""
					else: username = getinfo["username"]
					cpu = getinfo["cpu_percent"] if proc_per_cpu else round(getinfo["cpu_percent"] / THREADS, 2)
					mem = getinfo["memory_percent"]
					if getinfo["cmdline"] == err: cmd = ""
					else: cmd = " ".join(getinfo["cmdline"]) or "[" + getinfo["name"] + "]"
					if CONFIG.proc_mem_bytes and hasattr(getinfo["memory_info"], "rss"):
						mem_b = getinfo["memory_info"].rss
					else:
						mem_b = 0
				else:
					threads = mem_b = 0
					username = ""
					mem = cpu = 0.0

				if pid in cls.collapsed:
					collapse = cls.collapsed[pid]
				else:
					collapse = True if depth > CONFIG.tree_depth else False
					cls.collapsed[pid] = collapse

				if collapse_to and not search:
					out[collapse_to]["threads"] += threads
					out[collapse_to]["mem"] += mem
					out[collapse_to]["mem_b"] += mem_b
					out[collapse_to]["cpu"] += cpu
				else:
					if pid in tree and len(tree[pid]) > 0:
						sign: str = "+" if collapse else "-"
						inindent = inindent.replace(" ├─ ", "[" + sign + "]─").replace(" └─ ", "[" + sign + "]─")
					out[pid] = {
						"indent" : inindent,
						"name": name,
						"cmd" : cmd,
						"threads" : threads,
						"username" : username,
						"mem" : mem,
						"mem_b" : mem_b,
						"cpu" : cpu,
						"depth" : depth,
						}

			if search: collapse = False
			elif collapse and not collapse_to:
				collapse_to = pid

			if pid not in tree:
				return
			children = tree[pid][:-1]

			for child in children:
				create_tree(child, tree, indent + " │ ", indent + " ├─ ", found=found, depth=depth+1, collapse_to=collapse_to)
			create_tree(tree[pid][-1], tree, indent + "  ", indent + " └─ ", depth=depth+1, collapse_to=collapse_to)

		create_tree(min(tree), tree)
		cls.det_cpu = det_cpu

		if cls.collect_interrupt: return
		if cls.tree_counter >= 100:
			cls.tree_counter = 0
			for pid in list(cls.collapsed):
				if not psutil.pid_exists(pid):
					del cls.collapsed[pid]
		cls.num_procs = len(out)
		cls.processes = out.copy()

	@classmethod
	def sorting(cls, key: str):
		index: int = CONFIG.sorting_options.index(CONFIG.proc_sorting) + (1 if key == "right" else -1)
		if index >= len(CONFIG.sorting_options): index = 0
		elif index < 0: index = len(CONFIG.sorting_options) - 1
		CONFIG.proc_sorting = CONFIG.sorting_options[index]
		if "left" in key.mouse: del key.mouse["left"]
		collector.collect(Proccollector, interrupt=True, redraw=True)

	@classmethod
	def _draw(cls):
		ProcBox._draw_fg()