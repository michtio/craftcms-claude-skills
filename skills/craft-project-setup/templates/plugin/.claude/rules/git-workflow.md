# Git Workflow

- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `docs:`, `test:`, `chore:`.
- Single-line: `git add path/to/files && git commit -m "type(scope): description"`.
- `--amend` for fixes to the most recent unpushed commit. New commit once pushed.
- Run `ddev composer check-cs` and `ddev composer phpstan` before every commit.
- No AI attribution in commit messages. No "Co-Authored-By" lines referencing AI tools.
- All comments, commit messages, and documentation in English only.
