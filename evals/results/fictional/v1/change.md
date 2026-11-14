# Search each part of the situation separately; rule-by-rule eligibility check with code-enforced drop

- Retrieval (`app.py`, `rag/store.py`): the question is split into parts ("rideshare driver", "one kid aged 3") and each part is searched alongside the whole question. Every part's best hits are kept first, so one strong need can't crowd out another. Fixes the baseline misses in c04, c10 and c11, where the needed program was never retrieved.
- Answer (`rag/generate.py`, `prompts/answer.txt`): each program now carries a `rule_check` (every rule, the person's fact, met / not met / unknown) and an `eligibility` verdict written before the rest of the card. Code drops any program marked `fails_a_rule`. Fixes baseline c14, c17, c18 and c19, where the model listed programs while saying the person didn't qualify.
- Prompt also says household members count (a spouse or child can claim). No test-case-specific examples in the prompt.
