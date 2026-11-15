# tools

Small scripts so routine work is one call instead of several, and so the
output that reaches the model is a summary rather than a dump.

| Script | What it does |
|--------|--------------|
| `status.sh` | whole-system status in five lines: repo, briefs, config, listener, last run |
| `deploy.sh "msg" [--restart]` | commit, push with automatic rebase-and-retry, optionally hand the listener onto the new code |

`deploy.sh` retries up to three times because the bot commits `config.json`
from inside Actions, so a push race is normal rather than exceptional.
