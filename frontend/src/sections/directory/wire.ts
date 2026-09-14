// The wire this section reads: cut over to v1 in slice 4.1h. The transport
// reads nothing else to decide.
export const WIRE: "legacy" | "v1" = "v1" as const;
