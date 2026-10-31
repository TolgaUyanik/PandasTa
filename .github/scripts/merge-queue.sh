#!/usr/bin/env bash
# The merge queue for `dev`: one step for the PR at the head of the line. Run by
# .github/workflows/merge-queue.yml (push to dev, a PR queued, its own re-dispatch) and ci.yml (job `queue`, when a
# PR's CI finishes); merge-queue.yml's header says what it does and why.
# Needs REPO and GH_TOKEN (the job's token: pull-requests and actions write, contents read).
# MQ_TOKEN (environment secret MERGE_QUEUE_TOKEN, the owner's token) is used only for branch
# updates; ci.yml's job has none and dispatches merge-queue.yml (which sets MQ_REQUIRED=1) to
# update a branch. Either runner also dispatches merge-queue.yml after its one CI poll per step.
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

drop() {   # $1 PR, $2 reason; uses the loop's $head; skipped if the PR's head moved since read
  now_head="$(gh pr view "$1" --repo "$REPO" --json headRefOid --jq .headRefOid)" || return 1
  if [ "$now_head" != "$head" ]; then echo "#$1: head moved since this step read it; not dropping"; return 0; fi
  gh pr merge "$1" --repo "$REPO" --disable-auto || return 1
  gh pr comment "$1" --repo "$REPO" --body "Taken out of the merge queue: $2. Fix it, then queue it again with \`gh pr merge $1 --auto --merge\`." || return 1
  echo "#$1 dropped: $2"
}

# The rows come in on fd 3, so no gh call inside the loop can read them from stdin.
while IFS=$'\t' read -r pr ref head cross draft state tests <&3; do
  echo "#$pr: merge state $state, tests $tests"
  if [ "$cross" = "true" ]; then
    drop "$pr" "this workflow cannot update a branch from a fork; update it from dev by hand" || { echo "::error::#$pr: drop failed"; drop_failed=1; }
    continue
  fi
  if [ "$draft" = "true" ] || [ "$state" = "DRAFT" ]; then
    echo "#$pr: draft; skipping it"; continue
  fi
  case "$state" in
    DIRTY) drop "$pr" "it conflicts with dev" || { echo "::error::#$pr: drop failed"; drop_failed=1; }; continue ;;
    UNKNOWN) echo "#$pr: merge state still UNKNOWN after 60 s; skipping it this run"; continue ;;
  esac
  case "$tests" in
    FAILURE|TIMED_OUT|CANCELLED|ACTION_REQUIRED|STARTUP_FAILURE)
      drop "$pr" "its \`tests\` check ended $tests" || { echo "::error::#$pr: drop failed"; drop_failed=1; }; continue ;;
  esac
  if [ "$state" = "BEHIND" ]; then
    if [ -z "${MQ_TOKEN:-}" ]; then
      if [ "${MQ_REQUIRED:-}" = "1" ]; then
        echo "::error::MQ_TOKEN is empty: is MERGE_QUEUE_TOKEN set in the merge-queue environment?"; exit 1
      fi
      # No owner token in a PR's CI: hand the update to merge-queue.yml, which runs on `dev`
      # (the only ref its environment admits). A dispatch is the one GITHUB_TOKEN event that
      # starts a workflow; its concurrency group keeps at most one pending run.
      if ! gh workflow run merge-queue.yml --repo "$REPO" --ref dev; then
        echo "::error::#$pr is behind dev, and dispatching merge-queue.yml failed"; exit 1
      fi
      echo "#$pr is behind dev; merge-queue.yml dispatched to update it"
      exit 0
    fi
    # A rejected token (expired, revoked) must not take every PR out: fail red, drop nothing.
    if ! GH_TOKEN="$MQ_TOKEN" gh api "repos/$REPO" --silent; then
      echo "::error::MERGE_QUEUE_TOKEN was rejected (expired or revoked?); renew it. No PR was taken out."; exit 1
    fi
    # With the owner's token, not GITHUB_TOKEN. Measured on #226: a GITHUB_TOKEN update started a
    # pull_request run that waited for approval, and the PR stayed blocked although a dispatched
    # run passed `tests`. Expected (GitHub's rules, not yet measured here): the owner's update
    # starts pull_request CI like a push. A 422 on a PR that really conflicts drops it, so it does
    # not hold the line; so does an update that is accepted but never lands.
    # A 422 drops the PR only when it then reads as conflicting; a 422 that still reads BEHIND or
    # UNKNOWN, like any other failure, fails red and drops nothing.
    if ! out="$(GH_TOKEN="$MQ_TOKEN" gh api -X PUT "repos/$REPO/pulls/$pr/update-branch" 2>&1)"; then
      if grep -q "HTTP 422" <<<"$out"; then
        # GitHub computes the merge state lazily: give a real conflict up to 60 s to show.
        merge_state="" mergeable=""
        for attempt in $(seq 6); do
          read -r merge_state mergeable < <(gh pr view "$pr" --repo "$REPO" --json mergeStateStatus,mergeable \
            --jq '"\(.mergeStateStatus) \(.mergeable)"' || echo "READ_FAILED READ_FAILED")
          case "$merge_state" in DIRTY|CLEAN|HAS_HOOKS|UNSTABLE|BLOCKED|DRAFT) break ;; esac
          [ "$mergeable" = "CONFLICTING" ] && break
          [ "$attempt" -lt 6 ] && sleep 10
        done
        if [ "$merge_state" = "DIRTY" ] || [ "$mergeable" = "CONFLICTING" ]; then
          drop "$pr" "GitHub refused to update its branch from dev: it conflicts; merge dev into it by hand" || { echo "::error::#$pr: drop failed"; drop_failed=1; }
          continue
        fi
        # No update was needed after all (a stale read of BEHIND): treat it as the main loop does.
        case "$merge_state" in
          DRAFT) echo "#$pr: now a draft; skipping it"; continue ;;
          BLOCKED)
            if [ "$tests" = "SUCCESS" ]; then echo "#$pr: green but blocked; skipping it"; continue; fi
            echo "#$pr: update refused (HTTP 422), but it now reads BLOCKED; its CI end runs the queue"; exit 0 ;;
          CLEAN|HAS_HOOKS|UNSTABLE)
            echo "#$pr: update refused (HTTP 422), but it now reads $merge_state; auto-merge acts"; exit 0 ;;
        esac
        # Still behind (or unknown), refused, and not known to conflict: not retried (a repeating
        # 422 would loop) and not dropped (no evidence against the PR). Red, so it is seen.
        msg="$(jq -r '.message? // empty' 2>/dev/null <<<"${out%%gh:*}" || true)"
        [ -n "$msg" ] || msg="$(grep -m1 '^gh:' <<<"$out" || tail -c 200 <<<"$out")"
        msg="$(tr '\n%' '  ' <<<"$msg")"
        echo "::error::#$pr: update refused (HTTP 422) and it still reads $merge_state/$mergeable: $msg. Re-run this workflow, or update the branch by hand."
        exit 1
      fi
      echo "::error::#$pr: branch update failed, not a conflict (token permissions?): $(tail -c 300 <<<"$out"). No PR was taken out."; exit 1
    fi
    # The update is asynchronous: report only once the head commit has moved.
    now="$head"
    for attempt in $(seq 12); do
      sleep 5
      now="$(gh pr view "$pr" --repo "$REPO" --json headRefOid --jq .headRefOid)"
      [ "$now" != "$head" ] && break
    done
    if [ "$now" = "$head" ]; then
      drop "$pr" "its branch update from dev did not land within 60 s (see the merge-queue run log); merge dev into it by hand" || { echo "::error::#$pr: drop failed"; drop_failed=1; }
      continue
    fi
    echo "#$pr: updated from dev; its pull_request CI runs, and its end runs the queue again"
  elif [ "$tests" = "NONE" ]; then
    # Up to date, no `tests` check on its head. Its ci.yml runs for this head decide:
    #   waiting for approval -> drop (the queue cannot approve);
    #   queued / running     -> wait;
    #   all ended            -> drop (they left no `tests` check);
    #   none                 -> poll up to 3 minutes for one to appear, then drop (never started).
    # (Polling here, not a later run: if CI never starts, no CI end ever runs the queue again.)
    list_runs() {
      gh run list --repo "$REPO" --workflow ci.yml --branch "$ref" --limit 20 --json headSha,status,conclusion \
        --jq "[.[] | select(.headSha == \"$head\") | if .conclusion == \"action_required\" then \"action_required\" else .status end]"
    }
    # Poll once per step (job timeout 20 min): a later PR in the same step hands over to a fresh
    # step instead (dispatched), rather than wait for an unrelated event. Bounded: the earlier PR
    # was dropped (gone from the queue), and the fresh step polls once, then drops or proceeds.
    # If that drop failed, the earlier PR is still queued and would be polled again: stop red.
    if [ -n "${polled:-}" ]; then
      if [ -n "${drop_failed:-}" ]; then
        echo "::error::#$pr: a drop failed earlier in this step; not dispatching (it would repeat)"; exit 1
      fi
      if ! gh workflow run merge-queue.yml --repo "$REPO" --ref dev; then
        echo "::error::#$pr: no CI run yet, and dispatching merge-queue.yml failed"; exit 1
      fi
      echo "#$pr: no CI run yet; merge-queue.yml dispatched to look again"; exit 0
    fi
    polled=1
    runs="$(list_runs)"
    for attempt in $(seq 12); do
      [ "$(jq 'length' <<<"$runs")" != "0" ] && break
      sleep 15
      runs="$(list_runs)"
    done
    if [ "$(jq 'length' <<<"$runs")" = "0" ]; then
      drop "$pr" "no CI run started for $head within 3 minutes; push to it, or re-run CI, then queue it again" || { echo "::error::#$pr: drop failed"; drop_failed=1; }
      continue
    fi
    if [ "$(jq 'map(select(. == "waiting" or . == "action_required")) | length' <<<"$runs")" != "0" ]; then
      drop "$pr" "its CI run for $head waits for approval; approve it in the Actions tab" || { echo "::error::#$pr: drop failed"; drop_failed=1; }
      continue
    fi
    if [ "$(jq 'map(select(. != "completed")) | length' <<<"$runs")" != "0" ]; then
      echo "#$pr: a CI run for $head is still running; waiting"; exit 0
    fi
    drop "$pr" "CI ran on $head but left no \`tests\` check (cancelled before it started?); re-run CI on it" || { echo "::error::#$pr: drop failed"; drop_failed=1; }
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
