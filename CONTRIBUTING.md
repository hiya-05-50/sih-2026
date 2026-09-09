# Contributing to SAFIRE

## Branching Strategy

We use a **trunk-based** workflow on `main` with short-lived feature branches.

```
main                    ← always deployable
 └── feat/<name>        ← feature branches (short-lived)
 └── fix/<name>         ← bug fix branches
 └── docs/<name>        ← documentation-only changes
```

### Rules

1. **Never push directly to `main`.** Always use a pull request.
2. Feature branches must be **short-lived** (< 2 days).
3. Rebase onto `main` before merging — keep history linear.

> **Note:** This policy applies from Sprint 0 onward. Earlier commits were
> made directly to `main` during initial repository setup. The team should
> enable GitHub branch protection on `main` to enforce this rule.

## Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code restructuring, no behavior change |
| `test` | Adding or updating tests |
| `chore` | Build, tooling, dependency updates |
| `ci` | CI/CD pipeline changes |

### Scopes

Use the top-level directory: `backend`, `frontend`, `shared`, `tests`, `docs`, `infra`.

**Examples:**
```
feat(backend): add GET /health endpoint
fix(frontend): correct sidebar layout overflow
docs(shared): document ModelCapability enum values
ci: add GitHub Actions lint workflow
chore(backend): update fastapi to 0.115
```

## Pull Request Process

1. Create a feature branch from `main`.
2. Make your changes. Keep PRs small and focused.
3. Ensure all checks pass locally before requesting review.
4. Request review from at least one team member.
5. Address review feedback.
6. Squash-merge into `main`.

## Code Style

- **Python:** Formatted by [Ruff](https://docs.astral.sh/ruff/). Config in `backend/pyproject.toml`.
- **TypeScript:** Formatted by ESLint + Prettier. Config in `frontend/`.
- **EditorConfig:** Shared settings in `.editorconfig` — install the plugin for your editor.

## Environment Setup

1. Copy `.env.example` → `.env`
2. Fill in your local values
3. **Never commit `.env`** — it is gitignored
