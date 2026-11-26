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
    parser.add_argument('--config', default='/etc/allmon3/allmon3.ini')
    parser.add_argument('--state-dir', default='/var/lib/allmon3/audio-tot')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    directory = Path(args.state_dir)
    if not directory.exists() or not list(directory.glob('*.json')):
        return
    configs = NodeConfigs(args.config)
    guard = TimeoutGuard(directory, ami_command(configs), identities(configs, configs.all_nodes))
    asyncio.run(guard.recover(force=args.force))


if __name__ == '__main__':
    main()
