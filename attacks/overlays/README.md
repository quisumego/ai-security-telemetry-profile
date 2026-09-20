# Attack overlays

Material a scenario puts in front of the agent for that scenario's sessions
only. Documents under `<scenario>/corpus/` join the retrieval index through
`overlay_dirs`; pages in `<scenario>/web_fixtures.yaml` are served by
`fetch_url` through `extra_pages`. Nothing here is written into `lab/corpus/`
or `lab/web_fixtures.yaml`, which stay the benign estate the M3 sessions read.

Every host and address here is under `northgate-recoveries.invalid`, which
RFC 2606 reserves and which cannot resolve. Northgate Recoveries is the single
fictional outside party for the whole corpus.

This directory is inside the corpus digest, so an edit after the `freeze-m2`
tag shows up in every later manifest.

No file here may contain a canary value. `tests/test_corpus.py` scans this
directory. The documents themselves are listed in `OVERLAY-SPEC.md` and are
authored and reviewed by the owner before the freeze.
