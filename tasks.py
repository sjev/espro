# type: ignore
from invoke import task


@task
def venv(ctx):
    """Initialize development environment with uv workspace."""
    print("Initializing development environment with uv...")

    # Sync uv workspace (creates .venv and installs all workspace members)
    ctx.run("uv sync")

    print("Development environment initialization complete!")


@task
def clean(ctx):
    """
    Remove all files and directories that are not under version control to ensure a pristine working environment.
    Use caution as this operation cannot be undone and might remove untracked files.

    """

    ctx.run("git clean -nfdx")

    response = (
        input("Are you sure you want to remove all untracked files? (y/n) [n]: ")
        .strip()
        .lower()
    )
    if response == "y":
        ctx.run("git clean -fdx")


@task
def lint(ctx):
    """
    Perform static analysis on the source code to check for syntax errors and enforce style consistency.
    """
    ctx.run("ruff check src", pty=True)
    ctx.run("ruff format --check src", pty=True)
    ctx.run("mypy src", pty=True)


@task
def test(ctx):
    """
    Run tests with coverage information.
    """
    ctx.run("pytest --cov=src --cov-report=term-missing", pty=True)
