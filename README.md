# BODI — Grid Docket collector

Cloud collector for the Grid Docket Weekly brief (large-load and large-generation regulatory and market tracking).

- `probe/` — reachability test: which docket systems the GitHub Actions runner can reach, what robots.txt permits, and which API calls each portal makes.
- Results are committed to `probe/results/latest.md` and `latest.json`.

The collector honors robots.txt, identifies itself honestly, rate-limits per host, and never attempts to evade bot defenses.
