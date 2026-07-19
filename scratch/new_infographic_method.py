    def _render_infographic_page(
        self,
        payload: RendererInput,
        size: dict[str, int],
        page_text: dict,
        preset: str,
        background: tuple[int, int, int],
        primary: tuple[int, int, int],
        accent: tuple[int, int, int],
        secondary_text: tuple[int, int, int],
        light_text: tuple[int, int, int],
    ) -> tuple[Image.Image, dict[str, object]]:
        # ── Premium LinkedIn Infographic Renderer ────────────────────────────
        # Renders a multi-section infographic poster with the Jiraaf brand design system.
        # Pure white canvas, flat vector-style cards, purple/orange/yellow palette.
        import math as _math
        W = size["width"]
        H = size["height"]

        # Brand color tokens
        purple     = (51, 32, 111)        # #33206F
        orange     = (245, 154, 35)       # #F59A23
        yellow     = (255, 200, 87)       # #FFC857
        dark_text  = (34, 34, 34)         # #222222
        sec_text   = (91, 91, 91)         # #5B5B5B
        bg_color   = (255, 255, 255)      # #FFFFFF
        card_bg    = (250, 250, 252)      # #FAFAFC
        border_color = (236, 236, 236)    # #ECECEC
        success    = (46, 175, 98)        # #2EAF62
        blue       = (79, 142, 247)       # #4F8EF7
        gray       = (158, 163, 174)      # #9EA3AE
        prob_bg    = (255, 247, 247)
        sol_bg     = (240, 255, 247)
        red_pill   = (220, 60, 60)
        green_pill = (46, 175, 98)

        image = Image.new("RGB", (W, H), bg_color)
        draw = ImageDraw.Draw(image)

        # ── Parse content ─────────────────────────────────────────────────────
        headline_text     = str(page_text.get("headline_display") or page_text.get("headline") or "").strip()
        supporting_line   = str(page_text.get("supporting_line") or "").strip()
        cta_text          = str(page_text.get("cta_display") or page_text.get("cta") or "").strip()
        body_text         = str(page_text.get("body_display") or page_text.get("body") or "").strip()
        infographic_sections = page_text.get("infographic_section_specs") or []
        stat_highlights   = self._page_list_value(page_text.get("stat_highlights"))
        problem_statement = str(page_text.get("problem_statement") or "").strip()
        solution_statement = str(page_text.get("solution_statement") or "").strip()
        customer_quote    = str(page_text.get("customer_quote") or "").strip()
        customer_name     = str(page_text.get("customer_name") or "").strip()
        process_steps     = self._page_list_value(page_text.get("process_steps"))
        hashtags          = self._page_list_value(page_text.get("hashtags"))
        slide_copy        = page_text.get("slide_copy", [])
        claim_safety_notes = self._page_list_value(page_text.get("claim_safety_notes"))

        text_fit_manifest: list[dict] = []
        zones_used: list[dict] = []

        margin_x = 52
        margin_y = 44
        y = margin_y

        # ── Helper: draw a colored pill/badge label ───────────────────────────
        def draw_pill(text: str, cx: int, cy: int, color: tuple, text_color: tuple = (255, 255, 255), font_size: int = 13) -> None:
            font = self._font(font_size, weight="bold")
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            pad_x, pad_h = 14, 7
            pill_w = tw + pad_x * 2
            pill_h = (bbox[3] - bbox[1]) + pad_h * 2
            px0 = cx - pill_w // 2
            py0 = cy
            draw.rounded_rectangle((px0, py0, px0 + pill_w, py0 + pill_h), radius=pill_h // 2, fill=color)
            draw.text((px0 + pad_x - bbox[0], py0 + pad_h - bbox[1]), text, fill=text_color, font=font)

        # ── Helper: draw centered section heading pill ────────────────────────
        def draw_section_heading(label: str, y_pos: int) -> int:
            font = self._font(15, weight="bold")
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            pad_x, pad_y = 24, 8
            pill_w = tw + pad_x * 2
            pill_h = (bbox[3] - bbox[1]) + pad_y * 2
            px0 = (W - pill_w) // 2
            draw.rounded_rectangle((px0, y_pos, px0 + pill_w, y_pos + pill_h), radius=pill_h // 2, fill=purple)
            draw.text((px0 + pad_x - bbox[0], y_pos + pad_y - bbox[1]), label, fill=(255, 255, 255), font=font)
            return y_pos + pill_h + 16

        # ── Helper: draw vector icon in a colored circle ──────────────────────
        def draw_icon_circle(icon_name: str, cx: int, cy: int, size: int, color: tuple) -> None:
            r = size // 2
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
            s = int(size * 0.36)
            w = max(2, size // 18)
            ic = (255, 255, 255)
            name = (icon_name or "").lower().strip()
            if name in ("shield", "security", "risk"):
                pts = [cx, cy - s, cx + s, cy - s // 2, cx + s, cy + s // 3, cx, cy + s, cx - s, cy + s // 3, cx - s, cy - s // 2]
                draw.polygon(pts, fill=None, outline=ic)
                draw.line([(cx, cy - s // 3), (cx, cy + s // 3)], fill=ic, width=w)
            elif name in ("chart", "graph", "bar"):
                bw = s // 3
                for bi, bh in enumerate([s // 2, s, int(s * 0.75)]):
                    bx = cx - s + bi * (bw + 3)
                    draw.rectangle((bx, cy + s - bh, bx + bw - 1, cy + s), fill=ic)
            elif name in ("growth", "trend", "arrow"):
                pts2 = [(cx - s, cy + s), (cx, cy - s // 2), (cx + s, cy - s)]
                draw.line(pts2, fill=ic, width=w + 1)
                draw.polygon([(cx + s, cy - s), (cx + s - s // 3, cy - s + s // 3), (cx + s + s // 3, cy - s + s // 3)], fill=ic)
            elif name in ("wallet", "money", "cash"):
                draw.rounded_rectangle((cx - s, cy - s // 2, cx + s, cy + s), radius=4, outline=ic, width=w)
                draw.ellipse((cx - s // 4, cy - s // 4, cx + s // 4, cy + s // 4), outline=ic, width=w)
            elif name in ("calendar", "date", "monthly"):
                draw.rounded_rectangle((cx - s, cy - s // 2, cx + s, cy + s), radius=4, outline=ic, width=w)
                draw.line([(cx - s // 2, cy - s // 2), (cx - s // 2, cy - s)], fill=ic, width=w)
                draw.line([(cx + s // 2, cy - s // 2), (cx + s // 2, cy - s)], fill=ic, width=w)
                draw.line([(cx - s, cy), (cx + s, cy)], fill=ic, width=w)
            elif name in ("brain", "ai", "intelligence"):
                draw.ellipse((cx - s, cy - s, cx + s, cy + s), outline=ic, width=w)
                draw.line([(cx, cy - s), (cx, cy + s)], fill=ic, width=w)
                draw.arc((cx - s, cy - s, cx + s, cy + s), start=0, end=180, fill=ic, width=w)
            elif name in ("target", "goal"):
                for ri_scale in [1.0, 0.65, 0.35]:
                    ri = int(s * ri_scale)
                    draw.ellipse((cx - ri, cy - ri, cx + ri, cy + ri), outline=ic, width=w)
                draw.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=ic)
            elif name in ("portfolio", "diversification"):
                draw.ellipse((cx - s, cy - s, cx, cy), outline=ic, width=w)
                draw.ellipse((cx, cy - s, cx + s, cy), outline=ic, width=w)
                draw.ellipse((cx - s // 2, cy, cx + s // 2, cy + s), outline=ic, width=w)
            elif name in ("lock", "low volatility", "stable"):
                draw.rounded_rectangle((cx - s, cy - s // 3, cx + s, cy + s), radius=4, outline=ic, width=w)
                draw.arc((cx - s // 2, cy - s, cx + s // 2, cy), start=180, end=0, fill=ic, width=w)
                draw.ellipse((cx - 3, cy + s // 4, cx + 3, cy + s // 4 + 6), fill=ic)
            elif name in ("checkmark", "check", "accessible"):
                draw.line([(cx - s, cy), (cx - s // 4, cy + s), (cx + s, cy - s)], fill=ic, width=w + 1)
            else:
                # Default star
                for angle_deg in range(0, 360, 60):
                    angle = _math.radians(angle_deg)
                    draw.line([(cx, cy), (int(cx + s * _math.cos(angle)), int(cy + s * _math.sin(angle)))], fill=ic, width=w)

        # ══════════════════════════════════════════════════════════════════════
        # 1. LOGO top right + tagline
        # ══════════════════════════════════════════════════════════════════════
        logo_box = (W - margin_x - 180, y, W - margin_x, y + 56)
        logo_rendered = self._render_logo_box(
            canvas=image, draw=draw, payload=payload, box=logo_box,
            primary=purple, accent=orange, fill=purple,
        )
        zones_used.append(self._zone_manifest("logo", "logo", logo_box))
        tag_zone = self._zone_manifest("tagline", "label", (W - margin_x - 180, y + 58, W - margin_x, y + 72), 1)
        self._draw_text_block(draw, "AI-POWERED INVESTING. HUMAN-CENTERED.", type("Z", (), tag_zone)(), orange, 10, padding=0, align="center")

        # 2. ORANGE accent line
        draw.rectangle((margin_x, y + 6, W - margin_x - 190, y + 9), fill=orange)

        # 3. MAIN HEADLINE
        y_headline_start = y + 14
        headline_box = (margin_x, y_headline_start, W - margin_x - 190, y_headline_start + 110)
        hz = self._zone_manifest("headline", "headline", headline_box, 3)
        fit = self._draw_text_block(draw, headline_text, type("Z", (), hz)(), dark_text, 40, padding=0, weight="bold")
        text_fit_manifest.append(fit)
        zones_used.append(hz)
        y = (fit.get("occupied_box") or headline_box)[3] + 10

        # 4. SUBHEADLINE
        if supporting_line:
            sub_box = (margin_x, y, W - margin_x, y + 50)
            sz = self._zone_manifest("supporting_line", "supporting_line", sub_box, 2)
            fit2 = self._draw_text_block(draw, supporting_line, type("Z", (), sz)(), sec_text, 18, padding=0)
            text_fit_manifest.append(fit2)
            zones_used.append(sz)
            y += 52

        # 5. DIVIDER
        draw.line((margin_x, y, W - margin_x, y), fill=border_color, width=2)
        y += 18

        # 6. MAIN ILLUSTRATION
        illustration_h = 200
        illustration_box = (margin_x, y, W - margin_x, y + illustration_h)
        image_rendered = False
        if payload.image_assets:
            visual_result = self._paste_visual_card(
                image, payload.image_assets[0].storage_path,
                illustration_box, radius=20, frame_fill=card_bg, padding=0,
            )
            image_rendered = bool(visual_result.get("rendered"))
        if not image_rendered:
            self._draw_panel(draw, illustration_box, card_bg, radius=20, outline=border_color, width=1)
            self._draw_editorial_motif(draw, illustration_box, purple, orange, card_bg)
        zones_used.append(self._zone_manifest("main_illustration", "image", illustration_box))
        y += illustration_h + 22

        # ══════════════════════════════════════════════════════════════════════
        # 7. PROBLEM vs SOLUTION with colored pill headers + bullet points
        # ══════════════════════════════════════════════════════════════════════
        if problem_statement or solution_statement:
            ps_h = 170
            card_w = (W - 2 * margin_x - 16) // 2

            # Problem card (left, light red)
            prob_box = (margin_x, y, margin_x + card_w, y + ps_h)
            self._draw_panel(draw, prob_box, prob_bg, radius=20, outline=(255, 200, 200), width=1)
            draw_pill("THE PROBLEM", margin_x + card_w // 2, y + 12, red_pill)
            prob_pts = [p.strip() for p in problem_statement.split(".") if p.strip()][:3] if problem_statement else ["Many investors chase only equity returns", "Advice is confusing and emotional", "Unsure about risk tolerance"]
            py2 = y + 52
            for pt in prob_pts:
                bz = self._zone_manifest("prob_pt", "body", (margin_x + 28, py2, margin_x + card_w - 12, py2 + 28), 2)
                draw.ellipse((margin_x + 14, py2 + 8, margin_x + 24, py2 + 18), fill=red_pill)
                self._draw_text_block(draw, pt, type("Z", (), bz)(), dark_text, 13, padding=0)
                py2 += 34
            zones_used.append(self._zone_manifest("problem_card", "body", prob_box))

            # Solution card (right, light green)
            sol_x0 = margin_x + card_w + 16
            sol_box = (sol_x0, y, sol_x0 + card_w, y + ps_h)
            self._draw_panel(draw, sol_box, sol_bg, radius=20, outline=(180, 230, 200), width=1)
            draw_pill("THE SOLUTION", sol_x0 + card_w // 2, y + 12, green_pill)
            sol_pts = [p.strip() for p in solution_statement.split(".") if p.strip()][:3] if solution_statement else ["AI-driven personalized recommendations", "Balanced portfolios with bonds for income", "Smarter decisions, lower stress"]
            sy2 = y + 52
            for pt in sol_pts:
                bz2 = self._zone_manifest("sol_pt", "body", (sol_x0 + 30, sy2, sol_x0 + card_w - 12, sy2 + 28), 2)
                draw.ellipse((sol_x0 + 14, sy2 + 7, sol_x0 + 26, sy2 + 19), fill=green_pill)
                draw.line([(sol_x0 + 17, sy2 + 14), (sol_x0 + 20, sy2 + 18), (sol_x0 + 24, sy2 + 10)], fill=(255, 255, 255), width=2)
                self._draw_text_block(draw, pt, type("Z", (), bz2)(), dark_text, 13, padding=0)
                sy2 += 34
            zones_used.append(self._zone_manifest("solution_card", "body", sol_box))
            y += ps_h + 24

        # ══════════════════════════════════════════════════════════════════════
        # 8. FEATURE CARDS with REAL PIL-DRAWN ICONS
        # ══════════════════════════════════════════════════════════════════════
        y = draw_section_heading("BUILT FOR MODERN INVESTORS", y)

        default_features = [
            {"label": "AI-Powered\nIntelligence",  "body": "Advanced analysis of market trends, behavior, and goals.", "icon": "brain",       "color": purple},
            {"label": "Diversified\nPortfolios",   "body": "Curated portfolios across asset classes to balance risk.", "icon": "portfolio",   "color": blue},
            {"label": "Goal-Based\nApproach",      "body": "Define your goals — Jiraaf guides you every step.",       "icon": "target",      "color": orange},
            {"label": "Risk-First\nPhilosophy",    "body": "We understand and manage risk for long-term stability.",  "icon": "shield",      "color": red_pill},
            {"label": "Simple &\nAccessible",      "body": "Easy to use, whether you are a beginner or expert.",     "icon": "checkmark",   "color": success},
        ]

        features = []
        if infographic_sections:
            for idx, sec in enumerate(infographic_sections[:5]):
                def_feat = default_features[idx % len(default_features)]
                features.append({
                    "label": str(sec.get("section_label") or def_feat["label"]).strip(),
                    "body":  str(sec.get("body") or def_feat["body"]).strip(),
                    "icon":  str(sec.get("icon_hint") or def_feat["icon"]).strip().lower(),
                    "color": def_feat["color"],
                })
        else:
            features = default_features

        feat_card_h = 150
        num_feats = min(len(features), 5)
        feat_gap = 10
        feat_card_w = (W - 2 * margin_x - (num_feats - 1) * feat_gap) // num_feats

        for idx, feat in enumerate(features[:5]):
            fx0 = margin_x + idx * (feat_card_w + feat_gap)
            fbox = (fx0, y, fx0 + feat_card_w, y + feat_card_h)
            self._draw_panel(draw, fbox, bg_color, radius=16, outline=border_color, width=1)

            # Real icon circle (48px)
            icon_name = feat.get("icon", "checkmark")
            ic_col = feat.get("color") or purple
            icon_size = 48
            icon_cx = fx0 + feat_card_w // 2
            icon_cy = y + 32
            draw_icon_circle(icon_name, icon_cx, icon_cy, icon_size, ic_col)

            # Label
            lbl_zone = self._zone_manifest(f"feat_lbl_{idx}", "label", (fx0 + 4, y + 62, fx0 + feat_card_w - 4, y + 106), 3)
            self._draw_text_block(draw, feat.get("label", ""), type("Z", (), lbl_zone)(), dark_text, 12, padding=0, weight="bold", align="center")

            # Body description
            body_zone2 = self._zone_manifest(f"feat_body_{idx}", "body", (fx0 + 4, y + 106, fx0 + feat_card_w - 4, y + feat_card_h - 8), 4)
            self._draw_text_block(draw, feat.get("body", ""), type("Z", (), body_zone2)(), sec_text, 10, padding=0, align="center")

            zones_used.append(self._zone_manifest(f"feature_card_{idx}", "body", fbox))

        y += feat_card_h + 24

        # ══════════════════════════════════════════════════════════════════════
        # 9. METRICS STAT CARDS (large number + label)
        # ══════════════════════════════════════════════════════════════════════
        y = draw_section_heading("REAL IMPACT. MEASURABLE RESULTS.", y)

        default_stats = [
            {"num": "2X",   "label": "Higher Potential Returns vs traditional investing approaches", "color": purple},
            {"num": "30%",  "label": "Lower Risk through intelligent diversification",               "color": orange},
            {"num": "90%+", "label": "Goal Achievement Focus with personalized goal tracking",      "color": success},
            {"num": "10K+", "label": "Happy Investors growing their wealth with confidence",        "color": blue},
        ]
        stat_cards = []
        if stat_highlights:
            for i, s in enumerate(stat_highlights[:4]):
                parts = str(s).split(" ", 1)
                num = parts[0] if parts else str(s)
                label = parts[1] if len(parts) > 1 else ""
                stat_cards.append({"num": num, "label": label, "color": default_stats[i % len(default_stats)]["color"]})
        else:
            stat_cards = default_stats

        stat_card_h = 110
        num_stats = min(len(stat_cards), 4)
        stat_gap = 12
        stat_card_w = (W - 2 * margin_x - (num_stats - 1) * stat_gap) // num_stats

        for idx, sc in enumerate(stat_cards[:4]):
            sx0 = margin_x + idx * (stat_card_w + stat_gap)
            sbox = (sx0, y, sx0 + stat_card_w, y + stat_card_h)
            col = sc.get("color") or purple
            self._draw_panel(draw, sbox, bg_color, radius=16, outline=border_color, width=1)
            draw.rounded_rectangle((sx0, y, sx0 + stat_card_w, y + 5), radius=3, fill=col)
            # Large number
            num_zone2 = self._zone_manifest(f"stat_num_{idx}", "headline", (sx0 + 8, y + 12, sx0 + stat_card_w - 8, y + 58), 1)
            self._draw_text_block(draw, sc.get("num", ""), type("Z", (), num_zone2)(), col, 30, padding=0, weight="bold", align="center")
            # Label text
            lbl2_zone = self._zone_manifest(f"stat_lbl_{idx}", "body", (sx0 + 8, y + 60, sx0 + stat_card_w - 8, y + stat_card_h - 8), 3)
            self._draw_text_block(draw, sc.get("label", ""), type("Z", (), lbl2_zone)(), sec_text, 11, padding=0, align="center")
            zones_used.append(self._zone_manifest(f"stat_card_{idx}", "body", sbox))

        y += stat_card_h + 24

        # ══════════════════════════════════════════════════════════════════════
        # 10. TESTIMONIAL QUOTE
        # ══════════════════════════════════════════════════════════════════════
        if customer_quote:
            quote_h = 110
            qbox = (margin_x, y, W - margin_x, y + quote_h)
            self._draw_panel(draw, qbox, card_bg, radius=20, outline=border_color, width=1)
            draw.rounded_rectangle((margin_x, y, margin_x + 6, y + quote_h), radius=3, fill=purple)
            q_font = self._font(48, weight="bold")
            draw.text((margin_x + 16, y + 4), "\u201c", fill=orange, font=q_font)
            q_zone = self._zone_manifest("quote_text", "body", (margin_x + 52, y + 16, W - margin_x - 130, y + quote_h - 30), 4)
            self._draw_text_block(draw, customer_quote, type("Z", (), q_zone)(), dark_text, 14, padding=0)
            av_size = 44
            av_x = W - margin_x - av_size - 18
            av_y = y + (quote_h - av_size) // 2
            draw.ellipse((av_x, av_y, av_x + av_size, av_y + av_size), fill=purple)
            init = (customer_name or "U")[0].upper()
            i_zone = self._zone_manifest("avatar_init", "headline", (av_x, av_y, av_x + av_size, av_y + av_size), 1)
            self._draw_text_block(draw, init, type("Z", (), i_zone)(), (255, 255, 255), 18, padding=0, weight="bold", align="center")
            n_zone2 = self._zone_manifest("quote_name", "label", (margin_x + 52, y + quote_h - 28, W - margin_x - 130, y + quote_h - 8), 1)
            self._draw_text_block(draw, f"\u2014 {customer_name}", type("Z", (), n_zone2)(), purple, 12, padding=0, weight="bold")
            zones_used.append(self._zone_manifest("quote_card", "body", qbox))
            y += quote_h + 24

        # ══════════════════════════════════════════════════════════════════════
        # 11. HOW IT WORKS TIMELINE
        # ══════════════════════════════════════════════════════════════════════
        y = draw_section_heading("HOW IT WORKS", y)

        default_steps = [
            {"label": "Tell Us\nAbout You",   "body": "Share goals and risk appetite."},
            {"label": "AI Analyzes\n& Plans", "body": "We build a personalized investment plan."},
            {"label": "Invest\nSecurely",     "body": "Invest in curated portfolios."},
            {"label": "Track &\nOptimize",    "body": "Monitor returns and optimize anytime."},
        ]
        steps_list = []
        if process_steps:
            for i, s in enumerate(process_steps[:4]):
                steps_list.append({"label": str(s), "body": default_steps[i]["body"] if i < len(default_steps) else ""})
        else:
            steps_list = default_steps

        step_h = 90
        num_steps = min(len(steps_list), 4)
        arrow_w = 28
        usable_w = W - 2 * margin_x - (num_steps - 1) * arrow_w
        step_w = usable_w // num_steps

        for idx, step in enumerate(steps_list[:4]):
            sx0 = margin_x + idx * (step_w + arrow_w)
            sbox2 = (sx0, y, sx0 + step_w, y + step_h)
            self._draw_panel(draw, sbox2, card_bg, radius=14, outline=border_color, width=1)
            circle_r = 17
            cx3 = sx0 + step_w // 2
            cy3 = y + circle_r + 8
            draw.ellipse((cx3 - circle_r, cy3 - circle_r, cx3 + circle_r, cy3 + circle_r), fill=purple)
            n3_zone = self._zone_manifest(f"step_n_{idx}", "headline", (cx3 - circle_r, cy3 - circle_r, cx3 + circle_r, cy3 + circle_r), 1)
            self._draw_text_block(draw, str(idx + 1), type("Z", (), n3_zone)(), (255, 255, 255), 14, padding=0, weight="bold", align="center")
            lbl3_zone = self._zone_manifest(f"step_lbl_{idx}", "label", (sx0 + 4, cy3 + circle_r + 4, sx0 + step_w - 4, y + step_h - 8), 3)
            self._draw_text_block(draw, step.get("label", ""), type("Z", (), lbl3_zone)(), dark_text, 11, padding=0, weight="bold", align="center")
            if idx < num_steps - 1:
                ax2 = sx0 + step_w + 4
                ay2 = y + step_h // 2
                draw.line([(ax2, ay2), (ax2 + arrow_w - 8, ay2)], fill=gray, width=2)
                draw.polygon([(ax2 + arrow_w - 8, ay2 - 5), (ax2 + arrow_w - 8, ay2 + 5), (ax2 + arrow_w - 2, ay2)], fill=gray)
            zones_used.append(self._zone_manifest(f"step_{idx}", "body", sbox2))

        y += step_h + 24

        # ══════════════════════════════════════════════════════════════════════
        # 12. CTA BANNER
        # ══════════════════════════════════════════════════════════════════════
        cta_h = 72
        cta_box2 = (0, y, W, y + cta_h)
        draw.rectangle(cta_box2, fill=(235, 240, 255))
        left_z2 = self._zone_manifest("cta_left", "body", (margin_x, y + 8, W // 2, y + 36), 2)
        self._draw_text_block(draw, cta_text or "Ready to take control of your financial future?", type("Z", (), left_z2)(), purple, 15, padding=0, weight="bold")
        sub_z2 = self._zone_manifest("cta_sub", "body", (margin_x, y + 38, W // 2, y + cta_h - 6), 1)
        self._draw_text_block(draw, "Join Jiraaf today and invest with clarity and confidence.", type("Z", (), sub_z2)(), sec_text, 12, padding=0)
        btn_w2, btn_h2 = 180, 38
        btn_x2 = W - margin_x - btn_w2
        btn_y2 = y + (cta_h - btn_h2) // 2
        draw.rounded_rectangle((btn_x2, btn_y2, btn_x2 + btn_w2, btn_y2 + btn_h2), radius=19, fill=orange)
        btn_z2 = self._zone_manifest("cta_btn", "cta", (btn_x2 + 10, btn_y2 + 8, btn_x2 + btn_w2 - 10, btn_y2 + btn_h2 - 8), 1)
        self._draw_text_block(draw, "www.jiraaf.com", type("Z", (), btn_z2)(), (255, 255, 255), 13, padding=0, weight="bold", align="center")
        zones_used.append(self._zone_manifest("cta_section", "cta", cta_box2))
        y += cta_h + 6

        # DISCLAIMER
        disclaimer = body_text or "Figures shown are indicative. Actual results may vary. Read all risk related documents carefully."
        if y < H - 20:
            disc_z2 = self._zone_manifest("disclaimer", "legal", (margin_x, y + 4, W - margin_x, y + 20), 2)
            self._draw_text_block(draw, disclaimer, type("Z", (), disc_z2)(), gray, 10, padding=0, align="center")

        # BOTTOM ORANGE LINE
        draw.rectangle((0, H - 6, W, H), fill=orange)

        return image, {
            "logo_rendered": logo_rendered,
            "image_rendered": image_rendered,
            "template_rendered": False,
            "image_assessments": [],
            "render_path": "infographic_page",
            "layout_variant": "infographic_storyboard",
            "zones_used": zones_used,
            "text_blocks_used": [
                {"role": "headline", "text": headline_text},
                {"role": "supporting_line", "text": supporting_line},
                {"role": "cta", "text": cta_text},
            ],
            "text_fit": text_fit_manifest,
            "asset_boxes": [illustration_box],
            "overlap_checks": [],
            "pre_shortening": {
                "headline": {"original_length": len(headline_text), "fitted_length": len(headline_text), "shortened": False},
                "body": {"original_length": len(supporting_line), "fitted_length": len(supporting_line), "shortened": False},
            },
            "content_structure_type": page_text.get("content_structure_type") or "infographic",
        }
