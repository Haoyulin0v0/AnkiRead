"""Desktop launcher for AnkiRead, packaged as AnkiRead.exe."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from anki_today import local_collection, read_cards, render_period_report, render_report


def find_anki(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return path
        raise FileNotFoundError(f"找不到指定的 Anki 程序：{path}")
    candidates = [
        Path(r"D:\Anki\anki.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Anki" / "anki.exe",
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Anki" / "anki.exe",
        Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Anki" / "anki.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("自动找不到 anki.exe，请用 --anki-path 指定完整路径。")


def main() -> int:
    parser = argparse.ArgumentParser(description="启动 Anki、同步后生成 Anki 学习报告")
    parser.add_argument("--anki-path", help="anki.exe 的完整路径；默认自动查找")
    parser.add_argument("--profile", help="Anki 配置名称，例如 User 1")
    parser.add_argument("--days", type=int, default=5, help="报告天数，默认 5")
    parser.add_argument("--wait-seconds", type=int, default=45, help="启动后等待同步的秒数，默认 45")
    parser.add_argument("--output", type=Path, help="输出文件；默认 last_N_days.md")
    args = parser.parse_args()
    if args.days < 1 or args.wait_seconds < 0:
        parser.error("--days 必须为正数，--wait-seconds 不能为负数")

    if subprocess.run(["tasklist", "/FI", "IMAGENAME eq anki.exe"], capture_output=True, text=True).stdout.lower().count("anki.exe"):
        raise RuntimeError("Anki 已经在运行。请先关闭 Anki，再启动 AnkiRead.exe。")

    anki_path = find_anki(args.anki_path)
    process = subprocess.Popen([str(anki_path)])
    print(f"已启动 Anki：{anki_path}")
    print(f"等待 {args.wait_seconds} 秒，让 Anki 自动同步……")
    time.sleep(args.wait_seconds)
    close_script = "$p=Get-Process -Id %d -ErrorAction SilentlyContinue; if ($p) { $p.CloseMainWindow() | Out-Null; if (-not $p.WaitForExit(120000)) { exit 2 } }" % process.pid
    close_result = subprocess.run(["powershell", "-NoProfile", "-Command", close_script])
    if close_result.returncode != 0:
        raise RuntimeError("Anki 未能正常关闭，数据库仍可能被占用。")

    source = local_collection(args.profile)
    reports = []
    import datetime as dt
    today = dt.date.today()
    for offset in range(args.days - 1, -1, -1):
        day = today - dt.timedelta(days=offset)
        reports.append((day, read_cards(source, day)))
    output = args.output or Path(f"last_{args.days}_days.md")
    if args.days == 1:
        output.write_text(render_report(reports[0][1], today, source), encoding="utf-8")
    else:
        output.write_text(render_period_report(reports, source), encoding="utf-8")
    print(f"已生成 {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError) as error:
        print(f"错误：{error}", file=sys.stderr)
        raise SystemExit(1)

