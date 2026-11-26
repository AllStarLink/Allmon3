"""Root-configured optional add-ins. The base package has no audio dependency."""
import configparser
import importlib
import importlib.util
from pathlib import Path
import re


def load(web_config, node_config, security, directory='/etc/allmon3/addons.d'):
    result = []
    for path in sorted(Path(directory).glob('*.ini')):
        config = configparser.ConfigParser(interpolation=None)
        with path.open() as stream:
            config.read_file(stream)
        if not config.getboolean('addon', 'enabled', fallback=False):
            continue
        module = config.get('addon', 'module')
        factory = config.get('addon', 'factory')
        if not re.fullmatch(r'asl_allmon\.[a-z_]+', module) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', factory):
            raise ValueError('Invalid add-in registration')
        if importlib.util.find_spec(module) is None:
            continue  # Optional package removed; preserved conffile is harmless.
        result.append(getattr(importlib.import_module(module), factory)(web_config, node_config, security))
    return result
