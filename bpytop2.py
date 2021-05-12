#!/usr/bin/env python3
# pylint: disable=not-callable, no-member
# indent = tab
# tab-size = 4

# Copyright 2020 Aristocratos (jakob@qvantnet.com)

# Copyright 2021 Sklavit

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import argparse
# import signal
#
# from bpytop.collectors import Collector
from bpytop.config import *
# from bpytop.config import VERSION, errlog
# from bpytop.debug_utils import TimeIt
# from bpytop.event_loop import Timer, run_event_loop
# from bpytop.main_mvc import Controller, MainWidget
# from bpytop.old_classes import (
# 	Init,
# 	Theme,
# 	UpdateChecker,
# )
# from bpytop.old_functions import (
# 	clean_quit,
# 	get_cpu_name,
# 	now_awake,
# 	now_sleeping,
# 	quit_sigint,
# )
from bpytop.debug_utils import TimeIt
from bpytop.env import *
from bpytop.old_classes import Init
from bpytop.theme import Theme
from bpytop.old_functions import get_cpu_name
from engine.universe.terminal.terminal_engine import Draw

if errors:
	print ("ERROR!")
	for error in errors:
		print(error)
	if SYSTEM == "Other":
		print("\nUnsupported platform!\n")
	else:
		print("\nInstall required modules!\n")
	raise SystemExit(1)

reporter = logging.getLogger("reporter")
errlog = logging.getLogger("ErrorLogger")

if psutil.version_info[0] < 5 or (
	psutil.version_info[0] == 5 and psutil.version_info[1] < 7
):
	warn = (
		f'psutil version {".".join(str(x) for x in psutil.version_info)} detected, '
		f"version 5.7.0 or later required for full functionality!"
	)
	print("WARNING!", warn)
	errlog.warning(warn)


# Search for Config

# Setup self.config directory
CONFIG_DIR: str = f'{os.path.expanduser("~")}/.config/bpytop'
if not os.path.isdir(CONFIG_DIR):
	try:
		os.makedirs(CONFIG_DIR)
		os.mkdir(f'{CONFIG_DIR}/themes')
	except PermissionError:
		print(f'ERROR!\nNo permission to write to "{CONFIG_DIR}" directory!')
		raise SystemExit(1)

CONFIG_FILE: str = f'{CONFIG_DIR}/bpytop.conf'

# Theme config
THEME_DIR: str = ""

if os.path.isdir(f'{os.path.dirname(__file__)}/bpytop-themes'):
	THEME_DIR = f'{os.path.dirname(__file__)}/bpytop-themes'
else:
	for td in ["/usr/local/", "/usr/", "/snap/bpytop/current/usr/"]:
		if os.path.isdir(f'{td}share/bpytop/themes'):
			THEME_DIR = f'{td}share/bpytop/themes'
			break
USER_THEME_DIR: str = f'{CONFIG_DIR}/themes'

# ? Pre main -------------------------------------------------------------------------------------->

CPU_NAME: str = get_cpu_name()

THEME: Theme


def setup_logger():
	reporter.setLevel(level=logging.INFO)
	file_handler = logging.FileHandler("stats.csv")
	reporter.addHandler(file_handler)
	reporter.info("Timestamp - UTC,Event,CPU,used,free,available,total,other")

	# ? Setup error logger ---------------------------------------------------------------->

	try:
		errlog.setLevel(logging.DEBUG)
		eh = logging.handlers.RotatingFileHandler(f'{CONFIG_DIR}/error.log', maxBytes=1048576,
												  backupCount=4)
		eh.setLevel(logging.DEBUG)
		eh.setFormatter(
			logging.Formatter("%(asctime)s | %(levelname)s: %(message)s", datefmt="%d/%m/%y (%X)"))
		errlog.addHandler(eh)
	except PermissionError:
		print(f'ERROR!\nNo permission to write to "{CONFIG_DIR}" directory!')
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


def main():
	setup_logger()

	config = Config(CONFIG_FILE, DEBUG)

	controller = Controller()
	timer = Timer(update_ms=config.update_ms, controller=controller)
	collector = Collector()

	global THEME

	# ? Init -------------------------------------------------------------------------------------->
	if DEBUG:
		TimeIt.start("Init")

	main_widget = MainWidget()
	main_widget.init()

	# ? Start a thread checking for updates while running init
	if config.update_check:
		UpdateChecker.run()

	init_screen_widget = Init()

	# ? Draw banner and init status
	if config.show_init and not Init.resized:
		init_screen_widget.start()

	# ? Load theme
	if config.show_init:
		Draw.buffer(
			"+init!",
			f'{Mv.restore}{Fx.trans("Loading theme and creating colors... ")}{Mv.save}',
		)
	try:
		THEME = Theme(config.color_theme)
		config.color_theme = THEME.current

		#* Set terminal colors
		term.fg = THEME.main_fg
		term.bg = THEME.main_bg if config.theme_background else "\033[49m"
		Draw.now(THEME.main_fg, THEME.main_bg)

	except Exception as e:
		init_screen_widget.fail(e)
	else:
		init_screen_widget.success()

	# ? Setup boxes
	if config.show_init:
		Draw.buffer(
			"+init!",
			f'{Mv.restore}{Fx.trans("Doing some maths and drawing... ")}{Mv.save}',
		)
	try:
		if config.check_temp:
			Cpucollector.get_sensors()
		Box.calc_sizes()
		Box.draw_bg(now=False)
	except Exception as e:
		init_screen_widget.fail(e)
	else:
		init_screen_widget.success()

	# ? Setup signal handlers for SIGSTP, SIGCONT, SIGINT and SIGWINCH
	if config.show_init:
		Draw.buffer(
			"+init!",
			f'{Mv.restore}{Fx.trans("Setting up signal handlers... ")}{Mv.save}',
		)
	try:
		signal.signal(signal.SIGTSTP, now_sleeping)  # * Ctrl-Z
		signal.signal(signal.SIGCONT, now_awake)  # * Resume
		signal.signal(signal.SIGINT, quit_sigint)  # * Ctrl-C
		signal.signal(signal.SIGWINCH, terminal.refresh)  # * terminal resized
	except Exception as e:
		init_screen_widget.fail(e)
	else:
		init_screen_widget.success()

	# ? Start a separate thread for reading keyboard input
	if config.show_init:
		Draw.buffer(
			"+init!",
			f'{Mv.restore}{Fx.trans("Starting input reader thread... ")}{Mv.save}',
		)
	try:
		controller.start()
	except Exception as e:
		init_screen_widget.fail(e)
	else:
		init_screen_widget.success()

	# ? Start a separate thread for data collection and drawing
	if config.show_init:
		Draw.buffer(
			"+init!",
			f'{Mv.restore}{Fx.trans("Starting data collection and drawer thread... ")}{Mv.save}',
		)
	try:
		collector.start()
	except Exception as e:
		init_screen_widget.fail(e)
	else:
		init_screen_widget.success()

	# ? Collect data and draw to buffer
	if config.show_init:
		Draw.buffer(
			"+init!",
			f'{Mv.restore}{Fx.trans("Collecting data and drawing... ")}{Mv.save}',
		)
	try:
		collector.collect(draw_now=False)
		pass
	except Exception as e:
		init_screen_widget.fail(e)
	else:
		init_screen_widget.success()

	# ? Draw to screen
	if config.show_init:
		Draw.buffer("+init!", f'{Mv.restore}{Fx.trans("Finishing up... ")}{Mv.save}')
	try:
		collector.collect_done.wait()
	except Exception as e:
		init_screen_widget.fail(e)
	else:
		init_screen_widget.success()

	init_screen_widget.done()
	terminal.refresh()
	Draw.out(clear=True)
	if CONFIG.draw_clock:
		Box.clock_on = True
	if DEBUG:
		TimeIt.stop("Init")

	# ? Start main loop
	try:
		run_event_loop(terminal, timer, controller, collector)
	except Exception as e:
		errlog.exception(f"{e}")
		clean_quit(1)
	else:
		# ? Quit cleanly even if false starts being true...
		clean_quit()


if __name__ == "__main__":
	# ? Argument parser ------------------------------------------------------------------------------->
	args = argparse.ArgumentParser()
	args.add_argument(
		"-f",
		"--full",
		action="store_true",
		help="Start in full mode showing all boxes [default]",
	)
	args.add_argument(
		"-p",
		"--proc",
		action="store_true",
		help="Start in minimal mode without memory and net boxes",
	)
	args.add_argument(
		"-s",
		"--stat",
		action="store_true",
		help="Start in minimal mode without process box",
	)
	args.add_argument(
		"-v", "--version", action="store_true", help="Show version info and exit"
	)
	args.add_argument(
		"--debug",
		action="store_true",
		help="Start with loglevel set to DEBUG overriding value set in config",
	)
	stdargs = args.parse_args()

	if stdargs.version:
		print(
			f"bpytop version: {VERSION}\n"
			f'psutil version: {".".join(str(x) for x in psutil.version_info)}'
		)
		raise SystemExit(0)

	ARG_MODE: str = ""

	if stdargs.full:
		ARG_MODE = "full"
	elif stdargs.proc:
		ARG_MODE = "proc"
	elif stdargs.stat:
		ARG_MODE = "stat"

	if stdargs.debug:
		DEBUG = True
	else:
		DEBUG = False

	main()
