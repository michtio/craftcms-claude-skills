# History Rewrites with `git filter-repo`

Purging content (a leaked secret, a file that should never have shipped) from a plugin repo's published history. Everything here was learned on real purges; two of them had to be **re-done** because the first pass missed content, which is the worst outcome — a purge you believe is complete and isn't.

The tag risk model from `SKILL.md` applies with full force: a history rewrite moves **every** tag whose history contains the rewritten commits. If Packagist has served those tags, rewriting them breaks those versions permanently (cached metadata and dists reference the old objects). Decide up front whether the thing being purged is worth that cost — for a live credential it is, and the credential must be rotated regardless, because a purge does not un-leak anything already fetched.

## Sweep at blob level across all history — never from the current tree

A path-scoped purge (`--path <file> --invert-paths`) removes what lives at that path **now and wherever that path existed historically** — but it misses the same content that ever lived at a *different* path which no longer exists at the tip. This has caused two incomplete purges. Find the content itself, not the path you remember it at:

```bash
# Every blob in all history containing the needle, with the paths it lived at
git rev-list --all | while read c; do
  git grep -l 'NEEDLE' $c -- 2>/dev/null | sed "s/^/$c:/"
done | sort -u -t: -k3
```

(or `git log --all -S'NEEDLE' --name-only` for a faster first pass). Build the purge list from *that* output, then run filter-repo with every discovered path — or with `--replace-text` when the needle is a string rather than a whole file.

## Re-runs: `already_ran` and the interactive prompt

A repo that has been filtered before carries `.git/filter-repo/already_ran`. On the next run the tool **prompts interactively** ("Previous run detected — proceed?"):

- Under a non-tty (CI, an agent, a pipe) that prompt is an `EOFError` traceback, not a readable message.
- Piping `Y` past it can then crash with an `AssertionError` in `_compute_metadata`. **That step runs after the rewrite** — so the rewrite has already succeeded by the time the tool crashes. Check the refs before concluding a crash meant no-op; re-running a "failed" rewrite that actually landed compounds the confusion.

## Scope the rewrite

By default filter-repo rewrites all refs and **removes the `origin` remote** as a safety measure. For a targeted purge, scope it:

```bash
git filter-repo --partial --refs refs/heads/develop refs/heads/main \
    --invert-paths --path path/to/leaked-file
```

- `--refs` limits which refs are rewritten.
- `--partial` skips the destructive-cleanup conveniences — it keeps the `origin` remote and leaves other refs alone.

Remember tags are refs too: a scoped rewrite that omits `refs/tags/*` leaves the purged content reachable through every tag. For a secret purge that's a hole, not a scoping win — include the tags and accept the served-tag consequences, or the purge is cosmetic.

## Verify: compare tip tree hashes

The assertion a purge needs is "shipped content is unchanged, history differs." The tree hash proves it:

```bash
git rev-parse HEAD^{tree}   # before the rewrite (record it)
git rev-parse HEAD^{tree}   # after — identical hash = byte-for-byte identical tip content
```

Identical tree hashes with different commit hashes is exactly right. A *changed* tree hash means the rewrite altered current content — stop and diff before pushing anything.

Then verify the needle is actually gone from all history (`git log --all -S'NEEDLE'` returns nothing), and only then force-push — followed by the Packagist/GitHub verification pass from `SKILL.md`, since every downstream system now disagrees with the repo.
