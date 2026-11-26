"""Validated optional announcements settings, read during module initialization."""
import configparser
from pathlib import Path
from zoneinfo import ZoneInfo

class AnnouncementConfig:
    def __init__(self, path='/etc/allmon3/announcements.ini'):
        config = configparser.ConfigParser(interpolation=None)
        if Path(path).exists():
            with Path(path).open() as stream:
                config.read_file(stream)
            if set(config.sections()) != {'announcements'} or config.defaults():
                raise ValueError('announcements.ini must contain only an [announcements] section')
        values = dict(config['announcements']) if 'announcements' in config else {}
        allowed = {'max_upload_mb','max_seconds','segment_seconds','gap_seconds','timezone',
                   'release_hour','local_nodes','state_dir','cache_dir'}
        if set(values) - allowed:
            raise ValueError('Unknown announcements setting')
        def integer(name, default, minimum, maximum):
            value = int(values.get(name, default))
            if not minimum <= value <= maximum:
                raise ValueError('Invalid announcements setting: ' + name)
            return value
        self.max_upload = integer('max_upload_mb',100,1,100) * 1024 * 1024
        self.max_seconds = integer('max_seconds',3600,1,3600)
        self.segment_seconds = integer('segment_seconds',150,1,150)
        self.gap_seconds = integer('gap_seconds',15,1,60)
        self.release_hour = integer('release_hour',13,0,23)
        self.timezone = values.get('timezone','system')
        if self.timezone != 'system':
            ZoneInfo(self.timezone)
        self.local_nodes = {int(n) for n in values.get('local_nodes','').replace(',',' ').split()}
        if any(node <= 0 for node in self.local_nodes):
            raise ValueError('local_nodes must contain positive node numbers')
        self.state_dir = values.get('state_dir','/etc/allmon3/audio')
        self.cache_dir = values.get('cache_dir','/var/cache/allmon3')
        if not all(Path(p).is_absolute() for p in [self.state_dir,self.cache_dir]):
            raise ValueError('Announcements directories must be absolute')
