# Favorites regression tests

Run from the repository root with Python 3 and Node.js 18 or later.
The API tests require the runtime dependencies `aiohttp`, `aiohttp-session` and `websockets`;
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

HTTP tests bind only to an ephemeral loopback port and use the registered routes,
real cookie-session middleware and simulated credential validation. They cover
login/logout, all-group authorization on both GET endpoints and POST mutations,
route precedence, unchanged list/config/voter responses, malformed requests,
storage errors and custom-path restart persistence. CLI tests execute the actual
argument/config setup block without starting services, checking default/custom
paths and help text. Backup/restore tests use that parsed default path.
