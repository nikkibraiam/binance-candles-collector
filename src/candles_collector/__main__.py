"""Command line entry point: ``python -m candles_collector --interval 1h --interval 4h``."""

from __future__ import annotations

import argparse
import logging
import signal
import threading

from dotenv import load_dotenv

from .binance import BinanceClient
from .collector import run_forever
from .config import load_settings
from .db import CandleStore
from .models import INTERVALS


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="candles_collector", description=__doc__)
    parser.add_argument(
        "--interval",
        action="append",
        choices=(*INTERVALS, "all"),
        help="Interval to collect; repeat for several. Defaults to $INTERVALS or all.",
    )
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def resolve_intervals(cli: list[str] | None, env: tuple[str, ...]) -> tuple[str, ...]:
    chosen = tuple(cli or env or ("all",))
    if "all" in chosen:
        return INTERVALS
    unknown = set(chosen) - set(INTERVALS)
    if unknown:
        raise SystemExit(f"Unsupported interval(s): {', '.join(sorted(unknown))}")
    return chosen


def main(argv=None) -> None:
    load_dotenv()
    args = parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s",
    )
    settings = load_settings()
    intervals = resolve_intervals(args.interval, settings.intervals)

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())

    # One worker thread per interval, like the original daemon, but sharing code.
    workers = [
        threading.Thread(
            target=run_forever,
            name=f"candles-{interval}",
            args=(
                BinanceClient(settings.binance_url),
                lambda: CandleStore(settings.database),
                interval,
                settings.symbols,
                settings.symbol_pause_seconds,
                stop,
            ),
        )
        for interval in intervals
    ]
    for worker in workers:
        worker.start()
    while any(w.is_alive() for w in workers):
        for worker in workers:
            worker.join(timeout=1)


if __name__ == "__main__":
    main()
