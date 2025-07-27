from datetime import datetime, timedelta
from pathlib import Path
import threading
from time import sleep
from dataclasses import dataclass
import subprocess
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler
import argparse

exit = False


@dataclass
class Period:
    weekday: int | None = None
    hour: int | None = None
    minute: int | None = None
    second: int | None = None

    def get_next_date(self, now: datetime | None = None):
        if now is None:
            now = datetime.now()

        # Create a copy of the current time to modify it
        next_time = now.replace(microsecond=0)

        if self.second is not None:
            next_time = next_time.replace(second=self.second)
            if next_time <= now:
                next_time += timedelta(minutes=1)

        if self.minute is not None:
            next_time = next_time.replace(minute=self.minute)
            if next_time <= now:
                next_time += timedelta(hours=1)

        if self.hour is not None:
            next_time = next_time.replace(hour=self.hour)
            if next_time <= now:
                next_time += timedelta(days=1)

        if self.weekday is not None:
            days_until_weekday = (self.weekday - next_time.weekday()) % 7
            next_time += timedelta(days=days_until_weekday)

            if next_time <= now:
                next_time += timedelta(weeks=1)

        return next_time


class ExecuteScriptWatchdogHanlder(FileSystemEventHandler):
    _EXCLUDE_DIR = ".tasks"  # Ignore `.tasks` to prevent infinite loop
    _timer: threading.Timer | None

    def __init__(
        self, cwd: Path, script: Path, timeout: timedelta, logger: logging.Logger
    ) -> None:
        self._cwd = cwd
        self._script = script
        self._logger = logger

        self._timeout = timeout
        self._timer = None

        self.EXCLUDE_DIR = self._cwd / self._EXCLUDE_DIR

    def on_any_event(self, event: FileSystemEvent) -> None:
        self._logger.debug("Got Event")

        if event.src_path.startswith(str(self.EXCLUDE_DIR)):
            self._logger.debug("Skipping changes in '.tasks'")
            return

        # Use timer to debounce multiple events
        if self._timer:
            self._timer.cancel()

        self._timer = threading.Timer(
            self._timeout.total_seconds(), self._callback, args=(event,)
        )
        self._timer.start()

    def _callback(self, event: FileSystemEvent):
        self._logger.info("Executing...")
        subprocess.run(["python", str(self._script)], cwd=str(self._cwd))


def get_name(p: Path):
    """Gets script name from path (last three parts)"""

    return "/".join(p.parts[-3:])


def exec_periodic(cwd: Path, script: Path, period: Period):
    """Execute a task periodically at a given time"""

    logger = logging.getLogger(get_name(script))

    while not exit:
        now = datetime.now()
        next = period.get_next_date(now)
        diff = next - now

        logger.info(f"Running next at {next} (in {diff})")
        sleep(diff.total_seconds())

        logger.info("Executing...")
        subprocess.run(["python", str(script)], cwd=str(cwd))


def main(task_dirs: list[str] = [], log_level=logging.WARN):
    FILE_CHANGE_DEBOUNCE = timedelta(minutes=10)  # Timeout for file change debounce

    daily_period = Period(hour=1, minute=0, second=0)  # Run daily at 00:01:00
    weekly_period = Period(
        weekday=0, hour=0, minute=1, second=0
    )  # Run weekly at Monday (or Sunday depending on locale) 00:01:00

    logging.basicConfig(level=log_level)
    logger = logging.getLogger()

    threads: list[threading.Thread] = []
    for dir in task_dirs:
        cwd = Path(dir)

        logger.info(f"Register jobs for {cwd.name}")

        daily_script = cwd / ".tasks" / "daily.py"
        weekly_script = cwd / ".tasks" / "weekly.py"
        on_change_script = cwd / ".tasks" / "on_change.py"

        if daily_script.exists():
            t = threading.Thread(
                target=exec_periodic, args=(cwd, daily_script, daily_period)
            )
            threads.append(t)
        else:
            logger.error("Daily script not found!")

        if weekly_script.exists():
            t = threading.Thread(
                target=exec_periodic, args=(cwd, weekly_script, weekly_period)
            )
            threads.append(t)
        else:
            logger.error("Weekly script not found!")

        if on_change_script.exists():
            sub_logger = logging.getLogger(get_name(on_change_script))

            observer = Observer()
            observer.schedule(
                ExecuteScriptWatchdogHanlder(
                    cwd, on_change_script, FILE_CHANGE_DEBOUNCE, sub_logger
                ),
                str(cwd),
                recursive=True,
            )
            threads.append(observer)
        else:
            logger.error("On change script not found!")

        print("")

    for t in threads:
        t.start()

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.info("Press Ctrl-C again to exit!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "dirs", nargs="+", help="list of paths to check for task scripts"
    )
    parser.add_argument(
        "-l",
        "--log-level",
        choices=["debug", "info", "error"],
        help="log level",
        default="info",
    )

    args = parser.parse_args()
    log_level = (
        logging.DEBUG
        if args.log_level == "debug"
        else logging.INFO
        if args.log_level == "info"
        else logging.ERROR
    )

    main(args.dirs, log_level)
