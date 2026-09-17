# Feature 2 Flowchart: Evidence Ingestion & Citation Anchoring

**Date:** 2026-09-15
**Feature:** Evidence Ingestion & Citation Anchoring
**Scope:** Document pack preparation, PDF sandboxed parsing, tokenization, content-addressed storage, atomic pack admission, fail-closed block reads, and coordinate-anchored citation verification (Invariant 11).

---

## 1. Sources Consulted

- `server/api/commands/cases.py:84-89, 141-271` — `admit_sources` route handler, `_upload_envelope`, `_admission_documents`, `_bounded`, `_release_read`, `_peek`, and governed `run_command`.
- `server/evidence/ingest.py:1-411` — `admit_pack`, `prepare_pack`, `admit_prepared`, `_check_pack_limits`, `_extract`, `_prepare`, `_digest`, `_admit_one`, `_store_tokens`, `_blocks`, `block_ids_by_line`, `_store_blocks`.
- `server/evidence/extract.py:1-261` — `Token`, `AdmissionLimits`, `DEFAULT_LIMITS`, `ExtractorIdentity`, `Extractor`, `ExtractorDispatch`, `dispatch_by_content`, `PlainTextExtractor`, `_line_tokens`, `_words`.
- `server/evidence/pdf.py:1-525` — `PdfExtractor`, `page_frame`, `_in_child`, `_answer`, `_frame_answer`, `walk_pages`, `_pages`, `_crop_frame`, `_page_crop`, `_line_tokens`, `_runs`, `_Inflater`, `child_main`.
- `server/evidence/page.py:1-255` — `read_page`, `PageRead`, `_rows`, `_identity`, `_document`, `_frame`, `_text_frame`, `_view`.
- `server/evidence/read.py:1-139` — `read_evidence`, `read_block`, `read_run_block`, `_fetch_block`, `_is_block_id`, `Block`.
- `server/evidence/citations.py:1-288` — `anchor_citation`, `verify_citations`, `citation_candidates`, `_locate`, `_unique_run`, `_match_at`, `_rectangles`, `_page_tokens`, `_line_blocks`, `_document_sha256`, `Rect`, `Citation`, `AnchoredCitation`, `TokenIndex`.
- `server/api/reads/evidence.py:1-106` — `read_evidence_page`, `run_path`, `_source`, `_page`.
- `server/api/reads/upload.py:1-109` — `read_upload`, `case_path`.

---

## 2. Primary Execution Flowchart

```mermaid
flowchart TD
    %% Entry Point
    HTTP_REQ["HTTP POST /api/v1/cases/{case_id}/sources<br/>server/api/commands/cases.py:206"] --> ENV_CHK["_upload_envelope<br/>server/api/commands/cases.py:141"]

    %% Request Validation & Streaming
    ENV_CHK -->|"Valid Content-Length & multipart"| REL_TX["_release_read<br/>server/api/commands/cases.py:157"]
    ENV_CHK -->|"Declared length > 101MB or invalid"| REF_413["Refusal: SOURCE_TOO_LARGE / REQUEST_INVALID<br/>server/api/commands/cases.py:151"]

    REL_TX --> PARSE_DOCS["_admission_documents (_bounded stream)<br/>server/api/commands/cases.py:164"]
    PARSE_DOCS -->|"Stream > declared or malformed"| REF_REQ["Refusal: REQUEST_INVALID<br/>server/api/commands/cases.py:174"]
    PARSE_DOCS -->|"Extracted list[Document]"| PEEK_IDEM["_peek (find_receipt)<br/>server/api/commands/cases.py:260"]

    %% Idempotency Peek
    PEEK_IDEM -->|"Receipt found & digest matches"| REPLAY_RESP["command_response (Replayed SourcesAdmitted)<br/>server/api/commands/cases.py:231"]
    PEEK_IDEM -->|"Receipt found & digest mismatch"| REF_REUSE["Refusal: IDEMPOTENCY_KEY_REUSED<br/>server/api/commands/cases.py:229"]
    PEEK_IDEM -->|"No receipt (first attempt)"| PREP_PACK["prepare_pack<br/>server/evidence/ingest.py:116"]

    %% Preparation Stage (In-Memory, No Locks)
    subgraph PREPARATION ["Preparation Stage (Unprivileged, Pure Compute)"]
        PREP_PACK --> CHK_LIMITS["_check_pack_limits<br/>server/evidence/ingest.py:177"]
        CHK_LIMITS -->|"Doc count > 50 or total bytes > 100MB"| REF_PLARGE["Refusal: SOURCE_TOO_LARGE<br/>server/evidence/ingest.py:186"]
        CHK_LIMITS -->|"Passes pack limits"| EXTRACT_LOOP["_extract (per document)<br/>server/evidence/ingest.py:196"]

        EXTRACT_LOOP --> DISPATCH["dispatch_by_content<br/>server/evidence/extract.py:149"]
        DISPATCH -->|"Header %PDF-"| PDF_EXT["PdfExtractor.extract<br/>server/evidence/pdf.py:121"]
        DISPATCH -->|"Plain text / UTF-8"| TXT_EXT["PlainTextExtractor.extract<br/>server/evidence/extract.py:189"]

        PDF_EXT --> CHILD_PROC["_in_child (python -I sandbox)<br/>server/evidence/pdf.py:159"]
        CHILD_PROC -->|"Stream > max_decoded_bytes"| REF_INFLATE["Refusal: SOURCE_TOO_LARGE<br/>server/evidence/pdf.py:517"]
        CHILD_PROC -->|"Timeout > deadline"| REF_TIMEOUT["Refusal: SOURCE_EXTRACTION_TIMEOUT<br/>server/evidence/pdf.py:181"]
        CHILD_PROC -->|"Tokens JSON"| TOKENS_RET["_answer: list[Token]<br/>server/evidence/pdf.py:201"]

        TXT_EXT --> TOKENS_RET
        TOKENS_RET --> CHK_EMPTY{"Any tokens empty?<br/>server/evidence/ingest.py:145"}
        CHK_EMPTY -->|"Yes (scanned PDF)"| REF_NO_TXT["Refusal: SOURCE_HAS_NO_TEXT<br/>server/evidence/ingest.py:150"]
        CHK_EMPTY -->|"No"| PACK_PREP["_prepare & _blocks<br/>server/evidence/ingest.py:247"]
        PACK_PREP --> BLOCK_ORD["block_ids_by_line (b000000...)<br/>server/evidence/ingest.py:387"]
        BLOCK_ORD --> DIGESTS["_digest (output_sha256 & extraction_sha256)<br/>server/evidence/ingest.py:267"]
        DIGESTS --> RET_PREP["PreparedPack ready<br/>server/evidence/ingest.py:156"]
    end

    %% Governed Execution Stage (Transaction + Case Lock)
    RET_PREP --> RUN_CMD["run_command (ADMIT_SOURCES)<br/>server/store/commands.py:180"]

    subgraph GOVERNED ["Governed Unit (DB Transaction + Case Lock)"]
        RUN_CMD --> ADMIT_PREP["admit_prepared<br/>server/evidence/ingest.py:164"]
        ADMIT_PREP --> REQ_CASE["_require_case<br/>server/evidence/ingest.py:298"]
        REQ_CASE --> LOCK_CASE["lock_case (SELECT FOR UPDATE)<br/>server/store/cases.py:42"]
        LOCK_CASE --> ADMIT_ONE["_admit_one (for each _Packed)<br/>server/evidence/ingest.py:306"]

        %% Side Effects
        ADMIT_ONE --> BLOB_PUT["[IO Side Effect] blobs.put(data)<br/>server/blobs.py:47"]
        BLOB_PUT --> DB_SRC["[DB Write] INSERT INTO sources<br/>server/evidence/ingest.py:310"]
        DB_SRC --> DB_TOK["[DB Write] INSERT INTO source_tokens<br/>server/evidence/ingest.py:337"]
        DB_TOK --> DB_BLK["[DB Write] INSERT INTO source_blocks<br/>server/evidence/ingest.py:401"]
        DB_BLK --> DB_EXT["[DB Write] INSERT INTO source_extractions<br/>server/evidence/ingest.py:322"]

        DB_EXT --> DB_AUDIT["[DB Write] INSERT INTO governed_actions<br/>server/store/commands.py:210"]
        DB_AUDIT --> DB_RCPT["[DB Write] INSERT INTO receipts<br/>server/store/commands.py:215"]
    end

    DB_RCPT --> RESP_201["HTTP 201 Response (SourcesAdmitted)<br/>server/api/commands/cases.py:257"]

    %% Downstream Consumption Subgraphs
    subgraph READ_EVIDENCE ["Evidence Read Path (Runtime Consumption)"]
        EVID_CALL["read_evidence(source_id, block_id)<br/>server/evidence/read.py:118"] --> READ_BLK["read_block<br/>server/evidence/read.py:72"]
        READ_BLK --> FETCH_BLK["_fetch_block<br/>server/evidence/read.py:99"]
        FETCH_BLK --> DB_BLK_QUERY["[DB Read IO=1] SELECT FROM source_blocks JOIN live_sources<br/>server/evidence/read.py:32"]
        DB_BLK_QUERY -->|"Withdrawn or Missing"| REF_EVID_NA["Refusal: EVIDENCE_NOT_AVAILABLE<br/>server/evidence/read.py:105"]
        DB_BLK_QUERY -->|"Live Row Found"| RET_BTEXT["Return BoundaryText<br/>server/evidence/read.py:113"]
    end

    subgraph CITATION_ANCHORING ["Citation Anchoring Path (Invariant 11)"]
        VERIFY_CALL["verify_citations(delivered, citations)<br/>server/evidence/citations.py:161"] --> CHK_DELIV{"Source in delivered?<br/>server/evidence/citations.py:196"}
        CHK_DELIV -->|"No"| REF_NOT_DELIV["Refusal: CITATION_NOT_DELIVERED<br/>server/evidence/citations.py:198"]
        CHK_DELIV -->|"Yes"| FETCH_TOKENS["_page_tokens<br/>server/evidence/citations.py:222"]
        FETCH_TOKENS --> MATCH_RUN["_unique_run (_match_at)<br/>server/evidence/citations.py:95"]
        MATCH_RUN -->|"Matches == 0"| REF_NOT_LOC["Refusal: CITATION_NOT_LOCATED<br/>server/evidence/citations.py:105"]
        MATCH_RUN -->|"Matches > 1"| REF_AMBIG["Refusal: CITATION_AMBIGUOUS<br/>server/evidence/citations.py:107"]
        MATCH_RUN -->|"Matches == 1"| CHK_COV{"All tokens on delivered lines?<br/>server/evidence/citations.py:208"}
        CHK_COV -->|"No"| REF_NOT_DELIV2["Refusal: CITATION_NOT_DELIVERED<br/>server/evidence/citations.py:209"]
        CHK_COV -->|"Yes"| DERIVE_RECTS["_rectangles (QuadPoints per line)<br/>server/evidence/citations.py:263"]
        DERIVE_RECTS --> RET_ANCHORED["Yield AnchoredCitation(bboxes)<br/>server/evidence/citations.py:212"]
    end

    subgraph PAGE_RENDER ["Page Read Path (Evidence Drawer UI)"]
        PAGE_REQ["GET /api/v1/.../sources/{source_id}/pages/{page}<br/>server/api/reads/evidence.py:48"] --> READ_PAGE["read_page<br/>server/evidence/page.py:95"]
        READ_PAGE --> DB_PAGE_Q["[DB Read IO=1] _PAGE_QUERY on live_sources & source_tokens<br/>server/evidence/page.py:52"]
        DB_PAGE_Q --> BLOB_GET["[IO Side Effect] blobs.get(document_sha256)<br/>server/evidence/page.py:168"]
        BLOB_GET --> GET_FRAME["page_frame (_in_child)<br/>server/evidence/pdf.py:139"]
        GET_FRAME --> RET_PAGE_DOC["Return PageDocument<br/>server/api/reads/evidence.py:81"]
    end
```

---

## 3. External Dependencies

1. **Storage Layer**:
   - `server.blobs.BlobStore`: Content-addressed file blob store (`put` during admission, `get` during page frame generation).
   - PostgreSQL connection (`psycopg`): Manages relational tables `sources`, `source_tokens`, `source_blocks`, `source_extractions`, and views `live_sources`.
2. **Feature 1 (Edge & API Foundation / Governance)**:
   - `server.refusals.Refusal`, `RefusalCode`: Typed refusals without message leakage.
   - `server.boundary_text.BoundaryText`: Sanitized, bounded UTF-8 text representation across boundary interfaces.
   - `server.api.deps`: `Store`, `Blobs`, `Caller`.
   - `server.api.identity`: `Actor`, `GlobalRole`.
   - `server.api.wire`: `SourcesAdmitted`, `PageDocument`, `UploadDocument`, `PAGE_MAX`, `PAGE_LINES_MAX`.
3. **Feature 3 (Case & Run Management, Governance & Idempotency)**:
   - `server.store.cases.lock_case`: Row-level exclusive lock `SELECT FOR UPDATE` on `cases`.
   - `server.store.commands.run_command`: Transactional command executor enforcing idempotency keys, recording audit logs, and writing receipts.
   - `server.store.commands.find_receipt`: Replay detection before extraction starts.
   - `server.store.members`: `Standing`, `satisfies`, `standing_of`, `require_case_writer`.
   - `server.store.source_sets.case_sources`: Used by `read_upload` to list active/withdrawn sources.
4. **Operating System & Standard Library**:
   - `subprocess.Popen`: Child process creation for untrusted PDF extraction.
   - `zlib`: Decompression interception for inflation bomb prevention.
   - `pdfminer.six`: PDF layout and character coordinate analysis.
