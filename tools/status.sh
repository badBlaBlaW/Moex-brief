#!/usr/bin/env bash
# Whole-system status in one call, a few lines. Replaces 4 separate queries.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
REPO="badBlaBlaW/Moex-brief"
git fetch -q origin 2>/dev/null
echo "repo     $(git rev-parse --short origin/main)  private=$(gh api "repos/$REPO" --jq .private 2>/dev/null)"
echo "briefs   $(git ls-tree --name-only origin/main briefs/ 2>/dev/null | grep -c "[0-9]\{4\}-" ) published"
echo "config   $(git show origin/main:config.json 2>/dev/null | tr -d ' \n')"
echo "listener $(gh api "repos/$REPO/actions/runs" --jq '[.workflow_runs[]|select(.name=="Mark is listening" and .status!="completed")]|length' 2>/dev/null) live, head $(gh api "repos/$REPO/actions/runs" --jq '[.workflow_runs[]|select(.name=="Mark is listening" and .status!="completed")][0].head_sha[0:7] // "none"' 2>/dev/null)"
echo "last run $(gh api "repos/$REPO/actions/runs" --jq '.workflow_runs[0] | "\(.name) \(.status)/\(.conclusion // "running")"' 2>/dev/null)"
