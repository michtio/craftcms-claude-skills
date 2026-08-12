---
name: craft-plugin-release
description: "Releasing Craft CMS plugins — tagging, Packagist propagation, GitHub releases, branch promotion, shared-library ordering, history rewrites. ALWAYS load when cutting, preparing, verifying, or debugging a plugin release: bumping a version, dating a changelog, creating or moving a git tag, or checking what Packagist serves. Covers the composer.json version key (bump-or-omit trade-off, same-commit rule, verifying the tag's own blob), Packagist verification via repo.packagist.org/p2, the 'Skipped tag' silent failure, the tag recreation risk model (unserved safe, served never), GitHub release objects drifting from tags, gh api PATCH wiping tag_name, blank bodies from empty --notes-file, the create-release.yml Store dispatch (422 already_exists, allowUpdates), shared-library releases dependency-first (additive minors breaking released consumers, module: track invalid), two-way origin comparison, filter-repo purges (already_ran re-runs, --refs/--partial, tree-hash verify, blob-level sweeps), and path repositories (canonical, no exclude, branch-alias, duplicate names). Triggers on: cut/prepare a release, tag a version, Packagist not serving the new version, 'Skipped tag', repo.packagist.org, gh release create/edit, untagged- release, prerelease latest 404, target_commitish, draft release, promote develop to main, release the library first, Invalid migration track, purge a secret from history, filter-repo, path repository, branch-alias. NOT for writing changelog entries, CI workflow YAML (craftcms quality.md), or plugin store listings."
---

# Releasing Craft Plugins

A plugin release involves three independent systems that all claim to describe the same version: **git tags**, **Packagist**, and **GitHub release objects**. They drift from each other silently, and every observable signal can say "success" while consumers get nothing. This skill is the checklist and risk model for keeping them in agreement.

**Core rule: verify what each system actually serves, not what you pushed to it.** A `202 Accepted` from the Packagist webhook, a green tag push, and a rendered releases page each prove nothing about the other two.

## Companion Skills

- **`craft-php-guidelines`** — `references/tooling.md` for commit conventions and composer hygiene of the plugin manifest itself.
- **`craftcms`** — `references/quality.md` for the CI workflows a release depends on (`code-analysis`, `create-release.yml`).
- **`craft-pest`** — the suite must be green from the plugin's own root before tagging.

## The release commit

If the plugin's `composer.json` carries a `version` key, **bumping it is a mandatory release step, in the same commit that dates the changelog.** A tag whose `composer.json` says a different version is silently useless: Packagist reads the manifest from the tag's own tree, sees the mismatch, and skips the tag —

```
Reading composer.json of acme/craft-thing (1.7.4)
Skipped tag 1.7.4, tag (1.7.4.0) does not match version (1.7.3.0) in composer.json
```

— while the GitHub webhook still returns `202 Accepted`. Nothing in the push, the tag, or the webhook response surfaces this. Consumers simply never see the version.

After tagging, verify against the **tag's own blob**, not the branch head:

```bash
git show 1.7.4:composer.json | grep '"version"'
```

The branch can be correct while the tag isn't (the bump landed one commit after the tag), and vice versa.

### The `version` key: bump it or omit it

Composer's schema documentation recommends **omitting** `version` for VCS-distributed packages — the tag is the version, and an explicit key is a drift risk that `composer validate` warns about. Both choices are legitimate; know the trade-off:

- **Omit it**: the entire class of skipped-tag failures disappears. But a version-less package loaded through a `path` repository resolves as `dev-<branch>`, and `version_compare("dev-develop-v5", "5.9.0", ">=")` is **false** — any peer-plugin version check silently fails, and the CP shows a branch name where a version should be. `extra.branch-alias` mitigates this (see `references/path-repositories.md`).
- **Keep it**: local path-repository development gets a real, comparable version. The cost is that every release must bump it, enforced by the same-commit rule and the tag-blob check above. A release script that edits changelog date + `version` together and refuses to tag on mismatch removes the human step.

Present this as a per-plugin decision, not a doctrine — but whichever way a repo goes, it must go all the way: a `version` key that exists and doesn't get bumped is strictly worse than either consistent choice.

## Verifying Packagist

**Check `https://repo.packagist.org/p2/<vendor>/<name>.json`** — the metadata endpoint Composer itself resolves from. Do **not** use `https://packagist.org/packages/<vendor>/<name>.json`; it is served from a staler pipeline and can show a version p2 doesn't have (or lack one it does).

```bash
curl -s https://repo.packagist.org/p2/acme/craft-thing.json | jq -r '.packages["acme/craft-thing"][].version'
```

Compare that list against `git tag --list` — every releasable tag should appear. A tag missing here with no error anywhere is the skipped-tag failure above; fetch the package's update log on packagist.org (or re-trigger the webhook and watch the response body) to see the skip reason.

### The tag risk model

- **Recreating a tag Packagist has never served is safe.** Nothing downstream has cached that version, so delete-and-repush (with the fixed manifest) is the standard remedy for a skipped tag.
- **Moving a tag Packagist HAS served breaks that version permanently.** Composer's metadata and dist archives are cached by reference; a moved served tag means checksum mismatches and split-brain installs. Ship a new patch version instead.

That distinction is the whole model. Before touching any existing tag, check p2 for whether the version was ever served.

## GitHub release objects are not tags

A GitHub *release* is a separate object that references a tag — and the two drift independently. Packagist reads **tags**; humans read the **releases page**. A repo can be tagged several versions past its newest release object, so the releases page lies while Packagist is correct. Verify both:

```bash
git ls-remote --tags origin | tail -5
gh release list --limit 5
```

Editing and publishing pitfalls, each observed in practice:

- **`gh api -X PATCH /repos/O/R/releases/<id>` with only a `body` field wipes `tag_name`** — the release becomes `untagged-<hash>`, silently unbound from its tag. Update notes with `gh release edit <tag> --notes-file <file>` instead, then re-verify `tag_name`, `draft`, `prerelease`, and `target_commitish` on the release object — the edit path shares a call surface with the tag-wiping PATCH.
- **`gh api repos/O/R/releases/latest` returns 404 when every release is a prerelease** — that endpoint excludes prereleases and drafts by design. Not a bug; use `gh release list` instead of chasing it.
- **Publishing a draft release mints its tag from the tip of `target_commitish` at publish time.** Anything pushed to that branch between drafting and publishing lands in the release. Useful when intentional; a footgun when the branch moved. Pin the draft to a SHA, or verify the branch tip immediately before publishing.

### Release notes: verify the body landed

`gh release create <tag> --notes-file <file>` with an **empty file creates a release with a blank body and exits 0.** If the notes were extracted by a shell pipeline that failed, the pipeline's error prints right next to the success URL and the whole thing reads like a win. Always verify:

```bash
gh release view <tag> --json body -q '.body' | wc -c   # near-zero means blank
```

Extract the changelog section with a single regex rather than chained `sed` ranges, which fail obscurely and silently produce nothing:

```bash
perl -0777 -ne 'print $1 if /^## 1\.7\.4 - [0-9-]+\n(.*?)(?=^## |\z)/ms' CHANGELOG.md > /tmp/notes.md
test -s /tmp/notes.md   # refuse to proceed on an empty extraction
```

Fix a bad body with `gh release edit <tag> --notes-file`, then re-verify `tagName`, `isDraft`, `isPrerelease`, and `targetCommitish` as above.

### Plugin Store automation creates the release for you

Craft's standard `create-release.yml` workflow (triggered by a `craftcms/new-release` `repository_dispatch` from Craft Console — see the `craftcms` skill's `quality.md`) **creates the GitHub release itself** when a version is published through the Plugin Store. Two consequences:

- Creating the release by hand first makes the automation fail with `422 already_exists`. Setting `allowUpdates: true` on `ncipollo/release-action` makes either order safe.
- The dispatch only fires for **Store-listed** plugins, so the same repo behaves differently before and after listing: pre-listing you must create releases yourself; post-listing doing so collides with the automation unless `allowUpdates` is set.

## Branch promotion: never trust local refs

When deciding what to promote from a development branch to a release branch, stale local refs produce confidently wrong answers. Always:

```bash
git fetch --prune origin
git rev-list --left-right --count origin/develop...origin/main
```

Compare **origin against origin, in both directions**. A one-way "commits behind" count cannot distinguish *behind* from *diverged*, and cannot detect an *inverted* pair (release branch ahead of the dev branch) — both of which occur in real estates and both of which make a naive promotion destructive.

## Shared libraries: release order and runtime blast radius

When plugins share a library (an SDK package, a kit module), library releases interact with **already-released consumers** through their version constraints. "Additive" describes the API surface, not the runtime.

**Release the dependency first, verify Packagist serves it (p2, as above), then bump and release the consumer.** Tagging a consumer whose code needs an unreleased dependency guarantees red CI — and that is the *mild* version of what follows.

**An additive minor of a library can silently break released consumers.** The observed failure shape, worth checking for before any library release that touches schema:

1. The library adds a column and starts writing to it.
2. Consumers only reach that schema through **their own** migrations — the library has no migration track of its own (see below).
3. Every released consumer's caret constraint (`^1.2`) admits the new minor immediately, so anyone running `composer update` gets new code against old schema.
4. The library's write path wraps everything in `try { … } catch (Throwable $e) { Craft::warning(…) }` as "best-effort bookkeeping" — so the entire write fails on every request, silently, with one log line nobody reads.

The rules that fall out:

- Before releasing a library that adds schema, ask what a **released** consumer on a caret constraint does when it resolves the new minor **before** running any migration. If the answer is "breaks," the change isn't additive, whatever the API diff says.
- A best-effort `catch (Throwable)` around bookkeeping writes converts a schema mismatch into invisible data loss. When a library writes to a schema its consumers own the migrations for, that catch is the hazard, not the safety net.
- Where a consumer must ship a migration to receive a library change, **say so in the library's release notes.** A constraint bump alone changing nothing at runtime is deeply unobvious.

### Library-shipped Yii modules have no CLI migration track

`craft migrate/up --track=module:<handle>` fails with `Invalid migration track`. Craft's `MigrateController` resolves only `craft`, `content`, and `plugin:<handle>` tracks (plus an `EVENT_REGISTER_MIGRATOR` escape hatch that nothing wires up for you) — verified in `craftcms/cms` 5.10.12, `src/console/controllers/MigrateController.php:467`.

So a library-shipped module's migrations reach an install **only** when a consumer plugin runs them from its own dated migration:

```php
// In the consumer plugin's dated migration
\acme\kit\Kit::getInstance()->getMigrator()->up();
```

— and the consumer must also bump its own `schemaVersion`, or that dated migration never runs. Bumping the library constraint alone changes nothing at runtime; each consumer needs a migration + `schemaVersion` bump of its own.

## Release verification checklist

1. Suite green from the plugin's own root; `check-cs` and `phpstan` pass.
2. If the release needs a shared-library bump: the library is released **and served by p2** first.
3. Changelog dated and `composer.json` `version` bumped (if present) **in the same commit**.
4. Tag created; `git show <tag>:composer.json` shows the right version.
5. `repo.packagist.org/p2/<name>.json` lists the new version (allow a minute for the webhook).
6. GitHub release object exists, `tag_name` matches, `prerelease`/`draft` flags correct — and the **body is non-empty**: `gh release view <tag> --json body -q '.body' | wc -c`.
7. If promoting branches first: `git fetch --prune`, two-way `origin...origin` comparison, no unexplained divergence.

## Reference Files

| Task | Read |
|------|------|
| Multi-plugin local dev: path repositories, canonical semantics, branch aliases, duplicate package names | `references/path-repositories.md` |
| Purging content from published history: `git filter-repo` re-runs, `--refs`/`--partial` scoping, tree-hash verification, blob-level sweeps | `references/history-rewrites.md` |
