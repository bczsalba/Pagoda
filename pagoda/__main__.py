"""Pagoda's runner module."""

from .runtime import Pagoda


def main() -> None:
    """Runs Pagoda."""

    with Pagoda() as pagoda:
        pagoda.run()


if __name__ == "__main__":
    main()
