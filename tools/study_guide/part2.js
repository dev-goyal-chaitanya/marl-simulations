const { H1, H2, H3, P, B, N, EQ, NOTE, WARN, SAY, SP, T } = require("./lib");

module.exports = [
H1("Part 2. Background concepts, from zero"),
P("Each concept below is used somewhere in the deck. For each one: what it is, a small example, and how it appears in this project."),

H2("2.1 Robot exploration and the occupancy grid"),
P("**Exploration** is the task of building a map of an environment that nobody has mapped. The most common map representation is an **occupancy grid**: the floor is divided into square cells, and each cell is labelled *free* (a robot can be there), *occupied* (a wall or furniture) or *unknown* (not seen yet). Real systems store a probability of occupancy per cell; the prototype uses the three labels directly because its sensor is noise-free."),
P("**In the prototype:** maps are square grids of 32×32, 48×48 or 64×64 cells. At the start every cell is unknown to the team."),

H2("2.2 Sensing, line of sight"),
P("A robot sees cells within its **sensor radius** (4 cells in the prototype). It sees along straight lines (rays) from its position; a wall blocks the ray, so the robot sees the wall cell but nothing behind it. The prototype draws rays with **Bresenham's line algorithm**, the standard way to list the grid cells a straight line passes through."),
P("**Why it matters:** because walls block sight, exploring a room requires actually entering it or looking through its door. That is what makes the late part of exploration expensive: the last unknown pockets are behind doors and around corners."),

H2("2.3 Frontiers and frontier-based exploration"),
P("A **frontier cell** is a known free cell that has at least one unknown neighbour (up, down, left or right in the prototype). Standing at a frontier and looking around reveals new space. **Frontier-based exploration** (Yamauchi 1997) is the classical algorithm: repeatedly drive to a frontier, sense, update the map, and stop when no reachable frontier is left."),
P("**Example:** in the grid on slide 3, the pale-orange cells are frontiers: free cells next to the grey unknown area. A robot that drives to one of them and looks around will uncover part of the grey region."),

H2("2.4 Multi-robot coordination and task allocation"),
P("With several robots, the problem is **which robot goes to which frontier**, so that robots spread out instead of all going to the same place. This is a case of **multi-robot task allocation (MRTA)**. Gerkey & Matarić (2004) classify MRTA problems along three axes: single-task vs multi-task robots, single-robot vs multi-robot tasks, and instantaneous vs time-extended assignment. Exploration with one frontier per robot, re-planned every cycle, is roughly *single-task robots, single-robot tasks, instantaneous assignment, repeated over time*."),
P("Classic methods: **Burgard et al. (2005)** assign targets by trading the utility of a frontier (how much it will reveal) against the cost of reaching it, and reduce the utility of frontiers near targets already given to teammates. **MinPos** (Bautin et al. 2012) lets each robot pick the frontier where it ranks best among teammates by distance. **Market-based methods** let robots bid for frontiers."),
P("**In the prototype (Level 2):** a greedy allocator repeatedly gives the globally closest (robot, frontier) pair, then blocks every frontier within 8 cells (twice the sensor radius) of that target so the next robot goes elsewhere. This is deliberately simple: allocation is *not* the contribution."),

H2("2.5 Reinforcement learning (RL) basics"),
P("In RL an **agent** interacts with an **environment** over time. At each step it sees a **state** *s*, chooses an **action** *a*, receives a **reward** *r*, and the environment moves to a new state *s′*. A **policy** π tells the agent which action to take in each state. The goal is to maximise the **return**: the (possibly discounted) sum of future rewards."),
T([
  ["Term", "Meaning", "In this project (Level 1)"],
  ["State *s*", "What the agent knows when deciding", "A 7-number summary of the team's situation after each cycle"],
  ["Action *a*", "What it can do", "Continue for one more cycle, or stop"],
  ["Reward *r*", "Immediate feedback", "Net value of the cycle: cells revealed minus motion, message and coordination cost"],
  ["Episode", "One run from start to end", "One exploration of one map"],
  ["Return", "Sum of rewards over the episode", "Total net value when the team stops"],
  ["Policy π", "Rule mapping state to action", "Stop if Q(s) ≤ 0, otherwise continue"],
], [0.18, 0.37, 0.45]),
SP(),
P("**Value functions.** V(s) is the expected return from state *s* if you follow the policy. Q(s, a) is the expected return if you take action *a* now and follow the policy afterwards. The **Bellman equation** expresses a value in terms of the next step: the value now = the reward of this step + the value of where you land. Everything in RL is some way of estimating these values and acting greedily with respect to them."),
P("**Tiny example.** You are at a buffet. Each extra plate gives enjoyment but also discomfort. The value of \"take one more plate\" = enjoyment of that plate − discomfort + the value of being in the new state (fuller, and able to decide again). You should stop when that value is no longer positive. The stopping problem in this project has exactly this structure."),

H2("2.6 MDP, POMDP and belief"),
P("A **Markov decision process (MDP)** assumes the agent sees the full state. A **partially observable MDP (POMDP)** (Kaelbling, Littman & Cassandra 1998) assumes it only gets *observations* that reveal part of the state. The agent must then act on a **belief**: its best summary of what it knows. In exploration the true map is the hidden state; the known part of the map is the observation history."),
P("**In the prototype:** the Level-1 decision uses a hand-designed summary of what the team knows (the 7 features, Part 4). That summary plays the role of the belief. It is an approximation, which is standard practice."),

H2("2.7 Dec-POMDP: many agents, each with partial view"),
P("A **decentralised POMDP** (Dec-POMDP; Oliehoek & Amato 2016) is a POMDP with several agents that share one reward but each act on their own observations. It is written as a tuple ⟨I, S, {Aᵢ}, P, R, {Ωᵢ}, O⟩: agents I, states S, each agent's actions Aᵢ, transition probabilities P, shared reward R, each agent's observations Ωᵢ, and the observation model O. Slide 10 maps each symbol to the project."),
P("Solving Dec-POMDPs exactly is computationally very hard (finite-horizon Dec-POMDPs are NEXP-complete; Bernstein et al. 2002), which is why practical work uses learning and approximations. You do not need to prove anything about this; you only need to know why the problem is stated as a Dec-POMDP: **the map is unknown (partial observability) and each robot acts on what it sees (decentralised)**."),

H2("2.8 Multi-agent RL (MARL) and CTDE"),
P("**MARL** trains several agents at once. The main difficulty is that, from each agent's point of view, the others are part of a changing environment, and the shared reward makes it hard to know which agent deserves credit (*credit assignment*)."),
P("**Centralised training, decentralised execution (CTDE)** is the standard answer: during training (in simulation) a critic or mixer may use global information such as the full map and all robot positions; at execution time each agent's policy uses only its own observations. Common CTDE algorithms:"),
B("**MAPPO** (Yu et al. 2022): PPO with a centralised value function. Simple and strong; the planned Level-2 learner."),
B("**QMIX** (Rashid et al. 2018): value-based; combines per-agent Q-values through a monotonic mixing network so greedy per-agent actions are consistent with the team's best joint action."),
B("**COMA** (Foerster et al. 2018): actor-critic with a counterfactual baseline for credit assignment."),
B("**MADDPG** (Lowe et al. 2017): actor-critic with centralised critics, for continuous actions."),
P("**Parameter sharing** means all robots use the same network weights (with their own observations as input). It makes training faster and lets the policy run on any number of robots, which matters for the team-size tests."),
WARN(["The week-1 prototype is **not** MARL. Robot movement is a fixed rule and the stop is learned by a single central learner. Say this clearly before anyone asks."], "Be precise"),

H2("2.9 Hierarchical RL, options and termination"),
P("**Hierarchical RL** splits decisions across time scales. In the **options framework** (Sutton, Precup & Singh 1999) an *option* is a temporally extended action: a sub-policy plus a *termination condition* that says when it ends. The **option-critic** architecture (Bacon, Harb & Precup 2017) learns termination conditions by gradient. **Han et al. (2019)** study learned (\"dynamic\") termination of options in multi-agent settings."),
P("**Difference from this project:** those works learn when each agent's *sub-policy* ends. This project learns when the *whole mission* ends, for the whole team, based on expected remaining value versus team cost. That distinction is one of the four qualifiers of the novelty claim (slide 8)."),

H2("2.10 Communication in MARL"),
P("Robots share map updates. In MARL, communication is itself a research topic: learning what to send and to whom (TarMAC, Das et al. 2019), and coping with limited bandwidth or dropped messages (Tan et al. 2023 train with random communication dropouts). **In this project** communication is not learned; it is modelled as a **cost** (every robot sends its update to every other robot each cycle: N(N−1) messages), and later as a **constraint** (range and bandwidth limits)."),

H2("2.11 Optimal stopping"),
P("**Optimal stopping** asks: you observe a process step by step; at each step you may stop and collect a payoff, or continue; when should you stop to maximise the expected payoff? Classic examples: selling a house (accept this offer or wait?), the secretary problem, exercising an American option in finance."),
P("A **stopping time** is a rule that decides to stop at time *t* using only information available at time *t* (it cannot peek into the future). The central equation compares the value of stopping now with the value of continuing:"),
EQ("value now = max( payoff if you stop now ,  expected value of continuing )"),
P("The expected value of continuing is called the **continuation value**. Much of the practical literature estimates it by regression: **Longstaff & Schwartz (2001)** regress realised future payoffs on features of the current state and exercise an option when the immediate payoff beats the estimated continuation value; **Tsitsiklis & Van Roy (1999)** give convergence results for approximate methods; **Becker, Cheridito & Jentzen (2019)** learn the stop/continue decisions with neural networks."),
P("**In this project** the payoff of stopping now is 0 (nothing more is gained or paid), and the continuation value is Q(s): the expected net value of doing one more cycle and then continuing to decide optimally. So the rule is simply: **stop when Q(s) ≤ 0**."),
NOTE([
  "In optimal stopping, *the decision does not change the process until you stop*. The robots move the same way whether or not a stop was considered at some earlier cycle. So a log of the process run to the very end contains everything needed to evaluate every possible stopping time and to learn the continuation value. This is exactly why the prototype can explore each map once, to the end, and then evaluate every stopping rule on that log (Part 4.6). It is the same reason Longstaff–Schwartz can price options from simulated price paths.",
], "A key fact that makes the prototype valid"),

H2("2.12 Fitted Q-iteration and extra-trees"),
P("**Fitted Q-iteration (FQI)** (Ernst, Geurts & Wehenkel 2005) is a *batch* RL method: it learns from a fixed dataset of transitions (s, a, r, s′) instead of interacting with the environment. It repeats: (1) compute a target for each transition using the current Q estimate: y = r + value of the best action in s′; (2) fit a regression model that predicts y from s; (3) use that model as the new Q. After enough rounds, Q approximates the optimal action-value."),
P("**Extra-trees** (extremely randomised trees) is the regression model used. It is an ensemble of decision trees, each built with random split points, and the prediction is the average over trees. Ernst et al. showed it works well inside FQI. It needs no feature scaling, is fast on a CPU, and rarely diverges, which is why it was chosen for a first prototype. The deep-learning version of the same idea is **Neural Fitted Q** (Riedmiller 2005) and, later, DQN."),

H2("2.13 Generalisation and cost randomisation"),
P("**Generalisation** means the policy works in situations it was not trained on. Here: more robots, bigger maps, different communication costs. The main enemy is **distribution shift**: the test situations produce feature values the model never saw in training."),
P("**Domain randomisation** (Tobin et al. 2017) trains on many randomly varied versions of the simulator so the real world looks like just another variation. The prototype uses the same idea for costs: **cost randomisation**. Because costs do not change how robots move, each training run can be re-scored under several random cost settings for free, and the learner sees how the right stopping point moves when costs change."),

H2("2.14 Statistics used in the results"),
T([
  ["Term", "Meaning", "Where it is used"],
  ["Mean / median", "Average / middle value", "Everywhere"],
  ["10th percentile", "The value below which the worst 10% of maps fall", "Slide 19, \"worst 10% of maps\""],
  ["Ratio of totals", "Sum of a rule's net value over all maps ÷ sum of the oracle's", "The main % score. It weights big maps more than a mean of per-map percentages would, and avoids dividing by tiny per-map values"],
  ["Bootstrap 95% CI", "Resample the test maps with replacement 5,000 times, recompute the score each time, and take the middle 95% of the results", "Brackets on slide 18. If two intervals overlap a lot, the difference may be noise"],
  ["Paired comparison", "Compare two rules on exactly the same maps", "All comparisons; it removes map-to-map luck from the difference"],
  ["Pearson correlation r", "How well two quantities move together on a straight line; 1 = perfect, 0 = none", "Slide 20, learned Q vs true remaining value"],
  ["Interquartile mean (IQM)", "Mean of the middle 50% of values; ignores the top and bottom 25%", "Slide 22; recommended by Agarwal et al. (2021) as robust to outliers"],
  ["Probability of improvement", "Share of settings in which method A scores higher than method B", "Part 6.4"],
], [0.2, 0.45, 0.35]),
];
