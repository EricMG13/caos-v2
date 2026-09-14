# Phase 3 exit evidence

Candidate: `codex/execute-repair-plan` at `3400b6c`. This record maps every
`docs/REPAIR_PLAN.md` Phase 3 exit check to the regression tests that
demonstrate it. It is evidence for acceptance, not acceptance: the phase is
accepted only when the handoff records the complete gate, the whole-phase
confidence review and the adversarial audit (both at actual `xhigh`) and their
remediation.

## Task slices behind this evidence

| Concern | Commits (change, review remediation) |
|---|---|
| Claims adapter retired; canonical LITE route only (3.1, §42) | `df053ee`..`d06dac9` `4c66266` `be6710a` `a8acbc6` |
| Byte dispatch, pdfminer logs kept out (3.2a) | `e292238` `31255ce` |
| Anchoring within delivered blocks (3.2e) | `d9faaac` `9ea6c41` |
| PDF word splitting (3.2b) | `83fe083` `21f1984` |
| Admission limits and extraction deadline (3.2c) | `48e0436` |
| Crop and rotation geometry, identity v2 (3.2d) | `1635f24` `fffe5c8` |
| Verified root files, delivered authority (3.3a, §45) | `5fe91b2` `d1bacb3` |
| Whole authority, bounded request (3.3b) | `8db44db` `3c59273` |
| Record v2: authority digest and lineage (3.3c) | `83d7745` `fc8378f` |
| Upstream citation register (3.3d) | `e24df79` `1bb0cfd` |
| Realistic LITE fixtures (3.4a) | `1b60263` |
| Read-model labels (3.4e, §46.3) | `ea4f2f5` |
| CP-5 held for its named LITE object (3.4b, §46.1) | `4f0879b` `8abaefd` |
| End-to-end positive and negative (3.4c, 3.4d) | `f9120d4` |
| Exit evidence and ledger (3.4f) | `8736158` |
| Confidence review: only the proven pathway executes | `147ecf7` |
| Adversarial audit: PDF extraction in a killed, budgeted child (§47) | `3400b6c` |

## Exit checks

**1. Mixed text/PDF packs are atomic; scanned/encrypted/corrupt/oversized inputs
produce specific safe outcomes.**
`test_extractor_dispatch.py`: `test_a_mixed_text_and_pdf_pack_admits_each_through_its_own_extractor`,
`test_a_mixed_pack_with_one_bad_pdf_leaves_no_rows`,
`test_an_encrypted_pdf_is_refused_as_encrypted`,
`test_dispatch_reads_the_bytes_not_the_name`,
`test_a_refusal_and_its_logs_carry_no_document_text`,
`test_pdfminer_never_logs_document_text_through_this_process`.
`test_ingestion.py`: `test_a_document_with_no_extractable_text_is_refused` (scanned).
`test_pdf_extraction.py`: `test_a_pdf_that_is_not_a_pdf_is_refused_without_quoting_it` (corrupt).
`test_admission_limits.py`: `test_an_oversized_document_is_refused_before_extraction`,
`test_a_pack_over_the_document_or_byte_ceiling_is_refused`,
`test_pages_over_the_ceiling_refuse_without_parsing_the_rest`,
`test_tokens_over_the_ceiling_refuse`, `test_tokens_over_the_ceiling_refuse_in_a_pdf_too`,
`test_extraction_past_the_deadline_refuses`,
`test_one_page_cannot_outrun_the_deadline`,
`test_a_stream_that_inflates_past_the_ceiling_refuses[intact|corrupt checksum]`,
`test_an_ordinary_flate_page_still_extracts_in_the_child`,
`test_one_line_past_the_token_ceiling_stops_building_tokens`.
*Limit:* no OCR; a scanned page refuses `SOURCE_HAS_NO_TEXT` rather than admits.

**2. Spaced glyphs, wrapped quotes, columns, repeated quotes, page rotation and
crop coordinates are covered.**
`test_pdf_extraction.py`: `test_words_separated_by_positioning_are_separate_tokens`,
`test_tracked_glyphs_within_word_margin_form_one_token`,
`test_tracked_glyphs_beyond_word_margin_split_into_letters`,
`test_widely_spaced_glyphs_refuse_the_joined_quote`,
`test_a_quote_that_wraps_two_lines_of_the_page_gets_two_rectangles`,
`test_a_quote_wrapping_within_a_column_gets_one_rectangle_per_line`,
`test_a_quote_across_the_column_gutter_is_not_located`,
`test_a_quote_repeated_on_the_page_is_ambiguous`,
`test_rotated_page_rectangles_are_top_left_in_displayed_space`,
`test_a_mediabox_origin_is_subtracted_at_every_rotation`,
`test_an_inherited_or_negative_rotate_is_the_rotation_displayed`,
`test_a_rotation_that_is_not_a_quarter_turn_is_not_readable`,
`test_text_outside_the_cropbox_cannot_be_cited`,
`test_crop_offsets_rectangles_to_the_crop_origin`,
`test_a_crop_that_misses_the_mediabox_shows_nothing`,
`test_the_pdf_identity_records_effective_layout_and_convention`,
`test_v1_pdf_extractions_still_verify_and_reanchor_as_recorded`.
*Limit:* a letter-spaced heading cannot be quoted as one word (ledger).

**3. Module B receives the exact accepted data/lineage needed from module A; a
missing/changed predecessor prevents acceptance. Undelivered pages of a
delivered source cannot be cited.**
`test_handoff_invocation.py`: `test_the_prompt_carries_exact_upstream_bytes_and_every_block`,
`test_the_lite_upstream_follows_the_pinned_edges`,
`test_upstream_that_is_not_the_identity_refuses`,
`test_every_required_reference_byte_reaches_the_prompt`,
`test_an_upstream_section_carries_its_edge_allowed_use`,
`test_cp5_prompt_names_the_lite_object_as_qa_only_with_its_full_runbook`,
`test_section_markers_cannot_be_forged_by_evidence`.
`test_record_lineage.py`: `test_full_lineage_survives_direct_only_context`,
`test_a_changed_grandparent_prevents_acceptance`,
`test_an_ancestor_rewritten_during_the_call_prevents_acceptance`,
`test_the_proof_and_deliverable_refuse_a_lineage_the_store_does_not_hold`,
`test_the_record_binds_exactly_the_delivered_authority`.
`test_canonical_runtime.py`: `test_cp5_is_not_invoked_without_an_accepted_named_lite_object`,
`test_upstream_rewritten_during_transport_is_refused_keeping_the_bill`,
`test_a_changed_root_reference_refuses_before_the_call`,
`test_an_over_ceiling_context_refuses_without_truncation_or_call`.
`test_upstream_citation_register.py`: `test_upstream_text_and_citation_register_are_never_evidence`,
`test_quote_existence_is_host_verified_support_is_left_to_cp5`,
`test_mandatory_registers_and_disclosed_conflicts_reach_consumers_unchanged`.
`test_awkward_evidence.py`: `test_a_quote_on_an_undelivered_page_of_a_delivered_source_is_refused`,
`test_a_quote_straddling_delivered_and_undelivered_lines_is_refused`,
`test_a_repeated_quote_with_one_undelivered_copy_stays_ambiguous`.
`test_read_evidence.py`: `test_a_citation_may_only_name_evidence_that_was_delivered`.
`test_lite_route_e2e_negative.py`: `test_a_wrong_upstream_or_undelivered_citation_never_reaches_the_deliverable`.
*Limit:* every module is handed every captured block; per-module evidence
selection arrives with Phase 5.

**4. Blocked/invalid output is retained only as diagnostic attempt evidence,
never as usable downstream analysis.**
`test_canonical_execution.py`: `test_a_blocked_handoff_is_billed_and_kept_as_a_diagnostic`,
`test_billing_survives_every_analytical_refusal`,
`test_one_unanchorable_quote_refuses_the_whole_handoff`.
`test_canonical_runtime.py`: `test_a_validated_blocked_handoff_ends_the_run_blocked_without_retry`,
`test_a_crash_before_the_block_commits_resumes_blocked_without_a_second_call`,
`test_a_blocked_claim_without_a_validated_diagnostic_never_ends_the_run`.
`test_upstream_citation_register.py`: `test_a_blocked_or_refused_attempt_never_reaches_a_consumer_prompt`.
`test_canonical_proof.py`: `test_a_blocked_run_proves_only_what_it_accepted`.
`test_lite_route_e2e_negative.py`: `test_a_blocked_cp_l10_ends_the_run_and_cp5_never_sees_it`,
`test_a_malformed_cp_l10_is_diagnostic_only_and_nothing_downstream_proves`,
`test_a_truncated_cp_l10_keeps_its_bill_accepts_nothing_and_never_calls_cp5`.

**5. A deterministic provider completes the route through the real runtime and
validator with realistic handoffs. Valid restricted results retain their
limitations and proceed only where the contract permits; blocked/invalid
results cannot clear downstream gates. Disclosed conflicts are preserved
without an invented resolution.**
`test_lite_route_e2e_positive.py`: `test_realistic_lite_route_completes_proves_and_freezes`,
`test_realistic_fixture_handoffs_fit_the_completion_cap`,
`test_restricted_cp_l10_limitations_survive_a_passed_cp5_into_the_deliverable`,
`test_neither_restriction_nor_conflict_is_qa_clearance`,
`test_a_disclosed_conflict_is_byte_identical_in_cp5_prompt_proof_and_deliverable_with_no_host_resolution`.
`test_canonical_runtime.py`: `test_a_lite_route_completes_through_the_real_runtime`.
`test_canonical_handoff.py`: `test_restricted_is_accepted_with_limitations`,
`test_blocked_qa_status_is_diagnostic_only`, `test_a_screening_pathway_projects_its_scope`.
`test_deliverable_canonical.py`: `test_the_page_keeps_limitations_labels_screens_and_escapes_model_text`,
`test_the_deliverable_labels_source_fact_analysis_and_no_host_calculation`,
`test_freezing_binds_both_hashes_and_verification_refuses_either_moving`.
`test_lite_route_e2e_negative.py`: `test_injected_source_text_changes_no_route_tool_file_or_identity_end_to_end`.
Other routes stay disabled: `test_canonical_execution.py`
`test_canonical_wire_on_a_disabled_route_is_refused`; `test_runtime.py`
`test_the_route_carrying_the_qa_gate_is_refused_before_any_attempt`;
`test_disabled_routes.py` `test_a_disabled_route_pins_and_governs_but_makes_no_attempt`
and `test_acceptance_refuses_a_disabled_route` over FULL, DEEP and the
adapter-module LITE portfolio pathway (`ADAPTER_ROUTES`).
*Limits:* `semantic_rules`, `document_substrings_casefold` and LITE
`required_payload_fields` are not enforced (ledger, §46.5); the host runs no
CP-5 content checks (§46.4); completion cap 32,768 unmeasured live (§46.2).

**6. No paid call or worker.** Every test above uses a deterministic provider;
the paid suite stays deselected from `make test` and `make check`, and no
worker exists before Phase 4.

## Gates

Complete `make check` at `3400b6c` (pinned Trivy 0.70.0) exit 0: backend
2291 passed, races 2 passed, frontend 157 unit, accessibility,
90 workbench, image scanned with no fixable HIGH/CRITICAL. Reviews:
[confidence review](reviews/phase-3-confidence-review.md) and
[adversarial audit](reviews/phase-3-adversarial-audit.md), both Opus 5 at
`xhigh`; acceptance is recorded in the handoff.
