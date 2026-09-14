// The wire this section reads: "legacy" until its slice cuts it over to v1
// (brief 4.1, slices 4.1h-j). The transport reads nothing else to decide.
export const WIRE: "legacy" | "v1" = "legacy" as const;
