"""Revised, more descriptive proposal deck (v2) on the BITS CSIS template."""
import sys, json, pickle
import numpy as np
from helpers_v2 import *          # prs, slides, colours, text/box/arrow/table/chart helpers
from pptx.chart.data import XyChartData

sys.path.insert(0, PROTO)
from mapgen import make_map
from env import run_exhaustive
from stopping import CostModel, COMM_LEVELS, rewards, evaluate_stop, oracle_stop

E = json.load(open(f"{PROTO}/results/extra_metrics.json"))
RULES = pickle.load(open(f"{PROTO}/results/rules.pkl", "rb"))
LEARNED = RULES[-1]
KEYS = ["Explore until no frontiers", "Fixed cycle budget (tuned)", "Coverage threshold (tuned)",
        "One-step look-ahead", "Info-gain vs cost heuristic (tuned)", "Learned value-aware stopping"]
DISP = {"Explore until no frontiers": "Explore until no frontiers",
        "Fixed cycle budget (tuned)": "Fixed budget (19 cycles)",
        "Coverage threshold (tuned)": "Coverage threshold (84%)",
        "One-step look-ahead": "Myopic: stop after a losing cycle",
        "Info-gain vs cost heuristic (tuned)": "Gain-vs-cost rule (α = 1.6)",
        "Learned value-aware stopping": "Learned value-aware stop"}
P = E["pooled_in_distribution"]
GEN = E["generalisation"]
NREG = E["normalized_regret"]          # 36 values per rule, order: size -> robots -> comm
ORDER36 = [(s, n, c) for s in (32, 48, 64) for n in (2, 4, 6, 8) for c in ("low", "medium", "high")]
SUB = RGBColor(0xDD, 0xE3, 0xF7)
GREEN = RGBColor(0x1F, 0x7A, 0x4D)
RED = RGBColor(0xB0, 0x3A, 0x2E)


def pct(x):
    return f"{x:.0f}%"


# ======================================================================= 1. title
for sh in title_slide.shapes:
    if sh.is_placeholder and sh.placeholder_format.idx == 14:
        sh.text_frame.paragraphs[0].runs[0].text = \
            "Value-Aware Team-Level Stopping for Multi-Robot Exploration using Hierarchical MARL"
        for r in sh.text_frame.paragraphs[0].runs:
            r.font.size = Pt(30)
    elif sh.is_placeholder and sh.placeholder_format.idx == 13:
        ps = sh.text_frame.paragraphs
        ps[0].runs[0].text = "MARL Research Proposal (revised)"
        for r in ps[0].runs[1:]:
            r.text = ""
        ps[1].runs[0].text = "Chaitanya Goyal (2024A7PS0557P)"
        for r in ps[1].runs[1:]:
            r.text = ""
        ps[2].runs[0].text = "Supervisor: Prof. Avinash Gautam"
    elif sh.has_text_frame and "Presenting" in sh.text_frame.text:
        ps = sh.text_frame.paragraphs
        ps[1].runs[0].text = "October 2026"
        for r in ps[1].runs[1:]:
            r.text = ""
title_slide.notes_slide.notes_text_frame.text = (
    "This is the revised proposal after your feedback. The project is no longer framed as an LLM-style "
    "orchestrator. It asks one question: can a hierarchical multi-agent RL policy learn when continued "
    "multi-robot exploration is no longer worth its motion, communication and coordination cost? "
    "I will cover the problem and background, what already exists, the formal problem, a first working "
    "prototype with honest results, and the two-semester plan.")

# ======================================================================= 2. agenda
s = new_slide("What this talk covers",
              "Five parts. The first two explain why the problem matters and what already exists. The third "
              "states the problem formally. The fourth shows what I built in week 1 and what it does and does not "
              "show. The fifth is the plan for two semesters.")
parts = [("1", "The problem", "How multi-robot exploration works, and how it decides to stop today"),
         ("2", "What exists", "Stopping rules, MARL for exploration, and the closest prior work"),
         ("3", "Formulation", "Net value of a cycle, optimal stopping, the two-level architecture"),
         ("4", "First evidence", "Week-1 prototype, metrics, results, and its weak spots"),
         ("5", "The plan", "Phases, ablations, experiment matrix, timeline, risks")]
for i, (num, head, desc) in enumerate(parts):
    y = 1.75 + i * 0.98
    c = box(s, 0.6, y, 0.72, 0.72, fill=NAVY if i != 3 else AMBER, shape=MSO_SHAPE.OVAL)
    text(s, 0.6, y + 0.1, 0.72, 0.55, [[(num, {"size": 22, "bold": True, "color": WHITE})]], align=PP_ALIGN.CENTER)
    text(s, 1.6, y + 0.02, 3.4, 0.5, [[(head, {"size": 21, "bold": True, "color": NAVY})]])
    text(s, 5.0, y + 0.08, 7.8, 0.6, [[(desc, {"size": 17, "color": INK})]])
    if i < 4:
        box(s, 1.6, y + 0.84, 11.2, 0.012, fill=LINE)

# ======================================================================= 3. background
s = new_slide("Background: multi-robot exploration",
              "Exploration means building a map of an unknown place. The map is a grid: each cell is free, "
              "a wall, or still unknown. A frontier is a known free cell next to an unknown one; driving there "
              "reveals new space. The team repeats a cycle: sense, share maps, give each robot a frontier, move. "
              "Classical exploration (Yamauchi 1997) keeps doing this until no frontier is left.")
GRID = ["############",
        "#....#??????",
        "#.A..#??????",
        "#....F??????",
        "#.....FF????",
        "#..B...F????",
        "#....##F????",
        "############"]
cs, gx, gy = 0.46, 0.55, 1.85
for r_, row in enumerate(GRID):
    for c_, ch_ in enumerate(row):
        fill = {"#": RGBColor(0x3C, 0x3F, 0x48), "?": RGBColor(0xDD, 0xE0, 0xE7),
                "F": RGBColor(0xF6, 0xD9, 0x9B)}.get(ch_, WHITE)
        box(s, gx + c_ * cs, gy + r_ * cs, cs, cs, fill=fill, line=LINE)
for ch_, col in (("A", BLUE), ("B", TEAL)):
    r_ = [i for i, row in enumerate(GRID) if ch_ in row][0]
    c_ = GRID[r_].index(ch_)
    ring = box(s, gx + (c_ - 1.5) * cs, gy + (r_ - 1.5) * cs, 4 * cs, 4 * cs, fill=None, shape=MSO_SHAPE.OVAL)
    ring.line.color.rgb = col
    ring.line.width = Pt(1.5)
    ring.line.dash_style = 4
    box(s, gx + c_ * cs + 0.07, gy + r_ * cs + 0.07, cs - 0.14, cs - 0.14, fill=col, shape=MSO_SHAPE.OVAL)
legend = [(WHITE, "known free"), (RGBColor(0x3C, 0x3F, 0x48), "wall"), (RGBColor(0xDD, 0xE0, 0xE7), "unknown"),
          (RGBColor(0xF6, 0xD9, 0x9B), "frontier"), (BLUE, "robot + sensor range")]
for i, (col, lab) in enumerate(legend):
    lx = gx + (i % 3) * 1.9
    ly = gy + 8 * cs + 0.2 + (i // 3) * 0.38
    box(s, lx, ly + 0.04, 0.24, 0.24, fill=col, line=LINE)
    text(s, lx + 0.34, ly, 1.6, 0.35, [[(lab, {"size": 12, "color": MUTED})]])
text(s, 6.45, 1.75, 6.45, 5.0, [
    [("Occupancy grid. ", {"bold": True, "color": NAVY}), ("The map is a grid of cells: free, wall, or unknown. "
                                                           "Robots start knowing nothing.", {})],
    [("Sensing. ", {"bold": True, "color": NAVY}), ("Each robot sees cells within a fixed radius, in line of "
                                                    "sight. Walls block the view.", {})],
    [("Frontier. ", {"bold": True, "color": NAVY}), ("A known free cell next to an unknown one. Going there "
                                                     "reveals new space (Yamauchi 1997).", {})],
    [("Allocation. ", {"bold": True, "color": NAVY}), ("Each robot gets a different frontier, trading off "
                                                       "distance and expected gain (Burgard et al. 2005).", {})],
    [("Exploration cycle. ", {"bold": True, "color": NAVY}), ("Sense → share maps → assign frontiers → move. "
                                                              "Repeat.", {})],
    [("The open question. ", {"bold": True, "color": AMBER}), ("After how many cycles should the whole team "
                                                               "stop?", {"bold": True})],
], size=16, space_after=11)

# ======================================================================= 4. how exploration stops today
s = new_slide("How exploration decides to stop today",
              "Luperto et al. (2026) and Placed & Castellanos (2022) both point out that stopping is an "
              "under-studied part of exploration. Every rule in use today is either a fixed threshold, a "
              "single-robot criterion, or a per-robot rule. None of them weighs the expected value of the "
              "remaining map against what the whole team pays to get it.")
rows = [["Stopping rule", "How it decides", "Used in", "What it ignores"],
        ["No frontiers left", "Explore until nothing reachable is unknown",
         "Yamauchi 1997; Burgard et al. 2005", "Cost of the last, scattered pockets"],
        ["Coverage or time budget", "Stop at X% mapped or after T minutes",
         "Common in practice and in MARL benchmarks", "X and T must be re-tuned for every map and team"],
        ["Uncertainty saturation", "Stop when map and pose uncertainty stop improving",
         "Placed & Castellanos 2022", "Single robot; motion and messages not priced"],
        ["Learned map completeness", "A CNN judges if the partial map is complete",
         "Luperto et al. 2026", "Single robot; supervised, not cost-aware"],
        ["Per-robot return rule", "A robot relays data when returning pays more than exploring",
         "Kim et al. 2026 (PRoID)", "Per robot and hand-set; the mission ends at a deadline"]]
table(s, 0.45, 1.75, 12.45, [2.7, 3.7, 3.0, 3.05], rows, font=13, row_h=0.72)
text(s, 0.45, 6.2, 12.4, 0.5, [[("Common thread: ", {"size": 15, "bold": True, "color": NAVY}),
                                ("no rule decides, for the whole team, whether one more cycle is worth what it costs.",
                                 {"size": 15})]])

# ======================================================================= 5. the problem
rng = np.random.default_rng(50018)
ex = run_exhaustive(make_map(40, rng), 3, seed=50018 + 7)
cost = CostModel()
rr = rewards(ex, cost)
gain = np.r_[0, np.cumsum([o["gain"] for o in ex["outcomes"]])]
net = np.r_[0, np.cumsum(rr)]
spent = gain - net
t_stop = LEARNED.stop_time(ex, cost)
Tn = len(rr)
cov_stop = 100 * ex["obs"][t_stop]["free_coverage"]
s = new_slide("When should the team stop?",
              f"One real run from my prototype: 3 robots on a 40 by 40 map. Map revealed (blue) rises fast, then "
              f"flattens: the last part of the map comes in small, scattered pockets. Cost (amber) keeps growing "
              f"at a steady rate. Net value (teal) is revealed minus cost; it peaks and then falls. The learned "
              f"policy stopped at cycle {t_stop} with {cov_stop:.0f}% of the free space mapped. Carrying on to the last "
              f"frontier took {Tn - t_stop} more cycles, added {100 - cov_stop:.0f}% more map, and cut net value from "
              f"{net[t_stop]:.0f} to {net[-1]:.0f}.")
text(s, 0.45, 1.75, 4.1, 4.9, [
    "Early cycles reveal whole rooms. Late cycles reveal small, scattered pockets that need long drives.",
    "Every cycle costs the same or more: robot motion (energy, time), map-sharing messages, re-planning.",
    [("So the question is not whether the team ", {}), ("can", {"italic": True}),
     (" explore further, but whether one more cycle is ", {}), ("worth its cost.", {"bold": True, "color": NAVY})],
    [("Messages grow as N(N−1) with team size N, so the question gets sharper for bigger teams.",
      {"size": 14, "color": MUTED})],
], size=16, space_after=12)
cd = CategoryChartData()
cd.categories = [str(i) for i in range(Tn + 1)]
cd.add_series("Map revealed (cells)", [float(v) for v in gain])
cd.add_series("Cost: motion + messages + coordination", [float(v) for v in spent])
cd.add_series("Net value = revealed − cost", [float(v) for v in net])
gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(4.85), Inches(1.65), Inches(8.2), Inches(4.6), cd)
ch = gf.chart
style_chart(ch)
ch.has_legend = True
ch.legend.position = XL_LEGEND_POSITION.TOP
ch.legend.include_in_layout = False
ch.legend.font.size = Pt(12)
for ser, col in zip(ch.series, (BLUE, AMBER, TEAL)):
    ser.format.line.color.rgb = col
    ser.format.line.width = Pt(2.5)
    ser.smooth = False
    ser.marker.style = XL_MARKER_STYLE.NONE
pt = ch.series[2].points[t_stop]
pt.marker.style = XL_MARKER_STYLE.CIRCLE
pt.marker.size = 11
pt.marker.format.fill.solid()
pt.marker.format.fill.fore_color.rgb = TEAL
pt.marker.format.line.color.rgb = WHITE
dl = pt.data_label
dl.has_text_frame = True
dl.text_frame.text = f"Learned stop: cycle {t_stop}"
dl.position = XL_LABEL_POSITION.BELOW
dl.font.size = Pt(12)
dl.font.bold = True
dl.font.color.rgb = TEAL
gridlines(ch.value_axis)
ch.value_axis.tick_labels.font.size = Pt(11)
ch.category_axis.tick_labels.font.size = Pt(11)
ch.category_axis.format.line.color.rgb = LINE
tick_skip(ch.category_axis, 5)
axis_title(ch.category_axis, "Exploration cycle (6 robot steps each)")
axis_title(ch.value_axis, "Cells (cumulative)")
text(s, 4.85, 6.3, 8.2, 0.5, [[
    (f"Prototype run, 3 robots, 40×40 map. Stopping at cycle {t_stop} maps {cov_stop:.0f}% of the free space; the last "
     f"{Tn - t_stop} cycles add {100 - cov_stop:.0f}% more map but cut net value from {net[t_stop]:.0f} to {net[-1]:.0f}.",
     {"size": 12, "color": MUTED})]])

# ======================================================================= 6. three problems
s = new_slide("Three problems, one contribution",
              "Following the feedback, I separate three problems. Frontier allocation (A) and communication (B) are "
              "active research areas already, so I treat them as the machinery the robots run on and model "
              "communication as a cost. The contribution is C: a learned, team-level, cost-aware stopping decision.")
cards = [
    ("A", "Frontier allocation", "Which robot explores which frontier?",
     "Well studied: greedy, market-based, MinPos, and recent MARL methods (Tan et al. 2023; MARVEL 2025).",
     "Execution substrate"),
    ("B", "Communication", "Which robots talk, and what do they share?",
     "Active MARL topic: learned, targeted and bandwidth-limited messaging (TarMAC 2019).",
     "Modelled as a cost and a constraint"),
    ("C", "Team-level stopping", "When is one more cycle no longer worth its cost?",
     "Exploration uses fixed or single-robot rules; MARL work fixes the episode length.",
     "The contribution of this project"),
]
for i, (tag, name, q, lit, role) in enumerate(cards):
    x = 0.45 + i * 4.2
    main = tag == "C"
    box(s, x, 1.75, 3.95, 4.15, fill=NAVY if main else PALE)
    fg = WHITE if main else INK
    sub = RGBColor(0xCA, 0xD3, 0xF2) if main else MUTED
    text(s, x + 0.3, 1.95, 3.4, 0.6, [[(f"Problem {tag}", {"size": 13, "bold": True,
                                                           "color": GOLD if main else MUTED})]])
    text(s, x + 0.3, 2.35, 3.4, 0.6, [[(name, {"size": 22, "bold": True, "color": fg})]])
    text(s, x + 0.3, 3.0, 3.4, 1.2, [[(q, {"size": 17, "color": fg})]])
    text(s, x + 0.3, 4.05, 3.4, 1.2, [[(lit, {"size": 13, "color": sub})]])
    box(s, x + 0.3, 5.3, 3.35, 0.02, fill=GOLD if main else LINE)
    text(s, x + 0.3, 5.4, 3.4, 0.45, [[(role, {"size": 14, "bold": True, "color": GOLD if main else NAVY})]])
text(s, 0.45, 6.2, 12.4, 0.5, [[
    ("Frontier allocation is the machinery the robots run on, not the claim. ", {"size": 15, "color": INK}),
    ("The claim is about when the whole team should stop.", {"size": 15, "bold": True, "color": NAVY})]])

# ======================================================================= 7. literature map
s = new_slide("What is already known",
              "A summary of the literature by area. The full 2 to 3 page gap analysis (20 to 30 papers) is in "
              "progress. The LLM orchestration papers are motivation only: they ask the same 'when to stop' "
              "question in a different field, and they are not part of the proposed system.")
rows = [
    ["Area", "What exists", "What is still missing"],
    [[("Multi-robot exploration", {"bold": True}), ("\nYamauchi 1997; Burgard et al. 2005; MinPos 2012",
                                                    {"size": 11, "color": MUTED, "bold": False})],
     "Frontier-based coordination with utility and travel-cost allocation.",
     "Termination is a fixed rule: no frontiers left, coverage or time."],
    [[("MARL for exploration", {"bold": True}), ("\nTan et al. 2023 (RA-L); MARVEL 2025 (ICRA)",
                                                 {"size": 11, "color": MUTED, "bold": False})],
     "Learned, decentralised frontier selection; CTDE training.",
     "Episodes end at a fixed length or coverage; stopping is not learned."],
    [[("Stopping criteria for exploration", {"bold": True}),
      ("\nPlaced & Castellanos 2022; Luperto et al. 2026; PRoID 2026", {"size": 11, "color": MUTED, "bold": False})],
     "Uncertainty-based and learned single-robot stop rules; per-robot return rules.",
     "A team-level, learned, cost-aware decision to end the mission."],
    [[("Hierarchical MARL", {"bold": True}), ("\nOptions (Sutton et al. 1999); Han et al. 2019",
                                              {"size": 11, "color": MUTED, "bold": False})],
     "Learned termination of each agent's sub-policy (option).",
     "Termination of the whole task, driven by expected gain versus team cost."],
    [[("Optimal stopping", {"bold": True}), ("\nTsitsiklis & Van Roy 1999; Longstaff & Schwartz 2001; Becker et al. 2019",
                                             {"size": 11, "color": MUTED, "bold": False})],
     "Theory and regression or neural stopping rules, mostly single decision maker.",
     "Many agents, partial observability, costs that depend on coordination."],
    [[("LLM-agent orchestration", {"bold": True}), ("\nHu et al. 2025; Zhang 2026 (motivation only)",
                                                    {"size": 11, "color": MUTED, "bold": False})],
     "Statistical stop rules for LLM debates; a 2026 preprint survey finds no RL-trained stop.",
     "Same question in a different field. Not part of the proposed system."],
]
table(s, 0.45, 1.7, 12.45, [3.85, 4.3, 4.3], rows, font=13, row_h=0.74)

# ======================================================================= 8. closest prior work
s = new_slide("Closest prior work, and the gap",
              "Each row is a paper that a reviewer could say already does this. The columns are the five parts of "
              "my claim. No existing paper has all five. The novelty claim is phrased narrowly on purpose: to my "
              "knowledge, no prior work learns the team-level decision to end a multi-robot exploration mission "
              "as a cost-aware stopping problem.")
Y, X, H = "✓", "✗", "partly"
rows = [["Work", "Multi-agent", "Spatial exploration", "Learned stop", "Ends the whole mission",
         "Prices motion + messages + coordination"],
        ["Placed & Castellanos 2022", X, Y, X, "single robot", X],
        ["Luperto et al. 2026", X, Y, "supervised", "single robot", X],
        ["Kim et al. 2026 (PRoID)", Y, Y, X, "per robot", H],
        ["Szostak & Cohen 2024", Y, X, Y, H, "sampling cost"],
        ["Han et al. 2019", Y, X, Y, "sub-policies only", X],
        [[("This project", {"bold": True, "color": NAVY})], Y, Y, Y, Y, Y]]
tb = table(s, 0.45, 1.75, 12.45, [3.1, 1.55, 1.95, 1.75, 2.1, 2.0], rows, font=13, row_h=0.56,
           highlight_rows=(6,))
for r_ in range(1, 7):
    for c_ in range(1, 6):
        cell = tb.cell(r_, c_)
        for p_ in cell.text_frame.paragraphs:
            p_.alignment = PP_ALIGN.CENTER
            for run in p_.runs:
                if run.text == Y:
                    run.font.color.rgb = GREEN
                    run.font.bold = True
                    run.font.size = Pt(16)
                elif run.text == X:
                    run.font.color.rgb = RED
                    run.font.size = Pt(16)
text(s, 0.45, 5.85, 12.4, 1.0, [
    [("Szostak & Cohen: multi-agent RL that learns when to stop sampling in hypothesis testing (no map, no motion). "
      "Han et al.: learned termination of options, not of the task.", {"size": 12.5, "color": MUTED})],
    [("In the prototype the stop is learned by one central learner; the MARL version is the semester's work.",
      {"size": 12.5, "color": MUTED})]], space_after=4)

# ======================================================================= 9. research questions
s = new_slide("Research questions",
              "The main question uses your suggested wording. Each sub-question maps to one experiment and will "
              "become one results section. RQ2 and RQ4 already have first answers from the prototype; RQ1 needs the "
              "MARL Level 2, which comes next.")
box(s, 0.45, 1.7, 12.45, 1.3, fill=NAVY)
text(s, 0.75, 1.8, 11.9, 1.14, [[
    ("Can a hierarchical MARL policy learn a team-level stopping strategy that balances expected "
     "information gain against motion, communication and coordination costs during multi-robot exploration?",
     {"size": 18, "color": WHITE, "bold": True})]], anchor=MSO_ANCHOR.MIDDLE)
rqs = [("RQ1", "Can MARL learn efficient frontier allocation?",
        "Level-2 policy vs greedy and market-based allocation, with stopping held fixed."),
       ("RQ2", "Can the policy tell when further exploration has low marginal value?",
        "Learned value vs true remaining value; stop time vs the best stop in hindsight."),
       ("RQ3", "Does learned stopping save time and travel without losing meaningful coverage?",
        "Net value, coverage at stop, distance and messages against every baseline."),
       ("RQ4", "How does it scale with team size and communication limits?",
        "Train on 2 robots; test on 2 to 10 robots, 3 map sizes, 3 communication levels.")]
for i, (tag, q, how) in enumerate(rqs):
    x = 0.45 + (i % 2) * 6.3
    y = 3.2 + (i // 2) * 1.8
    box(s, x, y, 6.15, 1.62, fill=PALE)
    text(s, x + 0.25, y + 0.18, 0.9, 0.5, [[(tag, {"size": 20, "bold": True, "color": AMBER})]])
    text(s, x + 1.15, y + 0.18, 4.8, 0.8, [[(q, {"size": 16, "bold": True})]])
    text(s, x + 1.15, y + 0.98, 4.8, 0.6, [[(how, {"size": 13, "color": MUTED})]])

# ======================================================================= 10. formulation 1: setting
s = new_slide("Formulation (1): the setting",
              "Formally the team faces a decentralised partially observable Markov decision process, a Dec-POMDP "
              "(Oliehoek & Amato 2016). Partially observable because nobody sees the true map. Decentralised because "
              "each robot acts on its own observations. On top of it sits one team decision per cycle: continue or "
              "stop. The table maps each symbol to what it means in this project.")
rows = [["Symbol", "Meaning", "In this project"],
        ["I = {1, …, N}", "The agents", "N robots (trained with 2, tested with 2 to 8, later 10)"],
        ["S", "True state of the world", "True map, robot positions, what has been mapped so far"],
        ["Ωᵢ, O", "What robot i observes", "Cells within 4 cells of the robot, in line of sight"],
        ["Aᵢ", "Robot i's action (Level 2)", "Which frontier to drive to, one step at a time"],
        ["A₀", "Team action (Level 1)", "Continue or stop, once per cycle; later also: how many robots stay active"],
        ["P", "How the state changes", "Robots move and sense; the known map grows"],
        ["R", "Reward", "Net value of each cycle: cells revealed minus the team's costs (next slide)"],
        ["b", "Belief / team summary", "What the team knows at a decision point, compressed into features"]]
table(s, 0.45, 1.75, 12.45, [2.2, 3.4, 6.85], rows, font=13.5, row_h=0.53)
text(s, 0.45, 6.6, 12.4, 0.35, [[("One cycle = 6 robot steps. The Level-1 decision is made between cycles, "
                                  "using only information available at that moment.", {"size": 13, "color": MUTED})]])

# ======================================================================= 11. formulation 2: cycle value
c2 = CostModel(c_comm=0.2).cycle_cost(12, 2)
c8 = CostModel(c_comm=0.6).cycle_cost(48, 8)
s = new_slide("Formulation (2): the value of one cycle",
              "Everything is measured in map cells. The weights are an exchange rate: c_move = 2 means one robot step "
              "is worth two newly mapped cells to the operator. The worked example shows why team size matters: the "
              "message term grows with N squared, so an 8-robot cycle has to reveal five times more to pay for itself.")
box(s, 0.45, 1.75, 12.45, 1.05, fill=NAVY)
text(s, 0.75, 1.8, 11.9, 0.95, [[("r(t)  =  ΔI(t)  −  c_move · d(t)  −  c_comm · N(N−1)  −  c_coord",
                                  {"size": 26, "bold": True, "color": WHITE})]], anchor=MSO_ANCHOR.MIDDLE,
     align=PP_ALIGN.CENTER)
terms = [("ΔI(t)", "cells revealed in cycle t (new map)"),
         ("d(t)", "robot steps actually taken in cycle t"),
         ("N(N−1)", "map-sharing messages: every robot to every other"),
         ("c_coord", "fixed re-planning overhead per cycle")]
for i, (sym, meaning) in enumerate(terms):
    y = 3.05 + i * 0.62
    text(s, 0.45, y, 1.5, 0.5, [[(sym, {"size": 18, "bold": True, "color": NAVY})]])
    text(s, 1.95, y + 0.03, 4.1, 0.55, [[(meaning, {"size": 15})]])
text(s, 0.45, 5.6, 5.6, 1.1, [
    [("Weights used: ", {"bold": True}), ("c_move = 2, c_coord = 2, c_comm = 0.05 / 0.2 / 0.6 "
                                          "(low / medium / high).", {})],
    [("Stopping after T cycles earns V(T) = r(0) + … + r(T−1).", {"bold": True, "color": NAVY})]],
     size=14, space_after=6)
rows = [["Cost of one full cycle", "2 robots, medium", "8 robots, high"],
        ["Motion: 2 × steps", "2 × 12 = 24", "2 × 48 = 96"],
        ["Messages: c_comm × N(N−1)", "0.2 × 2 = 0.4", "0.6 × 56 = 33.6"],
        ["Coordination", "2", "2"],
        [[("Total: cells needed to break even", {"bold": True})], [(f"{c2:.1f}", {"bold": True})],
         [(f"{c8:.1f}", {"bold": True})]]]
table(s, 6.45, 3.0, 6.45, [3.05, 1.7, 1.7], rows, font=14, row_h=0.62, highlight_rows=(4,))
text(s, 6.45, 6.2, 6.45, 0.6, [[("Assumes every robot moves all 6 steps; idle robots cost no motion.",
                                 {"size": 12, "color": MUTED})]])

# ======================================================================= 12. formulation 3: optimal stopping
s = new_slide("Formulation (3): stopping as optimal stopping",
              "Choosing T is an optimal stopping problem. The decision at time t may only use what is known at "
              "time t. Q is the value of continuing now and then continuing to decide optimally. Stopping is worth "
              "exactly zero from that point on, so the rule is: stop the first time Q is not positive. The hindsight "
              "oracle sees the future and is used only as the 100% reference for scoring.")
# decision diagram (left)
box(s, 0.6, 3.25, 2.0, 1.0, fill=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
text(s, 0.6, 3.3, 2.0, 0.9, [[("Team state sₜ", {"size": 16, "bold": True, "color": WHITE})],
                              [("what is known now", {"size": 12, "color": SUB})]],
     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space_after=0)
box(s, 3.45, 1.95, 2.55, 1.05, fill=PALE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
text(s, 3.45, 2.0, 2.55, 0.95, [[("STOP", {"size": 16, "bold": True, "color": AMBER})],
                                 [("value from here: 0", {"size": 13})]], align=PP_ALIGN.CENTER,
     anchor=MSO_ANCHOR.MIDDLE, space_after=0)
box(s, 3.45, 4.5, 2.55, 1.35, fill=PALE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
text(s, 3.45, 4.55, 2.55, 1.25, [[("CONTINUE", {"size": 16, "bold": True, "color": TEAL})],
                                  [("earn r(t), then decide again at sₜ₊₁", {"size": 13})]],
     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space_after=0)
arrow(s, 2.62, 3.55, 3.43, 2.5)
arrow(s, 2.62, 3.95, 3.43, 5.15)
# maths (right)
text(s, 6.6, 1.75, 6.3, 5.0, [
    [("Value of continuing", {"bold": True, "color": NAVY, "size": 16})],
    [("Q(s) = E[ r(t) + max(0, Q(sₜ₊₁)) | sₜ = s ]", {"size": 19, "bold": True, "color": INK})],
    [("max(0, ·): at the next decision the team again picks the better of stop (0) and continue.",
      {"size": 13.5, "color": MUTED})],
    [("Stopping rule", {"bold": True, "color": NAVY, "size": 16})],
    [("Stop at the first t with Q(sₜ) ≤ 0", {"size": 19, "bold": True, "color": INK})],
    [("i.e. when the expected value of exploring further no longer covers its cost.",
      {"size": 13.5, "color": MUTED})],
    [("Reference for scoring (not a policy)", {"bold": True, "color": NAVY, "size": 16})],
    [("T* = argmax_T V(T), computed after the run", {"size": 17, "bold": True, "color": INK})],
    [("Needs the future. Every rule is scored as a % of V(T*).", {"size": 13.5, "color": MUTED})],
], size=15, space_after=6)

# ======================================================================= 13. architecture
s = new_slide("Two-level architecture",
              "Level 1 runs once per cycle and decides for the whole team. Level 2 runs every step and moves each "
              "robot. In the final system both are learned and trained with centralised training and decentralised "
              "execution (CTDE): during training a critic may see the whole map, during execution each robot uses "
              "only its own observations. In the week-1 prototype only Level 1 is learned.")
box(s, 0.45, 1.75, 6.2, 1.45, fill=NAVY)
text(s, 0.7, 1.87, 5.8, 1.3, [[("Level 1: team stopping policy", {"size": 17, "bold": True, "color": WHITE})],
                               [("Once per cycle. Sees a team summary (map known, expected gain vs cost, recent "
                                 "gain, frontiers). Decides continue or stop; later also how many robots stay active.",
                                 {"size": 13, "color": SUB})]], space_after=4)
for i, lab in enumerate(["Robot 1", "Robot 2", "Robot N"]):
    x = 0.45 + i * 2.13
    arrow(s, x + 0.97, 3.22, x + 0.97, 3.75)
    box(s, x, 3.8, 1.94, 1.25, fill=PALE, line=LINE)
    text(s, x + 0.15, 3.92, 1.7, 1.1, [[(lab, {"size": 15, "bold": True, "color": NAVY})],
                                        [("local map, picks next frontier", {"size": 12, "color": MUTED})]],
         space_after=2)
text(s, 0.45, 5.2, 6.2, 0.4, [[("Level 2: one policy per robot, every step, shared parameters",
                                {"size": 13, "bold": True, "color": INK})]])
box(s, 0.45, 5.72, 6.2, 0.95, fill=RGBColor(0xFD, 0xF3, 0xDF))
text(s, 0.65, 5.8, 5.9, 0.85, [[("CTDE: trained with the full map and all robot states; executed with each "
                                  "robot's own observations. That is what makes it multi-agent RL.",
                                  {"size": 13, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE)
rows = [["", "Week-1 prototype", "Final system"],
        ["Level 1 (stop)", "Learned: fitted Q-iteration, one central learner", "Learned inside the MARL hierarchy"],
        ["Level 2 (move)", "Fixed greedy nearest-frontier rule", "Learned MARL policy (e.g. MAPPO, CTDE)"],
        ["Communication", "Priced as a cost only", "Cost plus range and bandwidth limits"],
        ["Team size choice", "Not yet (stop or continue only)", "Activate fewer robots when it pays"]]
table(s, 7.0, 1.75, 5.9, [1.7, 2.1, 2.1], rows, font=12.5, row_h=0.95)

# ======================================================================= 14. how the stop is learned
s = new_slide("How the stopping policy is learned",
              "Fitted Q-iteration (Ernst et al. 2005) is batch RL: it repeatedly fits a regression model to the "
              "Bellman target from slide 12. Because stopping does not change how robots move before the stop, one "
              "full run of a map contains every possible stopping point; stopping after t cycles simply keeps the "
              "first t cycles. Cost randomisation re-scores each run under random cost weights, so the policy "
              "learns how the costs change the answer instead of memorising one setting.")
steps = [("1", "Collect", "300 training maps, 2 robots, 32×32. Explore each to the end and log every cycle."),
         ("2", "Re-score", "Score every run under 4 random cost settings (cost randomisation): 1,200 runs."),
         ("3", "Fit Q", "25 rounds of fitted Q-iteration; each round an extra-trees regressor (80 trees)."),
         ("4", "Decide", "At run time compute Q from the 7 features. Stop when Q ≤ 0.")]
for i, (num, head, desc) in enumerate(steps):
    x = 0.45 + i * 3.17
    box(s, x, 1.75, 2.9, 2.2, fill=PALE)
    text(s, x + 0.2, 1.88, 2.5, 0.5, [[(f"{num}  {head}", {"size": 18, "bold": True, "color": NAVY})]])
    text(s, x + 0.2, 2.45, 2.55, 1.45, [[(desc, {"size": 13.5})]])
    if i < 3:
        arrow(s, x + 2.93, 2.85, x + 3.14, 2.85, width=2)
rows = [["Feature (all ratios, so they transfer)", "Meaning"],
        ["Map known", "Fraction of all grid cells already known"],
        ["Expected gain ÷ cycle cost", "Unknown cells near the planned targets, per unit of cost"],
        ["Last gain ÷ cost, previous gain ÷ cost", "How well the last two cycles paid off"],
        ["Distance to targets ÷ 6", "How far away the planned frontiers are"],
        ["Share of robots with a target", "How much of the team still has work"],
        ["Frontier cells ÷ map side", "How much frontier is left"]]
table(s, 0.45, 4.15, 12.45, [4.6, 7.85], rows, font=12.5, row_h=0.38)

# ======================================================================= 15. baselines
bl = {r.name: getattr(r, "param", None) for r in RULES}
s = new_slide("The baselines it is compared against",
              "Every rule uses the same maps and the same robot motion; only the stopping moment differs. The three "
              "tuned rules had their single number chosen to maximise net value on the same 300 training maps in the "
              "training setting. That is their best case: an engineer tuning for the deployment they expect.")
rows = [["Stopping rule", "Stops when…", "Parameter", "Idea"],
        ["Explore until no frontiers", "no reachable frontier is left", "none", "Classical exploration"],
        ["Fixed budget", "B cycles have run", f"B = {bl['Fixed cycle budget (tuned)']} (tuned)",
         "Time budget"],
        ["Coverage threshold", "known fraction of the grid ≥ τ", f"τ = {bl['Coverage threshold (tuned)']:.2f} (tuned)",
         "Area threshold"],
        ["Myopic rule", "the last cycle lost value (r < 0)", "none", "Stop at the first bad cycle"],
        ["Gain-vs-cost rule", "α × expected gain ÷ cycle cost < 1", f"α = {bl['Info-gain vs cost heuristic (tuned)']} (tuned)",
         "Hand-made value test"],
        [[("Learned value-aware stop", {"bold": True, "color": NAVY})], "estimated Q ≤ 0", "learned",
         "Looks at the whole remaining future"],
        ["Best in hindsight (oracle)", "best cycle, chosen after the run", "needs the future",
         "100% reference, not a policy"]]
table(s, 0.45, 1.75, 12.45, [3.2, 3.85, 2.4, 3.0], rows, font=13.5, row_h=0.58, highlight_rows=(6,))
text(s, 0.45, 6.55, 12.4, 0.35, [[("With α = 1.6 the gain-vs-cost rule stops once expected gain < cycle cost ÷ 1.6 "
                                   "(about 0.63 × cost).", {"size": 12.5, "color": MUTED})]])

# ======================================================================= 16. metrics
s = new_slide("How methods are judged: evaluation metrics",
              "Net value against the hindsight-best stop is the main score. Regret is the same information in cells, "
              "normalised by map size, which stays meaningful when the best achievable value is close to zero. "
              "Everything is paired: every rule is scored on exactly the same maps. Results come with 95% bootstrap "
              "confidence intervals, and robustness across settings uses the interquartile mean and worst case "
              "(Agarwal et al. 2021).")
mets = [("Net value, % of best", "V(T) ÷ V(T*), totals over all maps", "Main score: did it stop at a good time?"),
        ("Regret", "V(T*) − V(T), as % of the map", "Value lost; stable even when V(T*) is tiny"),
        ("Stop-time error", "T − T* in cycles; share early / late", "How and when it gets it wrong"),
        ("Operational cost", "Coverage, cycles, robot steps, messages", "What the stop saves, and what it leaves"),
        ("Value estimate quality", "Correlation of Q with true value; sign accuracy", "Does it know the remaining value?"),
        ("Robustness", "Worst setting, interquartile mean, settings ≥ 80%", "Does it hold without retraining?")]
for i, (head, how, why) in enumerate(mets):
    x = 0.45 + (i % 3) * 4.2
    y = 1.75 + (i // 3) * 2.2
    box(s, x, y, 3.95, 2.0, fill=NAVY if i == 0 else PALE)
    fg = WHITE if i == 0 else NAVY
    text(s, x + 0.25, y + 0.18, 3.5, 0.5, [[(head, {"size": 17, "bold": True, "color": fg})]])
    text(s, x + 0.25, y + 0.7, 3.5, 0.65, [[(how, {"size": 13.5, "color": WHITE if i == 0 else INK})]])
    text(s, x + 0.25, y + 1.38, 3.5, 0.55, [[(why, {"size": 12.5, "italic": True,
                                                    "color": SUB if i == 0 else MUTED})]])
text(s, 0.45, 6.25, 12.4, 0.5, [[("Statistics: ", {"size": 13.5, "bold": True, "color": NAVY}),
                                 ("paired comparison on identical maps, 95% bootstrap intervals, and (for MARL) "
                                  "at least 5 training seeds.", {"size": 13.5})]])

# ======================================================================= 17. prototype
s = new_slide("Week 1: a working prototype",
              "What I built in week 1. Random indoor maps with rooms, doors and furniture. Robots see 4 cells around "
              "them through line of sight. Level 2 is a fixed greedy frontier allocator; Level 1 is the learned stop. "
              "The left map shows where the learned policy stops; the right shows exploring until no frontiers remain. "
              "The policy leaves the far corner because reaching it costs more than it would reveal at these weights.")
s.shapes.add_picture(f"{PROTO}/figures/fig_maps.png", Inches(0.45), Inches(1.75), height=Inches(4.85))
rows = [["Setting", "Value"],
        ["Maps", "Random rooms, doors, clutter"],
        ["Sensor", "Radius 4, line of sight"],
        ["Cycle", "6 steps per robot"],
        ["Level 2", "Greedy frontier allocation"],
        ["Level 1", "Learned stop (FQI)"],
        ["Train", "300 maps, 2 robots, 32×32"],
        ["Test", "140 + 36×40 unseen maps"],
        ["Compute", "Laptop CPU, ~15 min"]]
table(s, 9.85, 1.75, 3.05, [1.05, 2.0], rows, font=12, row_h=0.52)

# ======================================================================= 18. result 1 (training setting)
ORD = ["One-step look-ahead", "Explore until no frontiers", "Info-gain vs cost heuristic (tuned)",
       "Fixed cycle budget (tuned)", "Coverage threshold (tuned)", "Learned value-aware stopping"]
s = new_slide("Result 1: in the training setting it ties",
              "140 unseen maps in the training setting. Each bar is net value as a percentage of the best stop in "
              "hindsight, with the 95% bootstrap interval in brackets. The learned rule (91%) and the coverage "
              "threshold (92%) overlap: that is a statistical tie, not a win. Both myopic stopping and exploring to "
              "the end leave a quarter or more of the achievable value on the table.")
cd = CategoryChartData()
cd.categories = [DISP[k] for k in ORD]
cd.add_series("% of hindsight-best", [round(P[k]["pct"], 1) for k in ORD])
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.45), Inches(2.1), Inches(7.6), Inches(4.5), cd)
ch = gf.chart
style_chart(ch)
ch.has_legend = False
ch.has_title = False
plot = ch.plots[0]
plot.gap_width = 55
plot.vary_by_categories = False
ser = ch.series[0]
ser.format.fill.solid()
ser.format.fill.fore_color.rgb = GRAYBAR
for i, k in enumerate(ORD):
    pnt = ser.points[i]
    if k == ORD[-1]:
        pnt.format.fill.solid()
        pnt.format.fill.fore_color.rgb = BLUE
    elif k == "Coverage threshold (tuned)":
        pnt.format.fill.solid()
        pnt.format.fill.fore_color.rgb = RGBColor(0x8D, 0x96, 0xB5)
    lab = pnt.data_label
    lab.has_text_frame = True
    lo, hi = P[k]["ci"]
    lab.text_frame.text = f"{P[k]['pct']:.0f}%  ({lo:.0f}–{hi:.0f})"
    lab.position = XL_LABEL_POSITION.OUTSIDE_END
    lab.font.size = Pt(12)
    lab.font.color.rgb = INK
    lab.font.bold = k == ORD[-1]
ch.value_axis.maximum_scale = 118
ch.value_axis.minimum_scale = 0
ch.value_axis.visible = False
ch.value_axis.has_major_gridlines = False
ch.category_axis.tick_labels.font.size = Pt(12)
ch.category_axis.tick_labels.font.color.rgb = INK
ch.category_axis.format.line.color.rgb = LINE
text(s, 0.45, 1.7, 7.6, 0.4, [[("2 robots, 32×32 maps, medium communication. 140 unseen maps. Net value as % of the "
                                "best stop in hindsight (95% CI).", {"size": 12.5, "color": MUTED})]])
L_, C_ = P["Learned value-aware stopping"], P["Coverage threshold (tuned)"]
stats = [(f"{L_['pct']:.0f}% vs {C_['pct']:.0f}%", "learned vs best tuned rule; the intervals overlap, so this is a tie"),
         (f"{100 - P['Explore until no frontiers']['pct']:.0f}%", "of the achievable net value lost by exploring until "
                                                                  "no frontiers remain"),
         (f"{abs(L_['stop_err']):.0f} cycles early", "average stop of the learned rule vs the best stop; it errs on "
                                                     "the side of stopping early")]
for i, (big, small) in enumerate(stats):
    y = 1.8 + i * 1.62
    box(s, 8.4, y, 4.5, 1.45, fill=PALE)
    text(s, 8.65, y + 0.12, 4.1, 0.6, [[(big, {"size": 26, "bold": True, "color": NAVY})]])
    text(s, 8.65, y + 0.75, 4.1, 0.68, [[(small, {"size": 13, "color": MUTED})]])

# ======================================================================= 19. result 2 (how they stop)
O_ = P["_oracle"]
s = new_slide("Result 2: how each rule stops",
              "Averages over the same 140 maps. The learned rule maps less of the space than the tuned rules (78% vs "
              "90%) yet scores about the same, because it stops early on maps where the remaining space is expensive "
              "to reach. Its typical map is very good (median 96%) but its bad maps are worse than the coverage rule's "
              "(10th percentile 72% vs 82%). Exploring to the end is late on 97% of maps; the myopic rule is early on 76%.")
rows = [["Rule", "Net value (% of best)", "Median map", "Worst 10% of maps", "Map covered", "Cycles",
         "Robot steps", "Early / exact / late"]]
for k in ["Explore until no frontiers", "Fixed cycle budget (tuned)", "Coverage threshold (tuned)",
          "One-step look-ahead", "Info-gain vs cost heuristic (tuned)", "Learned value-aware stopping"]:
    d = P[k]
    rows.append([DISP[k], pct(d["pct"]), pct(d["median_map"]), pct(d["p10_map"]), pct(d["coverage"]),
                 f"{d['cycles']:.1f}", f"{d['steps']:.0f}",
                 f"{100 * d['early']:.0f} / {100 * d['exact']:.0f} / {100 * d['late']:.0f}%"])
rows.append([[("Best in hindsight", {"italic": True, "bold": True})], "100%", "100%", "100%", pct(O_["coverage"]),
             f"{O_['cycles']:.1f}", f"{O_['steps']:.0f}", "reference"])
table(s, 0.45, 1.75, 12.45, [3.25, 1.45, 1.1, 1.3, 1.25, 1.0, 1.15, 1.95], rows, font=12.5, row_h=0.55,
      highlight_rows=(6,))
text(s, 0.45, 6.3, 12.4, 0.5, [[("“Worst 10% of maps” is the 10th percentile of per-map scores. Messages sent = "
                                 "cycles × N(N−1), so fewer cycles also means fewer messages.",
                                 {"size": 12.5, "color": MUTED})]])

# ======================================================================= 20. result 3 (value check)
cost_m = CostModel(c_comm=COMM_LEVELS["medium"])
trajs140 = pickle.load(open(f"{PROTO}/results/test.pkl", "rb")) + pickle.load(open(f"{PROTO}/results/gen_32_2.pkl", "rb"))
qp, qt = [], []
for tr in trajs140:
    q = LEARNED.q_values(tr, cost_m)
    r_ = rewards(tr, cost_m)
    for t in range(len(r_)):
        qp.append(float(q[t]))
        qt.append(float(np.cumsum(r_[t:]).max()))
qp, qt = np.array(qp), np.array(qt)
pear = float(np.corrcoef(qp, qt)[0, 1])
sign = float(((qp > 0) == (qt > 0)).mean())
s = new_slide("Result 3: does it know the value that is left?",
              "Each dot is one decision point: one cycle of one of the 140 test maps. The horizontal axis is the true "
              "value of continuing, computed afterwards from what actually happened (best achievable sum of future "
              "cycle values). The vertical axis is the policy's estimate Q at that moment. Dots near the diagonal "
              "are good estimates. What matters for the decision is the sign: continue when positive, stop when not.")
xy = XyChartData()
sr = xy.add_series("decision points")
rng2 = np.random.default_rng(3)
idx = rng2.choice(len(qp), size=min(1500, len(qp)), replace=False)
for i in idx:
    sr.add_data_point(round(qt[i], 1), round(qp[i], 1))
lo_, hi_ = float(min(qt.min(), qp.min())), float(max(qt.max(), qp.max()))
sr2 = xy.add_series("perfect estimate")
sr2.add_data_point(lo_, lo_)
sr2.add_data_point(hi_, hi_)
gf = s.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER, Inches(0.45), Inches(1.7), Inches(7.6), Inches(5.0), xy)
ch = gf.chart
style_chart(ch, 11)
ch.has_legend = False
s0, s1 = ch.series[0], ch.series[1]
s0.format.line.fill.background()
s0.marker.style = XL_MARKER_STYLE.CIRCLE
s0.marker.size = 4
s0.marker.format.fill.solid()
s0.marker.format.fill.fore_color.rgb = BLUE
s0.marker.format.line.fill.background()
s1.marker.style = XL_MARKER_STYLE.NONE
s1.format.line.color.rgb = AMBER
s1.format.line.width = Pt(2)
gridlines(ch.value_axis)
axis_title(ch.category_axis, "True value of continuing (known afterwards), cells")
axis_title(ch.value_axis, "Estimated Q at that moment, cells")
stats = [(f"r = {pear:.2f}", "correlation between estimate and true value over all decision points"),
         (f"{100 * sign:.0f}%", "of decision points where the estimate has the right sign (continue vs stop)"),
         ("1,500 of " + f"{len(qp):,}", "points plotted (random sample) for readability; statistics use all points")]
for i, (big, small) in enumerate(stats):
    y = 1.8 + i * 1.62
    box(s, 8.4, y, 4.5, 1.45, fill=PALE)
    text(s, 8.65, y + 0.12, 4.1, 0.6, [[(big, {"size": 26, "bold": True, "color": NAVY})]])
    text(s, 8.65, y + 0.75, 4.1, 0.68, [[(small, {"size": 13, "color": MUTED})]])

# ======================================================================= 21. result 4 (generalisation)
s = new_slide("Result 4: without retraining, on 36 new settings",
              "Trained once on 2 robots, 32 by 32 maps, medium communication. Tested unchanged on every combination "
              "of 2, 4, 6, 8 robots, 32, 48, 64 cell maps and low, medium, high communication cost: 36 settings, "
              "40 new maps each. Lower is better. Regret is the net value lost against the best stop, as a percentage "
              "of all cells the full exploration reveals, so it stays meaningful when the best achievable value is small. "
              "Each point averages over the other two factors.")
show = [("Learned value-aware stopping", BLUE), ("Coverage threshold (tuned)", AMBER),
        ("Info-gain vs cost heuristic (tuned)", TEAL), ("Explore until no frontiers", PURPLE)]
dims = [(1, (2, 4, 6, 8), "Robots (trained on 2)"), (0, (32, 48, 64), "Map side, cells (trained on 32)"),
        (2, ("low", "medium", "high"), "Comm. cost (trained: medium)")]
ymax = 0
series_data = {}
for j, (pos, levels, label) in enumerate(dims):
    for name, _ in show:
        vals = []
        for lv in levels:
            v = [NREG[name][i] for i, key in enumerate(ORDER36) if key[pos] == lv]
            vals.append(round(float(np.mean(v)), 1))
        series_data[(j, name)] = vals
        ymax = max(ymax, max(vals))
for j, (pos, levels, label) in enumerate(dims):
    cd = CategoryChartData()
    cd.categories = [str(v) for v in levels]
    for name, _ in show:
        cd.add_series(DISP[name], series_data[(j, name)])
    gf = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(0.45 + j * 4.17), Inches(2.4),
                            Inches(4.05), Inches(3.6), cd)
    ch = gf.chart
    style_chart(ch, 11)
    ch.has_legend = False
    for ser, (_, col) in zip(ch.series, show):
        ser.smooth = False
        ser.format.line.color.rgb = col
        ser.format.line.width = Pt(2.25)
        ser.marker.style = XL_MARKER_STYLE.CIRCLE
        ser.marker.size = 7
        ser.marker.format.fill.solid()
        ser.marker.format.fill.fore_color.rgb = col
        ser.marker.format.line.color.rgb = WHITE
    ch.value_axis.minimum_scale = 0
    ch.value_axis.maximum_scale = float(np.ceil(ymax / 5) * 5)
    ch.value_axis.major_unit = 5
    gridlines(ch.value_axis)
    ch.category_axis.format.line.color.rgb = LINE
    axis_title(ch.category_axis, label, 11)
    if j == 0:
        axis_title(ch.value_axis, "Regret, % of map (lower is better)", 11)
for i, (name, col) in enumerate(show):
    lx = 0.45 + i * 3.1
    box(s, lx, 1.83, 0.32, 0.07, fill=col)
    text(s, lx + 0.42, 1.7, 2.65, 0.35, [[(DISP[name], {"size": 13})]])
text(s, 0.45, 2.05, 12.4, 0.3, [[("Regret = value lost vs the best stop in hindsight, as % of all cells revealed by "
                                  "full exploration. Mean over the other two factors.", {"size": 12, "color": MUTED})]])
text(s, 0.45, 6.15, 12.4, 0.7, [[("The tuned rules drift as the team grows and messages get expensive; the learned "
                                  "rule stays low. Its weak spot is the left end: with 2 robots on larger maps it stops "
                                  "far too early.", {"size": 13.5})]])

# ======================================================================= 22. result 5 (robustness table)
RG = E["robust_generalisation"]
GS = E["generalisation_summary"]
s = new_slide("Result 5: robustness across the 36 settings",
              "Summary per rule over the 36 unseen settings. In a typical setting the learned rule and the tuned "
              "coverage threshold are equally good: same interquartile mean, same number of settings above 80%. The "
              "difference is the worst case. A raw average of percentages is not used as the headline, because in the "
              "hardest settings the best achievable value is only a few dozen cells, and dividing by it turns small "
              "losses into numbers like minus 700%.")
rows = [["Rule", "Mean regret (% of map)", "Worst-setting regret", "Typical score (IQM)", "Settings ≥ 80% of best",
         "Settings < 50% of best", "Worst setting (% of best)"]]
for k in ["Explore until no frontiers", "Fixed cycle budget (tuned)", "Coverage threshold (tuned)",
          "One-step look-ahead", "Info-gain vs cost heuristic (tuned)", "Learned value-aware stopping"]:
    v = np.array(NREG[k])
    rows.append([DISP[k], f"{v.mean():.1f}%", f"{v.max():.1f}%", pct(RG[k]["iqm"]), f"{RG[k]['n_ge80']} / 36",
                 f"{GS[k]['n_below50']} / 36", pct(GS[k]["worst"])])
table(s, 0.45, 1.75, 12.45, [3.25, 1.55, 1.5, 1.45, 1.55, 1.55, 1.6], rows, font=13, row_h=0.6,
      highlight_rows=(6,))
text(s, 0.45, 6.1, 12.4, 0.8, [
    [("Reading it: ", {"size": 13.5, "bold": True, "color": NAVY}),
     ("equal in the typical case (IQM 89% vs 89%), much safer in the worst case (regret 9.9% vs 25.3% of the map). "
      "IQM = mean of the middle 50% of settings (Agarwal et al. 2021).", {"size": 13.5})]])

# ======================================================================= 23. wins and failures
gmap = {(g["size"], g["n"], g["comm"]): g for g in GEN}
cases = [((32, 6, "high"), "Costly team: tuned rules keep exploring at a loss"),
         ((48, 8, "high"), "Costlier still: every tuned rule loses value"),
         ((64, 6, "high"), "Large map, costly team"),
         ((48, 2, "medium"), "Small team, bigger map: learned stops too early"),
         ((64, 2, "medium"), "Small team, largest map: same failure, stronger"),
         ((32, 8, "high"), "Exploring is barely worth it at all: every rule fails")]
s = new_slide("Where it wins, and where it fails",
              "Six settings picked to show both sides. Top three: when the team is costly, the tuned rules keep "
              "exploring at a loss and the learned rule stops in time. Next two: with only 2 robots on bigger maps the "
              "learned rule stops 20 to 33 cycles too early; it has never seen such long episodes in training. Last: "
              "8 robots on a small map with expensive messages, where on 14 of 40 maps the best choice is not to explore "
              "at all. The right answer there is to use fewer robots, which the policy cannot choose yet.")
rows = [["Setting (map, robots, comm.)", "What happens", "Learned", "Coverage 84%", "Gain-vs-cost",
         "Learned stop error"]]
for key, why in cases:
    g = gmap[key]
    rows.append([f"{key[0]}×{key[0]}, {key[1]} robots, {key[2]}", why,
                 [(pct(g["Learned value-aware stopping"]), {"bold": True})],
                 pct(g["Coverage threshold (tuned)"]), pct(g["Info-gain vs cost heuristic (tuned)"]),
                 f"{g['Learned value-aware stopping|stoperr']:+.1f} cycles"])
tb = table(s, 0.45, 1.75, 12.45, [2.75, 4.2, 1.25, 1.45, 1.4, 1.4], rows, font=13, row_h=0.62)
for r_ in (1, 2, 3):
    for c_ in range(6):
        tb.cell(r_, c_).fill.fore_color.rgb = RGBColor(0xE6, 0xF3, 0xEC)
for r_ in (4, 5, 6):
    for c_ in range(6):
        tb.cell(r_, c_).fill.fore_color.rgb = RGBColor(0xFB, 0xEB, 0xE8)
text(s, 0.45, 6.2, 12.4, 0.6, [[("Scores are net value as % of the best stop in hindsight, 40 maps per setting. "
                                 "Negative means worse than not exploring at all. Stop error: negative = too early.",
                                 {"size": 12.5, "color": MUTED})]])

# ======================================================================= 24. what it shows / doesn't
s = new_slide("What the prototype shows, and what it does not",
              "This slide sets the scope of the claim. The prototype is evidence that the stopping decision can be "
              "learned and that a value-aware stop is safer when costs change. It is not yet MARL, not yet deep RL, and "
              "it has one clear failure mode, which gives the next steps.")
box(s, 0.45, 1.75, 6.1, 4.95, fill=RGBColor(0xE6, 0xF3, 0xEC))
box(s, 6.8, 1.75, 6.1, 4.95, fill=RGBColor(0xFB, 0xEB, 0xE8))
text(s, 0.75, 1.95, 5.6, 4.6, [
    [("It shows", {"size": 19, "bold": True, "color": GREEN})],
    "The stop decision can be learned from data as optimal stopping (Q ≤ 0).",
    "In the training setting it ties the best hand-tuned rule (91% vs 92%).",
    "Its value estimate tracks the true remaining value (r = 0.88).",
    "Without retraining it avoids the collapses of tuned rules when teams grow or messages get expensive.",
    "The full evaluation protocol and baselines already run end to end.",
], size=14.5, space_after=9)
text(s, 7.1, 1.95, 5.6, 4.6, [
    [("It does not show (yet)", {"size": 19, "bold": True, "color": RED})],
    "Multi-agent learning: Level 2 is a fixed rule and Level 1 is one central learner.",
    "Deep RL: the learner is an extra-trees regressor, chosen for speed and stability.",
    "Better typical performance: it is a tie, not a win.",
    "Scaling to much larger maps with small teams: it stops far too early there.",
    "Communication limits: messages cost value but do not yet limit what robots know.",
    "Results over several training seeds (one seed so far).",
], size=14.5, space_after=9)

# ======================================================================= 25. phased plan
s = new_slide("Phased plan",
              "The abstract-to-robotics sequence you endorsed. Each phase starts only once the previous one works, so "
              "RL problems and simulator problems are never debugged at the same time.")
phases = [("Phase 1", "Toy environment", "N agents, M tasks, communication cost, a stop action. Does the policy "
                                         "learn when to continue, stop, and how many agents to activate?",
           "Semester 1"),
          ("Phase 2", "2D grid-world exploration", "Partial maps, frontiers, sensing, team-size and communication "
                                                   "tests. Most quantitative results come from here.",
           "First version built (week 1)"),
          ("Phase 3", "ROS2 / Gazebo", "MRTA testbed: realistic motion and sensing. Checks that the policy "
                                       "transfers to a real robotics stack.", "Semester 2"),
          ("Phase 4", "Realistic environments", "Larger maps, real robots if available.", "Future work")]
for i, (ph, name, desc, when) in enumerate(phases):
    x = 0.45 + i * 3.17
    done = "built" in when
    box(s, x, 1.8, 2.9, 4.2, fill=NAVY if done else PALE)
    fg = WHITE if done else INK
    text(s, x + 0.25, 2.0, 2.45, 0.4, [[(ph, {"size": 13, "bold": True, "color": GOLD if done else AMBER})]])
    text(s, x + 0.25, 2.4, 2.45, 0.9, [[(name, {"size": 19, "bold": True, "color": fg})]])
    text(s, x + 0.25, 3.35, 2.45, 2.0, [[(desc, {"size": 13.5, "color": SUB if done else MUTED})]])
    text(s, x + 0.25, 5.45, 2.45, 0.4, [[(when, {"size": 13, "bold": True, "color": GOLD if done else NAVY})]])
    if i < 3:
        arrow(s, x + 2.93, 3.9, x + 3.14, 3.9, color=MUTED, width=2)
text(s, 0.45, 6.25, 12.4, 0.5, [[("The ROS2/Gazebo migration continues as a separate track, so a delay there "
                                  "never blocks Phases 1 and 2.", {"size": 14, "color": MUTED})]])

# ======================================================================= 26. ablations
s = new_slide("Ablations",
              "Your ablation table, extended with a hierarchy column and the status in the prototype. The key "
              "comparison is MARL allocation with a strong heuristic stop against the full method: it isolates whether "
              "the improvement really comes from the stopping policy.")
Y_, N_ = "✓", "–"
rows = [["Method", "Frontier allocation", "Stopping", "Hierarchical", "Status"],
        ["Greedy frontier", "greedy", "fixed", N_, "done: 3 fixed rules"],
        ["Classical MRTA", "market-based / MinPos", "fixed", N_, "planned"],
        ["MARL allocation", "learned", "fixed", N_, "planned (MAPPO)"],
        ["MARL + heuristic stop", "learned", "heuristic", N_, "heuristics done; MARL planned"],
        ["RL allocation + stop (flat)", "learned", "learned", N_, "planned"],
        ["Full hierarchical method", "learned", "learned, value-aware", Y_, "Level 1 done; Level 2 planned"]]
table(s, 0.45, 1.75, 12.45, [3.3, 2.65, 2.3, 1.55, 2.65], rows, font=14, row_h=0.56, highlight_rows=(6,))
text(s, 0.45, 5.9, 12.4, 0.8, [[("Row 4 against row 6 answers the key question: ", {"size": 15}),
                                ("is the improvement actually coming from the stopping policy?",
                                 {"size": 15, "bold": True, "color": NAVY})],
                               [("Heuristic stops tested so far: myopic, gain-vs-cost, coverage threshold, fixed budget. "
                                 "To add: uncertainty-saturation and PRoID-style rate rules.", {"size": 13, "color": MUTED})]])

# ======================================================================= 27. experiment matrix
s = new_slide("Experiment matrix",
              "Train small, test large, without retraining. The matrix directly answers RQ4. The prototype already "
              "runs 2 to 8 robots; 10 robots and communication range limits are added next.")
rows = [["Factor", "Training", "Testing (no retraining)"],
        ["Team size", "2 robots", "2, 4, 6, 8, 10 robots"],
        ["Map size", "small (32×32)", "small, medium (48×48), large (64×64); ROS2 maps in Phase 3"],
        ["Communication", "medium cost", "low, medium, high cost; limited range and bandwidth"],
        ["Environment", "grid-world", "grid-world, then ROS2/Gazebo (MRTA testbed)"],
        ["Seeds", "≥ 5 training seeds", "40+ unseen maps per setting, paired across methods"]]
table(s, 0.45, 1.75, 12.45, [2.6, 2.7, 7.15], rows, font=14, row_h=0.62)
text(s, 0.45, 5.7, 12.4, 0.9, [[("Reported per setting: ", {"size": 14.5, "bold": True, "color": NAVY}),
                                ("net value vs the best stop (95% CI), regret, stop-time error, coverage, cycles, "
                                 "distance, messages. Across settings: interquartile mean, worst case, settings ≥ 80%.",
                                 {"size": 14.5})]])

# ======================================================================= 28. timeline
s = new_slide("Timeline",
              "Literature and formulation come first, as requested. MARL for Level 2 starts only after the learned "
              "stopping result holds in the grid-world. Gazebo work runs in the background in semester 1.")
weeks_x0, week_w = 3.45, 0.295
rows_t = [("Gap analysis (20 to 30 papers)", 1, 3, AMBER),
          ("RL fundamentals", 1, 4, AMBER),
          ("Dec-POMDP formulation, baselines", 3, 6, NAVY),
          ("Phases 1-2: learned stopping", 5, 11, BLUE),
          ("Level 2: MARL allocation (CTDE)", 10, 16, BLUE),
          ("ROS2/Gazebo migration", 1, 16, GRAYBAR),
          ("Phase 3: port to Gazebo", 17, 22, TEAL),
          ("Full matrix + ablations", 21, 27, TEAL),
          ("Scaling, comm limits", 25, 29, TEAL),
          ("Write-up", 28, 32, PURPLE)]
for sem, x0 in ((1, weeks_x0), (2, weeks_x0 + 16 * week_w)):
    text(s, x0, 1.72, 16 * week_w, 0.35, [[(f"Semester {sem}", {"size": 14, "bold": True, "color": NAVY})]],
         align=PP_ALIGN.CENTER)
for wk in (1, 4, 8, 12, 16, 20, 24, 28, 32):
    text(s, weeks_x0 + (wk - 1) * week_w - 0.1, 2.05, 0.5, 0.3, [[(str(((wk - 1) % 16) + 1),
                                                                    {"size": 11, "color": MUTED})]])
box(s, weeks_x0 + 16 * week_w - 0.01, 2.05, 0.02, 4.55, fill=LINE)
for i, (lab, a, b, col) in enumerate(rows_t):
    y = 2.4 + i * 0.42
    text(s, 0.45, y + 0.02, 2.9, 0.35, [[(lab, {"size": 12.5})]], align=PP_ALIGN.RIGHT)
    box(s, weeks_x0 + (a - 1) * week_w, y + 0.04, (b - a + 1) * week_w - 0.03, 0.28, fill=col)
text(s, 0.45, 6.72, 12.4, 0.3, [[("Week numbers within each semester.", {"size": 11, "color": MUTED})]])

# ======================================================================= 29. risks
s = new_slide("Risks and mitigations",
              "The first risk has already partly happened, and the plan takes it into account: the claim is about "
              "robustness and about learning the team-level decision, not about beating a well-tuned rule in its own "
              "setting. The venue is chosen with you once the Phase 2 results are in.")
rows = [["Risk", "Mitigation"],
        ["Learned stopping does not beat well-tuned heuristics",
         "Already seen in the prototype (a tie in the training setting). The claim is robustness across team size "
         "and cost, measured by the full matrix, and a learned team-level decision."],
        ["Novelty overlaps with existing stopping work",
         "Structured gap analysis first; claim phrased narrowly: team-level, learned, cost-aware, spatial exploration."],
        ["Learned stop fails on larger maps with small teams",
         "Train on a mix of map sizes; add scale-free features; report it openly if it persists."],
        ["MARL training is unstable or slow",
         "Grid-world first, parameter sharing, established CTDE baselines (MAPPO, QMIX), several seeds."],
        ["ROS2/Gazebo migration runs late", "Separate track; grid-world results stand on their own."],
        ["Paper timing", "Venue decided with the supervisor after Phase 2: RA-L (rolling) or the ICRA 2028 cycle."]]
table(s, 0.45, 1.75, 12.45, [4.5, 7.95], rows, font=13.5, row_h=0.7)

# ======================================================================= 30-31. references
REFS1 = [
    ("Multi-robot exploration and allocation", [
        "Yamauchi. A frontier-based approach for autonomous exploration. CIRA 1997.",
        "Burgard, Moors, Stachniss, Schneider. Coordinated multi-robot exploration. IEEE T-RO 21(3), 2005.",
        "Gerkey & Matarić. A formal analysis and taxonomy of task allocation in multi-robot systems. IJRR 23(9), 2004.",
        "Bautin, Simonin, Charpillet. MinPos: a novel frontier allocation algorithm for multi-robot exploration. ICIRA 2012.",
        "Quattrini Li. Exploration and mapping with groups of robots: recent trends. Current Robotics Reports, 2020."]),
    ("Stopping criteria in exploration", [
        "Placed & Castellanos. Enough is enough: towards autonomous uncertainty-driven stopping criteria. IFAC IAV 2022.",
        "Luperto, Ferrara, Princisgh, Boracchi, Amigoni. Estimating map completeness in robot exploration. Autonomous Robots 50, 2026.",
        "Kim, Baek, Corah, Best, Moon, Scherer. PRoID: predicted rate of information delivery in multi-robot exploration and relaying. arXiv 2604.10433, 2026."]),
    ("MARL for exploration", [
        "Tan, Pizarro Bejarano, Zhu, Ren, Nejat. Deep RL for decentralized multi-robot exploration with macro actions. IEEE RA-L 8(1), 2023.",
        "Chiun, Zhang, Wang, Cao, Sartoretti. MARVEL: MARL for constrained field-of-view multi-robot exploration in large-scale environments. ICRA 2025."])]
REFS2 = [
    ("Cooperative MARL, communication, hierarchy", [
        "Oliehoek & Amato. A Concise Introduction to Decentralized POMDPs. Springer 2016.",
        "Yu et al. The surprising effectiveness of PPO in cooperative multi-agent games (MAPPO). NeurIPS 2022 (Datasets & Benchmarks).",
        "Rashid et al. QMIX: monotonic value function factorisation for deep MARL. ICML 2018.",
        "Das et al. TarMAC: targeted multi-agent communication. ICML 2019.",
        "Sutton, Precup, Singh. Between MDPs and semi-MDPs (options). Artificial Intelligence 112, 1999.",
        "Han, Böhmer, Wooldridge, Rogers. Multi-agent hierarchical RL with dynamic termination. PRICAI 2019."]),
    ("Optimal stopping and batch RL", [
        "Tsitsiklis & Van Roy. Optimal stopping of Markov processes. IEEE TAC 44(10), 1999.",
        "Longstaff & Schwartz. Valuing American options by simulation: a least-squares approach. Rev. Fin. Studies 14(1), 2001.",
        "Becker, Cheridito, Jentzen. Deep optimal stopping. JMLR 20, 2019.",
        "Ernst, Geurts, Wehenkel. Tree-based batch mode reinforcement learning. JMLR 6, 2005.",
        "Szostak & Cohen. Deep MARL for decentralized active hypothesis testing. IEEE Access 2024."]),
    ("Evaluation, and motivation", [
        "Agarwal et al. Deep RL at the edge of the statistical precipice. NeurIPS 2021.",
        "Hu, Tan, Wang, Qu, Chen. Multi-agent debate for LLM judges with adaptive stability detection. NeurIPS 2025.",
        "Zhang. RL for LLM-based multi-agent systems through orchestration traces. arXiv 2605.02801, 2026 (preprint)."])]
for n_, groups in ((1, REFS1), (2, REFS2)):
    s = new_slide(f"Key references ({n_} of 2)",
                  "Every reference was checked against the publisher page, DOI or arXiv entry for authors, year and "
                  "venue. The study document gives each paper's contribution and which part to read first.")
    paras = []
    for head, items in groups:
        paras.append([(head, {"bold": True, "color": NAVY, "size": 15})])
        paras += [[(it, {"size": 13})] for it in items]
    text(s, 0.45, 1.72, 12.45, 5.2, paras, space_after=5, line_spacing=1.0)

# ======================================================================= thank you
for sh in thanks_slide.shapes:
    if sh.is_placeholder and sh.placeholder_format.idx == 13:
        runs = sh.text_frame.paragraphs[0].runs
        runs[0].text = "Chaitanya Goyal"
        for r in runs[1:]:
            r.text = ""
        tf = sh.text_frame
        p2 = tf.paragraphs[1]
        r2 = p2.add_run()
        r2.text = "2024A7PS0557P"
        r2.font.size = runs[0].font.size or Pt(20)
        r2.font.color.rgb = RGBColor(0xB8, 0xC4, 0xE6)

sldIdLst = prs.slides._sldIdLst
ids = list(sldIdLst)
intro_id, thanks_id = ids[1], ids[2]
rId = intro_id.get(qn("r:id"))
sldIdLst.remove(intro_id)
prs.part.drop_rel(rId)
sldIdLst.remove(thanks_id)
sldIdLst.append(thanks_id)
prs.save(OUT)
json.dump(dict(pearson_140=pear, sign_140=sign, n_points=int(len(qp))),
          open(f"{PROTO}/results/value_check_140.json", "w"))
print("saved", OUT, "slides:", len(prs.slides), "pearson", round(pear, 3), "sign", round(sign, 3))
