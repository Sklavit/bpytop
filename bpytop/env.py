

# detect system platform
import sys

SYSTEM: str
if "linux" in sys.platform:
	SYSTEM = "Linux"
elif "bsd" in sys.platform:
	SYSTEM = "BSD"
elif "darwin" in sys.platform:
	SYSTEM = "MacOS"
else:
	SYSTEM = "Other"

