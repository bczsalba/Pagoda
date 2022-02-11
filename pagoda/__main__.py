"""Pagoda's runner module."""

import sys
from argparse import ArgumentParser, Namespace

from .runtime import Pagoda


def parse_arguments() -> tuple[Namespace, list[str]]:
    """Parses command line arguments."""

    ending_index = 3
    for arg in sys.argv[1:]:
        if arg in ("-a", "--app"):
            break

        ending_index += 1

    parser = ArgumentParser(
        description="A window-based TUI client for the Teahaz protocol.",
        exit_on_error=False,
    )

    parser.add_argument(
        "-a",
        "--app",
        metavar=("id"),
        help="Launch an application using its id.\
                All further arguments are handled by the given app.",
    )

    parser.add_argument(
        "-l",
        "--launch",
        action="store_true",
        help="Launch the application given using the `-app` argument.",
    )

    return parser.parse_args(sys.argv[1:ending_index]), sys.argv[ending_index:]


def main() -> None:
    """Runs Pagoda."""

    args, remaining = parse_arguments()

    with Pagoda(remaining, args.app, args.launch) as pagoda:
        pagoda.run()


if __name__ == "__main__":
    main()
