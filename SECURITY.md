# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest `1.x` release on `main` | Yes |
| Earlier `1.x` releases | No — upgrade to the latest |
| `1.4.x` branch | No — frozen Craft 5.9 snapshot, no longer maintained |

Fixes land on `main` and ship in the next release. There are no long-term support branches; the pack is content-driven and upgrading is a matter of pulling the latest skills. See [Versioning](README.md#versioning).

## Reporting a Vulnerability

**Please do not open a public issue for a security report.**

Use GitHub's [private vulnerability reporting](https://github.com/michtio/craftcms-claude-skills/security/advisories/new) — it is enabled on this repository and keeps the discussion private until a fix is published.

If you can't use that, email **michael@bleuchaud.com** with `SECURITY` in the subject.

Please include:

- What the issue is and where it lives (file path, skill name, or script).
- How to reproduce it, or the reasoning if it's a design flaw rather than a reproducible bug.
- The impact you think it has, and any suggested fix.

You'll get an acknowledgement within a few days. This is a solo-maintained project, so please allow reasonable time for a fix before public disclosure. Credit is given in the release notes unless you'd rather stay anonymous.

## What's In Scope

This repository ships **instructions for an AI coding agent**, two shell scripts, and a thin PHP library. Each carries a different kind of risk, and the first one is the least obvious.

### Skill content that induces unsafe behavior

Skills are loaded into a Claude Code session and treated as authoritative guidance. Content that causes an agent to take destructive or exfiltrating action is a security issue in this repository even though nothing here "executes" on its own. In scope:

- Instructions that would lead an agent to run destructive commands, disable safety checks, weaken authentication or authorization, or exfiltrate credentials, environment variables, or customer data.
- Prompt-injection payloads embedded in skill or reference content — including anything designed to override a user's instructions or a plugin's own guardrails.
- Code examples with genuine vulnerabilities (SQL injection, unescaped output, missing authorization checks, insecure defaults) that a reader or agent would reasonably copy verbatim into production.

That last category matters because these examples *are* meant to be copied. An insecure snippet in a reference file is a real defect, not a documentation nitpick — report it.

### Installer and uninstaller

`install.sh` and `uninstall.sh` create and remove symlinks under `~/.claude`. Path traversal, symlink attacks, unintended overwrites of files outside `~/.claude/skills` and `~/.claude/agents`, or privilege issues are in scope.

### PHP library

The `src/` package (`Michtio\CraftCmsClaudeSkills\`) requires PHP ^8.2 and has no runtime dependencies. Standard code vulnerabilities apply.

## What's Out of Scope

- **Vulnerabilities in Craft CMS itself.** Report those to Pixel & Tonic — see [Craft's security policy](https://github.com/craftcms/cms/security/policy).
- **Vulnerabilities in the third-party plugins this pack documents.** Report those to the plugin's own maintainer. If our *documentation* recommends an insecure configuration for such a plugin, that is in scope here.
- **Vulnerabilities in Claude Code or the Claude API.** Report those to [Anthropic](https://hackerone.com/anthropic-vdp).
- Anything requiring an attacker to already control the user's machine or their `~/.claude` directory.
- Missing hardening that has no demonstrable impact, and automated-scanner output with no exploit path.

## A Note on Trust

Installing this pack means an AI agent will read and act on its content. That's worth treating like installing a dependency: review what you're adding, prefer tagged releases over arbitrary commits, and check the diff when you update. The `release-validation` workflow verifies that release tags match the manifests, but it cannot vouch for content — that's what review and this reporting channel are for.
