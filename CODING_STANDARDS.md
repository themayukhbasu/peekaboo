# Coding standards

Agent-facing rules for the peekaboo package. The `code-review` skill reads this file.

## Packaging

uv is the only package manager. Project metadata lives in `pyproject.toml` and the lockfile is `uv.lock`. Install, test, and run the console script with `uv sync` and `uv run`.

## Lint and format

Ruff is the lint and format gate. It is a uv-managed dev dependency, configured under `[tool.ruff]` in `pyproject.toml`, and `uv sync` installs it. Before a pull request, `uv run ruff check` and `uv run ruff format --check` must pass.

The lint selection is Pyflakes (`F`) and pycodestyle's import, statement, and runtime errors (`E4`, `E7`, `E9`): undefined names, unused imports, and syntax problems. Format follows Ruff's defaults for Python (88 columns, double quotes). Markdown is outside this gate. Ruff is not a provider SDK, an agent framework, or a type checker.

## Modules and seams

Use the vocabulary in the `codebase-design` skill: module, interface, seam, adapter, depth.

- Put behaviour behind a small interface. Callers and tests use that interface.
- Add a seam when a second adapter exists. Until then, keep one function or type in the module that owns the decision.
- The config seam is `peekaboo.config.load_config`. It returns a `Config`. Feature code takes that value. The only place that may read the environment (`os.environ`, `os.getenv`, and similar) or a dotenv file is `load_config`.
- Keep a single settings reader. Extend `Config` and `load_config` when a later ticket needs a setting.

## Helpers

If a function exists, call it. Do not paste the same behaviour again at the call site. Delete a helper that nothing calls.

## Pull requests

Keep a pull request near 250 significant lines. Count logic, tests, and user-facing docs. Split a larger change.

## Language

Write user-facing copy in British English. That includes help text, errors a person reads, and documentation.
