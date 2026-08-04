#!/usr/bin/env python3
"""Quick layout-router + sample-template lock check."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.prompts.jiraaf_layout import (  # noqa: E402
    classify_layout,
    static_ranking_style,
    requested_rank_count,
)
from app.prompts.jiraaf_sample_templates import (  # noqa: E402
    resolve_creative_template,
    list_locked_samples,
)

CASES = [
    (
        "Top 6 countries investing in India",
        "infographic",
        "static_ranking",
        "vertical_country_ranking",
        "vertical_countries",
    ),
    (
        "Explain what is sweep-in FD",
        "infographic",
        "carousel_story",
        "infographic_explain_editorial",
        None,
    ),
    (
        "Top 7 oil-consuming countries, describe why India is top 3",
        "static",
        "static_ranking",
        "horizontal_bar_ranking",
        "horizontal_bar",
    ),
    (
        "Why is RBI testing plastic currency notes",
        "infographic",
        "carousel_story",
        "infographic_explain_editorial",
        None,
    ),
    (
        "Bank FD penalty rates top 5 banks",
        "static",
        "static_hub_facts",
        "static_hub_facts",
        None,
    ),
    (
        "India Russia trade deficit export import infographic",
        "infographic",
        "static_ranking",
        "trade_deficit_board",
        "trade_board",
    ),
    (
        "Explain benefits of corporate bonds",
        "static",
        "carousel_story",
        "static_explain_poster",
        None,
    ),
    (
        "Top 10 countries FDI into India",
        "static",
        "static_ranking",
        "vertical_country_ranking",
        "vertical_countries",
    ),
]


def main() -> int:
    failed = 0
    for prompt, fmt, want_layout, want_template, want_style in CASES:
        d = classify_layout(prompt, fmt)
        tpl = resolve_creative_template(prompt, fmt)
        ok = d.layout_type == want_layout and tpl.template_id == want_template
        style = static_ranking_style(prompt) if want_style else None
        style_ok = want_style is None or style == want_style
        rank_n = requested_rank_count(prompt)
        status = "OK" if ok and style_ok else "FAIL"
        if status == "FAIL":
            failed += 1
        print(
            f"[{status}] fmt={fmt:12} layout={d.layout_type:18} "
            f"template={tpl.template_id:28} sample={tpl.sample_file[:40]:40} | {prompt[:45]}"
        )
        if d.layout_type != want_layout:
            print(f"       expected layout={want_layout}, reason={d.reason}")
        if tpl.template_id != want_template:
            print(f"       expected template={want_template}, got={tpl.template_id}")
        if not style_ok:
            print(f"       expected style={want_style}, got={style}")

    print("\nLocked sample registry:")
    for row in list_locked_samples():
        print(f"  - {row['template_id']}: {row['sample']} ({row['layout_type']}/{row['format']})")

    if failed:
        print(f"\n{failed} case(s) FAILED")
        return 1
    print(f"\nAll {len(CASES)} layout + template locks OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
