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
import psutil
import signal

from bpytop.config import *

from bpytop.collectors import Collector, Cpucollector
from bpytop.config import CONFIG, VERSION, errlog
from bpytop.debug_utils import TimeIt
from bpytop.event_loop import Timer, run_event_loop
from bpytop.main_mvc import Controller, MainWidget
from bpytop.old_classes import (
	Init,
	Theme,
	UpdateChecker,
)
from bpytop.old_functions import (
	clean_quit, get_cpu_name, now_awake, now_sleeping, quit_sigint,
)
from bpytop.terminal_engine import Draw
from bpytop.terminal_widgets import Box, Fx

#? Argument parser ------------------------------------------------------------------------------->
args = argparse.ArgumentParser()
args.add_argument("-f" , "--full"		,action="store_true" ,help ="Start in full mode showing all boxes [default]")
args.add_argument("-p" , "--proc"		,action="store_true" ,help ="Start in minimal mode without memory and net boxes")
args.add_argument("-s" , "--stat"		,action="store_true" ,help ="Start in minimal mode without process box")
args.add_argument("-v" , "--version"	,action="store_true" ,help ="Show version info and exit")
args.add_argument("--debug"				,action="store_true" ,help ="Start with loglevel set to DEBUG overriding value set in config")
stdargs = args.parse_args()

if stdargs.version:
	print(f'bpytop version: {VERSION}\n'
		f'psutil version: {".".join(str(x) for x in psutil.version_info)}')
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

#? Pre main -------------------------------------------------------------------------------------->

CPU_NAME: str = get_cpu_name()

THEME: Theme


def main():
	config = CONFIG(DEBUG)

	controller = Controller()
	timer = Timer(update_ms=config.update_ms, controller=controller)
	collector = Collector()

	global THEME

	#? Init -------------------------------------------------------------------------------------->
	if DEBUG:
		TimeIt.start("Init")

	main_widget = MainWidget()
	main_widget.init()

	#? Start a thread checking for updates while running init
	if CONFIG.update_check:
		UpdateChecker.run()

	#? Draw banner and init status
	if CONFIG.show_init and not Init.resized:
		Init.start()

	#? Load theme
	if CONFIG.show_init:
		Draw.buffer("+init!", f'{Mv.restore}{Fx.trans("Loading theme and creating colors... ")}{Mv.save}')
	try:
		THEME = Theme(CONFIG.color_theme)
	except Exception as e:
		Init.fail(e)
	else:
		Init.success()

	#? Setup boxes
	if CONFIG.show_init:
		Draw.buffer("+init!", f'{Mv.restore}{Fx.trans("Doing some maths and drawing... ")}{Mv.save}')
	try:
		if CONFIG.check_temp: Cpucollector.get_sensors()
		Box.calc_sizes()
		Box.draw_bg(now=False)
	except Exception as e:
		Init.fail(e)
	else:
		Init.success()

	#? Setup signal handlers for SIGSTP, SIGCONT, SIGINT and SIGWINCH
	if CONFIG.show_init:
		Draw.buffer("+init!", f'{Mv.restore}{Fx.trans("Setting up signal handlers... ")}{Mv.save}')
	try:
		signal.signal(signal.SIGTSTP, now_sleeping) #* Ctrl-Z
		signal.signal(signal.SIGCONT, now_awake)	#* Resume
		signal.signal(signal.SIGINT, quit_sigint)	#* Ctrl-C
		signal.signal(signal.SIGWINCH, terminal.refresh) #* terminal resized
	except Exception as e:
		Init.fail(e)
	else:
		Init.success()

	#? Start a separate thread for reading keyboard input
	if CONFIG.show_init:
		Draw.buffer("+init!", f'{Mv.restore}{Fx.trans("Starting input reader thread... ")}{Mv.save}')
	try:
		controller.start()
	except Exception as e:
		Init.fail(e)
	else:
		Init.success()

	#? Start a separate thread for data collection and drawing
	if CONFIG.show_init:
		Draw.buffer("+init!", f'{Mv.restore}{Fx.trans("Starting data collection and drawer thread... ")}{Mv.save}')
	try:
		collector.start()
	except Exception as e:
		Init.fail(e)
	else:
		Init.success()

	#? Collect data and draw to buffer
	if CONFIG.show_init:
		Draw.buffer("+init!", f'{Mv.restore}{Fx.trans("Collecting data and drawing... ")}{Mv.save}')
	try:
		collector.collect(draw_now=False)
		pass
	except Exception as e:
		Init.fail(e)
	else:
		Init.success()

	#? Draw to screen
	if CONFIG.show_init:
		Draw.buffer("+init!", f'{Mv.restore}{Fx.trans("Finishing up... ")}{Mv.save}')
	try:
		collector.collect_done.wait()
	except Exception as e:
		Init.fail(e)
	else:
		Init.success()

	Init.done()
	terminal.refresh()
	Draw.out(clear=True)
	if CONFIG.draw_clock:
		Box.clock_on = True
	if DEBUG:
		TimeIt.stop("Init")

	#? Start main loop
	try:
		run_event_loop(terminal, timer, controller, collector)
	except Exception as e:
		errlog.exception(f'{e}')
		clean_quit(1)
	else:
		#? Quit cleanly even if false starts being true...
		clean_quit()


if __name__ == "__main__":
	main()
