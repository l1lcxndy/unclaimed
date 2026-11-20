Drop text-based benefit-program PDFs here, then run: python ingest.py

Scanned (image-only) PDFs won't work; they have no extractable text.
The program name comes from the file name (farm-income-support.pdf -> "Farm Income Support").
Optional: add meta.json here to set names, region and category per file:
{"farm-income-support.pdf": {"program_name": "Farm Income Support", "region": "North", "category": "agriculture"}}
With more than one region, the page asks where the person lives and only searches that region's programs.

Optional: real_cases.jsonl here holds eval cases for your own PDFs (format as evals/cases.jsonl, plus "region").
Run them with: python evals/run_eval.py --real
PDFs, meta.json and *.jsonl in this folder are kept out of git.

Optional held-out test: put new PDFs, meta.json and cases.jsonl in docs/heldout/ (also kept out of git),
write the cases before running anything, then run once with: python evals/run_eval.py --heldout
