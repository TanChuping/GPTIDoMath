<!-- Example 5 · a referee's voice turned on one's own approach: three objections and a conclusion · field: computational and proof complexity. Suits: algorithm design, performance limits, judging whether an approach can work at all. A reference only: write a new one in this spirit; do not send it as is or reuse its sentences. -->
Before going further, I want to raise three objections to our own approach. If they stand, what follows has to change direction.

**First, the argument may run into a known barrier.** Complexity theory has three famous ones: relativisation (Baker–Gill–Solovay), natural proofs (Razborov–Rudich) and algebrisation (Aaronson–Wigderson). A technique that works equally relative to every oracle cannot separate the classes we care about, and a proof resting on a property that is both easy to decide and shared by most functions cannot give strong lower bounds under standard cryptographic assumptions. Has our argument slipped into one of these classes without our noticing? Each needs checking, one by one.

**Second, locally sound is not globally sound.** The Unique Games Conjecture is still open, but the 2-to-2 games theorem of Khot, Minzer and Safra has shown that how reliable local tests are, and what global structure they force, are related far more subtly than intuition suggests. In our object many local conditions hold one by one, and we have not proved that together they imply the global property. That step cannot be waved through by analogy.

**Third, the evidence of difficulty may come from instances rather than structure.** Sum-of-squares lower bounds for planted clique show that some instances are hard for a whole family of algorithms, not merely for the few we happened to try. Is the difficulty we observe a feature of the object, or a limit of how we measure it?

Conclusion: before proposing any new construction, characterise the reachable structure and the real bottlenecks. Every conclusion carries a proof, or a reproducible instance with measurements, or is marked as a conjecture together with the evidence it still needs.

The full set-up and the requirements for this stage are in the shared material, which is the only authority; here I state doubts, not the problem.
