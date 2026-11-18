# v10: a long document's second slot goes to its eligibility passage

v9 (an extra eligibility search for every retrieved program) scored 5/11 and was reverted: the added passages
took room from programs that matched the person. Its diagnosis still held: in the 42-page tax booklet (123
chunks) the rules list on page 2 never reached the model, because tables and worked examples match the person's
words better.

Change: only for documents longer than 10 chunks, the program's second slot goes to its passage that best
answers "Am I eligible? Who can get this and what are the requirements to qualify" (moved up if it was found but
ranked too low, added if not). The program keeps the same number of slots, so other programs lose nothing.
Short documents are untouched: retrieval for all 25 fictional cases is identical to v8 (checked by diff).

Result (real smoke, 7 cases): 6/7. r09 passes for the first time since v4; r01, r02, r05, r12, r13 still pass.
r10 still fails, now on reasoning rather than retrieval: the model sees the rules list but applies the income
limit meant for people without children to a parent ("no"), and marks "taxpayers with earned income and
qualifying children" unknown.
