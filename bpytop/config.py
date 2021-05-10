from string import Template

import os
import sys
import logging.handlers
from time import time
from datetime import datetime
from distutils.util import strtobool
from typing import List, Dict, Tuple, Union


reporter = logging.getLogger("reporter")
errlog = logging.getLogger("ErrorLogger")


errors: List[str] = []
try: import fcntl, termios, tty, pwd
except Exception as e: errors.append(f'{e}')

try: import psutil # type: ignore
except Exception as e: errors.append(f'{e}')

SELF_START = time()



VERSION: str = "1.0.44"

#*?This is the template used to create the config file
DEFAULT_CONF: Template = Template(f'#? Config file for bpytop v. {VERSION}' + '''

#* Color theme, looks for a .theme file in "/usr/[local/]share/bpytop/themes" and "~/.config/bpytop/themes", "Default" for builtin default theme.
#* Prefix name by a plus sign (+) for a theme located in user themes folder, i.e. color_theme="+monokai"
color_theme="$color_theme"

#* If the theme set background should be shown, set to False if you want terminal background transparency
theme_background=$theme_background

#* Set bpytop view mode, "full" for everything shown, "proc" for cpu stats and processes, "stat" for cpu, mem, disks and net stats shown.
view_mode=$view_mode

#* Update time in milliseconds, increases automatically if set below internal loops processing time, recommended 2000 ms or above for better sample times for graphs.
update_ms=$update_ms

#* Processes sorting, "pid" "program" "arguments" "threads" "user" "memory" "cpu lazy" "cpu responsive",
#* "cpu lazy" updates top process over time, "cpu responsive" updates top process directly.
proc_sorting="$proc_sorting"

#* Reverse sorting order, True or False.
proc_reversed=$proc_reversed

#* Show processes as a tree
proc_tree=$proc_tree

#* Which depth the tree view should auto collapse processes at
tree_depth=$tree_depth

#* Use the cpu graph colors in the process list.
proc_colors=$proc_colors

#* Use a darkening gradient in the process list.
proc_gradient=$proc_gradient

#* If process cpu usage should be of the core it's running on or usage of the total available cpu power.
proc_per_core=$proc_per_core

#* Show process memory as bytes instead of percent
proc_mem_bytes=$proc_mem_bytes

#* Check cpu temperature, needs "osx-cpu-temp" on MacOS X.
check_temp=$check_temp

#* Which sensor to use for cpu temperature, use options menu to select from list of available sensors.
cpu_sensor=$cpu_sensor

#* Draw a clock at top of screen, formatting according to strftime, empty string to disable.
draw_clock="$draw_clock"

#* Update main ui in background when menus are showing, set this to false if the menus is flickering too much for comfort.
background_update=$background_update

#* Custom cpu model name, empty string to disable.
custom_cpu_name="$custom_cpu_name"

#* Optional filter for shown disks, should be last folder in path of a mountpoint, "root" replaces "/", separate multiple values with comma.
#* Begin line with "exclude=" to change to exclude filter, oterwise defaults to "most include" filter. Example: disks_filter="exclude=boot, home"
disks_filter="$disks_filter"

#* Show graphs instead of meters for memory values.
mem_graphs=$mem_graphs

#* If swap memory should be shown in memory box.
show_swap=$show_swap

#* Show swap as a disk, ignores show_swap value above, inserts itself after first disk.
swap_disk=$swap_disk

#* If mem box should be split to also show disks info.
show_disks=$show_disks

#* Set fixed values for network graphs, default "10M" = 10 Mibibytes, possible units "K", "M", "G", append with "bit" for bits instead of bytes, i.e "100mbit"
net_download="$net_download"
net_upload="$net_upload"

#* Start in network graphs auto rescaling mode, ignores any values set above and rescales down to 10 Kibibytes at the lowest.
net_auto=$net_auto

#* Sync the scaling for download and upload to whichever currently has the highest scale
net_sync=$net_sync

#* If the network graphs color gradient should scale to bandwith usage or auto scale, bandwith usage is based on "net_download" and "net_upload" values
net_color_fixed=$net_color_fixed

#* Show battery stats in top right if battery is present
show_battery=$show_battery

#* Show init screen at startup, the init screen is purely cosmetical
show_init=$show_init

#* Enable check for new version from github.com/aristocratos/bpytop at start.
update_check=$update_check

#* Set loglevel for "~/.config/bpytop/error.log" levels are: "ERROR" "WARNING" "INFO" "DEBUG".
#* The level set includes all lower levels, i.e. "DEBUG" will show all logging info.
log_level=$log_level
''')




#? Set up self.config class and load self.config ----------------------------------------------------------->

class Config:
	'''Holds all self.config variables and functions for loading from and saving to disk'''
	keys: List[str] = ["color_theme", "update_ms", "proc_sorting", "proc_reversed", "proc_tree", "check_temp", "draw_clock", "background_update", "custom_cpu_name",
						"proc_colors", "proc_gradient", "proc_per_core", "proc_mem_bytes", "disks_filter", "update_check", "log_level", "mem_graphs", "show_swap",
						"swap_disk", "show_disks", "net_download", "net_upload", "net_auto", "net_color_fixed", "show_init", "view_mode", "theme_background",
						"net_sync", "show_battery", "tree_depth", "cpu_sensor"]
	conf_dict: Dict[str, Union[str, int, bool]] = {}
	color_theme: str = "Default"
	theme_background: bool = True
	update_ms: int = 2000
	proc_sorting: str = "cpu lazy"
	proc_reversed: bool = False
	proc_tree: bool = False
	tree_depth: int = 3
	proc_colors: bool = True
	proc_gradient: bool = True
	proc_per_core: bool = False
	proc_mem_bytes: bool = True
	check_temp: bool = True
	cpu_sensor: str = "Auto"
	draw_clock: str = "%X"
	background_update: bool = True
	custom_cpu_name: str = ""
	disks_filter: str = ""
	update_check: bool = True
	mem_graphs: bool = True
	show_swap: bool = True
	swap_disk: bool = True
	show_disks: bool = True
	net_download: str = "10M"
	net_upload: str = "10M"
	net_color_fixed: bool = False
	net_auto: bool = True
	net_sync: bool = False
	show_battery: bool = True
	show_init: bool = True
	view_mode: str = "full"
	log_level: str = "WARNING"

	warnings: List[str] = []
	info: List[str] = []
	DEBUG: bool = False

	sorting_options: List[str] = ["pid", "program", "arguments", "threads", "user", "memory", "cpu lazy", "cpu responsive"]
	log_levels: List[str] = ["ERROR", "WARNING", "INFO", "DEBUG"]

	view_modes: List[str] = ["full", "proc", "stat"]

	cpu_sensors: List[str] = [ "Auto" ]

	if hasattr(psutil, "sensors_temperatures"):
		try:
			_temps = psutil.sensors_temperatures()
			if _temps:
				for _name, _entries in _temps.items():
					for _num, _entry in enumerate(_entries, 1):
						if hasattr(_entry, "current"):
							cpu_sensors.append(f'{_name}:{_num if _entry.label == "" else _entry.label}')
		except:
			pass

	changed: bool = False
	recreate: bool = False
	config_file_path: str = ""

	_initialized: bool = False

	def __init__(self, config_file_path: str, is_debug: bool):
		self.config_file_path = config_file_path

		try:
			self.init()
			if is_debug:
				errlog.setLevel(logging.DEBUG)
			else:
				errlog.setLevel(getattr(logging, self.log_level))
				if self.log_level == "DEBUG":
					self.DEBUG = True
			errlog.info(f'New instance of bpytop version {VERSION} started with pid {os.getpid()}')
			errlog.info(f'Loglevel set to {"DEBUG" if is_debug else self.log_level}')
			errlog.debug(f'Using psutil version {".".join(str(x) for x in psutil.version_info)}')
			errlog.debug(f'CMD: {" ".join(sys.argv)}')
			if self.info:
				for info in self.info:
					errlog.info(info)
				self.info = []
			if self.warnings:
				for warning in self.warnings:
					errlog.warning(warning)
				self.warnings = []
		except Exception as e:
			errlog.exception(f'{e}')
			raise SystemExit(1)
		
	def init(self):
		self.conf: Dict[str, Union[str, int, bool]] = self.load_config()
		if not "version" in self.conf.keys():
			self.recreate = True
			self.info.append(f'Config file malformatted or missing, will be recreated on exit!')
		elif self.conf["version"] != VERSION:
			self.recreate = True
			self.info.append(f'Config file version and bpytop version missmatch, will be recreated on exit!')
		for key in self.keys:
			if key in self.conf.keys() and self.conf[key] != "_error_":
				setattr(self, key, self.conf[key])
			else:
				self.recreate = True
				self.self.conf_dict[key] = getattr(self, key)
		self._initialized = True

	def __setattr__(self, name, value):
		if self._initialized:
			object.__setattr__(self, "changed", True)
		object.__setattr__(self, name, value)
		if name not in ["_initialized", "recreate", "changed"]:
			self.conf_dict[name] = value

	def load_config(self) -> Dict[str, Union[str, int, bool]]:
		'''Load config from file, set correct types for values and return a dict'''
		new_config: Dict[str, Union[str, int, bool]] = {}
		self.conf_file: str = ""
		if os.path.isfile(self.config_file_path):
			self.conf_file = self.config_file_path
		elif os.path.isfile("/etc/bpytop.conf"):
			self.conf_file = "/etc/bpytop.conf"
		else:
			return new_config
		try:
			with open(self.conf_file, "r") as f:
				for line in f:
					line = line.strip()
					if line.startswith("#? Config"):
						new_config["version"] = line[line.find("v. ") + 3:]
					for key in self.keys:
						if line.startswith(key):
							line = line.replace(key + "=", "")
							if line.startswith('"'):
								line = line.strip('"')
							if type(getattr(self, key)) == int:
								try:
									new_config[key] = int(line)
								except ValueError:
									self.warnings.append(f'Config key "{key}" should be an integer!')
							if type(getattr(self, key)) == bool:
								try:
									new_config[key] = bool(strtobool(line))
								except ValueError:
									self.warnings.append(f'Config key "{key}" can only be True or False!')
							if type(getattr(self, key)) == str:
									new_config[key] = str(line)
		except Exception as e:
			errlog.exception(str(e))
		if "proc_sorting" in new_config and not new_config["proc_sorting"] in self.sorting_options:
			new_config["proc_sorting"] = "_error_"
			self.warnings.append(f'Config key "proc_sorted" didn\'t get an acceptable value!')
		if "log_level" in new_config and not new_config["log_level"] in self.log_levels:
			new_config["log_level"] = "_error_"
			self.warnings.append(f'Config key "log_level" didn\'t get an acceptable value!')
		if "view_mode" in new_config and not new_config["view_mode"] in self.view_modes:
			new_config["view_mode"] = "_error_"
			self.warnings.append(f'Config key "view_mode" didn\'t get an acceptable value!')
		if isinstance(new_config["update_ms"], int) and new_config["update_ms"] < 100:
			new_config["update_ms"] = 100
			self.warnings.append(f'Config key "update_ms" can\'t be lower than 100!')
		for net_name in ["net_download", "net_upload"]:
			if net_name in new_config and not new_config[net_name][0].isdigit(): # type: ignore
				new_config[net_name] = "_error_"
		if "cpu_sensor" in new_config and not new_config["cpu_sensor"] in self.cpu_sensors:
			new_config["cpu_sensor"] = "_error_"
			self.warnings.append(f'Config key "cpu_sensor" does not contain an available sensor!')
		return new_config

	def save_config(self):
		"""
		Save current config to config file if difference in values or version,
		creates a new file if not found.
		"""
		if not self.changed and not self.recreate:
			return

		try:
			# model = "w" if os.path.isfile(self.config_file_path) else "x" # is it needed ?
			with open(self.config_file_path, "w") as f:
				f.write(DEFAULT_CONF.substitute(self.conf_dict))
		except Exception as e:
			errlog.exception(str(e))






