"""Shared Piper profile selection. Does not dispatch audio or change Asterisk."""
import configparser
from dataclasses import dataclass
import hashlib
import json
from fractions import Fraction
import os
from pathlib import Path
import re

CONFIG = '/etc/allmon3/speech.ini'
DEFAULT_BIN = '/usr/bin/piper'
DEFAULT_DIR = '/var/lib/piper-tts'
DEFAULT_VOICE = 'en_US-amy-low'
FILTER = 'aresample=8000,volume=4/3,alimiter=limit=0.95:level=false:latency=true'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


@dataclass(frozen=True)
class SpeechProfile:
    binary: str
    model: str
    model_sha256: str
    json_sha256: str
    backend: str = 'asl3'
    length_scale: str = '1.25'
    volume: str = '0.8'
    sentence_silence: str = '0.18'
    gain: str = '4/3'
    limiter: str = '0.95'

    @property
    def identity(self):
        values = {**self.__dict__, 'filter': self.audio_filter, 'format': '8000-mono-mulaw', 'revision': 4}
        return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()

    def check_model(self):
        # A running service must not render a replaced model under its old cache key.
        if digest(self.model) != self.model_sha256 or digest(self.model + '.json') != self.json_sha256:
            raise ValueError('Speech model changed: restart Allmon3 at audio idle to load the new profile')

    @property
    def audio_filter(self):
        return (('volume=' + self.volume + ',' if self.backend == 'asl3' else '') +
                'aresample=8000,volume=' + self.gain + ',alimiter=limit=' + self.limiter + ':level=false:latency=true')

    def command(self, output):
        if self.backend == 'asl3':
            return ['nice','-n','10',self.binary,'--model',self.model,
                    '--length_scale',self.length_scale,'--sentence_silence',self.sentence_silence,
                    '--output_file',str(output)]
        return ['nice','-n','10',self.binary,'--model',self.model,
                '--length-scale',self.length_scale,'--volume',self.volume,
                '--sentence-silence',self.sentence_silence,'--output-file',str(output)]


def load_profile(path=CONFIG, legacy=None, environ=None):
    """INI configuration is authoritative; no environment-variable configuration.

    An existing but malformed/unreadable config is an error, never a silent fallback.
    """
    legacy = legacy or {}
    settings = {}
    environ = os.environ if environ is None else environ
    path = Path(path)
    if path.exists():
        config = configparser.ConfigParser(interpolation=None)
        with path.open() as stream:
            config.read_file(stream)
        if set(config.sections()) != {'speech'} or config.defaults():
            raise ValueError('speech.ini must contain only a [speech] section')
        settings = config['speech']
        if set(settings) - {'voice', 'model_dir', 'piper_bin', 'backend', 'length_scale', 'volume', 'sentence_silence', 'gain', 'limiter'}:
            raise ValueError('Unknown speech.ini setting')
        voice = settings.get('voice', '')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}', voice):
            raise ValueError('Set speech.voice to an installed voice name (without path or .onnx)')
        directory = Path(settings.get('model_dir', DEFAULT_DIR))
        if not directory.is_absolute():
            raise ValueError('Speech model_dir must be absolute')
        binary = settings.get('piper_bin', DEFAULT_BIN)
        model = str(directory / (voice + '.onnx'))
    else:
        binary = legacy.get('piper_bin') or DEFAULT_BIN
        model = legacy.get('piper_model') or str(Path(DEFAULT_DIR)/(DEFAULT_VOICE+'.onnx'))
    if not Path(binary).is_absolute() or not Path(binary).is_file() or not os.access(binary, os.X_OK):
        raise ValueError('Piper executable is missing or not executable')
    if not Path(model).is_absolute() or not Path(model).is_file() or not model.endswith('.onnx'):
        raise ValueError('Piper voice model is missing or invalid')
    companion = Path(model + '.json')
    with companion.open() as stream:
        metadata = json.load(stream)
    if not isinstance(metadata, dict) or not metadata:
        raise ValueError('Piper voice configuration must be a non-empty JSON object')
    backend = settings.get('backend','asl3')
    if backend not in {'asl3','python'}:
        raise ValueError('speech.backend must be asl3 or python')
    def number(name, default, lower, upper):
        value = settings.get(name, default)
        try:
            parsed = Fraction(value)
        except (ValueError, ZeroDivisionError):
            raise ValueError('Invalid speech setting: ' + name) from None
        if not lower <= parsed <= upper:
            raise ValueError('Speech setting outside range: ' + name)
        return value if name == 'gain' else str(float(parsed))
    return SpeechProfile(binary, model, digest(model), digest(companion), backend,
                         number('length_scale','1.25',0.5,2), number('volume','0.8',0,2),
                         number('sentence_silence','0.18',0,2), number('gain','4/3',0,4),
                         number('limiter','0.95',0.0625,1))
