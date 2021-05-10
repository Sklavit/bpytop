import logging

import os

from typing import Dict, List, Tuple

from engine.universe.terminal.colors import Color, Colors

reporter = logging.getLogger("reporter")
errlog = logging.getLogger("ErrorLogger")

DEFAULT_THEME: Dict[str, str] = {
	"main_bg" : "",
	"main_fg" : "#cc",
	"title" : "#ee",
	"hi_fg" : "#969696",
	"selected_bg" : "#7e2626",
	"selected_fg" : "#ee",
	"inactive_fg" : "#40",
	"graph_text" : "#60",
	"meter_bg" : "#40",
	"proc_misc" : "#0de756",
	"cpu_box" : "#3d7b46",
	"mem_box" : "#8a882e",
	"net_box" : "#423ba5",
	"proc_box" : "#923535",
	"div_line" : "#30",
	"temp_start" : "#4897d4",
	"temp_mid" : "#5474e8",
	"temp_end" : "#ff40b6",
	"cpu_start" : "#50f095",
	"cpu_mid" : "#f2e266",
	"cpu_end" : "#fa1e1e",
	"free_start" : "#223014",
	"free_mid" : "#b5e685",
	"free_end" : "#dcff85",
	"cached_start" : "#0b1a29",
	"cached_mid" : "#74e6fc",
	"cached_end" : "#26c5ff",
	"available_start" : "#292107",
	"available_mid" : "#ffd77a",
	"available_end" : "#ffb814",
	"used_start" : "#3b1f1c",
	"used_mid" : "#d9626d",
	"used_end" : "#ff4769",
	"download_start" : "#231a63",
	"download_mid" : "#4f43a3",
	"download_end" : "#b0a9de",
	"upload_start" : "#510554",
	"upload_mid" : "#7d4180",
	"upload_end" : "#dcafde",
	"process_start" : "#80d0a3",
	"process_mid" : "#dcd179",
	"process_end" : "#d45454",
}


class Theme:
	"""__init__ accepts a dict containing { "color_element" : "color" }"""

	themes: Dict[str, str] = {}
	cached: Dict[str, Dict[str, str]] = { "Default" : DEFAULT_THEME }
	current: str = ""

	main_bg = main_fg = title = hi_fg = selected_bg = selected_fg = inactive_fg = proc_misc = cpu_box = mem_box = net_box = proc_box = div_line = temp_start = temp_mid = temp_end = cpu_start = cpu_mid = cpu_end = free_start = free_mid = free_end = cached_start = cached_mid = cached_end = available_start = available_mid = available_end = used_start = used_mid = used_end = download_start = download_mid = download_end = upload_start = upload_mid = upload_end = graph_text = meter_bg = process_start = process_mid = process_end = NotImplemented

	gradient: Dict[str, List[str]] = {
		"temp" : [],
		"cpu" : [],
		"free" : [],
		"cached" : [],
		"available" : [],
		"used" : [],
		"download" : [],
		"upload" : [],
		"proc" : [],
		"proc_color" : [],
		"process" : [],
	}
	def __init__(self, theme: str):
		self.refresh()
		self._load_theme(theme)

	def __call__(self, theme: str):
		for k in self.gradient.keys(): self.gradient[k] = []
		self._load_theme(theme)

	def _load_theme(self, theme: str):
		tdict: Dict[str, str]
		if theme in self.cached:
			tdict = self.cached[theme]
		elif theme in self.themes:
			tdict = self._load_file(self.themes[theme])
			self.cached[theme] = tdict
		else:
			errlog.warning(f'No theme named "{theme}" found!')
			theme = "Default"
			tdict = DEFAULT_THEME
		self.current = theme

		if not "graph_text" in tdict and "inactive_fg" in tdict:
			tdict["graph_text"] = tdict["inactive_fg"]
		if not "meter_bg" in tdict and "inactive_fg" in tdict:
			tdict["meter_bg"] = tdict["inactive_fg"]
		if not "process_start" in tdict and "cpu_start" in tdict:
			tdict["process_start"] = tdict["cpu_start"]
			tdict["process_mid"] = tdict.get("cpu_mid", "")
			tdict["process_end"] = tdict.get("cpu_end", "")


		#* Get key names from DEFAULT_THEME dict to not leave any color unset if missing from theme dict
		for item, value in DEFAULT_THEME.items():
			default = False if item not in ["main_fg", "main_bg"] else True
			depth = "fg" if item not in ["main_bg", "selected_bg"] else "bg"
			if item in tdict:
				setattr(self, item, Color(tdict[item], depth=depth, default=default))
			else:
				setattr(self, item, Color(value, depth=depth, default=default))

		#* Create color gradients from one, two or three colors, 101 values indexed 0-100
		self.proc_start, self.proc_mid, self.proc_end = self.main_fg, Colors.null, self.inactive_fg
		self.proc_color_start, self.proc_color_mid, self.proc_color_end = self.inactive_fg, Colors.null, self.process_start

		rgb: Dict[str, Tuple[int, int, int]]
		colors: List[List[int]] = []
		for name in self.gradient:
			rgb = { "start" : getattr(self, f'{name}_start').dec, "mid" : getattr(self, f'{name}_mid').dec, "end" : getattr(self, f'{name}_end').dec }
			colors = [ list(getattr(self, f'{name}_start')) ]
			if rgb["end"][0] >= 0:
				r = 50 if rgb["mid"][0] >= 0 else 100
				for first, second in ["start", "mid" if r == 50 else "end"], ["mid", "end"]:
					for i in range(r):
						colors += [[rgb[first][n] + i * (rgb[second][n] - rgb[first][n]) // r for n in range(3)]]
					if r == 100:
						break
				self.gradient[name] += [Color.fg(*color) for color in colors]

			else:
				c = Color.fg(*rgb["start"])
				for _ in range(101):
					self.gradient[name] += [c]

	@classmethod
	def refresh(cls):
		'''Sets themes dict with names and paths to all found themes'''
		cls.themes = { "Default" : "Default" }
		try:
			for d in (THEME_DIR, USER_THEME_DIR):
				if not d: continue
				for f in os.listdir(d):
					if f.endswith(".theme"):
						cls.themes[f'{"" if d == THEME_DIR else "+"}{f[:-6]}'] = f'{d}/{f}'
		except Exception as e:
			errlog.exception(str(e))

	@staticmethod
	def _load_file(path: str) -> Dict[str, str]:
		'''Load a bashtop formatted theme file and return a dict'''
		new_theme: Dict[str, str] = {}
		try:
			with open(path, "r") as f:
				for line in f:
					if not line.startswith("theme["): continue
					key = line[6:line.find("]")]
					s = line.find('"')
					value = line[s + 1:line.find('"', s + 1)]
					new_theme[key] = value
		except Exception as e:
			errlog.exception(str(e))

		return new_theme


MENUS: Dict[str, Dict[str, Tuple[str, ...]]] = {
	"options" : {
		"normal" : (
			"┌─┐┌─┐┌┬┐┬┌─┐┌┐┌┌─┐",
			"│ │├─┘ │ ││ ││││└─┐",
			"└─┘┴   ┴ ┴└─┘┘└┘└─┘"),
		"selected" : (
			"╔═╗╔═╗╔╦╗╦╔═╗╔╗╔╔═╗",
			"║ ║╠═╝ ║ ║║ ║║║║╚═╗",
			"╚═╝╩   ╩ ╩╚═╝╝╚╝╚═╝") },
	"help" : {
		"normal" : (
			"┬ ┬┌─┐┬  ┌─┐",
			"├─┤├┤ │  ├─┘",
			"┴ ┴└─┘┴─┘┴  "),
		"selected" : (
			"╦ ╦╔═╗╦  ╔═╗",
			"╠═╣║╣ ║  ╠═╝",
			"╩ ╩╚═╝╩═╝╩  ") },
	"quit" : {
		"normal" : (
			"┌─┐ ┬ ┬ ┬┌┬┐",
			"│─┼┐│ │ │ │ ",
			"└─┘└└─┘ ┴ ┴ "),
		"selected" : (
			"╔═╗ ╦ ╦ ╦╔╦╗ ",
			"║═╬╗║ ║ ║ ║  ",
			"╚═╝╚╚═╝ ╩ ╩  ") }
}
MENU_COLORS: Dict[str, Tuple[str, ...]] = {
	"normal" : ("#0fd7ff", "#00bfe6", "#00a6c7", "#008ca8"),
	"selected" : ("#ffa50a", "#f09800", "#db8b00", "#c27b00")
}