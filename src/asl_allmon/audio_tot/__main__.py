"""Recovery only: never creates leases and never disables a timer."""
import argparse
import asyncio
import logging
from pathlib import Path
from . import TimeoutGuard, ami_command, identities
from ..node_configs import NodeConfigs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    directory = Path('/var/lib/allmon3/audio-tot')
    if not directory.exists() or not list(directory.glob('*.json')):
        return
    configs = NodeConfigs('/etc/allmon3/allmon3.ini')
    guard = TimeoutGuard(directory, ami_command(configs), identities(configs, configs.all_nodes))
    asyncio.run(guard.recover(force=args.force))


if __name__ == '__main__':
    main()
