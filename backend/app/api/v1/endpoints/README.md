# API Endpoints

Base URL: `/api/v1`

---

## Auth

### `POST /auth/signup`

Register a new user.

**Request:**
```json
{
  "name": "John Doe",
  "phone_number": "9876543210",
  "password": "secret123"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### `POST /auth/signin`

Login with existing credentials.

**Request:**
```json
{
  "phone_number": "9876543210",
  "password": "secret123"
}
```

**Response:** Same as signup.

---

> All endpoints below require `Authorization: Bearer <token>` header.

---

## Cases

### `POST /cases/`

Create a new empty case. Initializes all pipeline statuses to `not_started`.

**Request:** No body needed.

**Response:**
```json
{
  "id": "case_object_id",
  "pipeline_status": {
    "mer": "not_started",
    "pathology": "not_started",
    "risk": "not_started",
    "face_match": "not_started",
    "location_check": "not_started"
  },
  "documents": {},
  "decision": null,
  "decision_by": null,
  "decision_at": null,
  "decision_comment": null,
  "created_at": "2026-02-07T10:00:00",
  "updated_at": "2026-02-07T10:00:00"
}
```

> **Why `pipeline_status` instead of a single `status`?**
> MER extraction, pathology extraction, risk analysis, face matching, and location check all run **in parallel**.
> A single linear status (created → processing → done) can't represent concurrent pipelines.
> Each pipeline tracks its own state independently:
> `not_started` → `processing` → `extracted` → `reviewed` (or `failed`).

### `GET /cases/`

List all cases for the logged-in user (newest first).

**Response:**
```json
{
  "cases": [
    {
      "id": "case_object_id",
      "pipeline_status": { "mer": "extracted", "pathology": "processing", ... },
      "documents": {},
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### `GET /cases/{case_id}`

Get a single case by ID. Returns the full case document including all documents and pipeline statuses.

### `GET /cases/{case_id}/status`

**Lightweight polling endpoint for pipeline statuses.**

Designed for the frontend to poll at 2–3 second intervals while pipelines are running. Returns only `pipeline_status` with enriched metadata — no documents payload, keeping it fast and bandwidth-friendly.

For pipelines that have produced results (`extracted` or `reviewed`), the response is enriched with the latest version number, field count, source, and timestamp from the result collection.

**Response:**
```json
{
  "case_id": "abc123",
  "pipeline_status": {
    "mer": {
      "status": "extracted",
      "version": 1,
      "fields_count": 42,
      "source": "llm",
      "created_at": "2026-02-07T10:15:00"
    },
    "pathology": {
      "status": "processing",
      "version": null,
      "fields_count": null,
      "source": null,
      "created_at": null
    },
    "risk": {
      "status": "not_started",
      "version": null,
      "fields_count": null,
      "source": null,
      "created_at": null
    },
    "face_match": {
      "status": "not_started",
      "version": null,
      "fields_count": null,
      "source": null,
      "created_at": null
    },
    "location_check": {
      "status": "not_started",
      "version": null,
      "fields_count": null,
      "source": null,
      "created_at": null
    }
  },
  "updated_at": "2026-02-07T10:15:00"
}
```

> **Recommended polling flow:**
> 1. `POST /cases/{case_id}/process-all` → fire and forget
> 2. Poll `GET /cases/{case_id}/status` every 2–3 seconds
> 3. When a pipeline reaches `extracted` or `failed`, stop polling for that pipeline
> 4. When all pipelines are done, stop polling entirely

### `POST /cases/{case_id}/process-all`

**Trigger all applicable processing pipelines in parallel.**

This is the main orchestration endpoint. It inspects which document types are uploaded and fires off all applicable pipelines concurrently:

| Pipeline | Condition |
|----------|-----------|
| MER extraction | MER docs uploaded |
| Pathology extraction | Pathology docs uploaded |
| Face matching | Both photo AND id_proof uploaded |
| Location check | Photo docs uploaded |

Each pipeline updates its own `pipeline_status.{name}` independently via MongoDB `$set`.

**Guards:**
- Returns `409 Conflict` if any pipeline is already in `processing` state (prevents double-triggering).

**Response:**
```json
{
  "case_id": "abc123",
  "pipelines_triggered": ["mer", "pathology"],
  "pipelines_skipped": ["face_match", "location_check"],
  "results": {
    "mer": {
      "pipeline": "mer",
      "status": "extracted",
      "result": { "_id": "...", "version": 1, "fields_count": 42 }
    },
    "pathology": {
      "pipeline": "pathology",
      "status": "extracted",
      "result": { ... }
    }
  }
}
```

> **Why `process-all` instead of individual triggers?**
> The risk summary analysis depends on outputs from BOTH MER and pathology.
> `process-all` runs them in parallel via `asyncio.gather`, and the orchestrator
> collects all results. Individual `/mer/process` still exists for re-running
> a single pipeline if needed.

### `PATCH /cases/{case_id}/decision`

**Set the underwriter decision for a case.**

This is a human-in-the-loop endpoint for underwriters to record their decision after reviewing the risk analysis.

**Request:**
```json
{
  "decision": "approved",
  "comment": "All checks passed, low risk profile"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `decision` | string | Yes | `approved`, `review`, or `declined` |
| `comment` | string | No | Explanation for the decision |

**Response:**
```json
{
  "case_id": "abc123",
  "decision": "approved",
  "decision_by": "user_id",
  "decision_at": "2026-02-07T15:30:00",
  "decision_comment": "All checks passed, low risk profile",
  "message": "Case decision set to 'approved' successfully."
}
```

**Decision values:**

| Value | Meaning |
|-------|---------|
| `approved` | Application accepted |
| `review` | Needs further investigation / senior review |
| `declined` | Application rejected |

> **Workflow:**
> 1. Pipelines complete (MER, pathology, risk, face-match)
> 2. Underwriter reviews `GET /cases/{case_id}/risk/summary`
> 3. Underwriter checks red_flags, contradictions, risk_level
> 4. Underwriter sets decision via `PATCH /cases/{case_id}/decision`
> 5. Decision is recorded with user ID and timestamp for audit

---

## Documents

Document upload uses **pre-signed S3 URLs**. The flow is:

1. **Request upload URLs** → backend returns pre-signed PUT URLs
2. **Upload files directly to S3** using those URLs (from frontend)
3. **Confirm upload** → tell backend the uploads are done

### Document Types

| Type | Description |
|------|-------------|
| `mer` | Medical Examination Report |
| `pathology` | Pathology / Lab Reports |
| `photo` | Geo-tagged Photograph |
| `id_proof` | Identification Proof |

Each type can have multiple files (pdf, jpeg, png).
You **cannot append** files to an existing type — delete first, then re-upload.

---

### `POST /cases/{case_id}/documents/upload-url`

Get pre-signed upload URLs for a set of files.

**Request:**
```json
{
  "document_type": "mer",
  "files": [
    { "file_name": "page1.pdf", "content_type": "application/pdf" },
    { "file_name": "page2.jpg", "content_type": "image/jpeg" }
  ]
}
```

Allowed `content_type` values: `application/pdf`, `image/jpeg`, `image/png`

**Response:**
```json
{
  "document_type": "mer",
  "files": [
    {
      "file_id": "uuid-1",
      "file_name": "page1.pdf",
      "upload_url": "https://s3.amazonaws.com/...?X-Amz-Signature=..."
    },
    {
      "file_id": "uuid-2",
      "file_name": "page2.jpg",
      "upload_url": "https://s3.amazonaws.com/...?X-Amz-Signature=..."
    }
  ]
}
```

**Frontend must then:** Upload each file to its `upload_url` via HTTP `PUT` with the matching `Content-Type` header.

```js
await fetch(upload_url, {
  method: "PUT",
  headers: { "Content-Type": file.type },
  body: file,
});
```

Upload URLs expire in **15 minutes**.

---

### `POST /cases/{case_id}/documents/confirm-upload`

After uploading all files to S3, confirm so backend marks them as `uploaded`.

**Request:**
```json
{
  "document_type": "mer",
  "file_ids": ["uuid-1", "uuid-2"]
}
```

**Response:**
```json
{ "message": "Upload confirmed" }
```

---

### `GET /cases/{case_id}/documents`

List all uploaded documents for a case, with pre-signed download URLs.

Only files with status `uploaded` are returned. Download URLs expire in **30 minutes**.

**Response:**
```json
{
  "documents": {
    "mer": [
      {
        "id": "uuid-1",
        "file_name": "page1.pdf",
        "content_type": "application/pdf",
        "url": "https://s3.amazonaws.com/...?X-Amz-Signature=...",
        "uploaded_at": "2026-02-07T10:05:00"
      }
    ],
    "pathology": [],
    "photo": [],
    "id_proof": []
  }
}
```

---

### `DELETE /cases/{case_id}/documents/{document_type}`

Delete all files for a given document type. Removes from both S3 and the case record.

**Example:** `DELETE /cases/abc123/documents/mer`

**Response:**
```json
{ "message": "Deleted 2 file(s) for mer" }
```

After deleting, you can re-upload files for that type.

---

## MER Processing

MER (Medical Examination Report) extraction pipeline:
1. Downloads files from S3
2. Tesseract OCR on all pages (parallel across pages)
3. Page classification using fuzzy keyword matching + greedy assignment
4. LLM-based structured extraction per page (parallel)
5. Flattens extracted data into fields
6. Stores versioned snapshot in MongoDB

### `POST /cases/{case_id}/mer/process`

Trigger MER processing pipeline individually.

**Guards:**
- Returns `400` if no MER documents are uploaded.
- Returns `409 Conflict` if MER is already `processing`.

**Side effects:**
- Sets `pipeline_status.mer` to `processing` → `extracted` (or `failed`).

**Response:**
```json
{
  "id": "result_object_id",
  "case_id": "abc123",
  "version": 1,
  "source": "llm",
  "fields_count": 42,
  "classification": {
    "mapping_summary": { "1": { "source_page": 1, "confidence": 0.85 }, ... },
    "unmatched_pages": [],
    "missing_pages": [],
    "needs_review": []
  }
}
```

### `GET /cases/{case_id}/mer/result`

Get the MER extraction result.

| Query Param | Description |
|-------------|-------------|
| `version` | Specific version number. Omit for latest. |

**Response:** Full result including raw pages JSON, classification, and all flattened fields.

### `GET /cases/{case_id}/mer/versions`

List all MER result versions (metadata only — version number, source, timestamp).

Useful for showing version history to the user.

**Response:**
```json
{
  "case_id": "abc123",
  "versions": [
    { "id": "...", "version": 2, "source": "excel_import", "created_at": "..." },
    { "id": "...", "version": 1, "source": "llm", "created_at": "..." }
  ]
}
```

### `GET /cases/{case_id}/mer/export-excel`

Download MER result as a `.xlsx` file. **Dynamically generated** — not stored anywhere.

| Query Param | Description |
|-------------|-------------|
| `version` | Specific version. Omit for latest. |

**Excel coloring rules** (derived from field data, not stored separately):

| Condition | Cell Color | Meaning |
|-----------|-----------|---------|
| `source="llm"`, confidence >= 0.7 | White | High confidence, untouched |
| `source="llm"`, 0.5 <= confidence < 0.7 | Yellow | Medium confidence, needs review |
| `source="llm"`, confidence < 0.5 | Red | Low confidence, likely wrong |
| `source="user"` | Light Green | User reviewed & edited |

The Excel contains a hidden column A with field IDs (for re-import matching) and a hidden metadata row for validation.

**Response:** `.xlsx` file download.

### `POST /cases/{case_id}/mer/import-excel`

Upload an edited `.xlsx` to create a new versioned snapshot.

**How it works:**
1. Reads the uploaded Excel
2. Matches fields by hidden ID column against the latest version
3. Changed fields get `source="user"`, `confidence=1.0`
4. Unchanged fields keep their original values
5. Creates a new version (full snapshot — no diffs)

**Side effects:**
- Sets `pipeline_status.mer` to `reviewed`.

**Request:** `multipart/form-data` with `.xlsx` file.

**Response:**
```json
{
  "id": "new_result_id",
  "case_id": "abc123",
  "version": 2,
  "source": "excel_import",
  "fields_count": 42,
  "changed_fields": 5,
  "message": "Created version 2 with 5 field(s) changed."
}
```

> **Why versioned snapshots?**
> Each version is a complete, independent snapshot of all fields.
> No merge logic, no diffing — any version can generate a complete Excel.
> Rollback = just point to an older version.

---

## Pathology Processing

Pathology (Lab Reports) extraction pipeline:
1. Downloads files from S3
2. Tesseract OCR on all pages (parallel)
3. LLM-based OCR enhancement per page
4. LLM-based standardized parameter extraction (maps to 50 standard tests)
5. Flattens extracted data into fields
6. Stores versioned snapshot in MongoDB

### `GET /cases/{case_id}/pathology/result`

Get the pathology extraction result.

| Query Param | Description |
|-------------|-------------|
| `version` | Specific version number. Omit for latest. |

**Response:** Full result including patient_info, lab_info, standardized parameters, and all flattened fields.

### `GET /cases/{case_id}/pathology/versions`

List all pathology result versions (metadata only).

**Response:**
```json
{
  "case_id": "abc123",
  "versions": [
    { "id": "...", "version": 2, "source": "excel_import", "created_at": "..." },
    { "id": "...", "version": 1, "source": "llm", "created_at": "..." }
  ]
}
```

### `GET /cases/{case_id}/pathology/export-excel`

Download pathology result as a `.xlsx` file. **Dynamically generated**.

| Query Param | Description |
|-------------|-------------|
| `version` | Specific version. Omit for latest. |

**Excel coloring rules:**

| Condition | Cell Color | Meaning |
|-----------|-----------|---------|
| `source="llm"` | White | LLM extracted, untouched |
| `source="user"` | Light Green | User reviewed & edited |

**Response:** `.xlsx` file download.

### `POST /cases/{case_id}/pathology/import-excel`

Upload an edited `.xlsx` to create a new versioned snapshot.

**Side effects:**
- Sets `pipeline_status.pathology` to `reviewed`.

**Request:** `multipart/form-data` with `.xlsx` file.

**Response:**
```json
{
  "id": "new_result_id",
  "case_id": "abc123",
  "version": 2,
  "source": "excel_import",
  "fields_count": 55,
  "changed_fields": 3,
  "message": "Created version 2 with 3 field(s) changed."
}
```

---

## Risk Analysis

Risk analysis pipeline — runs automatically after MER and/or pathology extraction completes:
1. Loads latest MER result (if available)
2. Loads latest pathology result (if available)
3. Pre-processes: extracts patient info, calculates BMI, flags critical values, detects contradictions
4. LLM-based comprehensive risk assessment
5. Post-processes: validates sources, adds metadata
6. Stores versioned snapshot with source version tracking

> **Auto-trigger behavior:**
> Risk analysis triggers automatically when MER or pathology extraction completes.
> It can run with just one of them if the other is not uploaded.
> Uses atomic MongoDB operations to prevent duplicate triggers.

### `GET /cases/{case_id}/risk/result`

Get the risk analysis result.

| Query Param | Description |
|-------------|-------------|
| `version` | Specific version number. Omit for latest (by source_freshness). |

**Response:**
```json
{
  "id": "result_id",
  "case_id": "abc123",
  "version": 1,
  "based_on": {
    "mer_version": 1,
    "pathology_version": 1,
    "source_freshness": 2
  },
  "patient_info": { ... },
  "critical_flags": [ ... ],
  "contradictions": [ ... ],
  "llm_response": {
    "red_flags": ["HbA1c 9.2% indicates poorly controlled diabetes"],
    "contradictions": ["Denied diabetes but labs confirm diabetic range"],
    "summary": "Undisclosed diabetes with poor control. Requires senior review.",
    "risk_level": "High"
  },
  "created_at": "..."
}
```

> **Risk levels:** `High`, `Intermediate`, or `Low`

### `GET /cases/{case_id}/risk/versions`

List all risk analysis versions with source version metadata.

**Response:**
```json
{
  "case_id": "abc123",
  "versions": [
    {
      "id": "...",
      "version": 2,
      "mer_version": 2,
      "pathology_version": 1,
      "source_freshness": 3,
      "risk_level": "Intermediate",
      "created_at": "..."
    }
  ]
}
```

### `GET /cases/{case_id}/risk/summary`

Lightweight summary for quick polling / dashboard views. Designed for human decision makers.

**Response:**
```json
{
  "case_id": "abc123",
  "version": 1,
  "based_on": {
    "mer_version": 1,
    "pathology_version": 1,
    "source_freshness": 2
  },
  "red_flags": [],
  "contradictions": [],
  "summary": "Healthy 28-year-old female. All vitals and lab values within normal range.",
  "risk_level": "Low",
  "created_at": "..."
}
```

| Field | Description |
|-------|-------------|
| `red_flags` | Abnormal readings or concerning patterns (max 5) |
| `contradictions` | Mismatches between disclosed info and medical findings |
| `summary` | 2-3 sentence explanation of the risk assessment |
| `risk_level` | `High`, `Intermediate`, or `Low` |

> **Version freshness:**
> `source_freshness = mer_version + pathology_version` (null treated as 0).
> The "latest" risk result is determined by highest source_freshness, then version.
> This ensures re-analysis with updated MER/pathology data is considered "latest".

---

## Face Match

Face matching pipeline — compares a **geo-tagged selfie** (photo) with a **government ID** (id_proof):
1. Downloads photo and ID proof images from S3
2. YuNet face detection with rotation/scale fallbacks
3. SFace embedding extraction
4. Cosine similarity comparison
5. Converts raw similarity to user-friendly match percentage
6. Stores versioned result in MongoDB

> **Detection fallbacks:**
> - **Photo (selfie):** Assumes upright, tries 3 scales (1x, 1.5x, 2x)
> - **ID proof:** Tries all rotations (0°, 90°, 180°, 270°) and 4 scales (1x, 1.5x, 2x, 3x)
> 
> This handles rotated scans and small passport photos on ID cards.

### `GET /cases/{case_id}/face-match`

Get the face-match result with presigned URLs for viewing both images.

**Response:**
```json
{
  "id": "result_id",
  "case_id": "abc123",
  "version": 1,
  "match": true,
  "match_percent": 82,
  "decision": "match",
  "message": "Match: same person (cosine_similarity=0.521).",
  "photo_file_id": "uuid-photo",
  "id_file_id": "uuid-id",
  "photo_url": "https://s3.amazonaws.com/...?X-Amz-Signature=...",
  "id_url": "https://s3.amazonaws.com/...?X-Amz-Signature=...",
  "review_status": "pending",
  "reviewed_by": null,
  "reviewed_at": null,
  "review_comment": null,
  "created_at": "2026-02-07T10:20:00"
}
```

**Match percentage mapping:**

| Raw Similarity | Match? | Display % |
|----------------|--------|-----------|
| < 0 | No | 0% |
| 0.0 - 0.36 | No | 0% - 74% |
| **0.363** (threshold) | Borderline | **75%** |
| 0.5 | Yes | 80% |
| 0.7 | Yes | 88% |
| 0.9+ | Yes | 96%+ |

> Matches always show **75%+** to appear more convincing to users.

### `PATCH /cases/{case_id}/face-match/review`

Approve or reject a face-match result. Used for audit/compliance.

**Request:**
```json
{
  "status": "approved",
  "comment": "Verified manually"
}
```

| Field | Values |
|-------|--------|
| `status` | `"approved"` or `"rejected"` |
| `comment` | Optional review note |

**Side effects:**
- Sets `pipeline_status.face_match` to `reviewed`.
- Records reviewer ID and timestamp.

**Response:**
```json
{
  "case_id": "abc123",
  "review_status": "approved",
  "reviewed_by": "user_id",
  "reviewed_at": "2026-02-07T10:25:00",
  "review_comment": "Verified manually",
  "message": "Face-match result approved successfully."
}
```

### Dashboard Status

When polling `GET /cases/{case_id}/status`, face-match includes extra metadata:

```json
{
  "face_match": {
    "status": "extracted",
    "version": 1,
    "match_percent": 82,
    "match": true,
    "recommendation": "match",
    "review_status": "pending",
    "created_at": "2026-02-07T10:20:00"
  }
}
```

| Field | Description |
|-------|-------------|
| `match_percent` | User-friendly percentage (75%+ for match) |
| `match` | Boolean: true if faces match |
| `recommendation` | `"match"`, `"no_match"`, or `"inconclusive"` |
| `review_status` | `"pending"`, `"approved"`, or `"rejected"` |

---

## Location Check

Location check pipeline — compares locations from up to **3 sources** to detect inconsistencies:
1. **Photo** — GPS coordinates from EXIF metadata (geo-tagged selfie)
2. **ID Card** — Address extracted via LLM from ID proof image
3. **Lab Report** — Lab address from pathology extraction

The pipeline:
1. Extracts location from each available source
2. Geocodes addresses to coordinates (Google Maps API)
3. Calculates pairwise distances between all detected sources
4. Flags any pair exceeding distance threshold (default: 50km)
5. Stores versioned result in MongoDB

> **Decision logic:**
> - `pass` — All distances within threshold
> - `fail` — At least one distance exceeds threshold
> - `insufficient` — Less than 2 sources detected (can't compare)

### `GET /cases/{case_id}/location-check`

Get the location check result with presigned URLs for viewing images.

**Response:**
```json
{
  "id": "result_id",
  "case_id": "abc123",
  "version": 1,
  "photo_file_id": "uuid-photo",
  "id_file_id": "uuid-id",
  "pathology_version": 1,
  "photo_url": "https://s3.amazonaws.com/...?X-Amz-Signature=...",
  "id_url": "https://s3.amazonaws.com/...?X-Amz-Signature=...",
  "sources": [
    {
      "source_type": "photo",
      "status": "found",
      "raw_input": "19.0760,72.8777",
      "address": null,
      "coords": [19.0760, 72.8777],
      "message": "GPS coordinates extracted from EXIF"
    },
    {
      "source_type": "id_card",
      "status": "found",
      "raw_input": "123 Marine Drive, Mumbai 400001",
      "address": "123 Marine Drive, Mumbai, Maharashtra 400001",
      "coords": [18.9432, 72.8235],
      "message": "Address geocoded successfully"
    },
    {
      "source_type": "lab",
      "status": "found",
      "raw_input": "Sunrise Diagnostics, Andheri West",
      "address": "Sunrise Diagnostics, Andheri West, Mumbai 400053",
      "coords": [19.1364, 72.8296],
      "message": "Lab address from pathology report"
    }
  ],
  "distances": [
    { "source_a": "photo", "source_b": "id_card", "distance_km": 15.2, "flag": false },
    { "source_a": "photo", "source_b": "lab", "distance_km": 8.7, "flag": false },
    { "source_a": "id_card", "source_b": "lab", "distance_km": 22.1, "flag": false }
  ],
  "sources_detected": ["photo", "id_card", "lab"],
  "sources_not_detected": [],
  "decision": "pass",
  "flags": [],
  "message": "All locations within acceptable distance.",
  "review_status": "pending",
  "reviewed_by": null,
  "reviewed_at": null,
  "review_comment": null,
  "created_at": "2026-02-07T10:20:00"
}
```

**Source status values:**

| Status | Meaning |
|--------|---------|
| `found` | Location extracted and geocoded successfully |
| `not_found` | Source data not available (no EXIF, no address, etc.) |
| `skipped` | Source document not uploaded |
| `geocode_failed` | Address found but geocoding failed |

**Decision values:**

| Decision | Meaning |
|----------|---------|
| `pass` | All pairwise distances within threshold |
| `fail` | At least one distance exceeds threshold (flagged) |
| `insufficient` | Less than 2 sources detected, cannot compare |

### `PATCH /cases/{case_id}/location-check/review`

Approve or reject a location check result. Used for audit/compliance.

**Request:**
```json
{
  "status": "approved",
  "comment": "Verified locations are consistent"
}
```

| Field | Values |
|-------|--------|
| `status` | `"approved"` or `"rejected"` |
| `comment` | Optional review note |

**Side effects:**
- Sets `pipeline_status.location_check` to `reviewed`.
- Records reviewer ID and timestamp.

**Response:**
```json
{
  "case_id": "abc123",
  "review_status": "approved",
  "reviewed_by": "user_id",
  "reviewed_at": "2026-02-07T10:25:00",
  "review_comment": "Verified locations are consistent",
  "message": "Location check result approved successfully."
}
```

### Dashboard Status

When polling `GET /cases/{case_id}/status`, location-check includes extra metadata:

```json
{
  "location_check": {
    "status": "extracted",
    "version": 1,
    "decision": "pass",
    "sources_detected": ["photo", "id_card", "lab"],
    "flags_count": 0,
    "review_status": "pending",
    "created_at": "2026-02-07T10:20:00"
  }
}
```

| Field | Description |
|-------|-------------|
| `decision` | `"pass"`, `"fail"`, or `"insufficient"` |
| `sources_detected` | Which location sources were found |
| `flags_count` | Number of distance pairs exceeding threshold |
| `review_status` | `"pending"`, `"approved"`, or `"rejected"` |

---

## Architecture Notes

### All Functions Are Async

Every I/O operation is async:
- **S3 operations** — `boto3` calls wrapped in `asyncio.to_thread()`
- **Tesseract OCR** — CPU-bound, runs in `ProcessPoolExecutor` (max 4 workers)
- **LLM calls** — `httpx.AsyncClient` for non-blocking HTTP
- **Page classification** — fuzzy matching offloaded to thread via `asyncio.to_thread()`
- **MongoDB** — `motor` async driver

### Parallelism

| Level | What's parallelized |
|-------|-------------------|
| Case-level | MER, pathology, face match, location check run in parallel via `process-all` |
| Pipeline-level | Risk analysis auto-triggers after MER/pathology completes |
| File-level | Multiple S3 downloads in parallel |
| Page-level | Tesseract OCR across PDF pages in parallel |
| LLM-level | All matched MER pages extracted in parallel |

### MongoDB Collections

| Collection | Purpose |
|-----------|---------|
| `users` | User accounts |
| `cases` | Case metadata, documents, pipeline_status |
| `mer_results` | Versioned MER extraction snapshots |
| `pathology_results` | Versioned pathology extraction snapshots |
| `risk_results` | Versioned risk analysis snapshots (with source version tracking) |
| `face_match_results` | Versioned face-match results with review status |
| `location_check_results` | Versioned location check results with multi-source distances |
