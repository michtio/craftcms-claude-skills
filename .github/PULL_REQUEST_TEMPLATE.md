## Summary

Brief description of what this PR changes and why.

## Type

- [ ] New skill
- [ ] New reference file (added to existing skill)
- [ ] New plugin reference
- [ ] Skill/reference content fix
- [ ] Agent or project-setup change
- [ ] Documentation / README
- [ ] CI / repo maintenance

## Files changed

<!--
  Common patterns — delete the sections that don't apply:
-->

**Skills (SKILL.md)**
- `skills/{skill-name}/SKILL.md` —

**Reference files**
- `skills/{skill-name}/references/{file}.md` —

**Project setup**
- `skills/craft-project-setup/` —

**Other**
-

## Quality checklist

### Content accuracy
- [ ] Code examples use correct Craft CMS 5.x syntax
- [ ] Code examples use correct Twig 3.x syntax (no `?.` nullsafe — requires Twig 3.23+, Craft 5 ships 3.21)
- [ ] Patterns verified against Craft CMS source code or official docs
- [ ] No deprecated APIs or removed features referenced as current

### Skill structure
- [ ] Follows the existing heading hierarchy and section format
- [ ] Pitfalls are specific and actionable (not generic advice)
- [ ] Uses placeholder names (`YourVendor`, `plugin-handle`, `my-module`) not real vendor names
- [ ] Cross-references related skills/references with "Pair With" sections
- [ ] `WebFetch` guidance included where documentation links are referenced

### Testing
- [ ] Tested with Claude Code on a real Craft CMS project
- [ ] Verified that the target prompt produces correct output with these changes

## Notes

Any additional context for reviewers.
