# Browser Debugging with Chrome DevTools MCP

How to give Claude Code direct browser access to a DDEV site through the Chrome DevTools MCP server: installation, what it can inspect, when to reach for it, and how to log into the Craft control panel on a `*.ddev.site` host. Not to be confused with Craft's own MCP server [5.12+] (the `craft-mcp` skill).

The Chrome DevTools MCP server gives Claude Code direct browser access — inspect pages, read console logs, check network requests, capture screenshots, and interact with the DOM.

## Installation

```bash
claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest
```

Quit and reopen Claude Code to load the new MCP server. Requires Chrome or Chromium running — the MCP server handles the DevTools Protocol connection automatically.

## What it enables

| Capability | Use Case |
|-----------|----------|
| **Page inspection** | Check rendered HTML, verify template output, inspect meta tags |
| **Console logs** | Catch Twig errors, JS exceptions, Garnish initialization failures |
| **Network requests** | Debug 404 assets, failed AJAX calls, Sprig/htmx swaps |
| **DOM queries** | Verify form markup, check field rendering, validate ARIA attributes |
| **Screenshots** | Visual verification of CP templates, responsive testing |
| **Navigation & login** | Authenticate into the CP, navigate to plugin settings/edit pages |

## When to use

- **Front-end template debugging** — 404s, missing assets, broken layouts, SEOmatic meta tag verification
- **CP template verification** — plugin settings pages render correctly, editable tables work, slideout editors load
- **Garnish/JS debugging** — modals, drag-sort, disclosure menus initialize without console errors
- **Sprig/htmx debugging** — watch network requests for htmx swaps, verify response HTML fragments
- **Auth flow testing** — walk through login, registration, password reset end-to-end
- **Read-only mode verification** — confirm settings pages display correctly with `allowAdminChanges` off
- **Visual regression** — screenshot before/after template changes

## CP authentication pattern

DDEV sites are accessible at `https://{project}.ddev.site`. To inspect CP pages:

1. Navigate to `https://{project}.ddev.site/{cpTrigger}`
2. Log in with admin credentials
3. Navigate to the plugin/settings page to inspect
4. Check console for JS errors, inspect DOM for correct markup

## Project setup

The `craft-project-setup` skill offers to install Chrome DevTools MCP during scaffolding. If installed later, run `claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest` from the project root — this writes to the project's `.claude.json`, keeping it project-level.
