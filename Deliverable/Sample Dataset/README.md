# Sample Dataset

This directory intentionally contains no duplicate dataset files.

QI Sentinel uses synthetic, platform-shaped control-plane fixtures rather than a separate tabular sample dataset. The canonical synthetic inputs are maintained with the runnable source project:

- Seeded platform artifacts: [`../Src/mock-platform/`](../Src/mock-platform/)
- Clean baseline artifacts: [`../Src/tests/fixtures/baseline/mock-platform/`](../Src/tests/fixtures/baseline/mock-platform/)
- Synthetic measure specifications: [`../Src/specs/synthetic-2026/`](../Src/specs/synthetic-2026/)
- Seed definitions and expected dispositions: [`../Src/tests/fixtures/seeds.json`](../Src/tests/fixtures/seeds.json)

Keeping those files in one canonical location prevents copied samples from drifting away from the scanner and test inputs. Every artifact is synthetic; real member data, PHI, licensed measure text, and production exports must not be added here.
