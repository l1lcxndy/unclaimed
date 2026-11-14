# Same code as v2 on qwen2.5vl:7b, which fits fully in the 8 GB GPU

- Model only (`MODEL_NAME`): `qwen2.5vl:7b` (already downloaded, 5.3 GB in VRAM) instead of `qwen3:14b-q4_K_M` (~9 GB, spills to CPU). No code or prompt change.
- Why: v2 answers took a 78 s median. A benchmark on c11 showed ~all time is output generation at 7 tok/s (14B partly on CPU); the 7B model generates at 51 tok/s, 10 s vs 190 s warm on the same case.
