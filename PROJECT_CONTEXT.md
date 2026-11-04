# Project context: Value-Aware Adaptive Multi-Robot Exploration

Paste this file at the start of a new Claude conversation to bring it up to speed.
Last updated: 4 November 2026.

## Who and what
- **Student:** Chaitanya Goyal (2024A7PS0557P), B.E. Computer Science, BITS Pilani.
- **Supervisor:** Prof. Avinash Gautam, Dept. of CSIS. His review report names Nivedan Yakolli (2023PHXF0032P) as a co-author.
- **Course:** a two-semester Study Oriented Project (the review's header says "ME303 – Study Oriented Program").
- **Code and documents:** github.com/dev-goyal-chaitanya/marl-simulations (private).

## How to work with me
- Explain things briefly and simply, with little jargon. I don't want long report-style answers.
- I learn by building, so I prefer concrete step-by-step plans over reading-only plans.
- Be absolutely realistic and honest. No overclaiming, and no "nobody has done this" unless it has been checked.
- Accuracy matters: a wrong claim in front of my professor costs me. Flag anything unverified.

## The problem in one paragraph
A team of robots explores an unknown building on a grid. Early exploration "cycles" reveal whole rooms. Late cycles need long drives to reveal small leftover corners, but each cycle still costs driving, messages and planning. So at some point another cycle isn't worth it.

The original question was *when should the whole team stop?* After the professor's review, it became *how much exploration effort (how many robots, how much messaging) is still worth spending?* Stopping is the case where zero robots are active.

## The professor's review (October 2026): key points
1. **The novelty claim was too strong.** Earlier papers already deal with stopping exploration:
   - Amorín et al. 2019: a stop for the whole fleet based on expected information gain
   - Placed & Castellanos 2022
   - Luperto et al. 2026
   - PRoID 2026
   - WiSER-X 2026

   The narrowed claim: *to my knowledge, no earlier work learns, for the whole team, how much exploration effort to keep spending, counting the costs of motion, communication and coordination.*
2. **A yes/no stop doesn't justify hierarchical MARL.** So the top-level action is generalised to N_active ∈ {0..N}, the number of robots still working (plus a message budget B_comm later). N_active = 0 means stop.
3. **Staged programme:**
   - **A.** Is the problem real?
   - **B.** Is the remaining value learnable? Is RL needed?
   - **C.** A stopping-only benchmark with robot motion fixed.
   - **D.** Adaptive team size.
   - **E.** Hierarchical MARL (a resource controller on top, MAPPO for robot movement).

   MARL only comes after A–D show it's needed.
4. Other asks:
   - Realistic costs. Replace N(N−1) with a message cost over the actual links: Σ(αB + βM + ηL).
   - Entropy reduction as the information measure.
   - Report each quantity separately.
   - A Pareto analysis over cost weights.
   - Generalisation tests designed before training (environment, scale, team size and communication shifts).
   - Two oracles once robot motion is learned.
   - A literature matrix of 50–80 papers.
   - A one-page novelty statement.
5. **Possible papers:**
   1. Learning the marginal value of continued exploration (no MARL)
   2. Hierarchical resource-aware MARL
   3. Decentralised termination under communication limits

## What is built (repo folder `code/`)
- **Simulator** (`mapgen.py`, `env.py`):
  - random indoor maps (rooms, doors, furniture) of 32/48/64 cells
  - 2–8 robots with a sensor radius of 4 and line of sight
  - a cycle is 6 robot steps
  - robot movement is a fixed greedy nearest-frontier rule with spreading. This is not learned and not the contribution.
- **Cycle score:** r = new cells − c_move·steps − c_comm·N(N−1) − c_coord.
  - Defaults: c_move = 2, c_coord = 2.
  - c_comm = 0.05 / 0.2 / 0.6 for low / medium / high message cost.
  - V(T) is the sum of the first T scores. T\* = argmax V(T) is the hindsight-best stop, used only as the 100% grading reference.
- **Learned stop** (`stopping.py`):
  - estimates Q(s) = E[r + max(0, Q(next))] and stops at the first cycle where Q ≤ 0
  - trained with fitted Q-iteration (Ernst et al. 2005): 25 rounds, an extra-trees model with 80 trees and minimum leaf size 8
  - training data: 300 maps with 2 robots on 32×32, each re-scored under 4 random cost settings (1,200 runs)
  - **7 ratio features:** known fraction; expected gain ÷ cycle cost; last gain ÷ cost; previous gain ÷ cost; distance to targets ÷ 6; share of robots with a target; frontier cells ÷ map side
- **Baselines:**
  - explore until no frontiers
  - fixed budget (tuned to 19 cycles)
  - coverage threshold (tuned to 0.84)
  - myopic (stop after the first losing cycle)
  - gain-vs-cost rule (α = 1.6)
  - the hindsight oracle
- **Scripts:**
  - `demo.py`: live demo
  - `run_experiments.py`: full evaluation
  - `week1_problem_size.py`: Stage A
  - `week2_models.py`: Stage B
  - `make_figures.py`
  - `extra_metrics*.py`

  Saved runs are in `code/results/`, so nothing needs re-simulating.

**Important:** the prototype is **not** MARL and not CTDE. Level 1 is a single central learner, and Level 2 is a fixed rule.

## Results so far
- **Stage A** (1,440 runs: 2/4/6/8 robots × 3 map sizes × 3 message costs × 40 maps):
  - Exploring until done loses **11.4% of the map's value** on average (range 5–45%).
  - **36% of all driving** happens after the best stop.
  - The loss grows with team size: 8 robots lose 16.8%, 4 robots 8.0%.
  - It grows with message cost: high cost loses 18.3%, low cost 6.9%.
  - With 8 robots and high message cost, about 34% is lost.
  - **Caveat:** it depends on the price of driving. Value lost is 1.0 / 2.2 / 9.1 / 27.3% at a cost per step of 0.5 / 1 / 2 / 3. Cheap driving means the problem nearly disappears, so realistic costs are needed.
- **Stage B:**
  - Fitted Q-iteration beats supervised regression on hindsight labels for every model type.
  - Worst-setting loss is 9.9–13.0% for fitted Q-iteration, against 30.4–39.0% for hindsight labels. Average loss is 3.5–4.8% against 5.4–9.6%.
  - The reason: hindsight labels assume perfect future stopping (perfect-foresight bias), so they stop too late.
  - The model barely matters. Even a linear model works, and extra trees has the best worst case (9.9%).
  - Learned Q: correlation 0.88 with the true remaining value; it gets the sign right 89% of the time.
- **Stage C so far:**

  | Rule | % of best (140 maps) | Avg loss, 36 settings (% of map) | Worst setting |
  |---|---|---|---|
  | Learned | 91 | 3.6 | 9.9 |
  | Coverage threshold | 92 | 4.7 | 25.3 |
  | Gain-vs-cost | 89 | 6.9 | 15.8 |
  | Fixed budget | 91 | 9.1 | 37.1 |
  | Myopic | 68 | 11.4 | 24.5 |
  | Explore until done | 74 | 11.4 | 44.6 |

  The learned rule **ties** the coverage threshold in typical cases and is much safer in the worst case, with no retuning.
- **Weak spots:**
  - With 2 robots on 48/64 maps it stops 20–33 cycles early; the cause is undiagnosed.
  - Only one map style.
  - Only one training seed.
  - The costs are assumed, not measured.

## Plan (this semester; the dates are a proposal)
1. **November, weeks 1–2:** realistic costs or a cost sweep; add baselines in the style of Amorín, Luperto and PRoID.
2. **November, weeks 2–4:** Stage D, team shrinking.
   - Retired robots stop moving and messaging, so they cost nothing.
   - Training data includes random retirements.
   - Fitted Q-iteration with N_active as an input.
   - Compare: full team with learned stop, a fixed 8 → 4 → 2 → 0 schedule, and learned shrinking.
3. **Late November:** maze, warehouse and clutter maps; 5 seeds; diagnose the 2-robot failure.
4. **Early December:** write up Stages A–D and outline Paper 1.

**Next semester:** MAPPO for robot movement (only if Stage D shows a real gain), decentralised decisions, ROS2/Gazebo (the MRTA testbed).

**Literature:** the shared sheet has 33 entries. Target: 50 by end of November, 80 before MARL.

**Open questions for the professor:**
- Realistic cost values?
- Does a retired robot park or return to base?
- Is retirement permanent?
- Is Paper 1 (no MARL) a good first target?

## Key papers and how they relate
- **Amorín, Benavides, Grampín 2019 (LARS):** a stop for the whole fleet based on expected information gain. The closest work. *Known only from the abstract and the professor's description; the full text is unchecked.*
- **Luperto et al. 2026 (Autonomous Robots 50(1):6):** a CNN classifies a partial map as explored or not; supervised; single robot; about 35% time saved; public code.
- **PRoID (Kim et al., arXiv 2604.10433):** each robot decides when to return and relay, using a rate formula. Not learned. Counts time and risk only.
- **Placed & Castellanos 2022 (IFAC):** a single robot stops when uncertainty saturates.
- **WiSER-X (Jadhav, Behari, Wood, Gil; RA-L 2026):** decentralised, with asynchronous termination and no shared map. *Abstract only.*
- **Method:** Ernst et al. 2005 (fitted Q-iteration); Longstaff & Schwartz 2001 and Tsitsiklis & Van Roy 1999 (regression-based optimal stopping); Becker et al. 2019 (deep optimal stopping).
- **Background:**
  - Yamauchi 1997 (frontiers)
  - Burgard et al. 2005 (coordinated allocation)
  - Tan et al. 2023 and MARVEL 2025 (MARL exploration with a fixed episode end)
  - MAPPO (Yu et al. 2022)
  - Han et al. 2019 (dynamic termination in hierarchical MARL)
  - Sutton et al. 1999 (options)
  - Szostak & Cohen 2024 (MARL that learns when to stop sampling)
  - Oliehoek & Amato 2016 (Dec-POMDP)
  - Agarwal et al. 2021 (reporting RL results)

## Documents (in the repo)
- `docs/proposal/Progress_Review_Nov2026.pptx` (and `.pdf`): the current 28-slide deck, aligned with the review, with IEEE-style numbered citations.
- `docs/report/`: the semester progress report (LaTeX for Overleaf, plus the PDF).
- `docs/WEEK1_2_RESULTS.md`: Stage A and B notes.
- `docs/Study_Guide_Value_Aware_Stopping.docx`: explains the older proposal deck. Some framing in it is now outdated.
- `docs/literature/`: the paper database (33 entries) and the paper table.
- `ROADMAP.md`: done and to-do checklist.
- `tools/`: the scripts that generated the decks and the study guide.
