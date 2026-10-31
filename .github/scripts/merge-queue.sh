#!/usr/bin/env bash
# The merge queue for `dev`: one step for the PR at the head of the line. Run by
# .github/workflows/merge-queue.yml (push to dev, a PR queued) and ci.yml (job `queue`, when a
# PR's CI finishes); merge-queue.yml's header says what it does and why.
# Needs REPO and GH_TOKEN (the job's token: pull-requests write, contents and actions read).
# MQ_TOKEN (environment secret MERGE_QUEUE_TOKEN, the owner's token) is used only for branch
# updates; ci.yml's job has none and leaves updates to merge-queue.yml, which sets MQ_REQUIRED=1.
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
    if [ -z "${MQ_TOKEN:-}" ]; then
      if [ "${MQ_REQUIRED:-}" = "1" ]; then
        echo "::error::MQ_TOKEN is empty: is MERGE_QUEUE_TOKEN set in the merge-queue environment?"; exit 1
      fi
      echo "::notice::#$pr is behind dev; this job has no owner token, so merge-queue.yml updates it (next push to dev or queueing)"
      exit 0
    fi
    # A rejected token (expired, revoked) must not take every PR out: fail red, drop nothing.
    if ! GH_TOKEN="$MQ_TOKEN" gh api "repos/$REPO" --silent; then
      echo "::error::MERGE_QUEUE_TOKEN was rejected (expired or revoked?); renew it. No PR was taken out."; exit 1
    fi
    # With the owner's token, not GITHUB_TOKEN. Measured on #226: a GITHUB_TOKEN update started a
    # pull_request run that waited for approval, and the PR stayed blocked although a dispatched
    # run passed `tests`. Expected (GitHub's rules, not yet measured here): the owner's update
    # starts pull_request CI like a push. Refused on a conflict GitHub had not computed yet: drop
    # it, so it does not hold the line. The same if the update is accepted but never lands.
    if ! GH_TOKEN="$MQ_TOKEN" gh api -X PUT "repos/$REPO/pulls/$pr/update-branch" --silent; then
      drop "$pr" "updating its branch from dev failed (a conflict, or the token; see the merge-queue run log); merge dev into it by hand" || echo "::error::#$pr: drop failed"
      continue
    fi
    # The update is asynchronous: report only once the head commit has moved.
    now="$head"
    for attempt in $(seq 12); do
      sleep 5
      now="$(gh pr view "$pr" --repo "$REPO" --json headRefOid --jq .headRefOid)"
      [ "$now" != "$head" ] && break
    done
    if [ "$now" = "$head" ]; then
      drop "$pr" "its branch update from dev did not land within 60 s (see the merge-queue run log); merge dev into it by hand" || echo "::error::#$pr: drop failed"
      continue
    fi
    echo "#$pr: updated from dev; its pull_request CI runs, and its end runs the queue again"
  elif [ "$tests" = "NONE" ]; then
    # Up to date, no `tests` check on its head. Its ci.yml runs for this head decide:
    #   waiting for approval -> drop (the queue cannot approve);
    #   queued / running     -> wait;
    #   all ended            -> drop (they left no `tests` check);
    #   none, head < 10 min  -> wait (CI not registered yet); none, older -> drop (never started).
    runs="$(gh run list --repo "$REPO" --workflow ci.yml --branch "$ref" --limit 20 --json headSha,status \
              --jq "[.[] | select(.headSha == \"$head\") | .status]")"
    if [ "$(jq 'map(select(. == "waiting" or . == "action_required")) | length' <<<"$runs")" != "0" ]; then
      drop "$pr" "its CI run for $head waits for approval; approve it in the Actions tab" || echo "::error::#$pr: drop failed"
      continue
    fi
    if [ "$(jq 'map(select(. != "completed")) | length' <<<"$runs")" != "0" ]; then
      echo "#$pr: a CI run for $head is still running; waiting"; exit 0
    fi
    if [ "$(jq 'length' <<<"$runs")" = "0" ]; then
      committed="$(gh api "repos/$REPO/commits/$head" --jq .commit.committer.date)"
      age=$(( $(date -u +%s) - $(date -u -d "$committed" +%s) ))
      if [ "$age" -lt 600 ]; then
        echo "::notice::#$pr: no CI run for $head yet (head is ${age} s old); waiting"; exit 0
      fi
      drop "$pr" "no CI run started for $head within 10 minutes; push to it, or re-run CI, then queue it again" || echo "::error::#$pr: drop failed"
      continue
    fi
    drop "$pr" "CI ran on $head but left no \`tests\` check (cancelled before it started?); re-run CI on it" || echo "::error::#$pr: drop failed"
    continue
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
