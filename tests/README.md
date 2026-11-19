# Favorites regression tests

Run from the repository root with Python 3 and Node.js 18 or later.
The API tests require the runtime dependencies `aiohttp` and `websockets`;
no Asterisk instance, radio connection, or live credentials are needed.

```sh
python3 -m unittest discover -s tests -v
node --test tests/test_commands_favorites.js
node --check web/js/commands.js
git diff --check
```

Coverage includes per-source persistence, rename/delete, conflicts and damaged
files, anonymous/restricted-user access, row/manual Node # preservation,
HTML-safe labels, and successive additions without replacing earlier favorites.

Group coverage includes startup union and conflict rollback, bidirectional
rename/delete and restart persistence, unaffected ungrouped nodes, concurrent
writes, malformed/overlapping groups, unmanaged members, group-wide access
checks, and UI scope disclosure with stale-response protection.
