#!/usr/bin/env python3
"""
Log Viewer CLI - Real-time log monitoring and analysis
Supports: view, errors, performance, search, stats, clear
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import subprocess
import argparse


class LogViewer:
    """Log Viewer for Stepsales Logs"""

    # Colors
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[41m",   # Red background
        "RESET": "\033[0m",
    }

    LOGS_DIR = Path(__file__).parent / "logs"
    JSON_LOG = LOGS_DIR / "events.jsonl"

    def __init__(self):
        """Initialize log viewer"""
        if not self.LOGS_DIR.exists():
            print(f"❌ Logs directory not found: {self.LOGS_DIR}")
            sys.exit(1)

    def view_live(self, follow: bool = True, tail_lines: int = 20):
        """View logs in real-time (like tail -f)"""
        if not self.JSON_LOG.exists():
            print(f"❌ Log file not found: {self.JSON_LOG}")
            return

        print("=" * 80)
        print("📊 Live Log View (Press Ctrl+C to exit)")
        print("=" * 80)

        try:
            if follow:
                # Use tail -f for live updates
                cmd = f"tail -f {self.JSON_LOG}"
                proc = subprocess.Popen(
                    cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                for line in proc.stdout:
                    self._print_log_line(line.strip())
            else:
                # Just show last N lines
                with open(self.JSON_LOG, "r") as f:
                    lines = f.readlines()[-tail_lines:]
                for line in lines:
                    self._print_log_line(line.strip())

        except KeyboardInterrupt:
            print("\n✅ Log viewer stopped")
        except Exception as e:
            print(f"❌ Error reading logs: {e}")

    def view_errors(self, limit: int = 50):
        """View only error logs"""
        print("=" * 80)
        print(f"❌ Error Logs (Last {limit})")
        print("=" * 80)

        errors = []
        try:
            with open(self.JSON_LOG, "r") as f:
                for line in f:
                    try:
                        log = json.loads(line)
                        if log.get("level") in ["ERROR", "CRITICAL"]:
                            errors.append(log)
                    except json.JSONDecodeError:
                        continue

            # Show latest errors
            for log in errors[-limit:]:
                self._print_error_log(log)

            print(f"\n📊 Total errors: {len(errors)}")

        except Exception as e:
            print(f"❌ Error reading logs: {e}")

    def view_performance(self, threshold_ms: float = 0):
        """View performance metrics"""
        print("=" * 80)
        print(f"⏱️  Performance Metrics (> {threshold_ms}ms)")
        print("=" * 80)

        perf_logs = []
        try:
            with open(self.JSON_LOG, "r") as f:
                for line in f:
                    try:
                        log = json.loads(line)
                        if "duration_ms" in log:
                            duration = log.get("duration_ms", 0)
                            if duration >= threshold_ms:
                                perf_logs.append(log)
                    except json.JSONDecodeError:
                        continue

            if not perf_logs:
                print("✅ No slow operations found")
                return

            # Sort by duration (slowest first)
            perf_logs.sort(key=lambda x: x.get("duration_ms", 0), reverse=True)

            print(f"{'Operation':<40} {'Duration (ms)':<15} {'Level':<10}")
            print("-" * 65)

            for log in perf_logs[:50]:
                op = log.get("message", "")[:40]
                duration = log.get("duration_ms", 0)
                level = log.get("level", "INFO")

                color = self.COLORS.get(level, self.COLORS["RESET"])
                print(f"{op:<40} {duration:<15.2f} {color}{level}{self.COLORS['RESET']:<10}")

            print(f"\n📊 Total slow operations: {len(perf_logs)}")

        except Exception as e:
            print(f"❌ Error reading logs: {e}")

    def search(self, query: str, limit: int = 50):
        """Search logs by query string"""
        print("=" * 80)
        print(f"🔍 Search Results for: '{query}' (Limit: {limit})")
        print("=" * 80)

        results = []
        try:
            with open(self.JSON_LOG, "r") as f:
                for line in f:
                    try:
                        log = json.loads(line)
                        # Search in message and all string fields
                        if self._match_query(log, query):
                            results.append(log)
                    except json.JSONDecodeError:
                        continue

            if not results:
                print(f"❌ No results found for '{query}'")
                return

            for log in results[-limit:]:
                self._print_log_line(json.dumps(log))

            print(f"\n📊 Found {len(results)} matching logs")

        except Exception as e:
            print(f"❌ Error searching logs: {e}")

    def stats(self):
        """Show log statistics"""
        print("=" * 80)
        print("📈 Log Statistics")
        print("=" * 80)

        stats = {
            "DEBUG": 0,
            "INFO": 0,
            "WARNING": 0,
            "ERROR": 0,
            "CRITICAL": 0,
            "total": 0,
        }

        modules = {}
        slow_ops = []

        try:
            with open(self.JSON_LOG, "r") as f:
                for line in f:
                    try:
                        log = json.loads(line)
                        level = log.get("level", "INFO")
                        stats[level] = stats.get(level, 0) + 1
                        stats["total"] += 1

                        # Module stats
                        module = log.get("logger", "unknown")
                        modules[module] = modules.get(module, 0) + 1

                        # Slow operations
                        if log.get("duration_ms", 0) > 100:
                            slow_ops.append(log)

                    except json.JSONDecodeError:
                        continue

            # Print stats
            print("\n📊 By Level:")
            for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                count = stats.get(level, 0)
                pct = (count / stats["total"] * 100) if stats["total"] > 0 else 0
                color = self.COLORS.get(level, self.COLORS["RESET"])
                print(
                    f"  {color}{level:<10}{self.COLORS['RESET']}: {count:>6} "
                    f"({pct:>5.1f}%)"
                )

            print(f"\n📂 By Module:")
            for module in sorted(modules.keys()):
                count = modules[module]
                print(f"  {module:<30}: {count:>6}")

            print(f"\n⏱️  Performance Summary:")
            print(f"  Total log entries: {stats['total']}")
            print(f"  Slow operations (>100ms): {len(slow_ops)}")

            if slow_ops:
                avg_slow = sum(op.get("duration_ms", 0) for op in slow_ops) / len(slow_ops)
                print(f"  Average slow operation: {avg_slow:.2f}ms")

            print(f"\n📅 Log file size: {self._get_file_size(self.JSON_LOG)}")

        except Exception as e:
            print(f"❌ Error analyzing logs: {e}")

    def clear(self, days: int = 7):
        """Clear old log files"""
        print("=" * 80)
        print(f"🗑️  Clear Logs (older than {days} days)")
        print("=" * 80)

        try:
            now = datetime.now()
            cleared = []

            for log_file in self.LOGS_DIR.glob("*.log"):
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                age_days = (now - mtime).days

                if age_days > days:
                    size_before = log_file.stat().st_size
                    log_file.unlink()
                    cleared.append((log_file.name, size_before, age_days))

            if cleared:
                print(f"✅ Cleared {len(cleared)} old log files:")
                for name, size, age in cleared:
                    print(f"  - {name} ({self._format_size(size)}, {age} days old)")
            else:
                print(f"✅ No logs older than {days} days")

        except Exception as e:
            print(f"❌ Error clearing logs: {e}")

    def _print_log_line(self, line: str):
        """Print a formatted log line"""
        try:
            log = json.loads(line)
            level = log.get("level", "INFO")
            color = self.COLORS.get(level, self.COLORS["RESET"])
            timestamp = log.get("timestamp", "")[:19]
            logger = log.get("logger", "unknown")
            message = log.get("message", "")

            # Format: timestamp | logger | level | message
            print(
                f"{color}[{timestamp}] {logger:<20} [{level:<8}]{self.COLORS['RESET']} "
                f"{message[:100]}"
            )
        except (json.JSONDecodeError, KeyError):
            print(line)

    def _print_error_log(self, log: Dict):
        """Print a formatted error log"""
        timestamp = log.get("timestamp", "")[:19]
        logger = log.get("logger", "unknown")
        message = log.get("message", "")
        level = log.get("level", "ERROR")

        print(f"\n{self.COLORS['ERROR']}[{timestamp}] {logger}{self.COLORS['RESET']}")
        print(f"  Level: {level}")
        print(f"  Message: {message}")

        if log.get("exception"):
            exc = log["exception"]
            print(f"  Exception: {exc.get('type')}: {exc.get('message')}")
            if exc.get("traceback"):
                print(f"  Traceback:\n{exc['traceback'][:500]}")

    def _match_query(self, log: Dict, query: str) -> bool:
        """Check if log matches query"""
        query_lower = query.lower()

        # Search in message
        if query_lower in log.get("message", "").lower():
            return True

        # Search in logger name
        if query_lower in log.get("logger", "").lower():
            return True

        # Search in function name
        if query_lower in log.get("function", "").lower():
            return True

        return False

    @staticmethod
    def _get_file_size(path: Path) -> str:
        """Format file size"""
        if not path.exists():
            return "0 B"
        size = path.stat().st_size
        return LogViewer._format_size(size)

    @staticmethod
    def _format_size(size: int) -> str:
        """Format byte size to human readable"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="🔍 Stepsales Log Viewer - Real-time log monitoring and analysis"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # view command
    view_parser = subparsers.add_parser("view", help="View logs in real-time")
    view_parser.add_argument(
        "--no-follow", action="store_true", help="Don't follow new logs"
    )
    view_parser.add_argument(
        "--tail", type=int, default=20, help="Show last N lines (default: 20)"
    )

    # errors command
    errors_parser = subparsers.add_parser("errors", help="View error logs")
    errors_parser.add_argument(
        "--limit", type=int, default=50, help="Limit results (default: 50)"
    )

    # perf command
    perf_parser = subparsers.add_parser("perf", help="View performance metrics")
    perf_parser.add_argument(
        "--threshold",
        type=float,
        default=0,
        help="Only show operations slower than N ms (default: 0)",
    )

    # search command
    search_parser = subparsers.add_parser("search", help="Search logs")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--limit", type=int, default=50, help="Limit results (default: 50)"
    )

    # stats command
    subparsers.add_parser("stats", help="Show log statistics")

    # clear command
    clear_parser = subparsers.add_parser("clear", help="Clear old logs")
    clear_parser.add_argument(
        "--days", type=int, default=7, help="Clear logs older than N days (default: 7)"
    )

    args = parser.parse_args()

    viewer = LogViewer()

    if not args.command:
        parser.print_help()
        return

    if args.command == "view":
        viewer.view_live(follow=not args.no_follow, tail_lines=args.tail)

    elif args.command == "errors":
        viewer.view_errors(limit=args.limit)

    elif args.command == "perf":
        viewer.view_performance(threshold_ms=args.threshold)

    elif args.command == "search":
        viewer.search(args.query, limit=args.limit)

    elif args.command == "stats":
        viewer.stats()

    elif args.command == "clear":
        viewer.clear(days=args.days)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
