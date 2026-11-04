import copy, re, sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.oxml.ns import qn

NAVY = RGBColor(0x1E, 0x27, 0x61); INK = RGBColor(0x1A, 0x1A, 0x2E); MUTED = RGBColor(0x5B, 0x60, 0x70)
PALE = RGBColor(0xF1, 0xF3, 0xF8); WHITE = RGBColor(0xFF, 0xFF, 0xFF); BLUE = RGBColor(0x3A, 0x4A, 0xA8)
AMBER = RGBColor(0xA8, 0x6E, 0x10); GOLD = RGBColor(0xF5, 0xB2, 0x2A); LIGHT = RGBColor(0xCA, 0xD3, 0xF2)
SOFT = RGBColor(0xDD, 0xE3, 0xF7); GREEN = RGBColor(0x1F, 0x7A, 0x4D); RULE = RGBColor(0xD5, 0xD8, 0xE0)
FOOTER = "SOP Progress Review - Chaitanya Goyal"
DATE = "November 2026"

p = Presentation(sys.argv[1])
orig = list(p.slides)                      # original 19 slides, by old number orig[n-1]
footer_src = [sh._element for sh in orig[4].shapes if sh.is_placeholder and sh.placeholder_format.idx != 0]
layout = orig[4].slide_layout
miss = []


# ------------------------------------------------------------------ helpers
def new_slide(title, notes=None):
    s = p.slides.add_slide(layout)
    s.shapes.title.text = title
    for el in footer_src:
        s.shapes._spTree.append(copy.deepcopy(el))
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def text(s, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP, align=None, sp=4):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    for i, segs in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.space_after = Pt(sp)
        if align: para.alignment = align
        if isinstance(segs, tuple): segs = [segs]
        for t, o in segs:
            r = para.add_run(); r.text = t
            r.font.size = Pt(o.get("size", 14)); r.font.bold = o.get("bold", False)
            r.font.italic = o.get("italic", False); r.font.color.rgb = o.get("color", INK)
    return tb


def box(s, x, y, w, h, fill=PALE, line=None, shape=MSO_SHAPE.RECTANGLE):
    b = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    b.fill.solid(); b.fill.fore_color.rgb = fill
    if line is None: b.line.fill.background()
    else: b.line.color.rgb = line; b.line.width = Pt(1.25)
    b.shadow.inherit = False
    return b


def arrow(s, x1, y1, x2, y2, color=MUTED):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color; c.line.width = Pt(1.5)
    ln = c.line._get_or_add_ln(); te = ln.makeelement(qn("a:tailEnd"), {"type": "triangle"}); ln.append(te)
    return c


def table(s, x, y, widths, rows, font=12.5, row_h=0.42, bold_first_col=True, highlight=()):
    nr, nc = len(rows), len(rows[0])
    gf = s.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(sum(widths)), Inches(row_h * nr))
    t = gf.table
    tblPr = t._tbl.tblPr
    for c, w in enumerate(widths): t.columns[c].width = Inches(w)
    for r in range(nr):
        t.rows[r].height = Inches(row_h)
        for c in range(nc):
            cell = t.cell(r, c); cell.margin_left = cell.margin_right = Inches(0.08)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            val = rows[r][c]
            tf = cell.text_frame; tf.word_wrap = True
            para = tf.paragraphs[0]; para.text = ""
            run = para.add_run(); run.text = str(val); run.font.size = Pt(font)
            if r == 0:
                run.font.bold = True; run.font.color.rgb = WHITE; fill = NAVY
            else:
                run.font.bold = (c == 0 and bold_first_col) or r in highlight
                run.font.color.rgb = INK
                fill = SOFT if r in highlight else (PALE if r % 2 == 0 else WHITE)
            cell.fill.solid(); cell.fill.fore_color.rgb = fill
    return gf


def clear(s):
    for sh in list(s.shapes):
        if not sh.is_placeholder:
            sh._element.getparent().remove(sh._element)


def drop(sh):
    sh._element.getparent().remove(sh._element)


def rep(s, old, new, n=None):
    def paras():
        for sh in s.shapes:
            if sh.has_text_frame: yield from sh.text_frame.paragraphs
            if sh.has_table:
                for row in sh.table.rows:
                    for c in row.cells: yield from c.text_frame.paragraphs
    for para in paras():
        for r in para.runs:
            if old in r.text:
                r.text = r.text.replace(old, new, 1); return
    miss.append((n, old))


def shape_by_text(s, start):
    return next(sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.startswith(start))


# ================================================================== edit existing slides
# --- 1 title
s = orig[0]
rep(s, "Value-Aware Team-Level Stopping for Multi-Robot Exploration using Hierarchical MARL",
    "Value-Aware Adaptive Multi-Robot Exploration under Resource Constraints", 1)
rep(s, "MARL Research Proposal", "SOP Progress Review · November 2026", 1)

# --- 3 how exploration stops today: rebuilt table with Amorín and WiSER-X
s = orig[2]
old = [sh for sh in s.shapes if sh.has_table][0]; top = old.top / 914400; drop(old)
table(s, 0.34, top, [2.55, 3.6, 2.55, 3.75], [
    ["Stopping rule", "How it decides", "Used in", "What it leaves open"],
    ["No frontiers left", "Explore until nothing reachable is unknown", "Yamauchi 1997 [1]; Burgard et al. 2005 [2]", "Cost of the last, scattered pockets"],
    ["Coverage or time budget", "Stop at X% mapped or after T minutes", "Common in practice and MARL benchmarks", "X and T must be re-tuned per map and team"],
    ["Fleet information gain", "Team stops when expected information gain of the fleet is low", "Amorín et al. 2019 [27]", "Hand-designed criterion; team size not adapted"],
    ["Uncertainty saturation", "Stop when map and pose uncertainty stop improving", "Placed & Castellanos 2022 [3]", "Single robot; motion and messages not priced"],
    ["Learned map completeness", "A CNN judges if the partial map is complete", "Luperto et al. 2026 [4]", "Single robot; supervised, not cost-aware"],
    ["Per-robot return rule", "A robot relays data when returning pays more than exploring", "Kim et al. 2026 (PRoID) [5]", "Per robot, hand-set; mission ends at a deadline"],
    ["Asynchronous termination", "Each robot finishes on its own, without a shared map", "Jadhav et al. 2026 (WiSER-X) [28]", "Per robot; effort not priced against gain"],
], font=12, row_h=0.6)
rep(s, "no rule decides, for the whole team, whether one more cycle is worth what it costs.",
    "stopping has been studied, but no rule learns, for the whole team, how much exploration effort is still worth its cost.", 3)
foot = shape_by_text(s, "Common thread"); foot.top = Inches(6.55)

# --- 5 three problems: problem C becomes effort allocation
s = orig[4]
rep(s, "Team-level stopping", "Exploration effort", 5)
rep(s, "When is one more cycle no longer worth its cost?", "How much exploration (robots, messages) is still worth buying? Stopping = zero effort.", 5)
rep(s, "Exploration uses fixed or single-robot rules [1]–[5]; MARL work fixes the episode length [8], [9].",
    "Stop rules exist [1], [3], [4], [5], [27], but none learns how much effort to keep; MARL work fixes the episode length [8], [9].", 5)
rep(s, "The claim is about when the whole team should stop.",
    "The claim is about how much exploration effort the whole team should keep spending, with stopping as its zero point.", 5)

# --- 6 what is already known: stopping row
s = orig[5]
rep(s, "Placed & Castellanos 2022 [3]; Luperto et al. 2026 [4]; PRoID 2026 [5]",
    "Amorín et al. 2019 [27]; Placed & Castellanos 2022 [3]; Luperto et al. 2026 [4]; PRoID 2026 [5]; WiSER-X 2026 [28]", 6)
rep(s, "Uncertainty-based and learned single-robot stop rules; per-robot return rules.",
    "Fleet information-gain stop; uncertainty-based and learned single-robot stops; per-robot return and asynchronous termination.", 6)
rep(s, "A team-level, learned, cost-aware decision to end the mission.",
    "Learning how much effort to keep (active robots, messages) from expected gain vs cost.", 6)

# --- 7 closest prior work: new table + narrowed claim
s = orig[6]
for sh in list(s.shapes):
    if not sh.is_placeholder: drop(sh)
Y, N = "✓", "✗"
table(s, 0.34, 1.5, [2.75, 1.35, 1.35, 2.0, 2.3, 2.7], [
    ["Work", "Multi-agent", "Learned", "Decision made for", "Adapts team size / messages", "Prices motion + messages + coordination"],
    ["Amorín et al. 2019 [27]", Y, N, "whole team (stop)", N, "not stated*"],
    ["Placed & Castellanos 2022 [3]", N, N, "single robot", N, N],
    ["Luperto et al. 2026 [4]", N, "supervised", "single robot", N, N],
    ["Kim et al. 2026, PRoID [5]", Y, N, "each robot", "indirectly (robots leave to relay)", "time, risk"],
    ["Jadhav et al. 2026, WiSER-X [28]", Y, "not stated*", "each robot", N, "not stated*"],
    ["Szostak & Cohen 2024 [19]", Y, Y, "partly", N, "sampling cost"],
    ["Han et al. 2019 [13]", Y, Y, "sub-policies only", N, N],
    ["This project", Y, Y, "whole team", "planned (Stage D)", Y],
], font=12, row_h=0.47, highlight=(8,))
box(s, 0.34, 5.85, 12.45, 0.78, fill=NAVY)
text(s, 0.55, 5.9, 12.0, 0.7, [[("Narrowed claim: ", {"size": 13.5, "bold": True, "color": GOLD}),
     ("to my knowledge, no prior work learns, for the whole team, how much exploration effort to keep buying "
      "(active robots, messages), priced against motion, communication and coordination cost. Stopping is the zero-effort case.",
      {"size": 13.5, "color": WHITE})]], anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.34, 6.66, 12.45, 0.3, [[("* Amorín et al. and WiSER-X characterised from their abstracts; full-text check in progress.",
                                   {"size": 11, "italic": True, "color": MUTED})]])

# --- 8 research questions: the review's RQ1–RQ5 with status
s = orig[7]
clear(s)
box(s, 0.45, 1.5, 12.45, 1.05, fill=NAVY)
text(s, 0.7, 1.55, 12.0, 0.95, [[("Can a hierarchical multi-agent policy allocate exploration resources (active team size, message budget, "
     "and finally termination) according to the expected marginal value of continued exploration?",
     {"size": 16, "bold": True, "color": WHITE})]], anchor=MSO_ANCHOR.MIDDLE)
table(s, 0.45, 2.75, [0.8, 7.35, 4.3], [
    ["", "Question", "Status"],
    ["RQ1", "Can the remaining value of exploration be estimated online from partial observations?", "Partly answered: r = 0.88, sign right 89% (Stage B)"],
    ["RQ2", "Can a learned controller reduce exploration effort (robots active) as value declines?", "Next: Stage D, this semester"],
    ["RQ3", "Does learning allocation and exploration jointly beat designing them separately?", "Next semester: 5-way ablation"],
    ["RQ4", "Does the policy generalise to new environments, team sizes, costs and comms without retraining?", "Partly: 36 settings tested; full plan fixed in advance"],
    ["RQ5", "Can robots approximate the central decision with only local observations and messages?", "Long term (follow-up work)"],
], font=12.5, row_h=0.62)

# --- 9 formulation 1: team action generalised
s = orig[8]
rep(s, "Continue or stop, once per cycle; later also: how many robots stay active",
    "Once per cycle: how many robots stay active and the message budget; stop = 0 robots", 9)
rep(s, "Our addition: team decision (Level 1)", "Our addition: team resource decision (Level 1)", 9)
rep(s, "a₀(t) ∈ { continue, stop }", "a_H(t) = ( N_active(t), B_comm(t) )", 9)
rep(s, "taken once per cycle from the team summary b(t)", "from the team summary b(t); stop ⇔ N_active = 0 (prototype: continue / stop only)", 9)

# --- 10 formulation 2: what changes next
s = orig[9]
for sh in s.shapes:
    if sh.shape_id == 6: sh.height = Inches(3.9)
text(s, 0.45, 5.95, 12.45, 0.9, [
    [("Next, from the review: ", {"size": 13, "bold": True, "color": NAVY}),
     ("N(N−1) assumes every robot talks to every other. Replace it with the cost over the links actually used, "
      "C_comm = Σ(α·data + β·messages + η·latency), and measure information as map entropy reduction H(Mₜ) − H(Mₜ₊₁). "
      "Report each part separately, not only the combined score.", {"size": 13, "color": INK})]])

# --- 13 architecture: mission-level resource controller
s = orig[12]
rep(s, "Level 1: team stopping policy", "Level 1: mission-level resource controller", 13)
rep(s, "Decides continue or stop; later also how many robots stay active.",
    "Decides how many robots stay active and the message budget; stopping = 0 robots.", 13)
rep(s, "Level 2: one policy per robot, every step, shared parameters",
    "Level 2: robot-level exploration, one shared policy per active robot, every step", 13)
box(s, 7.05, 1.75, 5.85, 4.92, fill=PALE)
text(s, 7.3, 1.9, 5.4, 4.7, [
    [("Why a hierarchy now", {"size": 17, "bold": True, "color": NAVY})],
    [("A binary stop does not need hierarchical MARL: regression or a threshold could do it.", {"size": 13.5})],
    [("Choosing how many robots stay active does: the top level sets the effort, slowly; "
      "the bottom level must adapt to whichever robots remain.", {"size": 13.5})],
    [("Today", {"size": 14, "bold": True, "color": AMBER})],
    [("Level 1 learned (continue / stop); Level 2 a fixed nearest-frontier rule.", {"size": 13.5})],
    [("Next", {"size": 14, "bold": True, "color": AMBER})],
    [("Level 1 picks the team size (Stage D); Level 2 learned with MAPPO only if Stage D shows a real gain (Stage E).",
      {"size": 13.5})],
], sp=7)

# --- 14 baselines: planned literature baselines
s = orig[13]
rep(s, "With α = 1.6 the gain-vs-cost rule stops once expected gain < cycle cost ÷ 1.6 (about 0.63 × cost).",
    "With α = 1.6 the gain-vs-cost rule stops once expected gain < cycle cost ÷ 1.6. Being added: fleet information-gain "
    "threshold [27], map-completeness rule [4], gain-per-time rule [5].", 14)
t = shape_by_text(s, "With α"); t.top = Inches(6.4); t.height = Inches(0.6)

# --- 15 metrics: Pareto and oracle
s = orig[14]
rep(s, "paired comparison on identical maps, 95% bootstrap intervals, and (for MARL) at least 5 training seeds, following Agarwal et al. [24].",
    "paired comparison on identical maps, 95% bootstrap intervals, at least 5 training seeds [24]. "
    "Added from the review: Pareto front of map value vs cost as cost weights vary; once robot motion is learned, "
    "two oracles (best stop on this run vs best joint policy).", 15)


# ================================================================== new slides
# A. since the last review
s = new_slide("Since the last review",
              "Open by saying the review was taken on board: claim narrowed, problem reframed, and the staged programme started "
              "with Stages A and B done.")
items = [("Claim narrowed", "Amorín 2019 and WiSER-X added. No more 'first to study stopping'; the claim is about learning how much effort to keep."),
         ("Problem reframed", "From 'when to stop' to 'how much exploration effort is worth buying'. Stopping = zero robots active."),
         ("Stages A and B done", "The problem is real when costs are high; the RL-style target is needed, a big model is not."),
         ("Code on GitHub", "Simulator, learned stop rule, all experiments and plots, reproducible from saved runs.")]
for i, (h, b) in enumerate(items):
    x = 0.45 + i * 3.15
    box(s, x, 1.75, 2.95, 4.3, fill=NAVY if i == 2 else PALE)
    text(s, x + 0.2, 1.95, 2.6, 0.4, [[(f"0{i + 1}", {"size": 13, "bold": True, "color": GOLD if i == 2 else AMBER})]])
    text(s, x + 0.2, 2.4, 2.6, 0.9, [[(h, {"size": 19, "bold": True, "color": WHITE if i == 2 else INK})]])
    text(s, x + 0.2, 3.35, 2.6, 2.6, [[(b, {"size": 14, "color": SOFT if i == 2 else MUTED})]])
text(s, 0.45, 6.25, 12.4, 0.5, [[("Repository: github.com/dev-goyal-chaitanya/marl-simulations (private; access on request)",
                                   {"size": 13, "color": MUTED})]])
s_since = s

# B. formulation 4
s = new_slide("Formulation 4: allocation",
              "This is the review's generalisation. The prototype's stop rule is the two-action special case.")
sizes = ["8", "5", "2", "1", "0"]
for i, n in enumerate(sizes):
    x = 0.55 + i * 1.2
    box(s, x, 2.05, 0.85, 0.85, fill=NAVY if n != "0" else GOLD, shape=MSO_SHAPE.OVAL)
    text(s, x, 2.05, 0.85, 0.85, [[(n, {"size": 22, "bold": True, "color": WHITE if n != "0" else INK})]],
         anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
    if i < 4: arrow(s, x + 0.88, 2.475, x + 1.17, 2.475)
text(s, 0.45, 3.05, 6.0, 0.9, [[("Active robots N_active(t) over the mission. Effort shrinks as the remaining value falls; "
                                  "0 active robots is termination.", {"size": 13.5, "color": MUTED})]])
box(s, 0.45, 4.15, 5.9, 2.5, fill=PALE)
text(s, 0.65, 4.25, 5.5, 2.35, [
    [("What changes", {"size": 15, "bold": True, "color": NAVY})],
    [("Action: (N_active, B_comm) instead of {continue, stop}", {"size": 13.5})],
    [("Utility: map entropy reduction, not raw cell counts", {"size": 13.5})],
    [("Costs: motion, communication, coordination, and later risk", {"size": 13.5})],
    [("Prototype rule 'stop when Q ≤ 0' = the case with two actions", {"size": 13.5})],
], sp=6)
text(s, 6.75, 1.75, 6.15, 5.0, [
    [("Marginal value of exploration", {"size": 15, "bold": True, "color": NAVY})],
    [("MVE(bₜ, a) = E[ΔU | bₜ, a] − E[C_motion + C_comm + C_coord + C_risk | bₜ, a]", {"size": 15, "bold": True})],
    [("expected extra map utility minus expected cost of choosing effort level a", {"size": 12.5, "color": MUTED})],
    [("Decision", {"size": 15, "bold": True, "color": NAVY})],
    [("a* = argmax over a of Q(bₜ, a),   Q(b, a) = E[ r(a) + γ·V(bₜ₊₁) ]", {"size": 15, "bold": True})],
    [("γ ≤ 1 discounts the future; the prototype uses γ = 1", {"size": 12.5, "color": MUTED})],
    [("Termination", {"size": 15, "bold": True, "color": NAVY})],
    [("Q(b, STOP) = 0;  stop when max over a ≠ STOP of Q(b, a) ≤ 0", {"size": 15, "bold": True})],
    [("the optimal-stopping idea [14], [15], embedded in resource allocation", {"size": 12.5, "color": MUTED})],
], sp=6)
s_form4 = s

# C. experimental programme
s = new_slide("Experimental programme",
              "MARL comes last, only after the problem is shown to be real, learnable, and to benefit from team resizing.")
stages = [("A", "Is the problem real?", "Value lost by exploring to the end, across maps, teams, costs", "Done", GREEN),
          ("B", "Is it learnable?", "Simple models vs fitted Q-iteration for the remaining value", "Done", GREEN),
          ("C", "Stopping benchmark", "Robot motion fixed; all stop rules incl. [4], [5], [27] and the oracle", "In progress", AMBER),
          ("D", "Adaptive team size", "8 → 6 → 3 → 1 → 0: same map value at lower cost?", "Next", NAVY),
          ("E", "Hierarchical MARL", "Resource controller + MAPPO exploration [22]; ablation of 5 combinations", "Next semester", MUTED)]
for i, (k, h, b, st, col) in enumerate(stages):
    x = 0.45 + i * 2.5
    box(s, x, 1.8, 2.25, 3.9, fill=PALE)
    text(s, x + 0.15, 1.92, 2.0, 0.55, [[(f"Stage {k}", {"size": 13, "bold": True, "color": AMBER})]])
    text(s, x + 0.15, 2.35, 2.0, 0.9, [[(h, {"size": 17, "bold": True})]])
    text(s, x + 0.15, 3.3, 2.0, 1.7, [[(b, {"size": 13, "color": MUTED})]])
    tag = box(s, x + 0.15, 5.05, 1.95, 0.42, fill=col)
    text(s, x + 0.15, 5.05, 1.95, 0.42, [[(st, {"size": 12.5, "bold": True, "color": WHITE})]],
         anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
    if i < 4: arrow(s, x + 2.27, 3.75, x + 2.48, 3.75)
text(s, 0.45, 5.95, 12.4, 0.8, [[("Gazebo / ROS2 (MRTA testbed) is used to test what the grid world leaves out: pose noise, sensor noise, "
                                   "message drops, battery variation, robot failure. It is a check, not the contribution.",
                                   {"size": 13, "color": INK})]])
s_prog = s

# D. Stage A
s = new_slide("Stage A: is the problem real?",
              "1,440 scored runs: 2/4/6/8 robots x 32/48/64 maps x 3 message costs, 40 maps each. "
              "Value lost = (best stop value - explore-to-end value) / cells revealed. Driving after best stop = share of all robot steps.")
cd = CategoryChartData(); cd.categories = ["2 robots", "4 robots", "6 robots", "8 robots"]
cd.add_series("low message cost", (9.3, 6.1, 6.3, 5.8))
cd.add_series("medium", (9.6, 7.2, 8.8, 10.8))
cd.add_series("high", (10.3, 10.6, 18.5, 33.8))
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.35), Inches(1.6), Inches(7.6), Inches(4.5), cd)
ch = gf.chart; ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.TOP; ch.legend.include_in_layout = False
ch.legend.font.size = Pt(12)
for ser, col in zip(ch.plots[0].series, (LIGHT, BLUE, GOLD)):
    ser.format.fill.solid(); ser.format.fill.fore_color.rgb = col
pl = ch.plots[0]; pl.gap_width = 60; pl.has_data_labels = True
pl.data_labels.font.size = Pt(11); pl.data_labels.number_format = "0"; pl.data_labels.number_format_is_linked = False
pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
ch.category_axis.tick_labels.font.size = Pt(12)
va = ch.value_axis; va.has_major_gridlines = True; va.major_gridlines.format.line.color.rgb = RULE
va.tick_labels.font.size = Pt(11); va.has_title = True
va.axis_title.text_frame.text = "value lost by exploring to the end (% of map)"
va.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(11)
ch.has_title = False
text(s, 0.45, 6.2, 7.5, 0.6, [[("Averaged over 32/48/64 maps, 40 maps each. On average 11.4% of the map's value and 36% of all driving "
                                 "are spent after the best stopping point.", {"size": 12.5, "color": MUTED})]])
text(s, 8.3, 1.65, 4.6, 0.5, [[("But it depends on the price of driving", {"size": 15, "bold": True, "color": NAVY})]])
table(s, 8.3, 2.2, [1.35, 1.6, 1.65], [
    ["Cost per step", "Value lost (% of map)", "Driving after best stop"],
    ["0.5", "1.0", "4.8%"], ["1", "2.2", "9.6%"], ["2 (default)", "9.1", "33%"], ["3", "27.3", "68%"],
], font=12, row_h=0.5, highlight=(3,))
text(s, 8.3, 4.85, 4.6, 1.9, [
    [("Medium message cost, all 12 team/map combinations.", {"size": 12, "color": MUTED})],
    [("Cheap driving: just explore everything. The work matters when motion or messages are expensive, "
      "so the next step is real cost values or a full sweep (Pareto).", {"size": 13.5})],
], sp=6)
s_A = s

# E. Stage B
s = new_slide("Stage B: is RL needed?",
              "Same 7 features and training runs. fqi = fitted Q-iteration (target uses the model's own next-state estimate). "
              "hindsight = supervised regression on the best remaining value seen after the run. Regret = value lost vs best stop, "
              "% of map, over 36 settings without retraining. Sign accuracy measured on 100 test maps of the training setting.")
table(s, 0.45, 1.55, [2.6, 2.0, 2.05, 2.0, 1.75, 2.0], [
    ["Training target", "Model", "Avg value lost (% map)", "Worst setting", "Settings < 50%", "Sign of value right"],
    ["fitted Q-iteration", "extra trees (current)", "3.6", "9.9", "1", "89%"],
    ["fitted Q-iteration", "random forest", "3.7", "10.3", "1", "89%"],
    ["fitted Q-iteration", "linear", "3.5", "13.0", "4", "89%"],
    ["fitted Q-iteration", "neural net", "4.8", "12.1", "1", "89%"],
    ["hindsight labels", "linear", "6.7", "30.4", "6", "85%"],
    ["hindsight labels", "neural net", "5.4", "37.4", "5", "79%"],
    ["hindsight labels", "random forest", "9.0", "35.7", "8", "80%"],
    ["hindsight labels", "extra trees", "9.6", "39.0", "8", "79%"],
    ["reference: coverage threshold (tuned)", "—", "4.7", "25.3", "5", "—"],
], font=12, row_h=0.44, highlight=(1,))
text(s, 0.45, 6.05, 12.4, 0.85, [
    [("Why: ", {"size": 13, "bold": True, "color": NAVY}),
     ("hindsight labels assume the team will later stop perfectly, so they overvalue continuing and stop too late "
      "(the perfect-foresight bias known in optimal stopping [15]). The model barely matters: even linear works.", {"size": 13})]])
s_B = s

# F. stopping benchmark so far
s = new_slide("Stage C: stopping benchmark",
              "% of best = ratio of total net value to the hindsight-best total, 140 test maps of the training setting "
              "(2 robots, 32x32, medium cost). Value lost = mean over 36 settings without retraining.")
table(s, 0.45, 1.55, [3.6, 2.6, 3.0, 3.25], [
    ["Stop rule", "% of best (training setting)", "Avg value lost, 36 settings", "Worst setting (% of map)"],
    ["Learned value-aware stop", "91", "3.6", "9.9"],
    ["Coverage threshold (tuned)", "92", "4.7", "25.3"],
    ["Gain-vs-cost rule (tuned)", "89", "6.9", "15.8"],
    ["Fixed budget (tuned)", "91", "9.1", "37.1"],
    ["Myopic (stop after a losing cycle)", "68", "11.4", "24.5"],
    ["Explore until no frontiers", "74", "11.4", "44.6"],
], font=13, row_h=0.5, highlight=(1,))
box(s, 0.45, 5.25, 6.1, 1.45, fill=PALE)
text(s, 0.65, 5.33, 5.75, 1.3, [[("Typical case: ", {"size": 13.5, "bold": True, "color": NAVY}),
     ("a tie with the tuned coverage threshold.", {"size": 13.5})],
    [("Worst case: ", {"size": 13.5, "bold": True, "color": NAVY}),
     ("9.9% vs 25.3% lost, with no re-tuning per setting.", {"size": 13.5})]], sp=6)
box(s, 6.8, 5.25, 6.1, 1.45, fill=PALE)
text(s, 7.0, 5.33, 5.75, 1.3, [[("Known weakness: ", {"size": 13.5, "bold": True, "color": AMBER}),
     ("2 robots on 48/64 maps stop 20–33 cycles early; cause not yet diagnosed. One training seed so far.", {"size": 13.5})]])
s_C = s

# G. next: team shrinking
s = new_slide("Stage D: adaptive team size",
              "Design choices to confirm with the supervisor before building: what a retired robot does, and whether retirement is permanent.")
text(s, 0.45, 1.6, 6.1, 5.0, [
    [("How it will work", {"size": 16, "bold": True, "color": NAVY})],
    [("1. Each cycle the controller picks N_active ∈ {0, …, N}.", {"size": 14})],
    [("2. Retired robots stop moving and messaging: no motion or message cost.", {"size": 14})],
    [("3. Training data: runs where robots retire at random times, so every team size is seen.", {"size": 14})],
    [("4. Same fitted Q-iteration, with N_active as an input; pick the size with the highest Q.", {"size": 14})],
    [("Compare", {"size": 16, "bold": True, "color": NAVY})],
    [("Full team + learned stop  ·  fixed schedule 8 → 4 → 2 → 0  ·  learned resizing", {"size": 14})],
    [("Success = nearly the same map value at clearly lower motion and message cost.", {"size": 14})],
], sp=8)
box(s, 6.85, 1.6, 6.05, 5.0, fill=NAVY)
text(s, 7.1, 1.75, 5.6, 4.8, [
    [("Questions for you", {"size": 16, "bold": True, "color": GOLD})],
    [("1. Realistic costs: take energy per metre and bandwidth from the MRTA robots, or report a sweep?", {"size": 14, "color": WHITE})],
    [("2. A retired robot: park in place, or return to base (and pay that trip)?", {"size": 14, "color": WHITE})],
    [("3. Retirement permanent, or can robots be re-activated?", {"size": 14, "color": WHITE})],
    [("4. Paper 1 (value estimation + termination, no MARL) as the first target?", {"size": 14, "color": WHITE})],
], sp=10)
s_D = s

# H. generalisation and reporting plan
s = new_slide("Generalisation plan",
              "From section 10 of the review: designed before training, not after seeing results.")
table(s, 0.45, 1.6, [2.4, 5.6, 4.45], [
    ["Shift", "Train → test", "Status"],
    ["Environment", "rooms → maze, warehouse, cluttered, subterranean-style", "Only rooms so far; adding maps"],
    ["Scale", "32×32 → 64×64 → 128×128", "Tested up to 64×64"],
    ["Team size", "train 2–4 robots → test 5, 6, 8, 10", "Trained on 2, tested on 2–8"],
    ["Communication", "full → limited radius, bandwidth, packet loss, delays", "Only message cost varied"],
    ["Costs", "sweep of motion / message weights (Pareto front)", "3 message costs; motion sweep in Stage A"],
], font=13, row_h=0.6)
text(s, 0.45, 5.45, 12.4, 1.3, [
    [("Target result: ", {"size": 14, "bold": True, "color": NAVY}),
     ("a policy trained on small teams and maps transfers without retraining to larger teams and unseen environments, "
      "keeps a high share of the hindsight-best value, costs clearly less than full exploration, and beats tuned stopping baselines "
      "across cost and communication regimes. The numbers come from the experiments, not set in advance.", {"size": 14})]])
s_gen = s

# I. timeline + literature
s = new_slide("Plan for this semester",
              "Dates are a proposal; adjust to the semester calendar.")
table(s, 0.45, 1.6, [2.4, 5.6, 4.45], [
    ["When", "Build", "Output"],
    ["Nov, week 1–2", "Real cost values or sweep; baselines from [4], [5], [27]", "Full Stage C table"],
    ["Nov, week 2–4", "Team resizing (Stage D)", "Learned resizing vs fixed schedule vs full team"],
    ["Late Nov", "New map types, 5 seeds, diagnose 2-robot failure", "Generalisation table"],
    ["Early Dec", "Write-up of Stages A–D", "Report + Paper 1 draft outline"],
], font=13, row_h=0.6)
box(s, 0.45, 4.85, 12.45, 1.85, fill=PALE)
text(s, 0.7, 4.95, 12.0, 1.7, [
    [("Literature (in parallel)", {"size": 15, "bold": True, "color": NAVY})],
    [("Shared database: 33 entries today across exploration, stopping criteria, MARL exploration, hierarchical MARL, "
      "optimal stopping and communication. Target: 50 by end of November, 80 before the MARL stage.", {"size": 13.5})],
    [("Each paper recorded on the review's 10 questions: decision made, learned or hand-designed, single or multi-agent, "
      "individual or mission-level stop, utility, costs, comm constraints, dynamic team size, centralised or not, test settings.",
      {"size": 13.5})],
], sp=5)
s_plan = s

# J. publication plan
s = new_slide("Possible publication path",
              "Each stage can stand on its own; MARL is the mechanism, not the contribution.")
papers = [("Paper 1", "Learning the Marginal Value of Continued Multi-Robot Exploration",
           "Continuation-value estimation, value-aware termination, full stopping benchmark, generalisation. No MARL needed. Stages A–C.", "This semester"),
          ("Paper 2", "Hierarchical Resource-Aware MARL for Adaptive Multi-Robot Exploration",
           "Which robots explore, how many stay active, when to stop. Stages D–E.", "Next semester"),
          ("Paper 3", "Decentralised Value-Aware Mission Termination under Communication Constraints",
           "Local estimates, learned communication, robustness to packet loss and failures. RQ5.", "Follow-up")]
for i, (k, t_, b, when) in enumerate(papers):
    x = 0.45 + i * 4.2
    box(s, x, 1.75, 3.95, 4.3, fill=NAVY if i == 0 else PALE)
    text(s, x + 0.25, 1.9, 3.5, 0.4, [[(k, {"size": 13, "bold": True, "color": GOLD if i == 0 else AMBER})]])
    text(s, x + 0.25, 2.3, 3.5, 1.45, [[(t_, {"size": 17, "bold": True, "color": WHITE if i == 0 else INK})]])
    text(s, x + 0.25, 3.8, 3.5, 1.7, [[(b, {"size": 13.5, "color": SOFT if i == 0 else MUTED})]])
    text(s, x + 0.25, 5.5, 3.5, 0.4, [[(when, {"size": 13, "bold": True, "color": GOLD if i == 0 else NAVY})]])
text(s, 0.45, 6.25, 12.4, 0.5, [[("Framing: exploration as the sequential allocation of exploration resources under diminishing returns; "
                                   "termination is the zero-resource boundary.", {"size": 13.5, "italic": True, "color": NAVY})]])
s_pub = s

# ================================================================== order
O = lambda n: orig[n - 1]
order = [O(1), s_since, O(2), O(3), O(4), O(5), O(6), O(7), O(8), O(9), O(10), O(11), s_form4, O(12), O(13),
         O(14), O(15), s_prog, s_A, s_B, s_C, s_D, s_gen, s_plan, s_pub, O(17), O(18), O(19)]
lst = p.slides._sldIdLst
ids = {s.slide_id: el for el in lst for s in [None]} if False else None
by_id = {el.get("id"): el for el in lst}
old16 = O(16)
want = [str(s.slide_id) for s in order]
for el in list(lst): lst.remove(el)
for sid in want: lst.append(by_id[sid])
# drop old 16 (phased plan) relationship
rid = [r for r, rel in p.part.rels.items() if rel.target_part is old16.part][0]
p.part.drop_rel(rid)

# ================================================================== citations: renumber by first appearance
ref_slides = [O(17), O(18)]
old_refs = {}
for s in ref_slides:
    sh = [x for x in s.shapes if x.has_text_frame and x.shape_id == 6][0]
    for para in sh.text_frame.paragraphs:
        m = re.match(r"\[(\d+)\]\s+(.*)", para.text)
        if m: old_refs[int(m.group(1))] = m.group(2)
old_refs[27] = "Amorín, Benavides, Grampín. A novel stop criterion to support efficient multi-robot mapping. LARS/SBR/WRE 2019, pp. 369–374."
old_refs[28] = "Jadhav, Behari, Wood, Gil. WiSER-X: wireless signals-based efficient decentralized multi-robot exploration without explicit information exchange. IEEE RA-L 2026."


def all_runs(s):
    for sh in s.shapes:
        if sh.has_text_frame:
            for para in sh.text_frame.paragraphs: yield from para.runs
        if sh.has_table:
            for row in sh.table.rows:
                for c in row.cells:
                    for para in c.text_frame.paragraphs: yield from para.runs


body = [s for s in order if s not in ref_slides]
assert not any("]–[" in r.text for s in body for r in all_runs(s)), "range citation left"
mapping = {}
for s in body:
    for r in all_runs(s):
        for m in re.finditer(r"\[(\d+)\]", r.text):
            k = int(m.group(1))
            if k not in mapping: mapping[k] = len(mapping) + 1
for s in body:
    for r in all_runs(s):
        if re.search(r"\[\d+\]", r.text):
            r.text = re.sub(r"\[(\d+)\]", lambda m: f"[{mapping[int(m.group(1))]}]", r.text)
unused = sorted(set(old_refs) - set(mapping))
print("refs used", len(mapping), "unused", unused)
new_list = [old_refs[k] for k, _ in sorted(mapping.items(), key=lambda kv: kv[1])]
half = (len(new_list) + 1) // 2
for s, chunk, start in ((ref_slides[0], new_list[:half], 1), (ref_slides[1], new_list[half:], half + 1)):
    sh = [x for x in s.shapes if x.has_text_frame and x.shape_id == 6][0]
    tf = sh.text_frame
    tmpl = copy.deepcopy(tf.paragraphs[0]._p)
    for para in list(tf.paragraphs): para._p.getparent().remove(para._p)
    for k, txt in enumerate(chunk):
        el = copy.deepcopy(tmpl); tf._txBody.append(el)
        para = tf.paragraphs[-1]; para.runs[0].text = f"[{start + k}]  {txt}"
        for r in para.runs[1:]: r.text = ""
        for r in para.runs: r.font.size = Pt(12.5)
        para.space_after = Pt(4)

# ================================================================== footers and numbers
for i, s in enumerate(order, 1):
    for sh in s.shapes:
        if not sh.is_placeholder: continue
        t = sh.placeholder_format.type
        if t == 16: sh.text_frame.text = DATE
        elif t == 15: sh.text_frame.text = FOOTER
        elif t == 13: sh.text_frame.text = str(i)
    for sh in s.shapes:   # slide-number text boxes on title/closing slides
        if not sh.is_placeholder and sh.has_text_frame and sh.text_frame.text.strip().isdigit() and i in (1, len(order)):
            sh.text_frame.paragraphs[0].runs[0].text = str(i)

print("missing", miss)
p.save(sys.argv[2])
print("slides", len(order))
