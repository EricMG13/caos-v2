// The chip shows `D-04 p.68 ¶2`, not a document name. Its click passes the
// opener to the one evidence drawer (IA_SPEC.md 4.3, 5).
import type { MouseEvent } from "react";
import { useEvidence } from "./EvidenceContext";
import type { Citation } from "@/wire";

export function CitationChip({
  citation,
  linked = false,
}: {
  citation: Citation;
  linked?: boolean;
}) {
  const { openCitation, activeChip } = useEvidence();
  const open = activeChip === citation.chip;
  return (
    <button
      type="button"
      className={`chip${linked ? " linked" : ""}`}
      aria-label={`Evidence ${citation.chip}`}
      aria-expanded={open}
      aria-haspopup="dialog"
      data-chip={citation.chip}
      onClick={(event: MouseEvent<HTMLButtonElement>) =>
        openCitation(citation, event.currentTarget)
      }
    >
      {citation.chip}
    </button>
  );
}
