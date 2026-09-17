# Phase 4 exit evidence

Candidate: `codex/execute-repair-plan` at `0deb4a4`. This record maps every
`docs/REPAIR_PLAN.md` Phase 4 exit check to the tests that demonstrate it. It
is evidence for acceptance, not acceptance: the handoff's Phase 4 record holds
the complete gate, the whole-phase confidence review and the adversarial audit.

Python tests live in `tests/`; TypeScript unit tests in `frontend/tests/unit/`;
the real-stack journey in `frontend/tests/journey/journey.spec.ts`, run by
`tests/journey/run.py` (`make smoke-production`) against the production image,
PostgreSQL, a blob volume, the real API, the deterministic journey worker and a
test edge, on chromium, firefox and webkit (39 passed at the candidate).

## 1. One real-browser journey with PostgreSQL, immutable blobs, the real API and a deterministic provider; no Vite fixtures

Journey tests, in order:
- `journey: create a case and admit a mixed text and PDF pack`
- `journey: select the LITE route and pin the subject`
- `journey: preview and approve the source-set and research-plan gates`
- `journey: start the run and the worker completes it after one kill and restart`
- `journey: analysis shows labelled source facts, model analysis and limitations`
- `the highlight covers the rendered words of the matched text`

No fixture middleware: `test_the_image_contains_no_fixture_demo_marker_or_test_module`,
`test_no_server_module_imports_a_test_fixture`.

## 2. Every new endpoint across unauthenticated, nonmember, reader, writer, approver, revoked and administrative identities; unknown and unauthorized indistinguishable

- Section reads: `test_a_section_request_across_anonymous_nonmember_reader_writer_approver_revoked_and_admin`,
  `test_a_run_section_request_across_anonymous_nonmember_reader_writer_approver_revoked_and_admin`,
  `test_analysis_private_404_and_actor_matrix`,
  `test_unknown_unauthorised_revoked_and_malformed_case_are_one_private_404`.
- Commands: `test_every_command_across_the_seven_actors_and_a_global_reader_writer`,
  `test_create_case_actor_matrix`, `test_admission_actor_matrix`,
  `test_the_run_commands_across_the_actor_matrix`,
  `test_start_retry_and_cancel_across_the_actor_matrix`,
  `test_a_commit_time_revocation_answers_the_private_404`,
  `test_a_nonmember_upload_is_404_without_extraction`.
- Events and pages: `test_case_events_across_anonymous_nonmember_reader_writer_approver_revoked_and_admin`,
  `test_a_run_of_another_case_is_run_not_found_on_the_event_stream`,
  `test_a_page_request_across_anonymous_nonmember_reader_writer_approver_revoked_and_admin`.
- Health (no identity by design, §53.8): `test_health_needs_no_edge_token_and_no_identity`.

## 3. No impersonation through the deployed edge; no exposed dev-trust listener; CSRF/origin controls; safe rendering and CSP

- Edge and identity: `test_edge_mode_refuses_a_request_without_the_edge_token_before_routing`,
  `test_the_edge_token_never_reaches_the_app_a_log_or_a_refusal`,
  `test_edge_mode_never_believes_the_role_header`,
  `test_a_repeated_identity_header_is_not_authenticated`,
  `test_an_underscore_lookalike_identity_header_is_not_authenticated`,
  `test_production_never_trusts_role_header`,
  journey `journey: forged identity headers through the edge reach nobody else's case`,
  image `test_a_direct_forged_identity_request_without_the_token_is_refused`.
- Dev trust never reachable: `test_boot_refuses_the_trust_switch_alongside_an_edge_token`,
  `test_dev_mode_serves_only_loopback_peers_with_a_loopback_host`,
  `test_the_image_refuses_to_boot_with_the_trust_switch_and_a_token`,
  `test_the_image_without_a_token_answers_only_health`.
- CSRF and origin: `test_a_cross_site_or_same_site_api_request_is_origin_refused`,
  `test_an_unsafe_api_request_needs_the_public_origin_or_a_same_origin_fetch`,
  `test_no_response_sets_a_cookie_or_a_cors_header`,
  journey `journey: a cross-site form post through the edge changes nothing`.
- CSP and safe rendering: `test_every_response_carries_the_security_headers_and_the_policy`,
  `test_an_unhandled_fault_answers_a_secured_constant_500`,
  journey `the served policy refuses an injected inline script and the journey records no violation`.

## 4. Case switching closes/rebinds evidence; withdrawal updates an open drawer; a stale view does not advance without Reload; ordinary refresh preserves local selection

- `test_a_same_section_case_switch_closes_the_open_evidence` (R1)
- `test_withdrawal_updates_the_open_drawer_and_refuses_its_page` (R2)
- `test_a_late_response_after_a_case_switch_is_discarded` (R3)
- `test_a_nested_null_where_a_list_is_declared_is_refused`,
  `test_run_null_renders_the_defensive_empty_state_rather_than_crashing` (R4)
- `test_an_ordinary_refresh_preserves_run_node_selection_and_tab` (R5)
- `test_withdrawal_applies_to_a_stale_view_without_advancing_its_figures`,
  journey `a stale view holds its figures until Reload`
- `test_focus_returns_to_the_section_heading_when_the_opener_disappears`,
  journey `Escape returns focus to the chip that opened the drawer`

## 5. Report/Committee text byte-for-byte preserved; refused Book data nowhere in derived notes

Report, Committee and Book stay unavailable in every mode (§50.5); the dormant
sections carry the fixes so they cannot return with the defects:
- `test_report_text_is_preserved_byte_for_byte_with_an_unmatched_figure` (R6)
- `test_committee_paper_inserts_no_figure_absent_from_its_text` (R6)
- `test_book_notes_show_no_value_from_a_refused_snapshot` (R7)

## 6. Kill/restart the worker around reservation, provider return and acceptance; no duplicate acceptance; browser reconnect resumes events and stops after consumed terminal state

- Around reservation: `test_a_reclaimed_lease_refuses_the_stale_reservation_and_no_call_is_made`,
  `test_a_reclaimed_lease_refuses_the_stale_start_attempt`.
- Around provider return: `test_worker_sigkilled_after_provider_return_restarts_without_a_second_call`,
  `test_a_stale_worker_returning_after_reclaim_keeps_its_bill_and_accepts_nothing`.
- Around acceptance: `test_a_claim_during_an_in_flight_acceptance_takes_nothing`,
  `test_two_connections_completing_one_run_produce_one_terminal_event`,
  `test_a_stale_worker_cannot_end_the_run`.
- Real stack: journey `journey: start the run and the worker completes it after one kill and restart`.
- Events: `test_resume_delivers_strictly_after_the_composite_marker`,
  `test_a_marker_that_cannot_be_used_resumes_from_the_heads_over_http`,
  `test_a_consumed_terminal_marker_never_rereads_or_redelivers_the_run_tail`,
  journey `a dropped stream resumes after its Last-Event-ID`.

## 7. The production image boots with disposable data; readiness, static deep links and the real API work; no fixture middleware

- `test_the_image_serves_every_section_deep_link_and_the_real_api`
- `test_readiness_is_503_while_the_database_is_stopped_and_200_after`
- `test_the_image_contains_no_fixture_demo_marker_or_test_module`
- `test_the_image_worker_exits_without_provider_and_price`
- journey `journey: every section deep link loads through the edge with its query`
- `test_the_deep_link_sections_are_the_workspace_sections`

## Accepted limits carried forward

The CLAUDE.md "Repair Phase 4" ledger, and the adversarial audit's two recorded
P3s (unauthenticated readiness codes; the smoke credential in
`compose.smoke.yaml`). The journey proves the worker's exit-after-accept on its
first engine only.
