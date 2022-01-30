"""Pagoda's runner module."""

from .runtime import App


def main() -> None:
    """Run Pagoda."""

    with App() as app:
        app.run()


if __name__ == "__main__":
    main()
