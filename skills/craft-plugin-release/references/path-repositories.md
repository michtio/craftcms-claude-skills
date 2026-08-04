# Composer Path Repositories for Multi-Plugin Development

Local development across several plugins usually means a host project whose `composer.json` points `path` repositories at plugin checkouts. The semantics below are the ones that produce silent, expensive surprises. (For what belongs in the *plugin's own* committed manifest — never `../*` path repos — see the `craft-php-guidelines` skill's `references/tooling.md`, Composer Hygiene.)

## A path repository is canonical

If a `path` repository supplies a package name, that package's Packagist versions are **dropped from the resolution pool entirely**. Composer's own documentation states it verbatim: *"That repository is canonical so the lower priority repo's packages are not installable."*

Consequences:

- A constraint the local checkout can't satisfy is a **hard resolution failure** — never a quiet fallback to the published version. If the host requires `^1.8` and the checkout says `1.7.x`, the resolve fails even though Packagist has `1.8.0`.
- "It resolved fine" therefore means the *local* copy satisfied everything, which is a different claim from "the published package satisfies everything."

## No `exclude` option

A wildcard entry supplies **every** directory under it:

```json
{ "type": "path", "url": "/path/to/plugins/*" }
```

There is no way to carve one directory out — `path` repositories have no `exclude` option. The only escapes are enumerating entries individually or moving the directory out of the wildcard's reach. Plan for this before adopting a wildcard: the first time one checkout needs to be excluded (an experiment, a fork, a broken clone), the wildcard has to be unwound.

## `extra.branch-alias` makes a version-less checkout usable

A checkout whose `composer.json` omits `version` publishes as `dev-<branch>`, which satisfies no numeric constraint (`version_compare("dev-develop", "1.8.0", ">=")` is false, and `^1.0` doesn't match `dev-develop`). A branch alias in the *plugin's* manifest fixes that:

```json
{
    "extra": {
        "branch-alias": {
            "dev-develop": "1.x-dev"
        }
    }
}
```

Two rules that matter in practice:

- **Alias the major line (`1.x-dev`), not the minor (`1.7.x-dev`).** A minor-pinned alias recreates the lockstep-bump treadmill the alias exists to avoid — every minor release means editing the alias in every consumer's resolution path.
- **Alias every branch that gets checked out locally.** An uncovered branch fails resolution hard, and release work *does* check out the release branch. If `develop` and `main` (or `master`, or `develop-v5`) can each be the working checkout, each needs an alias entry.

## Two directories can publish the same package name

Composer does not error when two path-repository directories declare the same `name` — it silently picks whichever satisfies the constraints. Observed failure: a `craft-thing/` and a `craft-thing-584/` (a scratch clone) both declaring `acme/craft-thing`; `composer update --dry-run` was green **because** the scratch clone quietly won, masking a genuinely unsatisfiable constraint in the real checkout.

**A clean resolve is not proof of coverage.** When a wildcard path repo is in play, verify *which* directory won:

```bash
composer show acme/craft-thing | grep -E 'source|path'
```

and keep scratch clones outside the wildcard's directory.
