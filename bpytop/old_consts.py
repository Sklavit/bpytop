from typing import Dict, Tuple

#? Units for floating_humanizer function
UNITS: Dict[str, Tuple[str, ...]] = {
	"bit" : ("bit", "Kib", "Mib", "Gib", "Tib", "Pib", "Eib", "Zib", "Yib", "Bib", "GEb"),
	"byte" : ("Byte", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB", "BiB", "GEB")
}