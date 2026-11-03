# Roadmap

Direction (from the supervisor's review): treat multi-robot exploration as deciding **how much exploration
effort is still worth spending** as returns drop. Stopping is the end point, when zero robots are left working.

## Done
- [x] Grid-world simulator: random buildings, limited robot vision, rounds of 6 steps, nearest-frontier robots
- [x] Score per round: new area minus driving, message and planning costs
- [x] Learned stop rule (fitted Q-iteration, 7 simple features)
- [x] Baselines: explore until done, fixed rounds, coverage threshold, first-bad-round, gain-vs-cost
- [x] Tests on 2–8 robots, 3 map sizes, 3 message costs, no retraining
- [x] Week 1: is the problem real? (yes, when costs are high)
- [x] Week 2: is RL needed? (the RL-style target yes; a big model no)
- [x] Proposal deck with citations, study guide, paper sheet

## This semester
- [ ] Real cost values (energy per metre, bandwidth), or results across a range of costs
- [ ] Stop rules based on Amorín 2019, Luperto 2026 and PRoID 2026 as baselines
- [ ] Team shrinking: the controller chooses how many robots stay active (N → … → 0)
- [ ] New map types (maze, warehouse, clutter), bigger maps and teams
- [ ] Find out why 2 robots on large maps stop too early
- [ ] Several training seeds
- [ ] Literature table (50–80 papers) and a one-page novelty statement
- [ ] Update the deck to the new direction

## Next semester
- [ ] Learn robot movement too (MAPPO), only if team shrinking shows a real gain
- [ ] Decentralised decision (no central controller)
- [ ] ROS2 / Gazebo tests; real robots if possible
- [ ] Papers: (1) value of continued exploration and stopping, (2) team shrinking with hierarchical MARL
