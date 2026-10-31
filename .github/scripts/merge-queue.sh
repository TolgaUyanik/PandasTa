#!/usr/bin/env bash
# The merge queue for `dev`: one step for the PR at the head of the line. Run by
# .github/workflows/merge-queue.yml (push to dev), ci.yml (job `queue`, when a PR's CI finishes)
# and auto-merge-guard.yml (job `queue`, when a PR into dev is queued); merge-queue.yml's header
# says what it does and why. Needs GH_TOKEN (contents, pull-requests, actions: write) and REPO.
set -euo pipefail
owner="${REPO%/*}"; name="${REPO#*/}"

# Queued PRs into dev, oldest auto-merge first, with the state of the `tests` check runs on the
# head commit: NONE (no run), PENDING (any run unfinished, e.g. a re-run), else the latest run's
# conclusion. mergeStateStatus is computed lazily and reads UNKNOWN right after a push, so ask
# again until it settles.
queued() {
  gh api graphql -F owner="$owner" -F name="$name" -f query='
    query($owner:String!,$name:String!){repository(owner:$owner,name:$name){
      pullRequests(states:OPEN,baseRefName:"dev",first:100){nodes{
        number headRefName headRefOid isCrossRepository isDraft mergeStateStatus
        autoMergeRequest{enabledAt}
        commits(last:1){nodes{commit{statusCheckRollup{contexts(first:100){nodes{
          ... on CheckRun{name status conclusion startedAt}}}}}}}}}}}' \
    --jq '[.data.repository.pullRequests.nodes[] | select(.autoMergeRequest != null)]
          | sort_by(.autoMergeRequest.enabledAt) | .[]
          | [.commits.nodes[0].commit.statusCheckRollup.contexts.nodes[]?
             | select(.name == "tests")] as $t
          | [.number, .headRefName, .headRefOid, .isCrossRepository, .isDraft,
             .mergeStateStatus,
             (if ($t | length) == 0 then "NONE"
              elif any($t[]; .status != "COMPLETED") then "PENDING"
              else ($t | sort_by(.startedAt) | last | .conclusion) end)] | @tsv'
}
for attempt in 1 2 3 4 5 6; do
  rows="$(queued)"
  grep -q $'\tUNKNOWN\t' <<<"$rows" || break
  sleep 10
done
if [ -z "$rows" ]; then echo "queue empty"; exit 0; fi

drop() {   # $1 PR, $2 reason
  gh pr merge "$1" --repo "$REPO" --disable-auto || return 1
  gh pr comment "$1" --repo "$REPO" --body "Taken out of the merge queue: $2. Fix it, then queue it again with \`gh pr merge $1 --auto --merge\`." || return 1
  echo "#$1 dropped: $2"
}
dispatch() {   # $1 PR, $2 branch
  if ! gh workflow run ci.yml --repo "$REPO" --ref "$2"; then
    drop "$1" "dispatching CI on its branch failed (see the merge-queue run log)" || echo "::error::#$1: drop failed"
    return 1
  fi
  echo "#$1: CI dispatched on $2"
}

# The rows come in on fd 3, so no gh call inside the loop can read them from stdin.
while IFS=$'\t' read -r pr ref head cross draft state tests <&3; do
  echo "#$pr: merge state $state, tests $tests"
  if [ "$cross" = "true" ]; then
    drop "$pr" "this workflow cannot update a branch from a fork; update it from dev by hand" || echo "::error::#$pr: drop failed"
    continue
  fi
  if [ "$draft" = "true" ] || [ "$state" = "DRAFT" ]; then
    echo "#$pr: draft; skipping it"; continue
  fi
  case "$state" in
    DIRTY) drop "$pr" "it conflicts with dev" || echo "::error::#$pr: drop failed"; continue ;;
    UNKNOWN) echo "#$pr: merge state still UNKNOWN after 60 s; skipping it this run"; continue ;;
  esac
  case "$tests" in
    FAILURE|TIMED_OUT|CANCELLED|ACTION_REQUIRED|STARTUP_FAILURE)
      drop "$pr" "its \`tests\` check ended $tests" || echo "::error::#$pr: drop failed"; continue ;;
  esac
  if [ "$state" = "BEHIND" ]; then
    # Refused when dev changed a workflow file since the branch was cut (GITHUB_TOKEN may not
    # write those), or on a conflict GitHub had not computed yet: drop it, so it does not hold
    # the line. The same if the update is accepted but never lands.
    if ! gh api -X PUT "repos/$REPO/pulls/$pr/update-branch" --silent; then
      drop "$pr" "updating its branch from dev failed (a workflow file changed on dev, or a conflict; see the merge-queue run log); merge dev into it by hand" || echo "::error::#$pr: drop failed"
      continue
    fi
    # The update is asynchronous: dispatch only once the head commit has moved.
    now="$head"
    for attempt in $(seq 12); do
      sleep 5
      now="$(gh pr view "$pr" --repo "$REPO" --json headRefOid --jq .headRefOid)"
      [ "$now" != "$head" ] && break
    done
    if [ "$now" = "$head" ]; then
      drop "$pr" "its branch update from dev did not land within 60 s (likely a workflow file changed on dev); merge dev into it by hand" || echo "::error::#$pr: drop failed"
      continue
    fi
    dispatch "$pr" "$ref" || continue
  elif [ "$tests" = "NONE" ]; then
    # Up to date, no `tests` check on its head: start CI, unless a ci.yml run for this exact
    # head exists already (queued, or one whose check never reached the PR: never loop).
    runs="$(gh run list --repo "$REPO" --workflow ci.yml --branch "$ref" --limit 20 --json headSha,status \
              --jq "[.[] | select(.headSha == \"$head\") | .status]")"
    if [ "$(jq 'map(select(. != "completed")) | length' <<<"$runs")" != "0" ]; then
      echo "#$pr: a CI run for $head is still running; waiting"; exit 0
    fi
    if [ "$(jq 'length' <<<"$runs")" != "0" ]; then
      drop "$pr" "CI ran on $head but left no \`tests\` check (cancelled before it started?); re-run CI on it" || echo "::error::#$pr: drop failed"
      continue
    fi
    dispatch "$pr" "$ref" || continue
  elif [ "$state" = "BLOCKED" ] && [ "$tests" = "SUCCESS" ]; then
    # Green and up to date, yet blocked by something CI cannot fix (a review, an unresolved
    # conversation): let the next PR through instead of holding the line.
    echo "#$pr: green but blocked by something other than CI; skipping it"
    continue
  else
    echo "#$pr: waiting (CI running, or GitHub merges it)"
  fi
  exit 0
done 3<<<"$rows"
echo "no queued PR left to advance"
