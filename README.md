# SwasthMode

SwasthMode is an independent AI-powered wellness proof of concept with unified and dedicated meal/medication logging, morning/evening briefs, Clerk authentication, and a read-only clinician dashboard written in source. Its purpose is to demonstrate understandable AI workflows and engineering decisions using synthetic patient data and real providers.

## Status and source of truth

~~Current status: planning only. Implementation is on hold until the user reviews and approves this README.~~

~~Current status — 27 October 2026: foundation, text meals/corrections/background insights, and the medication event slice are written in source. Briefs remain planned.~~

~~Current status — 27 October 2026: foundation, meals, medication events and briefs are written; mixed logging remains planned.~~

~~Current status — 28 October 2026: unified meal/medication logging is also written in source, with bounded typed routing, sequential specialist execution, persisted step/question ownership, parent-fenced writes, recovery checkpoints and patient navigation. Voice and clinician patient-detail views remain planned. All application behavior is unverified.~~

~~Current status — 28 October 2026, Phase 5: voice input/output is now also written in source. Desktop Chrome records WebM/Opus for separate transcription, transcripts remain editable before submission, and Cartesia reads committed replies and saved briefs on demand. Clinician patient-detail views remain planned. All application behavior is unverified; no tests or provider checks were run.~~

**Current status — 28 October 2026, Phase 6: the read-only clinician dashboard is also written in source, with an assigned synthetic patient list, bounded date-filtered meals/insights and medication events, and latest saved morning/evening briefs. Clerk authentication and authoritative database role/assignment scopes protect every clinician endpoint and record query. All application behavior remains unverified. Source inspection only: no tests, builds, startup, migrations, app/API exercises, provider checks or paid requests were run.**

This README is the single source of truth for the requirements, architecture, decisions, implementation progress, setup instructions, and manual checking guide. Do not maintain competing plan documents in a `docs/` folder.

- `[x]` means the stated planning decision or deliverable is complete. It does not mean application behavior has been tested.
- `[ ]` means planned, incomplete, or awaiting a decision.
- When a requirement changes, strike through the previous wording and put its replacement directly below it, with the date and reason.
- Keep implementation progress separate from user-reported manual verification.
- Never mark an unexecuted check as passed.
- Update this README as work proceeds and distinguish implemented behavior from proposals.

~~No application code has been written.~~

Application source has now been written. No dependency installation, build, application startup, migration execution, automated tests, browser testing, manual application/API exercises, or provider connectivity checks have been performed by the agent.

## Decisions and changes — 27 October 2026

- [x] Name the application **SwasthMode**.
- [x] ~~Use MariaDB for application persistence.~~
  Use **PostgreSQL**, as selected by the user. Keep SQLAlchemy and Alembic; use psycopg as the planned driver. This is one database implementation, not dual-database support.
- [x] ~~Organize features across top-level API, schema, workflow, AI extraction, and service folders.~~
  Organize by feature. Keep each feature's router, schemas, business rules, extraction, and models together. Shared infrastructure belongs in `core/`; shared provider code belongs in `ai/` and `speech/`.
- [x] ~~Keep architecture, setup, database, checking, demo, and decisions in separate Markdown documents.~~
  Keep these sections in this README as the single source of truth.
- [x] ~~Use unspecified conversation locking.~~
  Use short database transactions and an expiring conversation lease with an owner token and version checks. Never hold a transaction across AI calls, speech generation, or streaming.
- [x] ~~Allow pending medication confirmations to disappear silently when conversation state expires.~~
  Retain enough expired-state metadata to explain late confirmations and prevent them from saving an event.
- [x] Clarify the proposed 24-hour inactivity expiry: it ends actionable conversation continuity, not the lifetime of saved meals, medication events, or briefs. Physical cleanup is a separate retention decision.
- [x] ~~Leave supported voice browsers unspecified.~~
  Support **desktop Google Chrome only** for this POC. Record WebM/Opus and require compatible transcription input support.
- [x] Clarify meal insights: real AI generates qualitative observations grounded in recorded foods. Nutritional estimation remains outside scope.
- [x] Create and review this README before application implementation.
- [x] User approval to begin implementation.
- [x] Use **uv** for Python dependency management and backend commands, including the backend Docker image, as requested after approval.
- [x] ~~Use a `PatientRepository(Protocol)` and a separate `platform/` interface/implementation pair.~~
  Keep one concrete `features/meals/repository.py` for implemented meal data access. The user clarified that patient and clinician data belong in our database, with no second database or external patient platform. Future feature repositories will also use the same PostgreSQL database. Removing the extra Protocol makes this boundary easier to understand while keeping SQL outside the AI model.
- [x] ~~Use only our own rule-based input guardrails and limited output checks.~~
  Use **our rule-based checks plus NVIDIA NeMo Guardrails** in hybrid mode, as requested on 27 October 2026. NeMo's library is Apache-2.0 licensed and free to use; model-backed safety checks can incur provider charges. Integration source is written for the current meal slice, not installed or exercised. Upcoming features must use the same layered boundary when implemented.
- [x] Medication slice — 27 October 2026: reuse the shared lease/request store with a feature parameter defaulting to meals, and add a concrete medication repository in the same PostgreSQL database. No new worker or provider is needed.
- [x] ~~Require medication confirmation only where a prescription match is uncertain.~~
  **27 October 2026:** require confirmation of **every** medication event and time correction. This gives the user a consistent readback of both reported fields and the prescription reference before any event write.
- [x] **Medication parsing decision — 27 October 2026:** extraction remains model-backed, but deterministic validation accepts one complete statement beginning `I took` or `I have taken`, ending in `now` or `at YYYY-MM-DD HH:MM`. Every word in the medicine portion must be accounted for by separately evidenced reported fields. Vague, multi-medicine, negated, overlapping, or incomplete reports ask for a new complete report. This conservative first slice avoids silently dropping unrecognized words or guessing dates.
- [x] **27 October 2026:** retain medication questions as permanent POC records, with immutable proposal/readback, question ID, step ID, medication ID, owning conversation/version, expiry and disposition. Keep one conversation row per patient/feature and a monotonically increasing version; never reset that version on inactivity expiry. Old question IDs cannot regain consent when the same conversation row is reused.
- [x] **Brief slice — 27 October 2026:** adopt the existing morning same-local-day and evening 30-minute reuse plan. End both windows at local midnight. Define morning context as the previous seven complete local days; evening context is today up to capture time. These are bounded POC context choices, not clinical windows.
- [x] **Brief grounding decision — 27 October 2026:** the configured real model returns a typed narrative plan: an opening, one to six distinct recorded-fact IDs in narrative order, and one allowed logging/reflection focus. Python renders those selected facts verbatim, preventing the model from authoring unsupported numbers, causes or medication claims. There is no offline/generated-text fallback. This intentionally constrains narrative variety; it does not claim general free-form grounding.
- [x] **Backend debugging — 28 October 2026:** add opt-in debugpy for the running API and Celery worker only, through `compose.debug.yaml`, a `debug` dependency group and VS Code attach configurations. Tests and scripts are excluded, as requested. The default image and Compose startup are unchanged.

## Technology and scope

- Python 3.12+, FastAPI, and Pydantic.
- uv for Python environments and dependencies; npm for the React frontend.
- NVIDIA NeMo Guardrails 0.24.1 through its native Python integration, alongside our own deterministic guardrails. No LangChain orchestration or separate guardrails service.
- OpenAI Python SDK with configurable endpoint and model/deployment names.
- PostgreSQL, SQLAlchemy, Alembic, and psycopg.
- Celery and Redis for background work; Flower for task status.
- Cartesia for genuine text-to-speech.
- A separately configured real speech-to-text provider accepting WebM/Opus.
- React, TypeScript, and Vite.
- Docker Compose for local infrastructure.

Use one modular backend application plus a worker, not microservices. Use supported SDK integrations rather than building authentication or speech protocols from scratch. Do not add LangChain, LangGraph, a vector database, document RAG, Kubernetes, or an autonomous multi-agent system.

AI interprets language and proposes typed information. Python controls permissions, deterministic validation, confirmations, state transitions, allowed operations, and database writes. The model never receives unrestricted SQL or arbitrary operation execution.

## PostgreSQL decision and trade-offs

Both PostgreSQL and MariaDB can handle the relational records, transactions, unique constraints, and access mappings required here. PostgreSQL was selected for this project; no performance benchmark has been performed.

| Consideration | PostgreSQL | MariaDB |
| --- | --- | --- |
| Structured extraction and conversation state | Native JSONB with indexing options | JSON is validated text through a LONGTEXT alias |
| Event timestamps | `timestamptz` for instants; retain the patient's IANA timezone separately | Requires an explicit consistent timestamp convention and separate patient timezone |
| Practical preference | Convenient structured-state inspection and querying | Useful if matching an existing MariaDB team environment is the priority |
| Moving later | Driver, SQL, JSON queries, and migrations can need changes | The same portability consideration applies |

Use relational columns for identities, permissions, dates, statuses, and important queryable fields. Use bounded JSONB payloads for structured extraction checkpoints and conversation state where useful. Do not store the whole domain as unstructured JSON. The repository adapter isolates data access but does not make database dialects interchangeable.

Store event instants consistently in UTC and preserve each patient's IANA timezone, defaulting to `Asia/Kolkata` for synthetic profiles. PostgreSQL timestamps do not preserve the original IANA zone by themselves. Calculate local days in Python for meal context and brief reuse.

References: [PostgreSQL JSON types](https://www.postgresql.org/docs/current/datatype-json.html), [PostgreSQL date/time types](https://www.postgresql.org/docs/current/datatype-datetime.html), [MariaDB JSON type](https://mariadb.com/docs/server/reference/data-types/string-data-types/json).

## Synthetic data and real providers

Persist multiple varied synthetic patients, small prescription lists, meal records, medication events, several days of sleep/activity measurements, and simple wellness goals in PostgreSQL.

Use real providers for intent planning, extraction, meal insights, briefs, transcription, and speech generation. Do not use canned AI responses or offline AI fixtures during the running demo. Provider failures must produce honest errors or failed states rather than fake success.

~~Put domain access behind a small repository/platform adapter so an external patient service could replace local persistence later.~~

Put domain queries and writes in concrete feature repositories connected to our single PostgreSQL database. No external platform or second database is required. We can add an interface later if a real replacement becomes necessary. A separate mock-platform server is unnecessary.

Do not connect to company production services or use real patient data. Do not modify the reference Smart Coach repository or copy its proprietary code, prompts, wording, or assets.

## Proposed files and responsibilities

~~The tree mixes implemented and future files; the progress and limitations sections identify which slices have source. Add Python package files where necessary during implementation.~~
**28 October 2026 — tree updated to match the files actually in source.** Files still planned are marked `(planned)`. The original plan listed `features/timeline/`, `account/schemas.py`, `patients/schemas.py`, `conversations/schemas.py`, `SignIn.tsx`, `meals/Meals.tsx` and `BriefCard.tsx`; these were never created because their work lives elsewhere (see the note below the tree). Presence of a file does not mean its behavior is verified.

```text
SwasthMode/
  backend/
    app/
      main.py
      cli.py
      core/
        config.py
        streaming.py
        audit.py                  (planned)
        auth/
          clerk.py
          permissions.py
        db/
          base.py
          session.py
          model_registry.py
        conversations/
          models.py
          store.py
          leases.py
        requests/
          models.py
          idempotency.py          (planned)
      features/
        account/
          router.py
          models.py
          setup.py
        patients/
          models.py
          seed.py
        meals/
          router.py
          schemas.py
          service.py
          extraction.py
          validation.py
          replies.py
          models.py
          prompts.py
          insights.py
          repository.py
        medications/
          router.py
          schemas.py
          service.py
          extraction.py
          matching.py
          validation.py
          replies.py
          models.py
          prompts.py
          repository.py
        briefs/
          router.py
          schemas.py
          service.py
          context.py
          generation.py
          validation.py
          models.py
          prompts.py
          repository.py
        health_logs/
          router.py
          schemas.py
          planner.py
          service.py
          prompts.py
        clinician/
          router.py
          schemas.py
          queries.py
      ai/
        client.py
        guardrails.py
        nemo.py
        nemo_config.yml
      speech/
        router.py
        schemas.py
        stt.py
        tts.py
      tasks/
        celery_app.py
        meal_insights.py
    alembic/
      env.py
      versions/
        0001_initial_slice.py
        0002_medication_events.py
        0003_briefs.py
    alembic.ini
    pyproject.toml
    Dockerfile
  frontend/
    src/
      main.tsx
      App.tsx
      api/client.ts
      auth/ProtectedRoute.tsx     (planned)
      features/
        account/AccountSetup.tsx
        patient/PatientHome.tsx
        medications/Medications.tsx
        briefs/Briefs.tsx
        health_logs/HealthLogs.tsx
        clinician/ClinicianDashboard.tsx
      components/
        Composer.tsx
        VoiceRecorder.tsx
        SpeechPlayback.tsx
        Timeline.tsx
        StatusBadge.tsx
      styles.css
    index.html
    vite.config.ts
    tsconfig.json
    package.json
    Dockerfile
  compose.yaml
  compose.debug.yaml
  .env.example
  .gitignore
  README.md
```

- Feature folders own their models and business rules. `core/db/model_registry.py` imports models for Alembic discovery; avoid a single growing domain models file.
- `patients/` holds synthetic profile, goal, activity, and sleep models and seed data.
- `health_logs/` coordinates mixed meal/medication input only; it does not introduce new logging domains.
- `core/conversations/` stores shared conversation state, pending question ownership, checkpoints, expiry, and leases.
- `core/requests/` handles scoped client request IDs and duplicate protection.
- `features/meals/repository.py` implements bounded meal queries and writes in the local PostgreSQL database; there is no `PatientRepository(Protocol)` or external platform connection.
- `ai/client.py` centralizes model/deployment configuration, provider timeouts, bounded retries, and typed responses. Feature prompts remain near their feature.
- `ai/guardrails.py` contains our deterministic rules; `ai/nemo.py` adapts NeMo's validation-only API, and `ai/nemo_config.yml` contains our own input/output safety policy prompts. Credentials and model settings are injected in memory, never written into that YAML file.
- `core/audit.py` records minimal operational metadata, not patient conversations.

~~The tree includes future files.~~ Only entries marked `(planned)` are future files. Meal and medication timelines are served by each feature's own list route (`GET /api/meals`, `GET /api/medications`), so there is no separate `timeline/` feature; request/response models live in each router's feature `schemas.py` where one exists. Clerk's `<SignIn>` is rendered directly in `App.tsx`, and the meals view lives in `PatientHome.tsx`. `core/requests/models.py`, `core/conversations/leases.py`, and `store.py` together handle request claims/checkpoints; there is no separate `idempotency.py` yet. Minimal operational logging lives in feature services, the AI client, and tasks; `audit.py` is planned. The frontend uses Clerk's `<Show>` guard in `App.tsx`; `PatientHome.tsx` offers Meals, Medication events and Daily briefs navigation. All three views stay mounted when switching so an in-flight request/retry body is retained. Briefs add a feature-owned `repository.py`; their card is local to `features/briefs/Briefs.tsx`. A separate protected-route module remains planned. These are organization simplifications, not missing backend access checks.

## Clerk authentication and RBAC

Clerk React prebuilt components → session token → `frontend/src/api/client.ts` → `core/auth/clerk.py` → verified Clerk identity → PostgreSQL account mapping → `core/auth/permissions.py` → feature operation.

- Use Clerk's supported Python integration to verify authenticity, expiry, configured issuer, and authorized frontend origins. Never merely decode JWTs or trust browser-supplied user IDs.
- Include sign-in, sign-out, optional sign-up if enabled, protected frontend pages, protected backend endpoints, and clear expired-session handling.
- Support exactly two roles: patient and clinician.
- Store roles and patient associations in PostgreSQL, linked to verified Clerk user IDs. These mappings are authoritative for application permissions.
- Newly signed-in, unmapped accounts see an account-setup-required state and cannot access existing patients.
- A developer-only command associates a patient account with a synthetic profile, grants clinician status, and assigns synthetic patients to a clinician.
- No admin dashboard, role selector, signup role fields, browser-controlled roles, company SSO, Azure AD B2C, custom passwords, or authentication bypasses.
- Return 401 for missing/invalid authentication; 403 for an authenticated account without permission.
- Scope conversation, request, timeline, brief, insight, speech-related, and domain resources to the authorized patient. A submitted patient/resource ID is never proof of access.

Patients may create/correct their meals, record their medication events, generate/view their briefs, use text/voice, and view their timeline and insights. They cannot access another patient, clinician endpoints, roles, or assignments.

Clinicians may only read assigned patient records through the limited clinician area. Frontend navigation hides unavailable screens, but FastAPI independently enforces permissions.

## Filename-based request flows

Backend paths below are relative to `backend/app/`.

### Meal logging

`Composer.tsx` → `features/meals/router.py` → `core/auth/permissions.py` → claim a short-transaction lease/request and load authorized conversation/today context → `ai/guardrails.py` input rules → `ai/nemo.py` input check for nontrivial allowed messages → `features/meals/extraction.py` → `ai/client.py` → `features/meals/schemas.py` → save extraction checkpoint → `features/meals/validation.py` and our output rules → `ai/nemo.py` output check → clarification or create/update through `features/meals/service.py` and the repository → `features/meals/replies.py` → persist conversation/result → queue `tasks/meal_insights.py` → `core/streaming.py` and optional `speech/tts.py`.

The lease/request claim can precede the input check, but a guardrail block never writes a meal. Schema-valid extraction can be retained as a checkpoint before semantic checking; it is a proposal, not an accepted domain record. The insight worker applies our qualitative output rules and a NeMo output check before storing its generated observation.

- Respond to a greeting without an unnecessary extraction call.
- Create a meal from natural language and ask for missing required information.
- Continue the same meal across messages: “I had rice and dal.” → “For lunch.” → “Actually, add curd.”
- Correct an existing record rather than creating an accidental duplicate. Ask which meal to update when the target is ambiguous.
- Preserve explicitly supplied quantities without inventing missing portions.
- Save extraction before attempting domain writes. Compose saved confirmations only after commit succeeds.
- Meal edits increment a revision and invalidate related insights. Old worker output cannot overwrite a newer revision.
- Display pending, completed, or failed insight status.

### Medication event logging

`features/medications/Medications.tsx` → `features/medications/router.py` → Clerk/database patient access → feature-scoped lease/request claim → deterministic input rules and NeMo input check → `extraction.py`/`ai/client.py`/typed schemas → extraction checkpoint → `validation.py` and `matching.py` → typed proposal checkpoint → deterministic readback plus NeMo output check → persist a pending question → explicit confirmation request with exact question/step/medication/version → proposal checkpoint in a separate short transaction → recheck question, lease, expiry, ownership, prescription and event revision → atomic event/question/request/conversation commit → `replies.py` composes the saved reply from committed event data.

The medication view uses ordinary JSON responses. `?stream=true` is also supported by the backend and streams only after processing/commit; ~~speech is still planned.~~ **28 October 2026:** Phase 5 adds separate optional speech after a completed result. The service stores the typed committed event snapshot and a small operation marker in the replay result, then composes the public saved message after commit, including on replays. Conversation reloads use the same rendering function. A lost response does not require repeating the write.

- Match against that patient's synthetic prescription list.
- Do not invent medicine names, strengths, units, or frequency. Preserve field provenance: user-reported versus prescription-derived.
- Read back and ask before applying an uncertain prescription match. Ask again if ambiguity remains.
- A pending question identifies its question ID, medication candidate, proposed fields, conversation version, owning workflow step, and expiry.
- Connect “yes” to that exact current question. It is never an independent instruction to record a medication.
- Retried request IDs cannot create duplicate events.
- Restrict edits to correcting the logged event time. No medicine/dose changes through the edit flow.
- Do not recommend dosage changes or tell the user they should take a medicine.
- Describe medication information as recorded events. A missing log does not prove a dose was missed.

Implemented medication details, **source only / unverified**:

- Report a single event such as `I took Metformin 500 mg now`, or `I took Metformin at 2026-10-26 09:00`, using the authorized patient's actual synthetic prescription name. This example is logging wording, not an instruction to take medicine. Missing strength/quantity/frequency remain null in `reported`.
- Each reported field has a literal value and evidence span from the current report. The full taking statement must also match the report. After removing the separately evidenced fields, unexplained words cause clarification. No prior report, prescription, or model-normalized unit can silently supply a reported field. Clarification asks for a fresh complete report; fragment-by-fragment medication draft assembly is deferred.
- Supported reported strengths are a literal number plus `mg`, `mcg`, `g`, `ml`, `iu`, `units` or `%`. Quantities require a number plus tablet/capsule/puff/drop/ml/unit wording. Optional frequency supports once/twice/number-of-times daily or weekly (including `a day`/`per day`/week variants). These are parsing limits, not dose recommendations. Other wording asks for a new report; no value or unit is converted or invented.
- Match names case/whitespace-insensitively first. If no exact match exists, use a conservative string-similarity candidate only when exactly one prescription qualifies. A possible match is explicitly labeled in the readback. Multiple matching candidates, unknown names, and duplicate exact names ask for a new report; no medicine is selected by the model. Only that patient's bounded prescription list is queried.
- Keep `reported` separate from `prescription_snapshot`. A reported strength different from the reference is retained as reported data, and both values are read back for confirmation. The workflow never modifies a prescription or asserts that the reported amount is clinically appropriate. Medicine names/strengths/units/frequency shown as reference come only from the patient's stored prescription.
- Resolve `now` to the original request-claim instant, retained in the checkpoint, rather than confirmation/retry time. Parse explicit local timestamps in Python using the patient's IANA timezone and store UTC instants plus the timezone. Reject future, invalid, ambiguous or nonexistent local times; do not guess yesterday, morning, time offsets or daylight-saving folds.
- A question expires after **15 minutes**. Conversation inactivity expiry remains configurable up to **24 hours**. A report creates no medication event until its current readback is confirmed. Confirmation carries `action=confirm`, conversation ID, question ID, step ID, prescription/medication ID and question version; version must equal the current conversation version. A text-only `yes` cannot save anything, even with a conversation ID.
- Confirmation/cancel controls use exact allowlisted text. They reuse a previously safety-checked proposal, without another model interpretation. Confirmation is rejected if any ownership token differs, the question is superseded/cancelled/consumed, the prescription changed, the event revision changed, or either expiry elapsed. A reply to an expired question explains expiry and requests a new report. Unknown/other-patient question IDs reveal no question contents.
- Any completed new turn consumes, cancels, expires or supersedes the old pending question before recording a new state. A failed provider/safety call leaves existing state intact; expiry still applies. A stale mismatched reply asks for a new report and does not transfer consent. Questions are not deleted when conversation state advances. Late replies naming an expired retained question still receive the expiry explanation after a newer report.
- Request identity is `(patient_id, request_id)` across features, with a feature check and a fingerprint of the complete typed body. An exact completed retry replays the committed event snapshot; changed input or reuse across features conflicts. New UUIDs are new operations: identical medicine/time reports under different request IDs are not automatically deduplicated because they may describe distinct reported events. Retry the original body first after a lost response.
- Claim, extraction/proposal checkpoint, and final write each use their own short transaction. Provider calls and response streaming happen outside transactions. The final transaction rechecks lease owner/version/deadline, current question/step/medication/version/expiry, prescription snapshot and correction revision. Event mutation, question disposition, conversation version and replay result commit together. A stale lease owner cannot release a newer owner's lease.
- Time corrections select an authorized existing event and its revision. The correction body is **only** `YYYY-MM-DD HH:MM` or `now`; it is parsed deterministically, checkpointed as a typed proposal, safety-checked and read back. Confirmation updates only `occurred_at`, `timezone`, `time_evidence`, revision and update timestamp. Original reported fields and prescription snapshot stay unchanged. A correction is unavailable if its current prescription reference differs from the event's original snapshot; this slice does not rewrite historical medicine details. Question history retains the correction proposal; there is no delete, medicine edit, dose edit or prescription-edit endpoint.
- The frontend retains failed request bodies for exact retries while mounted. Reloading the page loses that in-memory retry body; the database retains request results and question history. Refresh/reload recovers current questions but does not recreate a lost client request ID. Inspect records before starting a new operation if the original response was lost.

### Morning and evening briefs

~~`Briefs.tsx` → brief generation → streaming and optional speech.~~

**27 October 2026, source implementation:** `Briefs.tsx` → `features/briefs/router.py` → verified Clerk identity/local patient mapping → `service.py` claims the shared patient-scoped request and `briefs` lease → `repository.py` checks reuse → `context.py` gathers local facts/calculates metrics → context checkpoint → input rules/NeMo → `generation.py`/`prompts.py`/`ai/client.py` → typed `schemas.py` narrative → `validation.py` grounding/output rules and NeMo → validated narrative checkpoint → owner/version/lease/context-expiry check → brief and request-result commit → truthful saved/reused JSON reply. JSON delivery keeps this incremental slice simple; ~~brief streaming and speech remain deferred.~~ **28 October 2026:** streaming remains deferred; Phase 5 adds optional speech of the saved brief and focus. Provider calls never run inside database transactions.

- Generate on request; automatic scheduling is unnecessary.
- Morning: summarize relevant recent data and suggest a modest daily focus.
- Evening: summarize recorded activity and progress.
- Calculate metrics and goal outcomes in Python. Restrict suggestions to a small allowed catalog with deterministic bounds.
- State missing data honestly. Do not invent measurements, causes, diagnoses, or medication adherence.
- Reuse a morning brief for the same patient-local day.
- ~~Reuse an evening brief within a proposed **30-minute window**.~~
  **27 October 2026:** implement the proposed **30-minute window** from the saved instant, ending at patient-local midnight if earlier. Morning reuse ends at the next local midnight. The patient's current IANA timezone must match the saved timezone.
- Show when a stored result is reused and its saved time. It reflects its original context snapshot, not newly added records.
- Include a small “Based on” section with recorded facts, never hidden model reasoning.

**Written context and narrative behavior, unverified:**

- Morning reads the previous seven complete local days, excluding today's partial measurements. Evening reads today's local day to the capture instant. Python converts medication window boundaries to UTC using the patient's IANA timezone, including day-length changes. Meals use their recorded local day; measurements have day precision only.
- Context includes up to seven daily measurement rows, the first 20 goals ordered by ID, and up to 100 meals and medication events in the window. Queries fetch one extra goal/event/meal to detect truncation; sampled counts say **at least** when truncated. Every query filters the authorized patient. Narrative does not receive free-text profile summaries, foods, medicine names or instructions from records.
- Only finite, nonnegative supported measurements are used: integer steps up to 200,000 and sleep hours up to 24. These are input bounds, not healthy ranges. Missing/invalid measurements are labeled unusable per day. Python calculates recorded-day averages excluding missing days, and compares the latest window day to a single supported positive stored goal. Duplicate/unsupported goals produce missing-comparison wording. Goal outcomes compare recorded values only, not health or adherence.
- The real model chooses a typed narrative composition; Python checks fact identity/uniqueness and renders exact grounded clauses. Exactly one optional focus comes from three fixed choices: record one remembered meal, record activity already done, or note something noticed in the records. No exercise target, treatment action, nutritional estimate or medication recommendation is generated. All facts, missing-data messages and context limits remain visible even when the short narrative selects only some facts.
- “Based on” shows window dates, capture time, facts and expandable table/record/field or revision references. Goals/measurements/profiles are synthetic POC context, seeded medication events are explicitly labeled, and later corrections do not rewrite an earlier snapshot. Zero medication records means no reports in this window; it never means a missed dose.
- A new request UUID within a reuse window returns `reused: true` without another provider call. An exact completed retry returns the original result with `replayed: true`, even after the reuse window ends. History is a patient-only latest-30 read with no provider calls. There is no force-refresh action during a reuse window.
- Both brief kinds share one `briefs` conversation lease per patient. Context and validated typed narrative checkpoints precede domain writes; failed/expired owners cannot checkpoint or commit. An expired context or intervening completed turn requires a fresh request UUID. Retrying an interrupted request preserves its snapshot when still applicable. Brief rows and request-result writes commit together. A provider/safety failure produces an honest failure and no fallback brief.

### Unified meal/medication logging

`features/health_logs/router.py` → `planner.py` → `ai/client.py` → typed meal/medication steps in `schemas.py` → `service.py` executes the existing specialist services sequentially.

The planner proposes steps but cannot write records. Persist which step owns each pending question and which steps are complete. A retry must not repeat a completed step. Do not add other logging domains or elaborate autonomous orchestration. Dedicated meal and medication routes skip AI routing because their feature is already known.

**28 October 2026 — Phase 4 source implementation, unverified:**

- Patient navigation defaults to **Meals + medication** (`frontend/src/features/health_logs/HealthLogs.tsx`). Dedicated views remain mounted and retain their own retry bodies. Unified records use the same meal/event tables and appear in the dedicated histories after refresh. Unified replies use JSON; ~~streaming and voice remain future work.~~ **28 October 2026:** unified streaming remains deferred; Phase 5 adds voice input and separate optional playback of completed replies.
- `POST /api/health-logs/messages` and `GET /api/health-logs/conversation` require Clerk verification and authoritative patient mapping. No patient ID is accepted. The typed planner proposes at most **four** ordered steps, only `meals` or `medications`. Python requires exact contiguous source spans, ordered without overlap; only whitespace, punctuation and narrow conjunctions may separate them. Meaningful omitted text rejects the plan before any specialist runs. Literal source coverage cannot prove that the model chose the correct domain or semantic split.
- Non-logging dispositions are greeting, unsupported and clarification. Other logging domains, medical advice and brief generation are not executed here. Missing meal information is clarified by the meal specialist; missing medication information asks for a fresh complete statement. The coordinator does not synthesize medicine wording, dates, doses, prescriptions or consent.
- Deterministic rules and NeMo input/output checks precede the plan checkpoint. Existing specialists independently validate/safety-check their inputs and proposals. No safety or provider failure becomes a successful plan or fabricated domain result. The planner receives the current message only, not unrestricted patient records or tools.
- **Bounded execution decision — 28 October 2026:** one request executes at most one specialist step under the existing total turn deadline. A queued next step requires **Continue to next report**, avoiding an unbounded multi-provider turn. Pending clarification/readback blocks later steps. **Stop unfinished steps** marks unsaved steps stopped; saved steps remain saved. Cancelling a medication readback skips that event and allows later queued reports. A stopped specialist step does not invent a successful save.
- Root conversation scope is `health_logs`; specialist scopes are `health_meals` and `health_medications`. These are separate from dedicated `meals`/`medications` conversation state, so a dedicated screen cannot confirm or supersede a unified question. Unified meal steps retain saved-meal continuity for explicit corrections but start without an earlier unfinished draft. Saved domain queries and prescription matching still belong to the existing repositories.
- The current bounded workflow lives in `conversations.state` JSONB: workflow ID, original report instant, ordered stable step IDs, literal step text, status, specialist conversation ID, committed record ID/reply, and current pending question. Each pending question carries a new outer question ID, owning workflow/step, root conversation version and deadline. Medication readbacks additionally retain the complete immutable specialist question/step/medication/version/conversation binding. Permanent `medication_questions` retain the original proposal and disposition as before. Historical root outcomes remain in completed request results; no new retention cleanup is added.
- Reply actions are `report`, `answer`, `confirm`, `cancel`, `continue`, and `abandon`. A clarification reply names the current conversation/workflow/question/step/version; Continue names the current queued step and version. Medication confirmation/cancel also submits the exact nested `MedicationMessage` readback binding. Python compares it with the current stored binding, then the existing medication service rechecks consent, prescription, question, event revision and expiry at commit. Generic `yes`, unrelated/stale bindings and old screen controls cannot supply consent. Time corrections continue through **Medication events** and retain the existing time-only readback/confirmation boundary.
- Questions expire after 15 minutes, bounded by the medication question's deadline when applicable. Root inactivity expiry remains configurable up to 24 hours with monotonically increasing versions. Expired questions/conversations cannot authorize new writes; saved records remain. A new report can replace an expired workflow. The original mixed-report claim instant anchors `now` for queued reports even when Continue happens later; a fresh complete medication clarification uses its own request instant.
- **Day-boundary decision — 28 October 2026:** a unified workflow also expires at the next patient-local midnight after its original report. This keeps queued meals within the specialist's today-only scope. Question and child-write deadlines are bounded by that midnight; start a new report after it. Saved records and completed retry results remain retained.
- Each outer request has a patient-scoped full-body fingerprint and checkpoint. Its specialist request UUID is derived from the outer UUID and stable step ID, and its exact typed body is checkpointed **before** invocation. Specialist commit and specialist replay result remain atomic. Progress and final root result use separate short transactions. If interruption falls between those commits, exact child replay recovers the domain result without rerunning its write. An operation with a saved step result skips specialist invocation on retry. This is recoverable partial progress, not an atomic multi-record transaction or an exactly-once guarantee across new UUIDs.
- Shared `Turn` optionally carries the parent owner/version/deadline. Child claim, checkpoints and final domain commits verify the parent in the same short transaction. Parent takeover or deadline expiry fences old child writers. Parent/child rows are not held across provider calls. Expiry during clarification prevents a later new child write; a previously completed child result can still be read back. A new root request is blocked while an unexpired interrupted request owns the workflow, preventing a new plan from bypassing unknown partial progress.
- GET returns current progress and, when a specialist body was persisted, the original root retry body for reload recovery. A completed retry can describe an older result; the UI reloads current controls rather than turning a replayed old readback into a current question. If interruption occurs before the recovery body checkpoint, retry using the original browser body or wait for inactivity expiry. Inspect dedicated records after lost responses; restarting with a fresh UUID can create a distinct report.

**Schema/setup — 28 October 2026:** no new relational fields, tables, enum constraints or migration are needed for this slice. The existing `feature` string columns and JSONB conversation/request checkpoints hold the additional scopes and bounded workflow state; medication question/event and meal schemas are reused. Revision `0003` remains the current migration head. Rebuild/restart API and frontend yourself using the existing setup commands; keep the existing worker for meal insights. No new dependencies, provider settings or environment placeholders were needed. Existing `.env` contents were not read or changed.

### Voice and supported browser

`VoiceRecorder.tsx` → `speech/router.py` → `speech/stt.py` → editable transcript → the same text workflow → text reply → `speech/tts.py` → Cartesia audio playback.

**28 October 2026, Phase 5 source:** voice controls are available in the unified, meal and medication composers. Stop (or the 60-second browser limit) sends the recording for transcription. Review/edit the transcript, choose **Replace message with this transcript**, review the main message, then submit through the existing text endpoint. This explicit replacement preserves the existing draft until chosen. Recording and transcription never acquire a logging lease, create a record, submit a message, or confirm a medication event. Medication confirmations continue to require the current bound button controls; spoken “confirm” cannot supply their action/ownership fields.

**Output:** a **Listen · AI-generated voice** button prepares audio; the native audio controls start/pause playback. There is no autoplay. Meal and medication playback appears after a completed/recovered message in this mounted view; their legacy conversation reloads have no request ID, so their reloaded text is not offered as a speech source. Unified reloads can recover the last completed request ID. Saved brief cards, including history, support playback of their narrative and focus. Brief context facts, missing-data lists and provenance remain visible in text and are not all narrated.

**Backend boundary:** `POST /api/speech/transcriptions` accepts a raw `audio/webm` or `audio/webm;codecs=opus` body. Authentication and the patient-role/local-patient mapping are required. Uploads are streamed into memory with a 2 MiB ceiling and a 20-second upload deadline; the EBML signature is checked, with actual decoding delegated to the configured STT provider. Transcription returns only a readable nonempty transcript of at most 2,000 characters. It has no domain side effects. Edited transcripts receive the existing feature input rules, NeMo, extraction, validation and confirmation safeguards when submitted.

`POST /api/speech/audio` accepts `{feature, source_id}` only. `feature` is `meals`, `medications`, `health_logs`, or `briefs`; `source_id` is the completed request UUID, or the brief UUID for `briefs`. A short DB lookup enforces patient ownership, feature and completed status, or ownership of the saved brief. Arbitrary browser-supplied text is not accepted. Medication operation markers are rendered through the existing saved-reply presenter. The DB connection is closed before deterministic output checks, configured NeMo output checks and Cartesia generation. Speech failures never reverse or repeat the domain write. Missing/foreign sources return the same 404; clinicians and unmapped accounts cannot use speech endpoints.

**Bounds and cleanup:** STT uses the existing OpenAI Python SDK against a separately configured OpenAI-compatible API root supporting `/audio/transcriptions`, WebM/Opus and JSON results. It does not inherit the text key, model or Azure API-version settings. Cartesia uses its Python v4 SDK, a configured voice/model, English and 24 kHz PCM WAV. Both adapters have a configurable 45-second default deadline and disable automatic retries. Speech checks can add the configured NeMo deadline. WAV generation is buffered in memory up to 20 MiB and accepted only with a WAV signature; responses use `Cache-Control: no-store`. Browser requests time out at 90 seconds. The browser stops tracks and cancels pending requests on cancellation, view changes or unmount; late results are ignored. Starting a recording pauses current playback; playback is paused and local audio URLs are revoked when its source/view changes or recording begins. Local raw audio is not written to disk or the database. Cartesia receives `save=False`; provider-side processing/retention still follows the configured provider/account policy. Cancellation cannot guarantee cancellation of provider work already accepted by the server.

- Support desktop Google Chrome only for this POC. Other browsers and mobile support are outside the initial supported scope.
- Use push-to-talk with MediaRecorder and request `audio/webm;codecs=opus` after a runtime `isTypeSupported` check. Upload with the actual recorder MIME type; never relabel WebM bytes as WAV.
- The configured transcription provider must accept WebM/Opus. A provider requiring another format needs an explicit conversion adapter and a plan update before implementation.
- Configure transcription separately from text generation; do not assume a text deployment supports audio.
- Use localhost or HTTPS for microphone access. Bound recording duration and upload size, and protect speech endpoints with authentication and applicable patient access checks.
- Handle microphone denial, recording errors, unsupported format, transcription errors, medication-name/number ambiguity, and audio playback failures.
- Keep the transcript editable before submission. Recording/transcription alone does not create a domain record.
- Preserve a usable text response if Cartesia generation or playback fails. Do not retain raw recordings by default.
- Full-duplex conversation, interruption handling, and always-listening audio are excluded.

Reference: [Chrome MediaRecorder guidance](https://developer.chrome.com/blog/mediarecorder).

SDK references read during implementation (documentation only, no provider calls): [OpenAI transcription API](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create), [Cartesia Python SDK](https://github.com/cartesia-ai/cartesia-python), [Cartesia generated TTS resource](https://github.com/cartesia-ai/cartesia-python/blob/main/src/cartesia/resources/tts.py).

## Conversation concurrency, expiry, and retries

### Reference inspection and independent implementation

Read-only source inspection of Smart Coach found that its `smartcoach/conversations.py` uses version-checked updates and short transactions, explicitly avoiding an open transaction during model calls. Its separate `smartcoach/idempotency.py` uses expiring write claims and an attempt counter. These are separate mechanisms; the reference does not establish that it already uses the proposed conversation timestamp lease.

SwasthMode will implement its own simpler mechanism and prompts. The reference repository was not modified or executed.

### Expiring turn lease

- Atomically acquire a conversation lease with a conditional update and commit immediately. Store an owner token, expiry timestamp, and conversation version.
- Refuse an overlapping active turn with 409 and a clear busy state rather than waiting through another model call.
- Set the lease longer than the configured total turn deadline, including bounded provider retries. Mixed-step execution must also fit that deadline or stop with persisted progress.
- Do not hold a database transaction or connection open across external AI calls, speech generation, or streaming.
- Before every checkpoint/domain write, verify the owner, version, and lease expiry in the same short transaction as the mutation. A late attempt cannot save after takeover.
- Final local domain writes, conversation outcome, and completed request status share a short database transaction where possible.
- Release only the current owner's lease after finalizing state, before final response delivery and speech generation. Client playback cannot hold the lease.
- Crash recovery is possible after expiry. Do not claim exactly-once processing or production-grade distributed recovery.

### Conversation and confirmation expiry

- The planned continuity window is **24 hours of inactivity**, refreshed on an accepted completed turn. This is a reviewable POC choice, not a retention policy for all records.
- Saved meals, medication events, insights, and briefs remain after conversation expiry.
- Expiry makes pending extraction/confirmation state non-actionable; it does not immediately delete the conversation row.
- ~~Retain only minimal expired-state metadata: patient ownership, conversation ID, expiry, pending feature/question ID, and expired status.~~
  **27 October 2026:** medication questions retain these identities plus the bounded typed proposal/readback and disposition. The immutable proposal supports exact consent and time-correction history; full multi-turn conversation transcripts are not collected by the medication workflow. Keep these rows and completed request identities until a separate retention/replay policy is decided.
- If a late “yes” refers to an expired medication confirmation, reply: “That medication confirmation has expired. Please tell me again which medication you want to record. Nothing was saved from this reply.” Do not interpret it as a fresh medication event.
- The client submits conversation and pending question IDs with replies. Reject stale mismatched questions rather than transferring consent to a different medication.
- A stale/unknown conversation ID receives an ended-session explanation. A bare confirmation without enough context asks what the user is confirming and writes nothing.
- Decide and document physical cleanup/retention separately before adding a cleanup job. Do not silently delete the metadata required to explain a stale confirmation.

### Requests, checkpoints, and background jobs

- Persist patient-scoped client request IDs, input fingerprints, status, and replayable results. Reusing an ID with different input returns a conflict.
- Save validated AI extraction as a checkpoint before domain writes; a retried attempt can reuse applicable extraction.
- Keep completed request identities independent of active conversation expiry so a known stale retry cannot become a new write. Document a replay-window policy before introducing request cleanup.
- Give mixed-workflow steps distinct operation keys; completed steps do not run again.
- Queue insight generation only after meal commit. If enqueueing fails, preserve the saved meal and show a truthful insight failure/retry state.
- Make insight jobs retry-safe and revision-aware. Outdated results cannot replace current insights.
- Use bounded provider timeouts/retries and clear pending, failed, and saved states.

## Meal insights versus nutritional estimation

Meal insights are short qualitative observations grounded in the recorded foods and explicit quantities. For a rice, dal, and curd log, an insight could acknowledge that combination and suggest recording portions next time for a more informative log.

Do not estimate calories, protein grams, carbohydrates, micronutrients, serving sizes, or nutritional scores. Do not claim nutritional adequacy, medical suitability, or predicted health outcomes from an incomplete log. Nutritional estimation, pledges, and AI-generated meal pictures remain outside scope.

The background insight uses a real model. Provider failure is shown as failed; it never becomes a canned successful insight.

## Layered guardrails and NeMo

### Licensing and running cost

NVIDIA's NeMo Guardrails **Python library is free and open source under Apache License 2.0**. SwasthMode uses that library inside the existing backend/worker, not a second application platform. Its self-check rails ask an LLM to classify inputs/outputs; those requests use the configured AI provider and can cost money even though the library has no license fee. No safety-model calls or paid connectivity checks have been made by the agent.

Sources checked for this decision: [NeMo license](https://github.com/NVIDIA-NeMo/Guardrails/blob/develop/LICENSE.md), [native integration and optional LangChain support](https://docs.nvidia.com/nemo/guardrails/get-started/integrate-into-application), [LLM self-check rails](https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/self-check), and [validation-only APIs](https://docs.nvidia.com/nemo/guardrails/run-guardrailed-inference/using-python-apis/generation-options). NeMo 0.22 and later provide a native OpenAI-compatible integration, so LangChain remains outside our application architecture.

### What each layer controls

1. **Our rules:** input length/control-character checks, simple prompt-injection and medical-advice patterns, and deterministic output restrictions such as no estimated nutrient amounts. These are cheap, readable Python rules that can block obvious cases before paid checks.
2. **NeMo input/output rails:** model-backed policy checks using our SwasthMode prompts. They add interpretation of policy violations beyond exact patterns. The adapter calls `LLMRails.check_async` with explicit input or output rail types; NeMo does not generate application replies, select operations, or write records.
3. **Application safeguards:** Clerk verification, PostgreSQL role/assignment checks, Pydantic schemas, food/medication evidence validation, exact pending-question ownership, permitted-operation checks, leases, and duplicate protection remain Python responsibilities. A NeMo pass never overrides them. Medication-specific safeguards now have source and remain unverified.

Current source coverage: nontrivial meal text and its recent bounded message context; structured meal proposals before domain writes; AI meal-insight text before storage; medication reports/time-correction requests before proposal creation; and medication proposals before persisting a readback. Medication policies explicitly allow reporting medicine/strength data and prescription references without treating them as prescribing. Exact allowlisted greetings, bound confirmation/cancel controls, bare-reply refusals and code-composed clarification/refusal messages avoid unnecessary model calls. Saved messages use validated committed fields; no LLM generates them. Completed-request replays do not generate or write a new record. Existing records are not retroactively rechecked.

Briefs apply this boundary to bounded context input and rendered generated output. The unified planner now applies it to current input and typed plans, with specialist checks retained. ~~Voice must adopt it when implemented.~~ **28 October 2026:** edited voice transcripts enter the existing feature checks on message submission, and server-resolved speech text receives deterministic plus configured NeMo output checks before synthesis. Transcribed text must enter the same input checks, and generated narrative must be checked before saving/displaying/speaking it. A blocked insight must not invalidate a meal that was already saved.

### Configuration and failure behavior

- `GUARDRAILS_MODE=hybrid` is the default and runs both layers. `rules_only` is an explicit developer configuration for running without NeMo; it must not be described as hybrid protection. There is no browser toggle and no silent fallback.
- `NEMO_MODEL` names a deliberately selected safety-check model/deployment on the configured `AI_PROVIDER` and `AI_BASE_URL`. It may equal `AI_MODEL` if configured explicitly. No model name is guessed.
- `NEMO_API_KEY` optionally supplies a separate backend key for that same provider; blank uses `AI_API_KEY`. Azure also uses `AI_API_VERSION` and the configured Azure resource endpoint.
- `NEMO_TIMEOUT_SECONDS` bounds each check (default 12 seconds), including adapter initialization and the provider call. `NEMO_MAX_TOKENS` controls the self-check response budget (default 1024). Use a compatible model; reasoning models may require a larger budget. An exhausted turn still cannot write after its deadline/lease.
- A block produces a code-composed explanation, with no new meal write. Modified outputs are rejected rather than silently rewriting reported facts.
- If NeMo cannot load, is misconfigured, times out, or errors, the API returns 503 before a new domain write. An insight job shows failed status and follows its bounded retry policy. It never substitutes a fake successful safety verdict.
- NeMo verbose/conversation logging is suppressed. Operational logs record only the layer, direction, and allowed/blocked/unavailable status, not raw prompts, safety verdict text, credentials, or patient conversations.
- Each check uses its own NeMo runtime instance to avoid sharing mutable conversation caches across patients or Celery event loops. This favors clarity over initialization speed for the POC.

The two layers can still miss harmful content or block legitimate reports. NeMo is not a clinical validator and cannot prove that an extracted fact is true. It adds latency and model cost; it does not replace deterministic evidence/permission checks or make the POC production-ready. No automated or agent-performed functional checks are added under this change.

## Read-only clinician dashboard

Use `features/clinician/router.py` and `queries.py` to show:

- Assigned synthetic patient list and profile summaries.
- Recent meals and meal insights with their statuses.
- Recorded medication events.
- Latest existing morning and evening briefs.
- Basic date filtering where straightforward.

Enforce clinician assignments on every query. Use existing records without unnecessary AI calls. No creating, editing, or deleting patient logs; prescribing; dosage changes; brief generation on a patient's behalf; clinician AI chatbot; messaging; appointments; care plans; clinical alerts; advanced adherence scoring; or role-management interface.

Missing medication records must not appear as confirmed missed doses.

**Phase 6 source decisions — 28 October 2026:** reuse existing `Patient`, `Account`, `Assignment`, `Meal`, `MedicationEvent` and `Brief` records and existing typed record views. The two clinician endpoints are GET-only:

- `GET /api/clinician/patients?offset=0` returns at most 50 assigned profiles ordered by name/ID, with `has_more`. Offset is bounded to 0–10000; no global patient search/count is exposed.
- `GET /api/clinician/patients/{patient_id}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` returns the profile, at most 100 meals and 100 events, independent truncation flags, and the latest existing brief of each kind within the selected range. Both date bounds are inclusive. Default end is today in the patient's current timezone; default start is 29 days before end. Allowed ranges span 1–90 days within 1900–2100. Meals/briefs use their saved local date; medication instants use UTC boundaries derived separately from the patient's local midnights.

Both routes depend on existing backend Clerk verification and a fresh database clinician-role check. Every profile/domain SELECT also includes an authoritative account-role/assignment subquery scoped to the verified Clerk identity and requested patient. Unknown and unassigned valid patient UUIDs return the same 404, malformed UUID/date/range input returns 422, patient/unmapped accounts return 403, and missing/invalid sessions return 401 when Clerk is configured. Existing missing-Clerk-configuration behavior remains 503. No clinician endpoint invokes AI, speech, Celery, generation, domain writes, or conversation/request recovery. No new tables, migrations, dependencies, environment variables or private `.env` edits are needed.

The clinician frontend replaces the role/assignment-count placeholder with list/detail navigation, pagination, refresh, date filters, loading/empty/error/session-expiry messages, insight status and explicit incomplete-history notices. Briefs retain saved context, missing-data statements and limits. There are no logging, correction, confirmation, generation, speech or role-management controls in this area.

### Phase 6 source review — 28 October 2026, unverified

Source inspection traced both registered clinician routes through Clerk verification, the database clinician dependency and assignment-scoped profile/domain queries. The assigned-list/profile, meals/insight statuses, reported medication events, saved briefs, bounded dates, read-only controls and honest missing-data requirements have source. This is a source assessment, not evidence of runtime correctness. No tests, builds, migrations, startup, browser exercises, provider/API checks or paid requests were run.

Review fixes written in source:

- `frontend/src/App.tsx` keys the workspace by Clerk user and session IDs so changing accounts/sessions remounts the workspace, discarding the previous account's clinician selection, saved responses and patient drafts. Account loading now aborts on unmount and ignores late results; retry uses the same cancellation-aware path. Backend permissions remain authoritative.
- `features/account/router.py` counts clinician assignments in SQL instead of materializing every assigned patient ID during workspace startup. The aggregate also includes the authoritative clinician role predicate.
- Clinician queries convert invalid stored timezone keys (including malformed/path-like keys) into the documented configuration error instead of an unhandled `ValueError`.
- ~~Default start is always 29 days before end.~~ **28 October 2026 review:** default start is 29 days before end, clamped to 1900-01-01. This prevents a valid early-1900 end date from producing an out-of-bounds default range. Explicit dates still require 1–90 inclusive days within 1900–2100.
- The detail view adds **Reset to latest 30 days**, including recovery from a rejected date range. Where a browser cannot format a server-supported timezone, medication event display falls back to the saved timestamp rather than failing the whole view.

Clinician file flow: `frontend/src/main.tsx` → Clerk provider → `App.tsx` (signed-in/session-keyed workspace) → `api/client.ts` → `features/account/router.py` (verified identity and local role) → `ClinicianDashboard.tsx` list/detail → authenticated GET through `api/client.ts` → `backend/app/main.py` registered `features/clinician/router.py` → `core/auth/permissions.py::clinician_access` → `core/auth/clerk.py::identity` → database account-role check → `features/clinician/queries.py` (role/assignment-scoped SELECTs and bounded local-date/UTC windows) → existing patient/meal/event/brief models → clinician response schemas and reused domain views → read-only React cards. FastAPI resolves authentication dependencies before executing the endpoint/query function. There is no guardrails, extraction, AI or write stage in this read-only flow; those stages belong to the patient logging/generation flows documented above.

## Interface plan

A distinct, simple SwasthMode interface will include Clerk account controls, role-appropriate navigation, a voice/text composer, editable transcripts, meal and medication views, a daily timeline, morning/evening brief cards, insight statuses, and the limited clinician dashboard.

Make saved, pending, failed, reused, busy, expired-session, and account-setup-required states explicit. Text remains usable when speech fails. Do not copy proprietary assets or UI wording.

## Phased implementation plan

- [x] Record the revised architecture and PostgreSQL choice in this README.
- [x] User reviews this README and approves implementation.
- [x] Phase 1 — Source written, unverified: local infrastructure, migrations, synthetic profiles/prescriptions/measurements/goals/meals, Clerk verification, developer account mapping, and text meal creation/clarification with persisted state, authorization, and guarded writes.
- [x] Phase 2 — Source written, unverified: meal corrections, meal timeline, duplicate protection, revision-aware background insights, Flower configuration, and pending/failed states.
- [x] Guardrail addition — Source written, unverified: our rules plus NeMo input/output checks for the current meal slice, hybrid configuration, and explicit failure behavior. No installation, model check, or application exercise performed.
- [x] Phase 3 — Source written, unverified: medication extraction/provenance, deterministic validation, prescription matching/readback, exact confirmations, retained expired questions, duplicate protection, logged-time corrections, synthetic events, patient navigation/composer/timeline, and README setup/schema/manual guide. No tests, installs, migrations, startup, builds/type checks, application/API exercises or provider checks were run.
- [x] Phase 4, brief portion — Source written, unverified on 27 October 2026: bounded context, Python metrics/goal comparisons, typed real-provider narrative composition, deterministic grounding, allowed focus catalog, NeMo boundaries, immutable snapshots, morning/evening reuse, retry checkpoints, explicit migration and patient UI. This chat retains **Phase 3** in its name as requested; this checklist's internal phase numbering is unchanged. No functional checks were run.
- [x] Phase 4, mixed logging — Source written, unverified on 28 October 2026: bounded typed planner, sequential specialist reuse, durable workflow/question ownership, parent-fenced checkpoints/writes, exact nested medication bindings, reload recovery, partial-save status and patient UI. This chat is **SwasthMode Phase 4 — Unified Meal and Medication Logging**. No tests, builds, provider checks or application exercises were run.
- [ ] ~~Phase 5 — Voice and clinician area: Chrome WebM/Opus recording, transcription, editable transcripts, Cartesia output, and read-only assigned-patient views.~~
- [x] **Phase 5, voice — 28 October 2026:** Chrome WebM/Opus recording, separately configured transcription, transcript review/edit/explicit transfer into the message, Cartesia playback of completed replies and saved briefs, patient-scoped speech APIs, limits, cancellation and text-preserving error states are written in source, unverified. This chat is **SwasthMode Phase 5 — Voice Input and Output**. No tests, builds, provider checks or application exercises were run.
- [ ] ~~Phase 5, remaining clinician area: read-only assigned-patient detail views remain planned. Split from voice on 28 October 2026 to follow the user's requested voice-only increment.~~
- [x] **Phase 6, clinician dashboard — 28 October 2026:** assigned synthetic patient list, bounded read-only patient details, basic date filtering, existing meals/insight statuses, recorded medication events and latest saved morning/evening briefs; backend Clerk verification plus authoritative role/assignment queries; frontend navigation/states; README endpoint/setup/limitations and unchecked user-only manual guide. Source written, unverified. Renumbered from the remaining Phase 5 area at the user's request. No tests, builds, startup, migrations, provider checks, paid requests or app/API exercises were run.
- [ ] ~~Phase 6 — Complete this README with commands and instructions reflecting the actual implementation, schema, limitations, and demonstration script.~~
- [ ] **Final documentation/demo follow-up — 28 October 2026:** remaining full demonstration wording and user-reported verification, after the clinician increment now named Phase 6. Setup/schema/source limitations and manual guides are maintained below; no demonstration success is claimed.

After approval, implement incrementally, explain decisions in simple English, and keep changes focused. Do not perform testing on the user's behalf.

## Secrets and configuration to supply

| Area | Required configuration |
| --- | --- |
| PostgreSQL | Local database name, username, password, and connection URL |
| Redis | Local broker/result configuration |
| Clerk frontend | Development publishable key |
| Clerk backend | Secret key, issuer, narrowly allowed frontend origins |
| Account setup | Verified Clerk patient/clinician IDs and synthetic patient assignments |
| Text AI | Endpoint, API key, configurable model/deployment, provider mode/API version if applicable |
| NeMo safety checks | `GUARDRAILS_MODE=hybrid`, explicit `NEMO_MODEL`, optional backend `NEMO_API_KEY`, per-check timeout and token budget; shares the configured AI provider/endpoint |
| Transcription | `STT_BASE_URL` API root, `STT_API_KEY`, `STT_MODEL`; separate OpenAI-compatible transcription service accepting WebM/Opus and `response_format=json` |
| Cartesia | Backend-only `CARTESIA_API_KEY`, `CARTESIA_VOICE_ID`, `CARTESIA_MODEL`; an English-compatible voice/model supporting WAV output |
| Speech limits | `SPEECH_TIMEOUT_SECONDS=45` (10–60); fixed 60-second browser recording and 2 MiB upload ceiling; 2,000-character transcript ceiling |
| Patient timezone | IANA timezone, default `Asia/Kolkata` for synthetic profiles |

Never display API keys, session tokens, or credentials. Do not modify an existing `.env` or display its contents. Provide `.env.example` with placeholders only. Backend secrets stay on the backend; only Clerk's publishable key belongs in frontend configuration.

Do not guess deployment names or perform paid checks/sample AI requests. Keep health information in PostgreSQL, not Clerk metadata.

Bind PostgreSQL, Redis, and Flower to loopback by default and configure frontend origins narrowly. Logs should contain only minimal request IDs, duration, task status, and model/deployment identifiers, excluding raw conversations, credentials, tokens, and raw audio.

## Local startup and shutdown

The commands below are for the user to run. They have not been executed by the agent. Use desktop Chrome and Docker Desktop with Linux containers. For optional host development, install uv and Node.js 22.12+ first.

Work in the approved project directory:

```powershell
Set-Location 'C:\Users\shraddha.choudhary_c\Desktop\SwasthMode'
```

If `.env` does not already exist, copy the example yourself. Do not overwrite an existing file:

```powershell
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
```

Edit `.env` privately. Fill PostgreSQL credentials and both database URLs, Clerk development keys/issuer, the text AI endpoint/model/key, **`NEMO_MODEL` for the default hybrid safety checks**, and Flower basic authentication. If you already have an `.env`, manually add the new guardrail settings from `.env.example`; do not overwrite your file. Use the same database credentials in both URLs; percent-encode special characters in URL passwords. Only the frontend publishable key goes to the frontend container. ~~Voice settings are placeholders for a later slice and are not consumed yet.~~ **28 October 2026:** Phase 5 consumes the STT/Cartesia fields and `SPEECH_TIMEOUT_SECONDS`. Set these privately before using voice; text workflows do not require speech credentials. No existing `.env` was read or changed.

For voice, set `STT_BASE_URL` to the provider's API root, not its `/audio/transcriptions` route. Choose an audio model with WebM/Opus plus JSON output; ordinary text deployments are insufficient. The initial adapter supports OpenAI-compatible transcription, without a dedicated Azure speech adapter. Select the Cartesia model and voice in your account and fill their IDs; no model, voice or key is guessed. Backend dependencies now include `cartesia>=4,<5`: when you choose to run the app, sync the backend dependencies or rebuild its API image with the startup commands below. No additional database migration or frontend dependency is introduced by voice. No dependencies were installed or resolved during this phase.

Build images, start local storage, migrate, and seed:

```powershell
docker compose build
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m app.cli seed
docker compose run --rm api python -m app.cli patients
```

The backend image uses uv to install Python dependencies. Migrations and seeding are explicit commands; starting the API does not silently migrate or reseed. Seed data includes three demo patients, one synthetic prescription each, five days of measurements with intentional missing values, goals, a previous-day meal, and two explicitly synthetic medication events per patient at 09:00 local time on previous days. Seeded meals have `not_requested` insight status and no canned AI insight. Medication events are synthetic domain data, not simulated provider responses or claims of real medication use.

For an existing first-slice database, rebuild the backend/frontend images yourself, run the same `alembic upgrade head` and `python -m app.cli seed` commands, then restart the services. New migration `0002_medication_events.py` follows revision `0001`; it adds tables without recreating existing ones. Re-running seed preserves existing profiles, prescriptions, meal records and medication events; it inserts only missing deterministic medication seed IDs for the three known synthetic profiles when their matching prescription still exists. It does not reset user corrections to seeded events or call AI. No additional environment variables or dependencies were required for the medication slice; existing `.env` files have not been read or changed by the agent.

For the brief slice, use the same user-run rebuild/migrate/restart sequence. `0003_briefs.py` (revision `0003`) follows the actual medication revision **`0002_medication_events`**, not a revision named `0002`. It adds only `briefs`. Brief generation uses the existing text AI and NeMo settings; no new dependencies, worker tasks, seed briefs or environment settings were added. Seed does not generate briefs or contact a provider. Existing `.env` contents remain unread and unchanged.

NeMo 0.24.1 is declared in `backend/pyproject.toml` using its native integration; no LangChain dependency is explicitly added. Dependency resolution remains unverified. After changing these dependencies or settings, rebuild the backend image and restart API/worker containers yourself. The agent has not run an install or build.

Map accounts using the next section, then start the app:

```powershell
docker compose up -d api worker flower frontend
```

- App: [http://localhost:5173](http://localhost:5173)
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
- Flower: [http://localhost:5555](http://localhost:5555), using your configured basic-auth credentials.

The process-only `/health` endpoint does not check database/provider connectivity or prove readiness. Compose's database/Redis health checks are runtime infrastructure behavior, not checks the agent executed.

Stop services without deleting PostgreSQL or Redis volumes:

```powershell
docker compose down
```

### Backend debugging with debugpy — 28 October 2026

Debug mode is opt-in through `compose.debug.yaml`, layered over `compose.yaml`. It covers the running backend only: the API (routers, services, repositories, AI/guardrail/speech adapters) and the Celery worker (background meal insights). It does not configure tests, CLI scripts, Flower or the frontend. `debugpy` lives in the `debug` dependency group in `backend/pyproject.toml` and is installed only when the debug override passes `UV_SYNC_EXTRA="--group debug"` to the image build; the default build still runs `uv sync --no-dev` alone.

```powershell
docker compose -f compose.yaml -f compose.debug.yaml up -d --build api worker
```

Then, in VS Code with the Python Debugger extension, choose **Run and Debug** → **Attach: API** (port 5678), **Attach: Worker** (port 5679) or **Attach: Backend** (both). `.vscode/launch.json` maps `backend/app` to `/app/app` in the containers. Set breakpoints in `backend/app/**` and exercise the app normally. Both ports bind to `127.0.0.1` only.

Debug-mode behavior:
- `backend/app` is mounted read-only into the API and worker containers, so source edits apply after `docker compose -f compose.yaml -f compose.debug.yaml restart api worker` without a rebuild. There is no auto-reload, because uvicorn's reloader runs the app in a child process that the debugger would not follow.
- The worker runs Celery with `--pool=solo`, so tasks execute one at a time in the debugged process. This is slower than the normal worker and is for debugging only.
- Pausing at a breakpoint holds the request open. Provider, browser (90 seconds), speech and conversation-lease deadlines keep running, so long pauses can produce timeouts or busy responses that would not occur otherwise.
- `justMyCode` is on; set it to `false` in `.vscode/launch.json` to step into FastAPI, SQLAlchemy or SDK code.

Return to normal mode with `docker compose up -d --build api worker`. Debug mode is for local development only.

**Do I have to start in debug mode to debug?** Yes. VS Code can only attach to an API or worker process that was started under debugpy; a normally started container has no debug port. You do not need to switch per session, though:
- Debug mode persists until those containers are recreated. Attaching or detaching the debugger does not change it, and the app works normally with no debugger attached.
- During development you can simply leave debug mode on. The API runs at normal speed when no breakpoint is hit; the only standing cost is the worker's one-task-at-a-time solo pool.
- A plain `docker compose up -d` (or `up -d api worker`) without `-f compose.debug.yaml` recreates the API and worker in **normal mode**, silently ending debug mode. Use the `-f compose.yaml -f compose.debug.yaml` form consistently while debugging.
- Optional: to make every plain `docker compose` command use debug mode, add `COMPOSE_FILE=compose.yaml;compose.debug.yaml` to your private `.env` (`;` separates files on Windows). Remove that line to return to normal plain commands. This is a personal choice and is not set by default.
- To check the current mode, run `docker compose ps api worker`. Debug mode shows ports `5678` (API) and `5679` (worker); normal mode does not.

**Editor warnings such as "Package `sqlalchemy` is not installed in the selected environment"** come from VS Code inspecting `backend/pyproject.toml` against your host Python. The backend's dependencies are installed inside the Docker images, not on the host, so these warnings do not affect the running app or debugging. To remove them and get editor autocomplete, optionally run `uv sync --group debug` in `backend/` and select `backend/.venv` as the VS Code Python interpreter.

### Optional uv host development

Run PostgreSQL/Redis in Compose. Root `.env` uses host database/Redis URLs; Compose overrides them for containers. In `backend/`:

```powershell
uv sync
uv run alembic upgrade head
uv run python -m app.cli seed
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In a separate terminal, from `frontend/`:

```powershell
npm install
npm run dev -- --host 127.0.0.1
```

For host frontend development, provide only `VITE_CLERK_PUBLISHABLE_KEY` and optional `VITE_API_URL` in your local frontend environment. Root `.env` is not automatically loaded by Vite. No frontend environment file is created by the agent.

On Windows, keep Celery/Flower in the Linux containers; native Windows Celery workers are not the supported path for this POC. Do not start a second API on the same port if the Compose API is already running.

No lockfiles have been fabricated. `uv sync` and `npm install` resolve dependencies on the user's first run. To adopt reproducible builds, generate and commit the real `backend/uv.lock` and `frontend/package-lock.json`, then change the Dockerfiles to copy them and use locked installation. Until then, dependency resolution and compatibility remain unverified. See [uv project guidance](https://docs.astral.sh/uv/guides/projects/) and [uv Docker guidance](https://docs.astral.sh/uv/guides/integration/docker/).

The planned sequence is: configure local secrets privately → start PostgreSQL/Redis → migrate → seed synthetic profiles → configure Clerk accounts and map them with the developer command → start API/frontend/worker/Flower.

Shutdown instructions must distinguish stopping containers from deleting data. Do not make data deletion the default shutdown action.

## Clerk and developer account setup guide

Create or use a Clerk **development instance**. Configure the frontend origin as exactly `http://localhost:5173`, and use that origin consistently rather than mixing `127.0.0.1` and `localhost` in the browser. Enable the desired prebuilt sign-in methods and sign-up if you want it. Obtain backend and publishable keys privately from that same instance. Set `CLERK_ISSUER` to its exact token issuer URL, without adding an extra slash.

The backend uses Clerk's Python SDK for signature/time validation, then checks the verified issuer, authorized party, expiry, subject, and session ID. Optional `CLERK_JWT_KEY` is the public PEM signing key from that instance; it is not the publishable key. Without it the SDK may retrieve signing keys from Clerk. A failing authentication never falls back to an unverified user ID.

Use Clerk's prebuilt sign-in screen in the app. An account without a local mapping sees setup required. Copy its verified user ID from your Clerk dashboard, and obtain synthetic patient IDs using `patients`. Replace the sample IDs below with your own; these are placeholders, not real accounts:

```powershell
docker compose run --rm api python -m app.cli map-patient --user-id user_replace_patient --patient-id replace_with_synthetic_patient_uuid
docker compose run --rm api python -m app.cli map-clinician --user-id user_replace_clinician
docker compose run --rm api python -m app.cli assign --clinician-id user_replace_clinician --patient-id replace_with_synthetic_patient_uuid
```

Reload after mapping. Commands are idempotent for the same mapping, refuse a conflicting account mapping, and verify local patient/clinician existence. They do not contact Clerk or create Clerk users: copy IDs from your own development instance carefully. These are local developer commands, not public API operations.

~~The clinician account can currently see its role and assignment count only. The read-only patient dashboard is a later slice.~~ **28 October 2026, Phase 6:** after the existing mapping/assignment commands, sign in or reload as the mapped clinician to open the assigned-patient dashboard. No additional configuration or migration is introduced by this slice; the existing database schema (including brief migration `0003`) and Clerk setup are required. Zero assignments show an empty state. Assignments are refreshed from the database on each list/detail request; role and assignment changes are developer-only operations. Clinician accounts remain rejected by patient logging, brief generation and speech endpoints, including patient-only reads.

SDK references: [Clerk React quickstart](https://clerk.com/docs/react/getting-started/quickstart), [Clerk Python request authentication](https://github.com/clerk/clerk-sdk-python#request-authentication). The frontend uses the current `@clerk/react` package and its `<Show>` controls.

Commands must separately cover patient association, clinician role assignment, and clinician-to-patient assignment. They are local developer operations, not public role-changing endpoints. Unmapped accounts remain blocked from patient records.

## Database tables and DBeaver guide

Planned entities: synthetic patients, prescriptions, sleep/activity measurements, wellness goals, account mappings, clinician assignments, meals, meal insights, medication events, briefs, conversations/extraction checkpoints, and request identities.

Migration `0001_initial_slice.py` (revision `0001`) defines the foundation tables explicitly. `0002_medication_events.py` adds the two medication tables; `0003_briefs.py` adds brief snapshots. None imports changing application models to construct migration history. These migrations have not been executed by the agent.

| Table | Purpose |
| --- | --- |
| `patients` | Synthetic profile, summary, IANA timezone |
| `prescriptions` | Synthetic patient prescription references used for medication matching/readback; never edited by logging |
| `measurements`, `goals` | Synthetic activity/sleep context and goal targets |
| `accounts` | Authoritative Clerk-user-to-role/patient mapping |
| `clinician_assignments` | Clinician-to-patient read associations |
| `meals` | Reported foods/evidence, local day, revision, inline insight/status |
| `conversations` | Patient/feature state, version, continuity expiry, short-lived lease |
| `client_requests` | Patient-scoped request IDs, fingerprints, extraction checkpoints, completed results |
| `medication_events` | Patient/prescription IDs, unique patient/source-request identity, reported evidence JSON, separate prescription snapshot JSON, UTC event instant, IANA timezone, latest time evidence, revision, synthetic flag, timestamps |
| `medication_questions` | Retained patient/conversation/medication/step/version identity, typed immutable proposal JSON, readback, status and confirmation expiry |
| `briefs` | Patient/source-request uniqueness; kind constraint; indexed patient/kind/local day; saved IANA timezone and UTC timestamp; bounded fact/provenance/missing-data context JSON; validated typed narrative JSON; rendered narrative and allowed focus |

Meal insights currently live on the meal row rather than in a separate table: ~~a separate meal insight table in the initial schema~~ → inline insight and status in `meals` for the POC, guarded by meal revision. Medication and brief tables now have migration source. No tables are created in Clerk. Medication question status is `pending`, `confirmed`, `cancelled`, `superseded` or `expired`; time expiry is always checked independently of the stored status, so a pending row can already be expired. No background cleanup job changes or deletes questions.

In DBeaver choose PostgreSQL, host `localhost`, port `5432`, and the database/user/password you configured privately. Example read-only queries for the implemented schema:

```sql
SELECT id, name, timezone FROM patients ORDER BY name;
SELECT clerk_user_id, role, patient_id FROM accounts;
SELECT clinician_id, patient_id FROM clinician_assignments;
SELECT id, patient_id, local_day, meal_type, foods, revision,
       insight_status, insight FROM meals ORDER BY updated_at DESC;
SELECT patient_id, request_id, status,
       checkpoint ->> 'base_version' AS extraction_version
FROM client_requests ORDER BY created_at DESC;
SELECT id, patient_id, feature, version, expires_at,
       expires_at <= CURRENT_TIMESTAMP AS expired,
       lease_expires_at
FROM conversations;
SELECT id, patient_id, prescription_id, reported, prescription_snapshot,
       occurred_at, timezone, time_evidence, revision, synthetic
FROM medication_events ORDER BY occurred_at DESC;
SELECT id, patient_id, conversation_id, step_id, medication_id,
       question_version, status, expires_at,
       expires_at <= CURRENT_TIMESTAMP AS expired
FROM medication_questions ORDER BY created_at DESC;
```

Do not expose DBeaver or database credentials through the frontend. Domain state/checkpoints are intentionally stored; application logs omit the raw conversation content.

## Worker, Flower, and Swagger guide

Inspect worker output yourself:

```powershell
docker compose logs -f worker
```

Flower shows the task `swasthmode.meal_insight`. Only a meal ID and revision are sent as task arguments, not the full conversation. Jobs call the real model, allow two task retries after the initial attempt, and save only to a matching meal revision. Provider failures display failed insight status even while a bounded retry is scheduled; a later successful retry may change it to completed. Final task failures are raised with a generic error for Flower. Completed insights cannot be overwritten by a duplicate failed task.

If enqueueing fails after meal commit, the meal remains saved and its insight becomes failed. There is no outbox or automatic recovery for the narrow crash window between database commit and queue publication; a process crash there can leave pending insight status. A user-facing retry-insight action is not yet included. These are documented POC limitations, not exactly-once delivery claims.

Swagger uses the bearer security scheme. Sign in to the app, obtain a short-lived session token privately from your own Clerk session, click **Authorize**, and supply the token as requested by the bearer dialog. Do not paste it into this README or chat. Reauthorize after expiry.

Implemented endpoints:

- `GET /api/account`: account setup state and mapped role.
- `GET /api/meals`: the authenticated patient's last 100 meals.
- `GET /api/meals/conversation`: current meal conversation ID, expiry flag, and last reply.
- `POST /api/meals/messages`: text workflow; optional `?stream=true` uses server-sent events.
- `GET /api/medications`: authenticated patient's last 100 recorded medication events.
- `GET /api/medications/prescriptions`: that patient's prescription references, bounded to 100.
- `GET /api/medications/conversation`: current medication conversation, last reply, expiry and actionable question, if any.
- `POST /api/medications/messages`: report, exact confirmation/cancel or logged-time correction; optional `?stream=true`.
- `GET /api/briefs`: authenticated patient's latest 30 stored brief snapshots, with no generation.
- `POST /api/briefs`: patient-only morning/evening generation or reuse; JSON result after commit.

Brief request body (a fresh UUID for a new operation; use `evening` for an evening brief):

```json
{
  "request_id": "8dc4142a-6da0-4a71-8fe1-ec6da8f186d2",
  "kind": "morning"
}
```

No patient ID, date, arbitrary prompt or conversation ID is accepted. The server derives the patient and local day. Retry the exact body/UUID after a lost response; changed kind or cross-feature UUID reuse conflicts. In **Daily briefs**, retry bodies stay in memory while switching views; a browser reload loses that body. “Start a new request” explicitly abandons this in-memory retry, not a possibly committed server result. Check saved history and retry first when the outcome is uncertain.

Example request body (generate a fresh UUID for each new message):

```json
{
  "request_id": "a7de472f-1d0c-4c57-9163-e088d81b6c01",
  "text": "I had rice and dal",
  "conversation_id": null
}
```

Use the returned conversation ID for the next message, such as “For lunch.” Retry with the **same complete body and request ID** to recover a lost result. A changed body under that ID returns 409. The frontend retains the pending body for retries until success or explicit editing. The server does not accept a patient ID in this workflow; it derives access from the verified account.

Structured extraction finishes before response streaming. The stream delivers the code-composed, committed reply and a final result event, rather than exposing partial model output as a successful write. Text remains usable without speech; ~~actual speech is planned for a later slice.~~ **28 October 2026:** Phase 5 offers a separate, explicit playback request after the final committed result, with speech failures isolated from domain writes.

Medication requests use a separate conversation. Example report body (synthetic Asha profile only; replace the UUID for each new message):

```json
{
  "request_id": "e6f278d1-7b37-4776-8848-23ebfbf81651",
  "conversation_id": null,
  "action": "report",
  "text": "I took Metformin 500 mg now"
}
```

The response should be a readback, not a saved event. For confirmation, send a fresh request UUID, returned `conversation_id`, `action: "confirm"`, `text: "confirm"`, and the returned pending fields mapped as `question_id: pending.id`, `step_id`, `medication_id`, and `question_version`. Copy all values from the **same current response**; never reuse example or old question IDs. Cancel uses the same binding fields with `action: "cancel"` and `text: "cancel"`. The frontend supplies them through explicit controls. A report containing `text: "yes"` without these bindings never creates an event.

To correct time, send `action: "correct_time"`, a current conversation ID if available, an authorized `event_id`, its current `event_revision`, a new request UUID and `text: "2026-10-26 09:15"` (replace with the intended past local time). Confirm the returned time-only readback using its new question fields. The timestamp must be the entire correction text. Retry any request with its exact full body and UUID. No endpoint accepts a patient ID or an updated dose/prescription.

Document how the user obtains a Clerk session token privately and uses Swagger's authorization controls, with example request IDs and feature requests. Never put real tokens into documentation or logs.

## Manual checking guide — user-run only

The implementation has not been verified through automated tests or agent-performed functional checks. The following items are planned user checks; none has been executed or marked as passed.

### Current slice walkthrough

These are instructions, not results:

1. Follow startup and mapping instructions above. Sign in with an unmapped Clerk account first: it should show setup required. Map it to one seeded patient and reload.
2. Submit “Hello.” It should give a greeting without a meal record or an extraction call. The meal workflow's code has a direct greeting branch.
3. Submit “I had rice and dal.” If the model interprets the foods correctly, the required meal type is missing and the app should ask which meal. Reply “For lunch.” The intended result is one saved lunch with rice and dal.
4. Reply “Actually, add curd.” The intended result is a revision of that lunch, not another meal. Inspect its foods/revision in DBeaver. If extraction is wrong, describe a correction explicitly.
5. Observe the insight state. With a configured model and running worker it should become completed; failures should remain visible without losing the saved meal. Existing seed meals intentionally have no generated AI insight.
6. In Swagger, send a new request with a fresh UUID, then resend the exact body. The second result should have `replayed: true` and should not add a second meal. Change the text under that same UUID: it should return 409.
7. Try an unknown or another patient's conversation ID in a request from the mapped patient. It should return a conflict without returning that patient's data. The list endpoint derives the patient from the account and has no patient-selector input.
8. Map a separate clinician account and assign a synthetic patient. ~~The current clinician screen only shows configuration/assignment count.~~ **28 October 2026:** the clinician screen now has assigned-patient list/detail source; follow the unchecked Phase 6 guide below. Calling `/api/meals` with that clinician's token should return 403.
9. Use the account control to sign out. Protected patient UI should no longer render. An unauthenticated meal request should return 401.

### Medication slice walkthrough — user-run only, all unchecked

These are expected outcomes to check, not results. Use only mapped synthetic patients and configured development services. Normal reports in hybrid mode call real extraction/safety providers and can incur charges when you run them.

1. Apply migrations and rerun seed yourself. Inspect the three patients and two synthetic medication events each; rerun seed and inspect that existing events/corrections are preserved. Sign in as Asha's mapped patient and open **Medication events**. Other patients' prescriptions/events must not appear.
2. Report `I took Metformin 500 mg now`. Inspect the readback and pending question. Before confirmation there should be no new event. Confirm using the button; inspect one new event with the original report instant, reported medicine/strength evidence, null unreported quantity/frequency, and a separate prescription snapshot. `synthetic` should be false for this user report.
3. Report `I took Metformin now`. Strength must remain unreported even though the prescription reference shows `500 mg`. A different explicitly reported strength should be read back as reported, alongside the unchanged prescription reference; the app must not recommend or change a dose.
4. Try a small medicine-name typo such as `I took Metformn now`. If the unique similarity rule proposes a match, it must label a possible match and require confirmation. An unknown name, multiple medicines, or ambiguous candidates must ask for a new report without an event. Inspect that a typo stays user-reported while the candidate name is prescription-derived.
5. Try vague times, future times, negation, advice, missing names and partial replies. The app should refuse or ask for a complete report. No event should appear. `now` should stay anchored to the initial report even after a delayed confirmation or retry.
6. In Swagger, submit `text: "yes"` with `action: "report"`, both with and without a conversation ID. No event should be created. Submit `action: "confirm"` without the full binding fields; it must not confirm a current question.
7. Retain one question body privately, create a newer readback, then submit the old confirmation. It must not save the old event or confirm the newer one. Change the step, medication, version or conversation field independently with fresh request IDs; each mismatch must fail closed. Another patient's question/event IDs must reveal no records.
8. Let a question expire after 15 minutes. The screen should explain expiry and remove confirmation controls. Submit its original bound confirmation in Swagger with a new request UUID; expect an explicit expired explanation and no new event. Repeat after a newer report: the retained old question should still be recognized as expired. A late bare `yes` when the current question/conversation is expired must explicitly explain expiry and ask for a new report.
9. Let the medication conversation expire (up to 24 hours); send a new complete report and inspect that the same conversation row has a higher version. Submit an old question/step/version binding. It must never regain consent. Saved events and old question metadata must remain.
10. Use **Correct recorded time**, enter a past local timestamp and inspect its readback. Confirm; only time/time evidence/timezone/revision/update timestamp should change. Original reported fields and prescription reference must stay unchanged. A stale event revision or a changed prescription reference should require a new report/readback. Dose/medicine edits in the time text must be rejected.
11. Retry the exact confirmation body/UUID after success or a lost response. Expect `replayed: true` and the same event with no additional write. Retry with a changed body under the same UUID, or reuse a meal request UUID for medication: expect conflict. Replaying an old readback result must not make its question current again.
12. If desired, submit overlapping messages or recover an expired lease. Only the current owner/version may checkpoint or write. Provider/NeMo failure must not save a medication event or silently substitute a successful readback; a retry may reuse its applicable checkpoint. After a successful event commit and a lost response, the exact retry must recover the committed result.
13. Use a clinician token, an unmapped account and no token against each medication route. Expect patient-role denial, setup denial and authentication denial respectively. Sign out and confirm patient navigation disappears. Check the meal create/correction/timeline flow yourself after this shared-store change.

### Brief slice walkthrough — user-run only, all unchecked

These are instructions and expected outcomes, not results. Generation/safety calls use your configured real providers and can incur charges. The agent has performed source reading and edits only.

1. Rebuild, apply `alembic upgrade head` and restart yourself using the setup above. In DBeaver inspect revision `0003` and the new `briefs` table; existing meals/medication events must remain. Sign in as a mapped synthetic patient and open **Daily briefs**.
2. Request a morning brief. Inspect the previous-seven-complete-local-day window, capture timestamp, narrative, single small focus, missing measurement dates, recorded-day averages, latest-day goal comparisons and expandable record references. The seeded five measurement days intentionally leave gaps in the morning window. Inspect that missing days are excluded rather than treated as zero.
3. Request morning again using a new UUID. Expect `reused: true`, the same brief ID, saved time, original snapshot and reuse deadline at the next local midnight. Add/correct a meal and request again: reuse must still identify the original snapshot without implying that it includes your later edit.
4. Generate evening, then request again within 30 minutes. Expect the same snapshot and a reused label; after that window request with a new UUID and expect fresh context/generation. A window near local midnight ends at midnight. Morning after midnight uses a new local day. Check a developer-configured synthetic timezone yourself if checking non-India boundaries; no browser-supplied timezone/date is accepted.
5. Inspect medication counts and synthetic-event labeling. A window with no medication events must say no records, never missed doses/adherence. No medicine names, doses, nutritional estimates, causes or diagnoses should be generated. The permitted focus must remain one optional logging/reflection suggestion.
6. Retry an identical successful request body/UUID in Swagger; expect `replayed: true` and the same saved result with no additional brief. Replay after its reuse deadline still recovers that original result; the screen labels it recovered. Change kind under the same UUID, reuse a meal/medication UUID, or add a patient/date/prompt field: expect conflict or invalid-field rejection, not access or generation for another patient.
7. If checking interruptions, overlap morning/evening requests, interrupt a response, or recover an expired lease. Only the current owner/version may checkpoint/write. A successful commit must remain recoverable after response loss. An expired checkpoint or intervening completed turn must conflict and ask for a new operation. Inspect `client_requests` feature `briefs`, context and validated narrative checkpoints, and its single committed result.
8. If provider/NeMo is unavailable or rejects the request/output, expect an honest failure with no fallback text/brief row. Retry using the retained body. “Based on” and missing data must stay separate from generated selection; unknown/duplicate model fact IDs must fail grounding. These are expected safety boundaries, not a claim of verified outcomes.
9. Use a different mapped synthetic patient and confirm history and provenance show only that patient. GET/POST with a clinician or unmapped token must return 403; without a valid token, 401. Brief endpoints accept no resource/patient selector. Sign out and confirm patient UI disappears.
10. Inspect bounded behavior yourself if you add synthetic records: more than 100 meal/event rows must show lower-bound counts and provenance truncation; unsupported or duplicate goals must avoid invented comparisons. Reloading history must not call generation. Repeat the meal and medication walkthroughs yourself after the shared safety-policy wording addition.

### Unified logging walkthrough — user-run only, all unchecked

These are instructions and expected outcomes, not executed results. Use synthetic mapped patients only. Real planner, extraction and safety calls can incur charges.

1. Rebuild/restart yourself, retaining existing data and migration head `0003`. Open **Meals + medication**. Submit `I had rice and dal for lunch; I took Metformin 500 mg now` using a synthetic patient whose prescription reference includes that medicine. Inspect the typed source spans and ordered steps. Only the first step should execute; if it saves, inspect that meal and the queued medication step. Continue should produce a medication readback without a medication event.
2. Confirm that exact readback. Inspect one saved medication event alongside the previously saved meal. The event time for `now` must use the original mixed report instant, not the later Continue/confirmation instant. Refresh the dedicated histories. Missing logs must never be described as missed doses.
3. Submit a mixed report with the meal type missing. Its question should own the first step; answer with `For lunch` using the UI. The medication step must wait. In reverse order, a medication readback must block the meal until confirm/cancel. A medication clarification requires a fresh complete report; fragments must not be silently assembled.
4. Cancel a medication readback and continue a queued meal. Stop an unfinished workflow after saving its first step. Earlier records must remain; cancelled/stopped steps must have no invented saved record ID. Make an explicit meal correction through a later unified report and inspect the existing meal revision instead of a duplicate.
5. Inspect Swagger's `HealthMessage` fields. Start with `action=report`, a fresh UUID, optional current `conversation_id`, and `text`. For follow-ups copy the current workflow/step/question/version from GET. For medication controls also copy the nested specialist conversation, question, step, medication and version into `medication`, with matching action and literal `confirm`/`cancel`. The UI constructs these bodies; never share private tokens or patient text in logs.
6. Send bare `yes`, modify each outer and nested binding independently, use an old readback after a newer turn, or reuse a dedicated medication confirmation in the unified route. None should save an event or transfer consent. Let a question expire and try its controls/body; expect an expiry explanation or conflict with no new write. Start a new report after expiry. Confirm that old questions never become current again.
7. Retry an exact successful body/UUID, including after a lost response. Expect its original result with `replayed=true`; a replayed readback must not restore old controls. Change text/action/bindings under that UUID or reuse the UUID across a dedicated feature: expect conflict. Inspect distinct derived specialist request IDs and retained root results.
8. If checking failures, interrupt after a specialist commits but before root progress completes, then retry the exact original request or reload its recovered retry control. Inspect one domain write and truthful recovered progress. Interrupt after the progress checkpoint and retry again: it must not advance to the next queued step. While that interrupted request owns the workflow, a new report must conflict. Provider/NeMo failure on a later step must leave earlier saved steps visible and unchanged.
9. If checking concurrency, overlap root requests or allow lease takeover. Late child checkpoints/writes must fail their parent owner/version/deadline checks. Let a question expire during provider work; no later new save may use it. A result already committed before expiry remains recoverable. Inspect `conversations` scopes `health_logs`, `health_meals`, `health_medications` and `client_requests` rather than assuming the root/child commits are one atomic transaction.
10. Submit unsupported domains, advice, more than four reports, unclear boundaries or a plan that omits meaningful text. Expect a refusal/clarification or rejection before execution. Switch to another synthetic patient, a clinician, an unmapped account and no token: data must stay patient-scoped, clinicians/unmapped accounts must receive 403, and unauthenticated requests 401. Repeat dedicated meal, medication and brief walkthroughs yourself after the shared-store changes.

~~Voice and clinician patient-detail checks remain future checks until their source is implemented.~~ ~~28 October 2026: voice source is written; the following checks are for future user verification only. Clinician patient-detail checks remain future work.~~ **28 October 2026, Phase 6:** both voice and clinician source are written. The following checks are for future user verification only. All manual checklist items remain unchecked until user verification.

### Phase 6 clinician manual checks — user only, not executed

These are expected outcomes for the user to check, not executed results. Use only synthetic profiles and development Clerk accounts. No tests, builds, application startup, migrations, provider requests or app/API exercises were performed by the agent.

- [ ] With existing setup/schema applied yourself, map a clinician and assign one synthetic patient using the documented developer commands. Sign in; inspect the assigned name, profile summary and timezone. Open records and return to the list. A clinician with no assignments should see the empty state without patient records.
- [ ] Compare meals, foods, revisions and pending/completed/failed/seed insight statuses with existing database records. Only completed insight text should appear. Refresh should read existing records without generating insights or creating requests/tasks.
- [ ] Compare recorded medication times, reported strength/quantity/frequency, prescription snapshots, revisions and synthetic-seed labels with saved events. Empty history must say no records; it must never label a dose missed or infer adherence.
- [ ] Compare each latest saved morning/evening brief within the selected range, including original timezone, capture/context dates, facts/sources, missing-data text and snapshot limits. An absent brief must show an empty state. Opening/reloading must not generate or reuse-create any brief, make AI/speech calls or change records.
- [ ] Apply single-day and 90-day inclusive ranges, including medication events around local midnight and a DST transition for a deliberately configured synthetic timezone. Meals/briefs use saved local days; medication instants use the current patient's timezone. Reversed, >90-day, malformed and out-of-1900–2100 ranges should return 422. Use **Reset to latest 30 days** after a valid or rejected range; inspect the default range. An end-only request for 1900-01-01 must clamp the default start to 1900-01-01. An invalid stored timezone must produce a configuration error, not an unhandled server failure.
- [ ] If adding sufficient synthetic data yourself, inspect 50-row patient pages and independently >100 meal/event rows. Check stable ordering, `has_more`, truncation flags/messages and narrowing dates. A bounded result must not be presented as complete history. The offset ceiling is 10000.
- [ ] With an authorized clinician token, request an unassigned existing patient UUID and an unknown valid UUID directly: both must return the same 404 with no profile, records or brief context. Alter browser state/IDs and repeat; a selected ID or old account response must never grant access.
- [ ] Against both clinician GET routes, try no/invalid/expired session (401 with configured Clerk), an unmapped account and a patient account (403). Revoke an assignment or clinician role through deliberate local developer database edits, then reload/request again; access must be denied without disclosing the removed patient's data. A list after assignment removal must omit the patient. Missing Clerk configuration should remain an honest 503.
- [ ] Check clinician requests to patient meal, medication, brief, unified and speech endpoints remain rejected. Try POST/PUT/PATCH/DELETE on clinician routes: no mutation operation should be available. Inspect the clinician UI for absence of write, generate, confirmation, playback and role/assignment controls.
- [ ] Check loading, failed database/network request, expired session, retry, empty date range, rapid navigation, date changes and sign-out. Late responses must not replace another view; sign-out must remove the clinician workspace. Returning to the list must refresh assignments. Previously displayed data cannot be remotely erased before the next request; reload after developer access changes.
- [ ] Switch directly between two active Clerk users/sessions (including clinician-to-patient) and delay an earlier account response yourself. The old workspace, selection, patient drafts and records must disappear on the switch; late responses must not restore them. Inspect assignment counts with multiple assignments and confirm they still match the database.
- [ ] Repeat existing patient/unified/voice walkthroughs yourself to check retained behavior. All prior behavior remains unverified; source reuse is not a passed regression check.

### Phase 5 voice manual checks — user only, not executed

- [ ] In desktop Chrome on localhost/HTTPS, record a meal, stop, edit the transcript, transfer it explicitly to the message, then submit. Check that recording/transcription alone saves nothing.
- [ ] Repeat for a dedicated medication and mixed report; check names, strengths, quantities and times. Confirm that only the current medication confirmation button can authorize the event, and saying “confirm” in a report cannot.
- [ ] Listen to a completed reply and saved morning/evening brief using native audio controls. Confirm AI-voice disclosure and that replay does not repeat logging or brief generation.
- [ ] Deny microphone permission; use an unsupported browser/format; record silence; reach the 60-second browser limit; exceed the 2 MiB upload ceiling with a direct request; check that typed input remains available.
- [ ] Cancel while permission is pending, while recording and while transcribing. Switch views/unmount during each state. Check microphone tracks stop and late transcripts do not replace drafts. Begin recording during playback and check playback pauses.
- [ ] Check missing speech configuration, STT failure/timeout, Cartesia failure/timeout, NeMo refusal/unavailability and browser playback failure. Check honest errors, usable text, unchanged saved records and no automatic paid retry.
- [ ] Try speech endpoints without a session, as an unmapped account, as a clinician, with another patient's request/brief UUID, with the wrong feature or an unfinished request. Expect rejection without audio or another patient's text.
- [ ] Check the request body rejects arbitrary TTS text; oversized/empty/malformed recordings fail. Confirm local recordings are absent from app storage/logs, audio responses use no-store, and the provider/account retention policy is understood separately.
- [ ] Recover an earlier completed request and check playback describes the saved response while current question controls/expiry still govern any confirmation.

- [ ] Login/logout, optional sign-up, expired sessions, and unmapped account setup state.
- [ ] Patient versus clinician navigation and independent backend enforcement.
- [ ] Block access to another patient's records, conversations, briefs, and insight resources.
- [ ] Create a meal, answer a clarification, continue the same meal, and correct it without duplication.
- [ ] Inspect insight pending/completed/failed status and invalidation after a meal edit.
- [ ] With hybrid mode configured, check our deterministic rule blocks, NeMo input blocks, NeMo proposal/output blocks, and safe normal meal reports. These outcomes are not guaranteed by source inspection.
- [ ] Make the NeMo configuration unavailable yourself and confirm new meal writes fail visibly; a saved meal must remain saved if its later insight fails. Do not mark unavailable checks as passed.
- [ ] Match a medication, read back an uncertain prescription, confirm the exact pending question, and inspect field provenance.
- [ ] Confirm ambiguous responses ask again and time corrections stay within the allowed edit scope.
- [ ] Reply “yes” to an expired medication question and confirm an explicit explanation with no new event.
- [ ] Generate morning/evening briefs, inspect missing-data wording and “Based on,” and check reuse labels/windows.
- [ ] Submit mixed meal/medication input, answer its correct pending step, and retry without repeating completed steps.
- [ ] Use desktop Chrome voice input, edit medicine names/numbers, submit the transcript, and play Cartesia output.
- [ ] Check microphone denial, transcription failure, and speech/playback failure while preserving usable text.
- [ ] Retry the same request ID, reject changed input under the same ID, and inspect for duplicate records.
- [ ] Check overlapping-turn busy behavior and, if desired, expired-lease recovery.
- [ ] Inspect worker logs and Flower task state.
- [ ] Inspect saved records and assignments in DBeaver.
- [ ] Authorize Swagger and manually check protected API requests without sharing tokens.

Add detailed steps and expected results here as implementation proceeds. No unit/integration tests, pytest, test runners, fixtures, automated evaluation suites, browser testing, provider connectivity checks, sample AI calls, or agent-run application/API exercises are authorized. Runtime token verification, validation, guardrails, and duplicate protection remain required application behavior.

## Demonstration script and final handoff

**Planned, not executed:**

~~The earlier nine-step outline listed the intended feature sequence without concrete outcomes.~~ **28 October 2026 documentation follow-up:** use the following rehearsal checklist after the setup and detailed manual checks above. Every item is unexecuted. Expected outcomes describe source intent, not verified behavior. Use synthetic profiles only; provider-backed steps can incur charges.

- [ ] Prepare the session: follow the local startup sequence, migrate through `0003`, seed, map two separate patient accounts and one clinician account, and assign only one of those patients to the clinician. Keep one additional Clerk account unmapped. Use desktop Chrome at `http://localhost:5173`; keep DBeaver and Flower available privately. Mapping does not create Clerk users, and `assign --clinician-id` takes the verified Clerk `user_...` ID.
- [ ] Establish the access boundary: sign in as the unmapped account and expect setup required; then use the mapped patient. Explain: “Clerk verifies who signed in; our database decides the role and which synthetic records that identity may access.” Signing out or switching users must discard the old workspace and drafts.
- [ ] Open **Meals** explicitly; the default patient tab is **Meals + medication**. Send `I had rice and dal`, answer `For lunch`, then send `Actually, add curd`. Expect a clarification followed by one saved lunch and a revision of that same meal. Inspect foods, evidence, ID and revision; explain that extraction proposes fields and Python checks evidence before writing.
- [ ] Refresh the meal timeline and inspect pending/completed/failed insight status. With working providers and worker, expect a qualitative observation; if it fails, show the honest failed state and retained meal. Explain that worker input is meal ID/revision and an outdated job cannot replace a newer revision. Do not promise queue delivery or nutrient estimates.
- [ ] Open **Medication events**, inspect this patient's actual synthetic prescription list, and report `I took Metformin 500 mg now` only if that reference exists. Otherwise use the name/strength from the selected synthetic profile. Expect an immutable readback and no new event before confirmation. Confirm using the current button, then inspect one new event with separate reported evidence and prescription reference. These examples describe fictional records, not instructions to take medicine.
- [ ] Use **Correct recorded time** on that event, enter an intended past `YYYY-MM-DD HH:MM` in the patient's timezone and confirm the new readback. Expect only the permitted time fields/revision to change. A bare `yes`, stale button or altered question binding must never save an event.
- [ ] Open **Daily briefs** and request morning, then morning again with a new request. Expect a saved snapshot followed by a reused label for the same patient-local day. Inspect the previous seven complete days, missing measurements and “Based on” references. Generate evening and inspect today's partial context; its reuse lasts up to 30 minutes, ending at local midnight. Explain that reuse preserves the old snapshot after later corrections.
- [ ] Open **Meals + medication** and submit `I had rice and dal for lunch; I took Metformin 500 mg now`, adapting the medicine to the synthetic reference. Expect at most the first specialist step in that request. Choose **Continue to next report**, inspect the medication readback and confirm it. Refresh dedicated histories to inspect the shared records. Explain that earlier saves survive a later failure or **Stop unfinished steps**, and root/child commits are separate.
- [ ] In desktop Chrome, record a short meal report, stop, edit its transcript and choose **Replace message with this transcript**. Expect no record until the main message is submitted. After a completed reply or saved brief, choose **Listen · AI-generated voice** and use native audio controls. Expect playback without another logging/generation operation; keep the written medication readback authoritative for the demo.
- [ ] Show one exact-body/request-ID replay privately in Swagger and inspect the same committed result with no duplicate record. Changing the body under that ID should return 409. Use the detailed failure/recovery checklists for interruptions and checkpoint boundaries; a fresh UUID is a new operation, not guaranteed duplicate prevention.
- [ ] Sign in as the clinician. Expect only the assigned synthetic profile, saved meals/insights, medication events and latest stored briefs within the date range. Use the date filters and **Reset to latest 30 days**. Expect empty states where no records exist and explicit truncation if limits are reached. Explain: “This path verifies identity, checks database role and assignment, then reads existing records; it has no AI, extraction, confirmation or write stage.”
- [ ] Privately check an unassigned existing patient UUID and an unknown valid UUID: both should return the same 404. Patient/unmapped clinician-route requests should return 403; missing/invalid sessions should return 401 when Clerk is configured. Clinician calls to patient logging/generation/speech routes must be denied. Complete the detailed stale-session, assignment-revocation, retry, provider-failure and account-switch checks above before claiming those behaviors work.
- [ ] Close the walkthrough by stating the observed results and unresolved checks separately. Explain conservative medication wording, today's meal boundary, saved-brief staleness, bounded histories, in-memory retry drafts, queue-publication gap and unresolved retention. Use `docker compose down` to stop while preserving data; do not remove volumes as routine shutdown.

The exact filenames and request boundaries are documented in **Filename-based request flows**, **Conversation concurrency, expiry, and retries**, and **Phase 6 source review**. This checklist does not replace the detailed manual checks or mark them complete. No runtime verification was performed during this documentation follow-up.

## Implemented / Simplified / Not implemented

~~Implemented: planning README only; no application implementation has started.~~

**Implemented in source, unverified:** PostgreSQL schema/migrations; uv-based Python project and Docker image; local Compose services; synthetic seed command including medication events; developer role/assignment commands; Clerk React/Python integration; unmapped-account screen; patient-only meal and medication APIs; persisted meal clarification/correction; medication reported-field provenance, prescription matching/readback, exact expiring confirmations and time-only corrections; retained question/step/version metadata; evidence validation; request/checkpoint/lease guards; code-composed confirmations; backend streamed text; qualitative Celery meal insights; meal timeline/status and medication composer/readback/timeline/navigation interfaces.

**Guardrail addition, source only:** custom rules plus NeMo 0.24.1 and our policy prompts cover nontrivial meal inputs, meal proposals, generated insights, medication reports/time-correction requests, medication proposals, brief context input/rendered output, and unified planner input/typed output in hybrid mode. Bound confirmation/cancel controls reuse the already checked immutable proposal. Nothing has been installed, run, or verified by this agent. ~~Voice coverage remains planned.~~ **28 October 2026:** submitted transcripts reuse feature input checks, and speech generation checks resolved saved text through deterministic and configured NeMo output checks.

**Planned simplifications:** one modular backend plus worker; two roles; synthetic local data; developer-only account setup; sequential planner steps; on-request briefs; 24-hour conversation continuity; bounded retries; desktop Chrome push-to-talk; qualitative meal insights; a read-only clinician dashboard.

**Brief source added, unverified:** feature-owned schemas/models/context/generation/prompts/validation/repository/service/router, migration `0003_briefs.py`, patient-only history/generation, local windows/metrics, allowed focus catalog, typed model narrative composition, deterministic fact grounding, NeMo input/output, immutable provenance snapshots, reuse and shared request/lease checkpoints; Daily briefs patient view with missing data, saved/reused/recovered labels and retained retry bodies. No checks were run.

**Unified source added, unverified:** feature-owned router, schemas, prompts, planner and service; exact source coverage, at-most-four steps, one specialist operation per request, stable step operation keys, persisted pending ownership and progress, parent-bound child writes/checkpoints, full medication consent bindings and retained recovery bodies; patient progress/composer/confirm/cancel/continue/stop controls. Existing specialist repositories perform domain writes. The existing schema supports this slice without an additional migration.

**Voice source added, unverified — 28 October 2026:** `speech/schemas.py`, `router.py`, `stt.py`, `tts.py`; patient-authorized streaming raw audio uploads; separate SDK transcription; completed-request/saved-brief speech lookup; deterministic/NeMo speech output checks; bounded WAV generation through Cartesia v4 SDK; reusable recording/transcript-review and audio components across existing views; active-view cancellation and resource cleanup. The existing DB schema is reused without a migration. Only `.env.example` is updated; existing secrets are untouched.

**Clinician source added, unverified — 28 October 2026, Phase 6:** feature-owned router/schemas/queries, shared clinician authentication dependency and clinician React dashboard, reusing existing models and typed record views. Every record query includes database role/assignment scope; two GET-only routes return paginated profiles and bounded date-filtered saved records without AI calls. Existing schema/configuration and developer commands are reused. Private `.env` files and lockfiles are untouched.

**Phase 6 review fixes, source only — 28 October 2026:** session/user-keyed workspace remounting with cancellable account loading; SQL assignment count; malformed-timezone error handling; clamped default lower date bound; explicit date reset and browser timezone-display fallback. The review adds no migration, dependency or configuration. All earlier behavior, the review fixes and all manual checklists remain unverified.

~~Not implemented yet: speech input/output, clinician patient-detail dashboard, brief/unified streaming, advanced date filtering, and the full multi-feature demonstration script.~~ ~~28 October 2026: speech input/output has source; clinician patient-detail dashboard, brief/unified streaming, advanced date filtering, and the full multi-feature demonstration script remain planned.~~ **28 October 2026, Phase 6:** voice and clinician dashboard now have source. Brief/unified streaming, advanced date filtering, and the full multi-feature demonstration script remain planned. No dependencies have been installed or resolved by this agent. Existing lockfiles were not read, regenerated or validated during this slice; earlier README statements that none exist describe the earlier slice and are not a current filesystem inventory. All current code still requires the user's manual checks.

**Clinician limitations:** source inspection only; all runtime behavior is unverified. All project patient profiles are synthetic by convention, as required; the schema has no independent synthetic-patient flag or real-patient integration. Do not load real patient data. The list exposes only assigned profiles, 50 per page with a maximum offset of 10000. Detail returns at most 100 meals and 100 medication events, without record pagination; narrowing dates may still leave high-volume days truncated. Latest briefs are selected within the date range, not all-time; their saved context may refer to earlier dates and remain stale after corrections. No new analytics, adherence scoring, measurements/goals editor, real-time updates or exports are added. Date filtering uses the patient's current timezone for medication instants and saved dates for meals/briefs; a timezone change can therefore shift which events match. Multiple reads are not an atomic clinical snapshot. Access is checked on every request/query; already displayed data remains visible until refresh/navigation/sign-out, and revocation cannot retract an already delivered response. No production security or reliability claim is made.

**Voice limitations:** source only, no runtime validation. Desktop Chrome is the supported browser; runtime capability checks may permit other browsers without claiming support. Recording uses click-to-start/click-to-stop, with a 60-second browser timer; the server enforces upload bytes/time but does not independently decode/measure duration. WebM signature checks do not validate the codec or spoken content. Provider configuration must support the actual uploaded format. The editable transcript is not proof of accurate medicine recognition; inspect names/numbers and the written readback. Drafts/transcripts/audio are held in memory; a reload loses them. Playback reads an immutable completed response, including historical/expired questions, and never grants consent or makes a question current. Brief playback omits context/provenance sections. Speech is buffered before playback, not realtime streaming; generated pronunciation may be inaccurate. Only one audio element plays at a time within the page. Speech limits are per request, with no account quotas or distributed rate limiter yet; explicit new speech attempts can incur provider charges. Aborting a browser request does not guarantee server/provider cancellation. No full-duplex voice, browser-native synthetic speech fallback, codec conversion, server audio store or dedicated Azure STT adapter is implemented.

**Unified limitations:** source-span validation does not establish semantic accuracy. A conservative split can reject natural conjunctions or send a report to the wrong specialist, which must then clarify/refuse; inspect readbacks. Execution pauses between queued steps for explicit Continue. Root and child commits are separate, so failures may leave partial saves; use exact retry recovery. Current workflow history is bounded to four steps; older outcomes remain in request records. Unexpired interrupted requests require original-body recovery before new operations; a crash before that body is checkpointed can require the original browser body or inactivity expiry. Physical retention/cleanup remains undecided. Reloading a dedicated history may be necessary to see newly unified records. Medication time correction remains in the dedicated view; unified report planning never invents a target event or changes a prescription.

**Brief limitations:** fixed narrative grammar and logging/reflection focus catalog intentionally constrain AI phrasing. Measurement bounds are plausibility input limits, not clinical interpretation. Morning excludes today; evening measurements are daily and can be partial. Snapshots can become stale after capture and remain unchanged during reuse. Provenance is bounded and history shows only the latest 30. Morning/evening requests serialize per patient through the same feature lease. Briefs do not use the worker, force refresh, background scheduling, free-text prompts or clinical recommendations. Existing request/checkpoint retention limitations also apply to briefs.

**Current slice limitations:** meal writes handle today in the patient's timezone and record a local day rather than an inferred eaten-at clock time; each timeline shows up to 100 records. Medication reports use the conservative complete-statement format documented above; free-form date inference, fragment draft assembly, multiple medicines per message and medicine/dose edits are unsupported. Similarity matching is a simple string heuristic and can propose an incorrect candidate; readback and explicit confirmation are required. Pattern-based guardrails and model safety checks do not prove clinical safety or perfect grounding. Request/checkpoint and medication-question rows have no automatic cleanup; retention policy is intentionally unresolved, and question evidence/proposals remain in the local database to recognize stale replies. Retry bodies live only in frontend memory while mounted. No exactly-once claim is made across fresh request UUIDs, browser reloads or user-confirmed extraction mistakes.

**Outside scope:** company SSO/Azure AD B2C, enterprise multi-tenancy, real patient integrations, company production services, prescribing or dosage recommendations, clinical escalation, nutritional estimation, pledges, generated meal pictures, clinician messaging/appointments/care plans/alerts, full-duplex or always-listening voice, production compliance, high availability, and deployment hardening.

Input guardrails and output checks have limitations; they do not establish clinical safety or production compliance. Clerk login alone does not make the application production-ready. Document remaining limitations honestly rather than claiming production reliability or exactly-once processing.
