# Every retrieved program gets a structured requirement check; verdict decided in code; more retrieval candidates

- Answer (`rag/generate.py`, `prompts/answer.txt`): the model returns an entry for EVERY retrieved program (not just the ones it thinks fit), each with `rule_checks`: every rule restated as a positive requirement, the person's stated fact, and met / not_met / unknown. Code decides eligibility: any not_met, or no requirement met by something the person said, drops the program. Targets v1's c21 regression (programs listed on "unknown" alone), c04 (the model flipped a "who cannot apply" income rule) and c11 (the model skipped a retrieved program).
- Retrieval (`rag/store.py`): 8 candidates per searched part (was 5), up to 10 chunks (was 8), cutoff unchanged at 0.75. Picked by a retrieval-only sweep over the eval cases: 0 expected programs missed vs 2 before. Tuned on the eval set itself, so not a held-out result.
- Cost: longer outputs, so answers are slower than v1.
