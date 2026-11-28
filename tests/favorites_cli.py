"""Run the executable's argument/config setup without starting node services."""

import argparse
import ast
import logging
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def cli_config(*arguments):
    tree = ast.parse((ROOT / 'src/allmon3').read_text())
    # Execute the actual Args and Log Setup block through the configuration
    # defaults, stopping before the first file read / service startup.
    start = next(i for i, node in enumerate(tree.body)
                 if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'ap' for t in node.targets))
    end = next(i for i in range(start, len(tree.body)) if isinstance(tree.body[i], ast.Try))
    setup = ast.Module(body=tree.body[start:end], type_ignores=[])
    scope = {'argparse': argparse, 'logging': logging, '_BUILD_ID': 'test'}
    loggers = [logging.getLogger('allmon3'), logging.getLogger('asl_allmon')]
    previous = [(logger, list(logger.handlers), logger.level) for logger in loggers]
    try:
        with patch.object(sys, 'argv', ['allmon3', *arguments]):
            exec(compile(setup, str(ROOT / 'src/allmon3'), 'exec'), scope)
        return scope
    finally:
        for logger, handlers, level in previous:
            logger.handlers[:] = handlers
            logger.setLevel(level)
