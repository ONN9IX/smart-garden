# Communications v2 delivery

Issue #175 implementation is based on approved `main` `76399b653a4585a9ae5327170f0d8bfc5892ac09` and adds the single Alembic revision `0017_communications_v2.py` after `0016`.

## Covered behavior

- V2 group channels support `all` and internal `teachers` audiences. DIRECTOR/ADMIN can enter only group channels; PARENT sees only an eligible child's `all` channel.
- V2 direct threads are keyed by organization, active group, child, guardian, and assigned Teacher Employee. Teacher options expose only employee ID, display name and active group context. Eligibility is rechecked on each read and write.
- Grandfathered direct threads with `teacher_employee_id IS NULL` remain in the legacy API and data. V2 lists exclude them, and V2 access rejects them.
- Message creation requires a client UUID. A retry by the same sender in the same thread returns the first message; reusing the key in another thread returns `409 IDEMPOTENCY_KEY_REUSED`. Audit details contain context and identifiers, never body text.
- `CommunicationReadState` is private to its user and thread. The cursor can only reference a message in that same tenant/thread and moves forward by `(created_at, id)`. Thread lists calculate unread messages from other users after the cursor; they do not expose read receipts.
- One unread communication notification per recipient/thread and one unread announcement notification per recipient/announcement are enforced with PostgreSQL partial unique indexes and conflict-safe inserts.
- Announcements support `all`, `parents`, and `staff` audiences for organization or group targeting. A teacher can publish only to an assigned active group. Published target, group and audience are immutable; content edits do not issue another publish notification. Parent read state is self-only. Recipient preview is a count and contains no recipient identifiers.
- The existing legacy communications and announcement endpoints remain available. V2 does not add attachments, media, reactions, editing/deletion/forwarding of messages, or read receipts.
- Downgrade to `0016` is supported on an empty V2 data set. The migration refuses rollback after V2 direct threads, client-key messages, read states, non-`all` announcements, or publish notifications exist because removing them would widen access or erase user state.

## Verification coverage

`backend/tests/test_communications_v2.py` exercises PostgreSQL-backed direct eligibility, retries and cross-thread collisions, unread count/cursor monotonicity, relation/assignment revocation, tenant-safe read rejection, announcement audience filtering, private read state, and no notification resend on content edits. Existing Stage 6 communications and announcement tests remain in place.

The compatibility canary runs the Communications v2 and existing Stage 6/announcement integration tests against its PostgreSQL service. Its backup/recovery job checks that both source and recovered databases run on PostgreSQL 18 and invokes the disposable synthetic backup/restore verifier using PostgreSQL 18 client tools.

The local Work environment has no PostgreSQL service, so database integration and migration round-trip checks must be completed by CI. The feature's technical coverage does not establish production legal approval or authorize use of real personal data; production 152-FZ readiness remains subject to specialist review, deployment/data-location/subprocessor decisions, retention and destruction policy, and operational backup/access controls.
