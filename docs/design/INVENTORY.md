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
| `Rail` | `ds/RailShell` idiom, new markup | all nine | 9a 9b 9c |
| `ServedRole` | new | all nine | 3a 3b 3c 4a 4b |
| `SeverityMark` | new (`DESIGN.md` glyph vocabulary) | all nine | 3a 3c 4a |
| `Panel` | `.pnl` markup from `caos.css` (the design project's panel) | all nine | 3a 3c 4a 4b |
| `Tag` | `ds/Tag` | all nine | 3a 3b 3c 4a |
| `RefusedControl` | `ds/ActionReason` + typed code | all nine | 3a 4a 4b 6a 8c |
| `RegionState` | `ds/SurfaceState` | all nine | 8a 8b |
| `MetricPassport` | new | Book, Model, Analysis | 3c 7b |
| `CitationChip` | `EvChip` styling | Analysis, Committee, Model | 3a 3c 7a 7b |
| `EvidenceDrawer` | new (`ds/useModalA11y`, opener passed) | Analysis, Book, Model | 7a |
| `FormulaBar` | `ds/FormulaBar` idiom | Analysis, Model | 3c |
| `Projection` | new | Model | 3c |
| `RouteGraph` | new | Run | 4a 4b |
| `FilingLadder` | new | Committee | 3a 3b |
| `Paper` | `ReportDoc` idiom | Committee | 3a 3b |
| `ProvenanceIndex` | new | Committee | 3b |
| `CaseRegister` | new | Directory | 5a |
| `IntakeSuggestions` | new | Directory | 5b |
| `SourcePack` | new | Upload | 5c |
| `UnavailableCapability` | new | Admin | 6b |
| `PageAlert` | new | all nine | 8b |
| `RevisionEditor` | new | Report | 6a |

Every row has a card. Nothing in this table ships without one, and nothing is drawn
that this table does not name.
