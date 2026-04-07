# Git Workflow

- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `docs:`, `test:`, `chore:`.
- Single-line: `git add path/to/files && git commit -m "type(scope): description"`.
- `--amend` for fixes to the most recent unpushed commit. New commit once pushed.
- Run `ddev composer check-cs` and `ddev composer phpstan` before every commit.
- All comments, commit messages, and documentation in English only.
