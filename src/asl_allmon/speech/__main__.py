"""Validate the selected profile without synthesis or transmission."""
import json
from . import load_profile

def main():
    try:
        profile = load_profile()
        print(json.dumps({'model': profile.model, 'piper_bin': profile.binary,
                          'profile': profile.identity, 'sentence_silence': profile.sentence_silence}))
    except Exception as exc:
        raise SystemExit('Speech configuration invalid: ' + str(exc))

if __name__ == '__main__':
    main()
