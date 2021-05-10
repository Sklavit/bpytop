import psutil
from string import Template
from typing import List, Tuple

# ? Variables ------------------------------------------------------------------------------------->
from bpytop.config import VERSION

BANNER_SRC: List[Tuple[str, str, str]] = [
	("#ffa50a", "#0fd7ff", "██████╗ ██████╗ ██╗   ██╗████████╗ ██████╗ ██████╗"),
	("#f09800", "#00bfe6", "██╔══██╗██╔══██╗╚██╗ ██╔╝╚══██╔══╝██╔═══██╗██╔══██╗"),
	("#db8b00", "#00a6c7", "██████╔╝██████╔╝ ╚████╔╝    ██║   ██║   ██║██████╔╝"),
	("#c27b00", "#008ca8", "██╔══██╗██╔═══╝   ╚██╔╝     ██║   ██║   ██║██╔═══╝ "),
	("#a86b00", "#006e85", "██████╔╝██║        ██║      ██║   ╚██████╔╝██║"),
	("#000000", "#000000", "╚═════╝ ╚═╝        ╚═╝      ╚═╝    ╚═════╝ ╚═╝"),
]


CORES: int = psutil.cpu_count(logical=False) or 1
THREADS: int = psutil.cpu_count(logical=True) or 1
