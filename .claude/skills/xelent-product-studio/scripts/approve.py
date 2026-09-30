#!/usr/bin/env python3
"""Record the user's decision on concept sheets.

  approve.py --dir D --ids ID [ID ...]          approve these products
  approve.py --dir D --all                      approve every product whose current sheet exists and is pending
  approve.py --dir D --changes ID "note"        ask for changes: bumps the version, stores the note
  approve.py --dir D --reset ID                 back to pending at the current version
  approve.py --dir D --list                     show every product's status

Only record what the user actually said. Your own pre-checks use --changes too, before the user sees anything.
"""
import argparse, json, os, sys

ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True)
ap.add_argument("--ids", nargs="*")
ap.add_argument("--all", action="store_true")
ap.add_argument("--changes", nargs=2, metavar=("ID", "NOTE"), action="append")
ap.add_argument("--reset", nargs="*")
ap.add_argument("--list", action="store_true")
a = ap.parse_args()
D = os.path.abspath(a.dir)
P = os.path.join(D, "approvals.json")
if not os.path.exists(P): sys.exit("no approvals.json yet: run plan.py --stage sheets first")
st = json.load(open(P))
sheet = lambda i: os.path.join(D, "sheets", f"{i}-v{st[i]['version']}.png")


def need(i):
    if i not in st: sys.exit(f"unknown id {i}")


for i in a.ids or []:
    need(i)
    if not os.path.exists(sheet(i)): sys.exit(f"{i}: sheet v{st[i]['version']} has not been generated, nothing to approve")
    st[i]["status"] = "approved"
if a.all:
    for i, s in st.items():
        if s["status"] == "pending" and os.path.exists(sheet(i)): s["status"] = "approved"
for i, note in a.changes or []:
    need(i)
    s = st[i]
    if s["status"] != "changes": s["version"] += 1      # several notes on one review go into the same next version
    s["status"] = "changes"
    s["notes"].append(note.strip().rstrip(".") + ".")
for i in a.reset or []:
    need(i); st[i]["status"] = "pending"
json.dump(st, open(P, "w"), indent=1)

counts = {}
for i, s in st.items():
    counts[s["status"]] = counts.get(s["status"], 0) + 1
    if a.list: print(f"{s['status']:9} v{s['version']}  {i}" + (f"   notes: {' '.join(s['notes'][-2:])}" if s["notes"] and s["status"] == "changes" else ""))
print(", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
