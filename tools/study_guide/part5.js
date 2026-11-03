const { H1, H2, H3, P, B, N, EQ, NOTE, WARN, SAY, DONT, SP, T, IMG } = require("./lib");

const img = (n) => IMG(`/home/claude/studydoc/slide-${String(n).padStart(2, "0")}.png`, 4.8, 2.7, `Slide ${n}`);

function slide(n, title, shows, say, details = [], careful = null) {
  const out = [H2(`Slide ${n}: ${title}`), ...img(n)];
  out.push(P("**What it shows.** " + shows));
  details.forEach((d) => out.push(B(d)));
  out.push(SAY([say], "What to say"));
  if (careful) out.push(WARN([careful], "Careful"));
  return out;
}

module.exports = [
H1("Part 7. Slide by slide"),
P("For each slide: a picture, what it shows, the details behind every element, a short script (about 30–60 seconds; the speaker notes in the .pptx contain a longer version), and what to be careful about. Total speaking time at this pace: about 20–22 minutes."),

...slide(1, "Title", "The project title, that this is the revised proposal, your name and ID, the supervisor, and the date.",
  "\"This is my revised proposal after your feedback. It asks one question: can a hierarchical multi-agent RL policy learn when continued multi-robot exploration is no longer worth its motion, communication and coordination cost? I'll cover the problem, what exists, the formulation, a first prototype with honest results, and the plan.\"",
  ["\"Value-aware\" = the stop is based on the estimated value of continuing. \"Team-level\" = one decision for the whole team. \"Hierarchical MARL\" = the final system has a team level and a robot level, both learned."],
  "Check the date on the title slide (currently October 2026) and the supervisor line before presenting."),

...slide(2, "What this talk covers", "The five parts of the talk. Part 4 is highlighted because it contains the new evidence.",
  "\"Five parts: the problem, what already exists, the formulation, the first evidence, and the plan.\""),

...slide(3, "Multi-robot exploration", "A small illustrated grid map (white = known free, dark = wall, grey = unknown, orange = frontier, two robots with their sensor ranges) and the key definitions.",
  "\"The team builds a grid map. Robots see a few cells around them, and walls block the view. A frontier is a known free cell next to unknown space. Each cycle the team senses, shares maps, gives each robot a frontier, and moves. Classical exploration repeats this until no frontier is left. My question is: after how many cycles should the whole team stop?\"",
  ["The picture is an illustration, not an actual prototype map.", "The citations: Yamauchi 1997 for frontiers; Burgard et al. 2005 for coordinated allocation that trades distance against expected gain."]),

...slide(4, "How exploration stops today", "The five kinds of stopping rules in use today, how each decides, where it is used, and what it ignores.",
  "\"Today, exploration stops with one of these rules. Frontier exhaustion ignores the cost of the last pockets. Coverage and time budgets need re-tuning for every map and team. Recent work has single-robot stopping criteria, based on uncertainty (Placed and Castellanos 2022) or on a learned map-completeness classifier (Luperto et al. 2026), and a per-robot rule for when to return and relay data (PRoID, 2026). None decides, for the whole team, whether one more cycle is worth what it costs.\"",
  ["Placed & Castellanos stop active SLAM when the map/pose uncertainty and mapped area stop improving (hand-set threshold, one robot).", "Luperto et al. train a CNN to classify a partial map as complete or not; exploration time drops by more than 35% (one robot, supervised, no cost model).", "PRoID: each robot decides when to stop exploring and go back to relay data, comparing information delivery rates; hand-designed rule; the mission ends at a fixed deadline."],
  "Do not say \"nobody has studied stopping\". People have; the gap is narrower (slide 8)."),

...slide(5, "When should the team stop?", "One real run (map 50018, 3 robots, 40×40): cells revealed (blue), cost (amber), net value (teal), and where the learned policy stopped.",
  "\"Here is one run from my prototype. The map revealed rises fast and then flattens, because the last part of a map comes in small scattered pockets. The cost keeps rising at a steady rate. Net value is the difference: it peaks and then falls. The learned policy stopped at cycle 20 with 83% mapped. Carrying on to the last frontier took 17 more cycles, added 17% more map, and cut the net value from 554 to 319.\"",
  ["The x-axis is cycles (6 robot steps each). The y-axis is cumulative cells.", "This map is an illustration; on this map the learned stop equals the hindsight-best stop. It is not a typical case: typical results are on slides 18–23.", "Messages grow as N(N−1), so the question gets sharper for bigger teams."],
  "If asked \"is this cherry-picked?\" say yes, it is chosen to illustrate the trade-off; the averages come later."),

...slide(6, "Three problems, one contribution", "The professor's point that frontier allocation, communication and stopping are three separate problems, and that the contribution is only C.",
  "\"Following your feedback I separate three problems. Frontier allocation and communication are active research areas, so I treat them as machinery: allocation is the substrate, and communication is modelled as a cost and a constraint. The contribution is C: when the whole team should stop.\""),

...slide(7, "What is already known", "The literature by area: what exists and what is missing in each.",
  "\"Multi-robot exploration has good allocation methods but fixed termination rules. MARL for exploration learns where robots go, but episodes end at a fixed length or coverage. Stopping criteria exist for single robots. Hierarchical MARL learns when sub-policies end, not when the task ends. Optimal stopping theory is mostly single decision maker. The LLM orchestration papers ask the same question in another field; they are only motivation.\"",
  ["The full gap analysis document (2–3 pages, 20–30 papers) is still to be written; this slide is its summary."],
  "The Zhang 2026 paper is an unrefereed preprint by a single independent author. Cite it only as motivation."),

...slide(8, "Closest prior work, and the gap", "The five papers a reviewer could say \"already did this\", checked against the five parts of the claim.",
  "\"This table is the novelty claim. Each row is a close paper; each column is part of my claim. Placed and Castellanos and Luperto et al. stop single robots. PRoID is multi-robot but decides per robot with a hand-set rule. Szostak and Cohen learn multi-agent stopping, but in hypothesis testing: no map, no motion. Han et al. learn when sub-policies end. None has all five. So the claim is narrow: to my knowledge, no prior work learns the team-level decision to end a multi-robot exploration mission as a cost-aware stopping problem.\"",
  ["\"partly\" for PRoID's costs: it accounts for travel time and failure risk, not message and coordination costs.", "\"partly\" for Szostak & Cohen's mission end: agents jointly declare a hypothesis, which ends the task, but it is not a spatial mission.", "The last row is the final system. In the prototype the learned stop comes from one central learner, not MARL (footnote)."],
  "Say \"to my knowledge\". The literature search is not finished; one very recent preprint (ICMAPE, arXiv 2609.33986) could not be checked yet."),

...slide(9, "Research questions", "The main question (the professor's wording) and four sub-questions, each with how it will be tested.",
  "\"The main question is in your wording. RQ1 is about allocation, tested with stopping fixed. RQ2 asks whether the policy knows when the remaining value is low. RQ3 asks whether stopping saves time and travel without losing meaningful coverage. RQ4 is about scaling. RQ2 and RQ4 already have first answers from the prototype; RQ1 needs the MARL Level 2.\""),

...slide(10, "Formulation 1: the setting", "The Dec-POMDP symbols and what each means in the project.",
  "\"Formally this is a decentralised POMDP: partially observable because nobody sees the true map, decentralised because each robot acts on its own observations. On top sits a team action once per cycle: continue or stop. The reward is the net value of each cycle.\"",
  ["A₀ is the team action (Level 1); Aᵢ are robot actions (Level 2).", "b is the belief: in practice, the 7-feature team summary."]),

...slide(11, "Formulation 2: value of a cycle", "The reward formula, each term, the weights, and a worked example of the break-even point for 2 vs 8 robots.",
  "\"Everything is measured in map cells. A cycle earns the cells it reveals and pays for robot steps, messages and coordination. The weights are an exchange rate: c_move = 2 means a step is worth two new cells. With 2 robots at medium cost, a cycle must reveal 26 cells to break even; with 8 robots at high cost, 132. So the right stopping point depends strongly on the team.\"",
  ["Worked examples are in Part 3.2 of this document."],
  "The weights are a modelling choice, not measured from real robots. That is why training randomises them and testing varies them."),

...slide(12, "Formulation 3: optimal stopping", "The decision diagram (stop gives 0; continue earns r and decides again), the definition of Q, the stopping rule, and the oracle.",
  "\"Choosing when to stop is an optimal stopping problem. Q is the value of continuing now and then continuing to decide optimally. Stopping is worth zero from that point on, so the rule is: stop the first time Q is not positive. The oracle is the best stop computed after the run; it needs the future, so it is only the 100% reference.\"",
  ["max(0, Q(next state)): at the next decision the team again picks the better of stop and continue. Worked example 3 in Part 3.4."]),

...slide(13, "Two-level architecture", "Level 1 (team stop) on top of per-robot Level 2 policies, CTDE, and a table of what is built now versus in the final system.",
  "\"Level 1 decides once per cycle for the whole team; Level 2 moves each robot every step. In the final system both are learned and trained with centralised training and decentralised execution. In the week-1 prototype only Level 1 is learned; Level 2 is a fixed greedy rule and communication is only a cost.\"",
  [], "This slide is where you pre-empt \"is this really MARL?\" Answer before they ask: not yet; the table shows what changes."),

...slide(14, "How the stop is learned", "The four-step training pipeline and the seven features.",
  "\"I explore each training map to the end and log every cycle. Each run is re-scored under four random cost settings: robot motion does not depend on the costs, so this is free, and it teaches the policy how costs move the stopping point. Then fitted Q-iteration fits Q in 25 rounds with an extra-trees regressor. At run time, the robots stop when Q is not positive. The features are all ratios so they transfer to other team and map sizes.\"",
  ["Why one full run per map is enough: Part 4.6.", "Exact feature formulas: Part 4.5."]),

...slide(15, "Baselines for comparison", "Every rule compared, its exact stopping condition, parameter and idea.",
  "\"Every rule is evaluated on the same maps with the same robot motion; only the stopping moment differs. The three tuned rules had their one number tuned on the same 300 training maps, for the training setting: that is their best case. The myopic rule stops after the first cycle that lost value. The gain-vs-cost rule stops when the expected gain falls below the cycle cost divided by 1.6.\"",
  [], "The coverage threshold uses the known fraction of the **whole grid** (free and wall cells), not the free-space coverage metric."),

...slide(16, "Evaluation metrics", "The six metric groups (main score, regret, stop-time error, operational cost, value-estimate quality, robustness) and the statistics used.",
  "\"The main score is net value relative to the best stop in hindsight. Regret is the same information in cells, normalised by map size, which stays meaningful when the best achievable value is tiny. Stop-time error shows how rules fail. Coverage, cycles, steps and messages show what a stop saves and leaves. For the value estimate I report correlation and sign accuracy. Across settings I report the interquartile mean and the worst case. All comparisons are paired, with 95% bootstrap intervals.\"",
  ["Every metric is defined in Part 5."]),

...slide(17, "Week 1: a working prototype", "The same map as slide 5, where the learned policy stops (left) and after exploring until no frontiers (right), plus the prototype settings.",
  "\"On the left, the learned policy has stopped at cycle 20 with 83% mapped; on the right, exploring until no frontiers remain takes 37 cycles. The policy leaves the far corner because reaching it costs more than it would reveal at these weights. Everything runs on a laptop CPU in about 15 minutes.\"",
  ["Test = 140 maps in the training setting + 36 settings × 40 maps."]),

...slide(18, "Result 1: training setting", "Net value as % of the best stop for each rule, 140 unseen maps, with 95% confidence intervals, and three key numbers.",
  "\"In the setting it was trained on, the learned rule reaches 91% of the best achievable value, the tuned coverage threshold 92%. The intervals overlap, so this is a tie, not a win. Exploring until no frontiers loses about a quarter of the achievable value, and stopping at the first bad cycle loses about a third. The learned rule stops about three cycles early on average.\"",
  ["Numbers in brackets are 95% bootstrap intervals.", "The coverage bar is darker because it is the strongest baseline."],
  "Say \"tie\". If asked why the old version said 93%: that was one test subset; Part 6.2 explains."),

...slide(19, "Result 2: how each rule stops", "Coverage, cycles, steps, per-map median and 10th percentile, and early/exact/late shares for every rule.",
  "\"The learned rule maps less, 78% against 90%, but scores the same, because it stops early on maps where the rest is expensive to reach. Its typical map is excellent, a median of 96%, but its bad maps are worse than the coverage rule's: the worst 10% of maps score 72% against 82%. Exploring to the end is late on 97% of maps; the myopic rule is early on 76%.\"",
  ["Messages = cycles × N(N−1), so fewer cycles means fewer messages."]),

...slide(20, "Result 3: value estimate", "Estimated Q versus the true value of continuing at every decision point (1,500 of 3,886 plotted), with correlation and sign accuracy.",
  "\"Each dot is one decision point. Horizontal is the true value of continuing, known afterwards; vertical is the policy's estimate at that moment. The correlation is 0.88, and the estimate has the right sign, continue versus stop, at 89% of decision points. It underestimates when a lot of map is left, because tree models cannot extrapolate, but that does not affect the decision early on; what matters is accuracy near zero.\""),

...slide(21, "Result 4: 36 unseen settings", "Regret (lower is better) by team size, map size and communication cost, averaged over the other two factors, for four rules.",
  "\"Now the policy is used unchanged in 36 new settings. The metric is regret: the value lost against the best stop, as a percentage of the map. As the team grows and messages get expensive, the tuned rules drift up; the learned rule stays low. Its weak spot is the left end: with 2 robots on larger maps it stops far too early.\"",
  ["Each point averages 3 or 4 settings × 40 maps.", "The learned line at 2 robots (7.7%) is worse than the coverage threshold (2.9%). Point this out yourself."]),

...slide(22, "Result 5: robustness", "Per-rule summary across the 36 settings, including two optimistic control rows.",
  "\"In a typical setting the learned rule and the coverage threshold are equally good: same interquartile mean, 89%, and the same 27 of 36 settings above 80%. The difference is the worst case: 9.9% of the map lost at worst, against 25% for the coverage rule, and only one setting below 50%. The grey rows re-tune a simple rule for each setting using that setting's own test maps. That is the best an engineer could do with data from every new deployment, and the learned rule comes close to it without any re-tuning. I don't use the raw average of percentages as a headline, because in the hardest settings the best achievable value is only a few dozen cells, and dividing by it produces numbers like minus 700%.\"",
  [], "Concede the control rows honestly: a per-setting re-tuned budget has a better worst case (4.1%). The learned rule's advantage is that it needs no per-setting data."),

...slide(23, "Where it wins, and where it fails", "Six settings: three wins (costly teams), two failures (small team, big map), one where every rule fails.",
  "\"Top three: when the team is costly, the tuned rules keep exploring at a loss and the learned rule stops in time. Next two: with only 2 robots on bigger maps, the learned rule stops 20 to 33 cycles too early; it never saw such long episodes in training. Last: 8 robots on a small map with expensive messages, where on 14 of 40 maps it is not worth exploring at all; every rule fails there, and the right answer is to use fewer robots, which the policy cannot choose yet.\"",
  ["Diagnosis and fixes for the failure: Part 6.5."]),

...slide(24, "What it shows, and what not", "The scope of the evidence: five things it shows, six things it does not.",
  "\"To be clear about scope: the prototype shows the stop can be learned, that it ties the best tuned rule at home, that its value estimate is meaningful, and that it is safer when conditions change. It is not yet MARL, not deep RL, not better in the typical case, it fails on large maps with small teams, communication does not yet limit what robots know, and it uses one training seed.\""),

...slide(25, "Phased plan", "The four phases (toy environment, grid-world, ROS2/Gazebo, realistic), with Phase 2 highlighted as started.",
  "\"This is the abstract-to-robotics sequence you endorsed. Each phase starts only when the previous one works, so RL problems and simulator problems are never debugged together. The ROS2 migration continues separately.\""),

...slide(26, "Ablations", "Six system variants that swap allocation and stopping components one at a time, with their status.",
  "\"Row 4 against row 6 is the key comparison: MARL allocation with a strong heuristic stop against the full method. It isolates whether the improvement comes from the stopping policy. I will also add the stopping rules from the recent literature as baselines: uncertainty saturation and PRoID-style rate rules.\""),

...slide(27, "Experiment matrix", "Training vs testing conditions and what is reported.",
  "\"Train small, test large, without retraining: team size up to 10, three map sizes, three communication costs, then ROS2 maps, with at least five training seeds.\""),

...slide(28, "Timeline", "Two-semester Gantt chart.",
  "\"Literature and formulation first, as you asked. MARL for Level 2 starts only once the learned stop holds in the grid-world. Gazebo runs in the background in semester 1; porting, the full matrix, scaling and writing are in semester 2.\""),

...slide(29, "Risks and mitigations", "Six risks and how each is handled.",
  "\"The first risk has partly happened already: the learned stop ties a well-tuned rule at home. So the claim is robustness and a learned team-level decision, not a higher everyday score. The large-map failure is handled by training on mixed map sizes and scale-free targets.\""),

...slide(30, "Key references (1 of 2)", "Exploration, stopping criteria, MARL for exploration.", "Do not read references aloud. Say: \"All references were checked for authors, year and venue.\""),
...slide(31, "Key references (2 of 2)", "MARL, hierarchy, optimal stopping, evaluation, motivation.", "As above."),
...slide(32, "Thank you", "Closing slide.", "\"Thank you. I'm happy to take questions, and I can run the live demo on a new random map if useful.\""),
];
