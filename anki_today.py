#!/usr/bin/env python3
"""Generate today.md from an Anki collection or a desktop Anki instance."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sqlite3
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

STUDY_TYPES = {0: "学习", 1: "复习", 2: "重新学习", 3: "筛选牌组"}


def clean_html(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def markdown_text(value: str) -> str:
    value = clean_html(value).replace("\\", "\\\\").replace("|", "\\|")
    return value.replace("\n", "<br>") or "（空）"


def find_collection(source: Path, temp_dir: Path) -> Path:
    if source.is_dir():
        for name in ("collection.anki21", "collection.anki2"):
            candidate = source / name
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"目录中没有找到 collection.anki21 或 collection.anki2：{source}")
    if source.suffix.lower() not in {".colpkg", ".apkg", ".zip"}:
        return source
    with zipfile.ZipFile(source) as archive:
        names = set(archive.namelist())
        selected = next((n for n in ("collection.anki21", "collection.anki2") if n in names), None)
        if not selected:
            raise FileNotFoundError("Anki 导出包中没有 collection.anki21 或 collection.anki2")
        target = temp_dir / selected
        with archive.open(selected) as source_file, target.open("wb") as target_file:
            shutil.copyfileobj(source_file, target_file)
        return target


def local_collection(profile: str | None) -> Path:
    root = Path(os.environ.get("APPDATA", "")) / "Anki2"
    if not root.exists():
        raise FileNotFoundError(f"没有找到 Anki 用户目录：{root}")
    profiles = [root / profile] if profile else [p for p in root.iterdir() if p.is_dir()]
    candidates = [p / name for p in profiles for name in ("collection.anki21", "collection.anki2") if (p / name).exists()]
    if not candidates:
        raise FileNotFoundError(f"没有在 {root} 中找到 Anki collection")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def anki_connect(action: str, params: dict | None = None, url: str = "http://127.0.0.1:8765"):
    payload = json.dumps({"action": action, "version": 6, "params": params or {}}).encode()
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        raise RuntimeError("无法连接 AnkiConnect：请确认桌面 Anki 已打开并安装了 AnkiConnect") from error
    if result.get("error"):
        raise RuntimeError(f"AnkiConnect 错误：{result['error']}")
    return result.get("result")


def read_cards(source: Path, day: dt.date, deck: str | None = None) -> list[dict]:
    with tempfile.TemporaryDirectory(prefix="anki-today-") as temp:
        collection = find_collection(source, Path(temp))
        db = sqlite3.connect(f"file:{collection}?mode=ro", uri=True, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=30000")
            start = int(dt.datetime.combine(day, dt.time.min).timestamp() * 1000)
            end = int(dt.datetime.combine(day + dt.timedelta(days=1), dt.time.min).timestamp() * 1000)
            query = """
                SELECT r.cid, r.ease, r.ivl, r.time, r.type,
                       d.name AS deck_name, n.flds, n.tags
                FROM revlog r
                JOIN cards c ON c.id = r.cid
                JOIN notes n ON n.id = c.nid
                LEFT JOIN decks d ON d.id = c.did
                WHERE r.id >= ? AND r.id < ?
            """
            params: list = [start, end]
            if deck:
                query += " AND d.name = ?"
                params.append(deck)
            query += """
                ORDER BY r.id
            """
            rows = db.execute(query, params).fetchall()
        finally:
            db.close()

    cards: dict[int, dict] = {}
    for row in rows:
        fields = row["flds"].split("\x1f")
        item = cards.setdefault(row["cid"], {
            "deck": row["deck_name"] or "未命名牌组",
            "front": fields[0] if fields else "",
            "back": fields[1] if len(fields) > 1 else "",
            "tags": row["tags"] or "",
            "events": [],
        })
        item["events"].append({
            "kind": STUDY_TYPES.get(row["type"], f"类型 {row['type']}"),
            "ease": str(row["ease"]), "ivl": str(row["ivl"]),
            "time": f"{row['time'] / 1000:.1f} 秒",
        })
    return list(cards.values())


def render_report(cards: list[dict], day: dt.date, source: Path) -> str:
    reviewed = sum(any(e["kind"] == "复习" for e in c["events"]) for c in cards)
    learned = sum(any(e["kind"] in {"学习", "重新学习"} for e in c["events"]) for c in cards)
    lines = [
        f"# Anki 学习记录 · {day.isoformat()}", "",
        f"> 数据来源：`{source.name}` · 生成时间：{dt.datetime.now().astimezone():%Y-%m-%d %H:%M}", "",
        f"- 学习/重新学习卡片：**{learned}** 张",
        f"- 复习卡片：**{reviewed}** 张",
        f"- 当天接触卡片（去重）：**{len(cards)}** 张", "",
    ]
    if not cards:
        lines.append("今天还没有找到学习或复习记录。请确认桌面 Anki 已完成同步，并检查日期/时区设置。")
        return "\n".join(lines) + "\n"
    by_deck: dict[str, list[dict]] = defaultdict(list)
    for card in cards:
        by_deck[card["deck"]].append(card)
    for deck, deck_cards in sorted(by_deck.items(), key=lambda pair: pair[0].casefold()):
        lines += [f"## {deck}", "", f"共 {len(deck_cards)} 张", ""]
        for index, card in enumerate(deck_cards, 1):
            events = "; ".join(f"{e['kind']}（评分 {e['ease']}，间隔 {e['ivl']} 天，耗时 {e['time']}）" for e in card["events"])
            tags = " ".join(f"`{tag}`" for tag in card["tags"].split()) or "无"
            lines += [
                f"### {index}. {clean_html(card['front'])[:100] or '（无正面内容）'}", "",
                "| 正面 | 背面 | 标签 | 当天记录 |", "|---|---|---|---|",
                f"| {markdown_text(card['front'])} | {markdown_text(card['back'])} | {tags} | {events} |", "",
            ]
    return "\n".join(lines)


def render_period_report(reports: list[tuple[dt.date, list[dict]]], source: Path) -> str:
    lines = [
        f"# Anki 最近 {len(reports)} 天学习记录", "",
        f"> 数据来源：`{source.name}` · 生成时间：{dt.datetime.now().astimezone():%Y-%m-%d %H:%M}", "",
    ]
    total = sum(len(cards) for _, cards in reports)
    lines.append(f"共接触 **{total}** 条去重前卡片记录。以下按日期排列。")
    lines.append("")
    for day, cards in reports:
        lines.append(render_report(cards, day, source))
        lines.append("\n---\n")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="从 Anki 桌面客户端生成 today.md")
    parser.add_argument("input", nargs="?", type=Path, help="collection 文件；使用 --anki-connect 或 --local 时可省略")
    parser.add_argument("--local", action="store_true", help="直接读取桌面 Anki 本地 collection，不使用 AnkiConnect")
    parser.add_argument("--anki-connect", action="store_true", help="读取桌面 Anki 的本地 collection")
    parser.add_argument("--sync", action="store_true", help="先通过 AnkiConnect 请求桌面 Anki 同步")
    parser.add_argument("--profile", help="Anki 配置名称，例如 User 1")
    parser.add_argument("--deck", help="只输出指定牌组，例如 托福绿宝书")
    parser.add_argument("--date", type=dt.date.fromisoformat, default=dt.date.today(), help="日期 YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=1, help="输出最近几天，默认 1；例如 --days 5")
    parser.add_argument("--output", type=Path, default=Path("today.md"), help="输出文件，默认 today.md")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days 必须是正整数")
    if args.anki_connect:
        if args.sync:
            print("正在请求桌面 Anki 同步……")
            anki_connect("sync")
        source = local_collection(args.profile)
    elif args.local or args.profile:
        source = local_collection(args.profile)
    elif args.input:
        source = args.input
    else:
        parser.error("请提供 collection 文件，或使用 --anki-connect/--local")
    reports = [(args.date - dt.timedelta(days=offset), []) for offset in range(args.days - 1, -1, -1)]
    reports = [(day, read_cards(source, day, args.deck)) for day, _ in reports]
    output = args.output
    if args.days > 1 and output == Path("today.md"):
        output = Path(f"last_{args.days}_days.md")
    if args.days == 1:
        output.write_text(render_report(reports[0][1], args.date, source), encoding="utf-8")
    else:
        output.write_text(render_period_report(reports, source), encoding="utf-8")
    print(f"已更新 {output}：{sum(len(cards) for _, cards in reports)} 条卡片记录（{args.days} 天）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

