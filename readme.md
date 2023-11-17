### Simple Storage Optimizer
## Yay to MILP or at least LP programming

This small project is only there to show Stufe how google ORTools works. As i have nothing better to do i just spend this evening programming this as a small POC to show some basic principles oft stochastic linear programming

## What is done

We aim to solve a simple Recourse Problem which is statet in th the following (pseudo) way:

Minimize [ (sum of investment costs for solar panels and storage) + (expected costs (or savings) in the future, resulting from investment.) ]

I would love to write this in latex but i am too lazy to do so.

Anyways, so to say we select the best combination of Storage and Solar Panels to minimize the costs a.k.a maximize our profit $$$

