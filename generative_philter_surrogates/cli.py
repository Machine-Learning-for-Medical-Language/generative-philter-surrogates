import argparse
import asyncio
import sys
from typing import List

from generative_philter_surrogates import Scrubber


def get_parser():
    parser = argparse.ArgumentParser(usage="%(prog)s [OPTION]... [FILE]")

    parser.add_argument("file", metavar="FILE", default="-", nargs="?")
    parser.add_argument("--debug", "-d", action="store_true", help="Print replacements only")
    parser.add_argument("--seed", "-s", type=int, help="Seed for reproducible results")
    parser.add_argument("--asterisk", "-a", action="store_true", help="Use asterisks instead of surrogates")

    return parser


async def main(argv: List[str]) -> None:
    parser = get_parser()
    args = parser.parse_args(argv)

    # Get input:
    if args.file == "-":
        if sys.stdin.isatty():
            sys.exit("You must provide an input file")
        text = sys.stdin.read()
    else:
        with open(args.file, "r", encoding="utf8") as f:
            text = f.read()

    # Scrub it
    scrubber = Scrubber(seed=args.seed, asterisk=args.asterisk, debug=args.debug)
    result = scrubber.scrub_text(text)

    if not args.debug:
        print(result)


def main_cli():
    asyncio.run(main(sys.argv[1:]))


if __name__ == "__main__":
    main_cli()
