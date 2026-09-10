import { INITIAL, accepts, bind, issue, navigate, release, ticket } from "@/app/authority";

describe("the authority machine", () => {
  test("test_route_replay_discards_late_response_for_left_case", () => {
    const left = navigate(INITIAL, "CASE-2026-CVNA01");
    const sentForLeft = ticket(left);
    const current = navigate(left, "CASE-2026-HTZ02");
    // The response for the case the user left arrives after they moved on.
    expect(accepts(current, sentForLeft)).toBe(false);
    expect(accepts(current, ticket(current))).toBe(true);
    // A back navigation is a new seq: the earlier ticket is still late.
    const back = navigate(current, "CASE-2026-CVNA01");
    expect(accepts(back, sentForLeft)).toBe(false);
  });

  test("a later request for the same case supersedes an earlier one", () => {
    const first = issue(navigate(INITIAL, "CASE-2026-CVNA01"));
    const sentFirst = ticket(first);
    const second = issue(first);
    // The first response arrives after the second was issued: late, discarded.
    expect(accepts(second, sentFirst)).toBe(false);
    expect(accepts(second, ticket(second))).toBe(true);
  });

  test("a response for the same case under an earlier seq is late", () => {
    const first = navigate(INITIAL, "CASE-2026-CVNA01");
    const again = navigate(first, "CASE-2026-CVNA01");
    expect(accepts(again, ticket(first))).toBe(false);
  });

  test("test_book_binds_one_snapshot_per_compared_case", () => {
    const left = bind(INITIAL, "CASE-2026-CVNA01", "snp_cvna_q2_2026");
    expect(left.refusal).toBeNull();
    const right = bind(left.authority, "CASE-2026-CHTR03", "snp_chtr_q2_2026");
    expect(right.refusal).toBeNull();
    // A late response carrying a different snapshot for either case is refused.
    const lateLeft = bind(right.authority, "CASE-2026-CVNA01", "snp_cvna_q1_2026");
    expect(lateLeft.refusal?.code).toBe("SNAPSHOT_MISMATCH");
    expect(lateLeft.authority.bound["CASE-2026-CVNA01"]).toBe("snp_cvna_q2_2026");
    const lateRight = bind(right.authority, "CASE-2026-CHTR03", "snp_chtr_q1_2026");
    expect(lateRight.refusal?.code).toBe("SNAPSHOT_MISMATCH");
    // The same snapshot again is not a second identity.
    expect(bind(right.authority, "CASE-2026-CVNA01", "snp_cvna_q2_2026").refusal).toBeNull();
  });

  test("a binding moves only through an explicit release", () => {
    const held = bind(INITIAL, "CASE-2026-CVNA01", "snp_cvna_q2_2026").authority;
    const moved = bind(release(held, "CASE-2026-CVNA01"), "CASE-2026-CVNA01", "snp_cvna_q3_2026");
    expect(moved.refusal).toBeNull();
    expect(moved.authority.bound["CASE-2026-CVNA01"]).toBe("snp_cvna_q3_2026");
  });
});
