# Phase 2 exit evidence

Candidate: `codex/execute-repair-plan` at `e2da629`. This record maps every
`docs/REPAIR_PLAN.md` Phase 2 exit check and the handoff's Claude hook
prerequisite to the regression tests that demonstrate it. It is evidence for
acceptance, not acceptance: the phase is accepted only when the handoff records
the complete gate, the whole-phase confidence review and the adversarial audit
(both at actual `xhigh`) and their remediation.

## Task slices behind this evidence

| Concern | Commits (change, review remediation) |
|---|---|
| Fresh authority at artifact acceptance (17d3) | `829d863` `261d143` `17645f3` `1e720db` |
| Host-derived evidence, gate and upstream (17e) | `9f299a4` `595c4b2` `209b0ef` `6c32c99` `c88c579` `acf334d` |
| Proof and provenance read pins and stored calls (17f) | `4cc94c8` `8f06c68` `a8cc369` `2f12a2c` |
| One accepted owner per run node | `4facb0f` `036a104` |
| BLOCKED terminal state (§39, F02) | `b401253` `ad8e931` `e2da629` |
| QA clearance releases CP-6 only on `Passed` (F03) | `ebf6266` `ad312f9` |
| Priced reservations (§40, F06) | `ba04982` `1d0a8dd` |
| Claude hooks read the stdin event | `fea7543` `84bb6ce` |

## Exit checks

**1. Unapproved, changed-preview, wrong-route, wrong-build, wrong-case and
changed-input requests cause no provider call.**
`test_runtime.py`: `test_an_unapproved_run_never_reaches_the_provider`,
`test_a_historical_route_without_a_complete_input_never_reaches_the_provider`,
`test_each_current_gate_is_required_before_work[gate × missing|preview|input]`,
`test_live_authority_is_required_before_work[revoked|downgraded|withdrawn]`,
`test_the_final_pre_call_check_sees_a_late_revocation`,
`test_caller_identity_cannot_replace_stored_authority[route|bundle]`.
`test_gates.py`: `test_arbitrary_expected_digests_refuse`,
`test_use_checks_both_stored_digests`, `test_preview_is_exact_immutable_captured_content`,
`test_changed_live_document_identity_reopens_both_gates`,
`test_approval_cannot_be_transplanted[run|gate|case]`.
`test_execution_input.py`: `test_both_exact_approvals_are_required`,
`test_current_bundle_and_adapter_are_distinct_from_historical_readability`,
`test_execution_requires_an_actual_bundle_instance`.
`test_run_inputs.py`: `test_native_foreign_keys_bind_actual_case_source_and_route`,
`test_changed_host_or_research_refuses_replay_but_history_is_readable`.
`test_execution_freshness.py`: `test_whole_route_mismatch_keeping_the_node_is_refused`,
`test_direct_executor_refuses_a_mismatched_module_before_any_call`,
`test_direct_executor_refuses_a_moved_node_before_any_call`,
`test_upstream_with_foreign_envelope_identity_is_refused_before_any_call`,
`test_module_provider_never_delivers_a_block_outside_the_captured_set[other_case]`,
`test_check_attempt_and_runtime_recheck_transport_authority_before_use` (19 changes × 2 entries).
`test_pricing.py`: `test_a_price_for_another_model_refuses_before_any_attempt`.
*Limit:* a changed preview is proven at use by a stored-digest mismatch and by
live-identity reopening; wrong-case is proven at approval, schema and evidence
level rather than by a runtime run of another case's pins.

**2. Different research briefs cannot share the same execution input identity.**
`test_run_inputs.py`: `test_every_bound_component_changes_fingerprint_with_other_identity_fixed`,
`test_changed_host_or_research_refuses_replay_but_history_is_readable[research]`,
`test_research_exact_ordering_depth_count_and_utf8_size`,
`test_research_refuses_without_coercion_or_private_diagnostics`.

**3. A post-pin source cannot support an old run; a withdrawal during an
in-flight call prevents fresh acceptance from treating it as live evidence.**
`test_run_evidence.py`: `test_equal_bytes_do_not_admit_a_post_pin_source`,
`test_run_read_keeps_captured_membership_after_later_admission`,
`test_run_read_compares_each_captured_current_identity`.
`test_orchestration_proof.py`: `test_a_source_admitted_after_the_pin_cannot_support_the_proof`,
`test_a_readmitted_copy_of_a_withdrawn_pinned_source_does_not_revive_the_proof`,
`test_a_withdrawn_source_takes_the_proof_with_it`.
`test_execution_freshness.py`: `test_a_change_waits_for_the_context_unit_and_is_caught_after_the_call[withdraw]`,
`test_accept_refuses_what_changed_after_the_bill_committed[withdraw_cited|withdraw_uncited]`.

**4. Two first approvals serialize; revocation and governed writes have a
defined, tested commit order; no unauthorized late write or raw race exception
escapes.**
`test_case_ordering.py`: `test_two_first_approvals_serialize`,
`test_membership_change_first_refuses_waiting_approval`,
`test_membership_change_first_refuses_waiting_action`,
`test_approval_first_holds_authority_until_commit`,
`test_governed_first_holds_authority_until_commit`,
`test_mutations_lock_case_before_dependent_rows`,
`test_governed_failure_rolls_back_whole_unit_and_releases_lock`.
`test_execution_freshness.py`: `test_accept_waits_for_a_case_lock_holder_then_sees_its_revocation`,
`test_accept_holds_the_case_lock_from_the_authority_check_to_the_insert`.
`test_gates.py`: `test_approval_failure_is_atomic_and_releases_locks`.
`test_postgres_races.py`: `test_two_connections_completing_one_run_produce_one_terminal_event`.

**5. A blocked valid route remains blocked, and blocked CP-5 does not release
CP-6.**
`test_runtime.py`: `test_a_blocked_cp5_does_not_release_cp6[Blocked|Passed]`.
`test_route_resolution.py`: `test_qa_gate_blocks_cp6_until_cp5_accepted` (5 QA values).
`test_loop_charges.py`: `test_a_node_the_gate_blocked_costs_no_call_and_no_charge`
(ends BLOCKED; a second `run_route` refuses `RUN_NOT_RUNNING` with no call or charge).
`test_run_stream.py`: `test_a_blocked_run_refuses_new_attempts`,
`test_a_blocked_run_closes_the_stream_too`.
`tests/probes/f02_false_completion.py` reports `BLOCKED`.

**6. Two workers/retries cannot accept different authoritative results for the
same node generation; late responses after cancellation are recorded as
outcomes, not accepted analysis.**
`test_accepted_owner.py` (6 tests, including the provably concurrent race and
the atomic refusal of a populated upgrade holding duplicate owners).
`test_execution_freshness.py`: `test_exact_replay_never_rechecks_authority_or_duplicates`.
`test_execution_billing.py`: `test_late_known_refusal_is_billed_after_inflight_run_cancellation`.
`test_call_outcomes.py`: `test_late_outcome_is_durable_without_analytical_acceptance`,
`test_acceptance_rechecks_termination_after_outcome_commit`.
*Limit:* Phase 2 has no cancel command; a terminal FAILED/COMPLETE/BLOCKED
transition stands in for cancellation.

**7. Actual charge above estimate consumes capacity; NaN/infinity/negative/
boolean amounts refuse; timeout/crash preserves possible spend.**
`test_pricing.py`: `test_an_overrun_charge_stops_the_next_node_before_its_call`,
`test_reservation_is_the_worst_case_charge_for_the_configured_model`,
`test_invalid_prices_refuse`, `test_a_free_price_refuses_rather_than_reserving_nothing`.
`test_budget.py`: `test_known_charge_raises_exposure_but_never_releases_a_reservation`,
`test_invalid_money_refuses_at_each_store_entrance`,
`test_crash_after_remote_completion_keeps_its_reservation`,
`test_a_retry_without_provider_idempotency_reserves_again`.
`test_execution_billing.py`: `test_native_refusal_records_only_independently_known_money`.
`test_call_outcomes.py`: `test_record_outcome_keeps_unknown_exposure_and_known_overrun`.
`test_runtime.py`: `test_a_failed_attempt_leaves_its_row_and_its_reservation`.
`test_qualification_harness.py`: `test_unrun_attempts_separate_possible_spend_from_no_call_and_known_charge`.

**Hook prerequisite.** `test_claude_hooks.py` (41 tests): forbidden commands
refused, ordinary commands allowed, malformed events refused without echo, the
formatter limited to authored files with vendor bytes untouched, and the real
settings command deciding with and without the repo venv.

## Gates observed at the candidate

- Serial backend gate (`make -j1 check-postgres lint types test test-postgres-races security`)
  at `1d0a8dd`: 1892 passed, 3 live deselected, races 2 passed, lint, types,
  Bandit, pip-audit and gitleaks clean.
- Complete `make check` at `96e27ed` with the pinned Trivy 0.70.0 (official
  macOS-ARM64 release, SHA-256 `68e543c5…b838a` matching the published
  checksums): exit 0. Backend 1892 passed and races 2 passed; security clean;
  frontend 157 unit tests; accessibility; 90 browser workbench tests; image built
  and scanned with no fixable HIGH/CRITICAL findings.
- Whole-phase confidence review and adversarial audit at actual `xhigh`:
  complete, remediated in `118c685` and `b4298dc`, and the complete gate rerun
  green at `b4298dc` (see the handoff's Phase 2 acceptance record and
  `docs/reviews/`).
