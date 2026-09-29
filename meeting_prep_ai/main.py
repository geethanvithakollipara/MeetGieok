"""Meeting Prep Agent (Member 5: AI + Data pipeline)

Commands:
  python main.py seed                      # analyze + store all demo meetings in memory
  python main.py brief "Sarah Johnson"     # generate prep brief from memory
  python main.py analyze "Alex Morgan" notes.txt --title "Sync" --date 2026-10-01
  python main.py demo "Sarah Johnson"      # learning-curve demo (fresh memory, before/after)
  python main.py demo --all
"""
import argparse
import sys
import time

from analyzer import analyze_meeting
from brief import generate_brief, render_brief
from demo_data import CONTACTS, MEETINGS, UPCOMING
from memory import MemoryLayer


def ingest(mem: MemoryLayer, contact: dict, date: str, title: str, notes: str) -> dict:
    prior = mem.recall_context(contact["name"], per_query=3)
    analysis = analyze_meeting(contact, title, date, notes, prior)
    mem.store_analysis(contact["name"], date, title, analysis)
    return analysis


def make_brief(mem: MemoryLayer, name: str) -> str:
    contact, meeting = CONTACTS[name], UPCOMING[name]
    memories = mem.recall_context(name)
    brief = generate_brief(contact, meeting, memories)
    header = f"BRIEF FOR: {meeting['title']} with {name} ({meeting['date']}) | memories used: {len(memories)}"
    return f"{header}\n{'=' * len(header)}{render_brief(brief)}"


def cmd_seed(_):
    mem = MemoryLayer()
    print(f"Memory backend: {mem.name}")
    for name, meetings in MEETINGS.items():
        for m in meetings:
            print(f"  analyzing {name} / {m['date']} / {m['title']}")
            ingest(mem, CONTACTS[name], m["date"], m["title"], m["notes"])
    print("Seed complete. Try: python main.py brief \"Sarah Johnson\"")


def cmd_brief(a):
    print(make_brief(MemoryLayer(), a.contact))


def cmd_analyze(a):
    notes = open(a.file, encoding="utf-8").read()
    analysis = ingest(MemoryLayer(), CONTACTS[a.contact], a.date, a.title, notes)
    import json
    print(json.dumps(analysis, indent=2))


def demo_one(name: str, run_id: str):
    mem = MemoryLayer(prefix=f"demo{run_id}")  # fresh banks each run
    print(f"\n{'#' * 70}\nLEARNING CURVE: {name}  (backend: {mem.name})\n{'#' * 70}")
    checkpoints = {0, 1, len(MEETINGS[name])}
    for i in range(len(MEETINGS[name]) + 1):
        if i in checkpoints:
            print(f"\n>>> After {i} past meeting(s) in memory")
            print(make_brief(mem, name))
        if i < len(MEETINGS[name]):
            m = MEETINGS[name][i]
            ingest(mem, CONTACTS[name], m["date"], m["title"], m["notes"])


def cmd_demo(a):
    run_id = str(int(time.time()))
    names = list(CONTACTS) if a.all else [a.contact]
    for n in names:
        demo_one(n, run_id)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed").set_defaults(fn=cmd_seed)

    b = sub.add_parser("brief"); b.add_argument("contact", choices=list(CONTACTS)); b.set_defaults(fn=cmd_brief)

    z = sub.add_parser("analyze")
    z.add_argument("contact", choices=list(CONTACTS)); z.add_argument("file")
    z.add_argument("--title", default="Meeting"); z.add_argument("--date", required=True)
    z.set_defaults(fn=cmd_analyze)

    d = sub.add_parser("demo")
    d.add_argument("contact", nargs="?", choices=list(CONTACTS)); d.add_argument("--all", action="store_true")
    d.set_defaults(fn=cmd_demo)

    a = p.parse_args()
    if a.cmd == "demo" and not (a.all or a.contact):
        sys.exit("Give a contact name or --all")
    a.fn(a)


if __name__ == "__main__":
    main()
