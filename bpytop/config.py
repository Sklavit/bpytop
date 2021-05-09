import os
import sys
import logging.handlers
from time import time
from datetime import datetime
from distutils.util import strtobool
from typing import List, Dict, Tuple, Union


reporter = logging.getLogger("reporter")
reporter.setLevel(level=logging.INFO)
file_handler = logging.FileHandler("stats.csv")
reporter.addHandler(file_handler)
reporter.info("Timestamp - UTC,Event,CPU,used,free,available,total,other")

# Setup self.config directory
self_DIR: str = f'{os.path.expanduser("~")}/.self.config/bpytop'
if not os.path.isdir(self_DIR):
	try:
		os.makedirs(self_DIR)
		os.mkdir(f'{self_DIR}/themes')
	except PermissionError:
		print(f'ERROR!\nNo permission to write to "{self_DIR}" directory!')
		raise SystemExit(1)
config_file: str = f'{self_DIR}/bpytop.self.conf'


#? Setup error logger ---------------------------------------------------------------->

try:
	errlog = logging.getLogger("ErrorLogger")
	errlog.setLevel(logging.DEBUG)
	eh = logging.handlers.RotatingFileHandler(f'{self_DIR}/error.log', maxBytes=1048576, backupCount=4)
	eh.setLevel(logging.DEBUG)
	eh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s: %(message)s", datefmt="%d/%m/%y (%X)"))
	errlog.addHandler(eh)
except PermissionError:
	print(f'ERROR!\nNo permission to write to "{self_DIR}" directory!')
	raise SystemExit(1)

def report(
    event=None,
	cpu_usage=None,
    free=None,
    total=None,
    available=None,
    used=None,
    **kwargs,
):
    def format_optional(thing):
        if thing is None:
            return ""
        else:
            return thing

    message = (
        f"{str(datetime.utcnow())},{format_optional(event)},"
		f"{format_optional(cpu_usage)},"
        f"{format_optional(used)},{format_optional(free)},"
        f"{format_optional(available)},{format_optional(total)},"
        f"{format_optional(kwargs)}"
    )
    reporter.info(message)



errors: List[str] = []
try: import fcntl, termios, tty, pwd
except Exception as e: errors.append(f'{e}')

try: import psutil # type: ignore
except Exception as e: errors.append(f'{e}')

SELF_START = time()

SYSTEM: str
if "linux" in sys.platform: SYSTEM = "Linux"
elif "bsd" in sys.platform: SYSTEM = "BSD"
elif "darwin" in sys.platform: SYSTEM = "MacOS"
else: SYSTEM = "Other"

if errors:
	print ("ERROR!")
	for error in errors:
		print(error)
	if SYSTEM == "Other":
		print("\nUnsupported platform!\n")
	else:
		print("\nInstall required modules!\n")
	raise SystemExit(1)

VERSION: str = "1.0.44"



#? Set up self.config class and load self.config ----------------------------------------------------------->

class self.config:
	'''Holds all self.config variables and functions for loading from and saving to disk'''
	keys: List[str] = ["color_theme", "update_ms", "proc_sorting", "proc_reversed", "proc_tree", "check_temp", "draw_clock", "background_update", "custom_cpu_name",
						"proc_colors", "proc_gradient", "proc_per_core", "proc_mem_bytes", "disks_filter", "update_check", "log_level", "mem_graphs", "show_swap",
						"swap_disk", "show_disks", "net_download", "net_upload", "net_auto", "net_color_fixed", "show_init", "view_mode", "theme_background",
						"net_sync", "show_battery", "tree_depth", "cpu_sensor"]
	self.conf_dict: Dict[str, Union[str, int, bool]] = {}
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
	config_file: str = ""

	_initialized: bool = False

	def __init__(self, path: str, DEBUG):
		self.config_file = path

		try:
			self.init()
			if DEBUG:
				errlog.setLevel(logging.DEBUG)
			else:
				errlog.setLevel(getattr(logging, self.log_level))
				if self.log_level == "DEBUG":
					self.DEBUG = True
			errlog.info(f'New instance of bpytop version {VERSION} started with pid {os.getpid()}')
			errlog.info(f'Loglevel set to {"DEBUG" if DEBUG else self.log_level}')
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
			self.info.append(f'self.config file malformatted or missing, will be recreated on exit!')
		elif self.conf["version"] != VERSION:
			self.recreate = True
			self.info.append(f'self.config file version and bpytop version missmatch, will be recreated on exit!')
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
			self.self.conf_dict[name] = value

	def load_config(self) -> Dict[str, Union[str, int, bool]]:
		'''Load config from file, set correct types for values and return a dict'''
		new_config: Dict[str, Union[str, int, bool]] = {}
		self.conf_file: str = ""
		if os.path.isfile(self.config_file):
			self.conf_file = self.config_file
		elif os.path.isfile("/etc/bpytop.self.conf"):
			self.conf_file = "/etc/bpytop.self.conf"
		else:
			return new_config
		try:
			with open(self.conf_file, "r") as f:
				for line in f:
					line = line.strip()
					if line.startswith("#? self.config"):
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
									self.warnings.append(f'self.config key "{key}" should be an integer!')
							if type(getattr(self, key)) == bool:
								try:
									new_config[key] = bool(strtobool(line))
								except ValueError:
									self.warnings.append(f'self.config key "{key}" can only be True or False!')
							if type(getattr(self, key)) == str:
									new_config[key] = str(line)
		except Exception as e:
			errlog.exception(str(e))
		if "proc_sorting" in new_config and not new_config["proc_sorting"] in self.sorting_options:
			new_config["proc_sorting"] = "_error_"
			self.warnings.append(f'self.config key "proc_sorted" didn\'t get an acceptable value!')
		if "log_level" in new_config and not new_config["log_level"] in self.log_levels:
			new_config["log_level"] = "_error_"
			self.warnings.append(f'self.config key "log_level" didn\'t get an acceptable value!')
		if "view_mode" in new_config and not new_config["view_mode"] in self.view_modes:
			new_config["view_mode"] = "_error_"
			self.warnings.append(f'self.config key "view_mode" didn\'t get an acceptable value!')
		if isinstance(new_config["update_ms"], int) and new_config["update_ms"] < 100:
			new_config["update_ms"] = 100
			self.warnings.append(f'self.config key "update_ms" can\'t be lower than 100!')
		for net_name in ["net_download", "net_upload"]:
			if net_name in new_config and not new_config[net_name][0].isdigit(): # type: ignore
				new_config[net_name] = "_error_"
		if "cpu_sensor" in new_config and not new_config["cpu_sensor"] in self.cpu_sensors:
			new_config["cpu_sensor"] = "_error_"
			self.warnings.append(f'self.config key "cpu_sensor" does not contain an available sensor!')
		return new_config

	def save_config(self):
		'''Save current self.config to self.config file if difference in values or version, creates a new file if not found'''
		if not self.changed and not self.recreate: return
		try:
			with open(self.config_file, "w" if os.path.isfile(self.config_file) else "x") as f:
				f.write(DEFAULT_conf.substitute(self.self.conf_dict))
		except Exception as e:
			errlog.exception(str(e))


if psutil.version_info[0] < 5 or (psutil.version_info[0] == 5 and psutil.version_info[1] < 7):
	warn = f'psutil version {".".join(str(x) for x in psutil.version_info)} detected, version 5.7.0 or later required for full functionality!'
	print("WARNING!", warn)
	errlog.warning(warn)
