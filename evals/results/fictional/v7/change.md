# v7: household member in the "who it's for" check, names matched in code

v6: real 11/14 (best so far), fictional 21/25 (v5 24/25). All four new fictional misses (c10, c11, c25) were
programs meant for a household member: the model marked the person (a husband or father) outside "mothers of
children under six" or "pregnant women". Real r09 failed on names ("WIC Program" for "WIC").

Changes:
- `who_its_for` now names a `household_member` first (the person, their wife, their child...) and checks that
  member (`member_is_in_group`), so the schema itself asks about the household, not only the prompt.
- `match_names()` renames each listed program to the retrieved program it refers to (exact, containment,
  then close match), and drops duplicates and names matching nothing retrieved. Done in code, so it holds for
  any model.
