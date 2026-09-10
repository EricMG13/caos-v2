// Every governed action renders visible and, when refused, refused with its
// typed code and what clears it. aria-disabled, never disabled, never hidden
// (IA_SPEC.md 2; DESIGN.md "Rules with teeth").
import type { ReactNode } from "react";
import { ActionReason } from "@/ds/ActionReason";
import type { Refusal } from "@/wire";

/** A governed action nothing in this build performs is refused, not simulated. */
export const ACTION_UNPLACED: Refusal = {
  code: "ACTION_UNPLACED",
  clears: "the backend phase that owns this action lands (docs/REBUILD_PLAN.md)",
};

export function refusalText(refusal: Refusal): string {
  return `${refusal.code} — clears when ${refusal.clears}`;
}

export function RefusedControl({
  refusal,
  onClick,
  className = "",
  reasonDisplay = "inline",
  children,
  ...rest
}: {
  refusal: Refusal | null;
  onClick?: () => void;
  className?: string;
  reasonDisplay?: "inline" | "hidden";
  children: ReactNode;
  "aria-label"?: string;
}) {
  const effective = refusal ?? (onClick ? null : ACTION_UNPLACED);
  return (
    <ActionReason
      reason={effective ? refusalText(effective) : null}
      reasonDisplay={reasonDisplay}
      onClick={onClick}
      className={`${className}${effective ? " refused" : ""}`}
      data-refusal={effective?.code}
      {...rest}
    >
      {children}
    </ActionReason>
  );
}

/** The refusal on its own, for a ladder step or a panel foot. */
export function RefusalNote({ refusal }: { refusal: Refusal }) {
  return (
    <div className="refusal" data-refusal={refusal.code}>
      <code>{refusal.code}</code>
      <div className="cl">
        Clears when <b>{refusal.clears}</b>
      </div>
    </div>
  );
}
