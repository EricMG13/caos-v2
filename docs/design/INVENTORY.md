# Component inventory

From the design cards to the components Phase 9 writes. `ds/` means the primitive
is vendored from the predecessor at `f454c65` (`frontend/src/ds/VENDORED.md` records
the source path and digest); `new` means it is written against the tokens.

| Component | Source | Sections | Card |
|---|---|---|---|
| `Ribbon` | new | all nine | 3a 3b 3c 4a 4b |
| `DecisionBrief` | new | all nine | 3a 3b 3c 4a 4b |
| `SectionTabs` | new | all nine | 3a 3b 3c 4a 4b |
| `VerdictStrip` | new | all nine | 3a 3b 3c 4a 4b |
| `Rail` | `ds/RailShell` idiom, new markup | all nine | 3a 3b 3c 4a 4b |
| `ServedRole` | new | all nine | 3a 3b 3c 4a 4b |
| `SeverityMark` | new (`DESIGN.md` glyph vocabulary) | all nine | 3a 3c 4a |
| `Panel` | `ds/Panel` | all nine | 3a 3c 4a 4b |
| `Tag` | `ds/Tag` | all nine | 3a 3b 3c 4a |
| `RefusedControl` | `ds/ActionReason` + typed code | all nine | 3a 4a 4b |
| `RegionState` | `ds/SurfaceState` | all nine | Turn 8 |
| `MetricPassport` | new | Book, Model, Analysis | 3c · Turn 7 |
| `CitationChip` | `EvChip` styling | Analysis, Committee, Model | 3a 3c |
| `EvidenceDrawer` | new (`ds/useModalA11y`, opener passed) | Analysis, Book, Model | Turn 7 |
| `FormulaBar` | `ds/FormulaBar` idiom | Analysis, Model | 3c |
| `Projection` | new | Model | 3c |
| `RouteGraph` | new | Run | 4a 4b |
| `FilingLadder` | new | Committee | 3a 3b |
| `Paper` | `ReportDoc` idiom | Committee | 3a 3b |
| `ProvenanceIndex` | new | Committee | 3b |

Rows without a card id are drawn in the turn named in `DESIGN_HANDOFF.md`; no row
ships without one.
