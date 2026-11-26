# Craft 5.12 Twig Changes [changed 5.12]

[changed 5.12] What changed for template authors in Craft 5.12: the case filters now follow the site language, and the Twig upgrade from 3.28 to 3.30/3.31 brings macro deprecations and stricter filters. Read this when upgrading a site to 5.12 or writing templates that must also run on older releases.

## Case Filters Follow the Site Language [changed 5.12]

Craft overrides Twig's `upper`, `lower`, `title` and `capitalize` filters with
ICU casing for the current app language (the site's language on front-end
requests, the user's CP language in the CP), and NFC-normalizes the string.
[changed 5.12] Before 5.12: they were Twig's locale-neutral `mb_*` versions. No template changes,
but output does on some languages. Observed in a runtime check:

| Site language | Template | Output | With `('en')` |
|---|---|---|---|
| `tr` | `'istanbul'\|upper` | `İSTANBUL` | `ISTANBUL` |
| `tr` | `'ISTANBUL'\|lower` | `ıstanbul` | `istanbul` |
| `nl` | `'ijsland'\|title` | `IJsland` | `Ijsland` |
| `el` | `'άλφα'\|upper` | `ΑΛΦΑ` (accent dropped) | `ΆΛΦΑ` |

Other languages with their own ICU casing rules (Azerbaijani, Lithuanian) can
change too. Each filter takes an optional `language` argument [5.12+]:

```twig
{{ product.sku|upper('en') }}         {# locale-neutral codes and identifiers #}
{{ heading|upper }}                   {# site language: right for display copy #}
{{ heading|title(currentSite.language) }}
```

- Pass a neutral language (`'en'`) for codes, SKUs, handles, CSS-class or
  ID fragments built with `|lower`, and anything compared against stored values.
- Leave display copy on the default: the new casing is what the language expects.
- [5.12+] Before 5.12: the filters take no argument, so templates shared with older sites
  can't pass one. Audit `|upper`/`|lower` on tr/az/nl/el/lt sites when upgrading.

## Twig 3.29 to 3.31 [5.12+]

Craft 5.12.0 ships Twig 3.30 and [5.12.3+] Twig 3.31.1 (before 5.12: Twig 3.28).
What template authors see:

- **Macro deprecations** (Twig 3.29, errors in Twig 4): calling a macro without
  parentheses (`{{ forms.field }}` → `{{ forms.field() }}`), calling it with a
  different letter case than its definition, defining the same macro twice in a
  template, passing unknown extra arguments to a macro without a variadic
  argument, and omitting an argument that has no default.
- **`include()`'s `sandboxed` argument** is deprecated (Twig 3.29).
- **`matches`** throws on a PCRE error instead of returning false (Twig 3.29).
- **`split`, `random`, `shuffle`, `reverse`** throw a clear error on invalid
  UTF-8 (Twig 3.30).
- **`spaceless`**: the `{% spaceless %}` tag doesn't exist in Twig 3 (unknown tag,
  hard error, not a change in Craft). The `|spaceless` filter (and
  `{% apply spaceless %}`) still works but has been deprecated since Twig 3.12;
  Craft's own CP templates are the last core user of it [5.12.4+]. Use `{%-`/`-%}`
  whitespace control instead.
- Twig's `E_USER_DEPRECATED` notices are not recorded in Craft's deprecation
  log (confirmed for `|spaceless` in a runtime check), so these deprecations are
  silent until Twig 4. Grep for them instead of waiting for warnings.

