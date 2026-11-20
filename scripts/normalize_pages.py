#!/usr/bin/env python3
"""Normalize report pages to the shared SecondBrain reports look.

Idempotent. For every *.html at repo root except index.html and test.html:
  - remove embedded Design System <style> blocks (design.css carries the same rules)
  - make sure <link rel="stylesheet" href="design.css"> is in <head>
  - body class: weekly digests get "weekly-digest report-page",
    incident reports get "report-page incident"
  - replace old home-nav / back-nav with one standard site bar linking to index.html
Page text is never touched.

Usage: python3 scripts/normalize_pages.py [--check] [files...]
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP = {"index.html", "test.html"}
SITE_BAR = ('<nav class="site-bar" aria-label="主要導覽"><div class="site-bar-inner">'
            '<a class="site-home" href="index.html">回首頁</a>'
            '<span class="site-brand">SECONDBRAIN / REPORTS</span></div></nav>')
LINK = '<link rel="stylesheet" href="design.css">'


def kind(name: str) -> str:
    return "weekly" if re.search(r"weekly-.*digest\.html$", name) else "incident"


def normalize(name: str, s: str) -> str:
    k = kind(name)
    head_end = s.find("</head>")
    if head_end == -1:
        return s
    head, rest = s[:head_end], s[head_end:]
    labeled = False
    # Embedded Design System blocks. A broken template paste can leave an
    # unclosed <style> that swallows a second <head>; removing from the first
    # <style> to the last </style> in <head> clears both.
    if "<style" in head:
        first = head.find("<style")
        last = head.rfind("</style>")
        if last > first:
            block = head[first:last + len("</style>")]
            labeled = "已確認損害" in block
            head = head[:first] + head[last + len("</style>"):]
    if 'href="design.css"' not in head:
        head = head.rstrip() + "\n" + LINK + "\n"
    s = head + rest

    want = ["weekly-digest", "report-page"] if k == "weekly" else ["report-page", "incident"]
    if labeled:
        want.append("incident-labeled")

    def fix_body(m):
        attrs = m.group(1) or ""
        cm = re.search(r'class="([^"]*)"', attrs)
        have = cm.group(1).split() if cm else []
        cls = have + [c for c in want if c not in have]
        if cm:
            attrs = attrs[:cm.start()] + 'class="%s"' % " ".join(cls) + attrs[cm.end():]
        else:
            attrs = attrs + ' class="%s"' % " ".join(cls)
        return "<body%s>" % attrs

    s = re.sub(r"<body([^>]*)>", fix_body, s, count=1)
    # old navigation bars
    s = re.sub(r'\s*<nav class="(?:home-nav|back-nav)"[^>]*>.*?</nav>', "", s, flags=re.S)
    if 'class="site-bar"' not in s:
        s = re.sub(r"(<body[^>]*>)", r"\1\n" + SITE_BAR, s, count=1)
    return s


def main(argv):
    check = "--check" in argv
    files = [a for a in argv if not a.startswith("--")]
    paths = [ROOT / f for f in files] if files else sorted(ROOT.glob("*.html"))
    changed = []
    for p in paths:
        if p.name in SKIP:
            continue
        s = p.read_text(encoding="utf-8")
        n = normalize(p.name, s)
        if n != s:
            changed.append(p.name)
            if not check:
                p.write_text(n, encoding="utf-8")
    for c in changed:
        print(("needs normalize: " if check else "normalized: ") + c)
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
