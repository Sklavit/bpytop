import os

from bpytop.config import CONFIG_DIR

THEME_DIR: str = ""

if os.path.isdir(f'{os.path.dirname(__file__)}/bpytop-themes'):
	THEME_DIR = f'{os.path.dirname(__file__)}/bpytop-themes'
else:
	for td in ["/usr/local/", "/usr/", "/snap/bpytop/current/usr/"]:
		if os.path.isdir(f'{td}share/bpytop/themes'):
			THEME_DIR = f'{td}share/bpytop/themes'
			break
USER_THEME_DIR: str = f'{CONFIG_DIR}/themes'
