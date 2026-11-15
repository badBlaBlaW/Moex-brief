#!/usr/bin/env bash
# One call: commit, push (rebasing if the bot pushed first), optionally restart
# the listener, and print a short summary. Replaces 3-5 round trips.
#   tools/deploy.sh "message"            commit + push
#   tools/deploy.sh "message" --restart  ... and put the listener on the new code
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
MSG="${1:?usage: deploy.sh \"message\" [--restart]}"; RESTART="${2:-}"
REPO="badBlaBlaW/Moex-brief"
AUTHOR=(-c user.name=Claude -c user.email=noreply@anthropic.com)

rm -rf .github/scripts/__pycache__ 2>/dev/null
if [ -z "$(git status --porcelain)" ]; then
  echo "nothing to commit"
else
  git add -A
  git "${AUTHOR[@]}" commit -q -m "$MSG

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01WZf6TGBiN6qrYpHUK8dZtG" || true
fi

for attempt in 1 2 3; do
  if git -c push.negotiate=true push -q origin HEAD:main 2>/dev/null; then
    echo "pushed on attempt $attempt"; break
  fi
  git fetch -q origin && git rebase -q origin/main >/dev/null 2>&1 \
    || { echo "REBASE CONFLICT — stopping"; exit 1; }
  [ "$attempt" = 3 ] && { echo "PUSH FAILED after 3 attempts"; exit 1; }
done

git fetch -q origin
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] \
  && echo "in sync: $(git rev-parse --short HEAD)" || echo "OUT OF SYNC"

if [ "$RESTART" = "--restart" ]; then
  ID=$(gh api "repos/$REPO/actions/runs" \
       --jq '[.workflow_runs[]|select(.name=="Mark is listening" and .status=="in_progress")][0].id' 2>/dev/null)
  [ -n "$ID" ] && [ "$ID" != "null" ] && gh api -X POST "repos/$REPO/actions/runs/$ID/cancel" >/dev/null 2>&1 \
    && echo "listener handing over (was $ID)" || echo "no live listener to restart"
fi
