| relation | claim | formula |
|----------|-------|---------|
| clamp | the effective grade is the weakest along `rests-on` | $\mathrm{eff}(c) = \min\{\, \mathrm{grade}(c)\,\} \cup \{\, \mathrm{eff}(d) : d \in \mathrm{rests\text{-}on}(c)\,\}$ |
| disjoint | a grounding edge the measurement cannot see | $\mathrm{fp}(c) \cap \mathrm{fp}(d) = \emptyset$ |
| increment | the claim's irreducible sensitivity residual | $\mathrm{incr}(c) = \mathrm{fp}(c) \setminus \bigcup_{d \in \mathrm{rests\text{-}on}(c)} \mathrm{fp}(d)$ |
| collapse | the claim adds no sensitivity beyond its grounding | $\mathrm{incr}(c) = \emptyset$ |
