"""Where a run's context went (Sweep run records and Brief records, field "usage"). Added 2026-11-02.

The model cannot read its own token meter, so each run records, per step, what it can count:
  ctx_chars   characters that entered the MAIN session's context in that step (tool results and files it
              read itself - not what subagents read; add the sizes the tools report, rounded)
  sub_chars   characters handed to or read by subagents in that step (excerpt sizes, files they were told to read)
  calls       tool calls the main session made in that step
  agents      subagents started, as {"haiku": n, "sonnet": n, "opus": n}
Tokens are estimated as characters / 4. The point is comparison between runs and between steps, not billing.

usage
  python tracker/usage.py RECORD.json [RECORD.json ...]      per-step table for each record, then totals
  python tracker/usage.py --check RECORD.json                exit 1 if the usage block is missing or malformed
"""
import json
import sys

FIELDS = ("ctx_chars", "sub_chars", "calls")


def problems(rec):
    u = rec.get("usage")
    if not isinstance(u, dict) or not u:
        return ["no \"usage\" block (sweep.md Step 11 / brief.md Step 8)"]
    out = []
    for step, v in u.items():
        if not isinstance(v, dict):
            out.append(f"usage[{step}] is not an object")
            continue
        for f in FIELDS:
            if f in v and not isinstance(v[f], (int, float)):
                out.append(f"usage[{step}].{f} is not a number")
    return out


def table(rec):
    u = rec.get("usage") or {}
    rid = rec.get("run_id") or rec.get("date") or "?"
    lines = [f"{rid}  {'step':<6} {'main ktok':>9} {'sub ktok':>9} {'calls':>6}  agents"]
    tot = [0, 0, 0]
    for step in sorted(u, key=lambda s: [float(x) if x.replace('.', '', 1).isdigit() else 99 for x in s.split(".")]):
        v = u[step] if isinstance(u[step], dict) else {}
        c, s, n = (v.get("ctx_chars") or 0), (v.get("sub_chars") or 0), (v.get("calls") or 0)
        tot = [tot[0] + c, tot[1] + s, tot[2] + n]
        ag = ",".join(f"{k}{x}" for k, x in (v.get("agents") or {}).items() if x)
        lines.append(f"{'':<{len(rid)}}  {step:<6} {c / 4000:>9.1f} {s / 4000:>9.1f} {n:>6}  {ag}")
    lines.append(f"{'':<{len(rid)}}  {'total':<6} {tot[0] / 4000:>9.1f} {tot[1] / 4000:>9.1f} {tot[2]:>6}")
    return "\n".join(lines), tot


def main():
    args = sys.argv[1:]
    check = "--check" in args
    files = [a for a in args if a != "--check"]
    if not files:
        print(__doc__)
        sys.exit(2)
    bad = 0
    for f in files:
        rec = json.load(open(f, encoding="utf-8"))
        if check:
            p = problems(rec)
            for x in p:
                print(f"{f}: {x}")
            bad += bool(p)
        else:
            print(table(rec)[0])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
