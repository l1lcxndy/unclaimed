# Each program's best chunk before any program's second chunk

- Retrieval (`rag/store.py`): after merging the per-part searches, results are reordered so every program's top chunk comes before any program's second chunk, then cut to 10. Prompted by real documents: one 42-page publication (123 chunks) and multi-chunk fact sheets filled all 10 slots, so one-page programs ranked 4th-7th were dropped (2 of 4 real-doc spot checks missed).
- Retrieval-only check: eval cases still 0 expected programs missed; real-doc spot checks 4/4 (was 2/4).
- Also in this version, no effect on the eval: optional `region` filter on retrieval, and the loader skips unreadable PDFs.
