# v9: every retrieved program brings its own eligibility passages

v8: smoke 9/9, but real r04, r09 and r10 still failed. All three involve documents where the passages matching
the person's words are tables, worked examples or intro text, so the passage saying who qualifies never reached
the model (a 42-page tax booklet has 123 chunks; its rules list on page 2 was never retrieved).

Change: after the normal search, each program found is searched once more, inside that program only, for
"Am I eligible? Who can get this and what are the requirements to qualify". Its top two passages are interleaved
with the normal hits (after each program's best match), within the same 10-chunk limit. No new program can come
in this way, so an irrelevant question still retrieves nothing. Works for any document; the query wording was
picked by checking which phrasing ranks rules passages first across six real documents.

Result (smoke, 11 cases): 5/11, against 9/9 for v8 on the same kinds of cases. Fixed r09, but r05, c10, c11 and
c12 regressed and r04, r10 still failed. The extra passages took slots from the second passage of programs that
matched the person and gave them to loosely matching programs. Reverted; not kept.
