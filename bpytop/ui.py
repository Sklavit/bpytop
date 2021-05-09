from typing import Dict, Tuple

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