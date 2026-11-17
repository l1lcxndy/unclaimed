# v6: a required "who it's for" check

v5 scored 24/25 fictional but 6/14 real (baseline 9/14). On long real documents the model listed only paperwork
rules (land-record dates, certificates) as who_can_apply, all "unknown", and never the core rule
("landholding farmer families"), so the "fits at least one rule" check dropped the program.

Change: each program gets a required `who_its_for` group check that must be "yes". The "fits at least one
who_can_apply rule" condition is gone, so unknown paperwork rules no longer drop a program; a failed rule or a
matching exclusion still does. Exclusions now share the same `GroupCheck` shape (`excluded_group` -> `group`).
