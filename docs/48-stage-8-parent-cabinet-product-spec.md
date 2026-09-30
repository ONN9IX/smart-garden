# Stage 8 — PARENT Cabinet Product Specification

**Status:** design proposal for Issue #139; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.
**Baseline:** `16b11ea1d5e66e4c9b98d773be87dd4c2587b936`.

## 1. Goal

Turn the existing PARENT capabilities into one coherent daily cabinet without changing frozen Stage 6 participant/privacy semantics or Stage 7 financial semantics.

The PARENT cabinet is child-centric:

```text
Home / Today
→ choose eligible child
→ attendance / schedule
→ announcements / communication
→ diary / polls / photos
→ notifications / notices
→ contracts & billing when Stage 7 exists
```

## 2. Core principles

1. PARENT sees only data derived from active same-tenant Guardian↔Child relationships.
2. Financial access remains stricter: Stage 7 resources are visible only to the contracting Guardian.
3. Backend authorization is authoritative.
4. Tenant is derived only from authenticated User.
5. Multi-child support is explicit; no cross-child data mixing.
6. No medical data, diagnosis, treatment or absence reason.
7. No other parent's private financial or direct-message data.
8. Mobile-first use is required.
9. Dev/test/preview use synthetic data only.
10. Technical acceptance is not full 152-FZ compliance or real-pilot authorization.

## 3. Navigation

Primary navigation:

- Главная
- Дети
- Расписание
- Объявления
- Сообщения
- Дневник
- Опросы
- Фото
- Уведомления
- Документы/уведомления
- Договоры и оплата — only when Stage 7 capability exists

On small screens, high-frequency areas should remain reachable with minimal taps.

## 4. Multi-child selector

A PARENT may have multiple active ChildGuardian relations.

The selector shows only actively linked children in the authenticated tenant.

Switching child context changes:

- attendance;
- schedule;
- diary;
- eligible group announcements;
- communication context;
- polls;
- photo eligibility.

It does not silently change Stage 7 financial entitlement. A linked Child can still have a Contract whose contracting Guardian is someone else.

The Backend does not trust the selected child from the client without revalidating the relation.

## 5. Home / Today

Home answers:

> What do I need to know about my child today?

For the selected eligible child, show privacy-minimized cards:

- attendance state for garden-local today if available;
- today's eligible schedule;
- unread eligible group/direct communication count;
- unread announcement count;
- active polls requiring the current PARENT's vote;
- diary recency indicator;
- new eligible photo count/indicator;
- own unread notifications;
- own document notices requiring acknowledgement;
- financial attention only when Stage 7 exists and the current Guardian is the contracting Guardian.

Do not put into the Home aggregator:

- message body;
- diary text;
- photo bytes/public URL;
- another Guardian's name or finances;
- incident details;
- medical/absence reason;
- full contract/receipt content.

## 6. Child overview

The Child card is read-only for PARENT in this Stage.

Minimum presentation:

- child name;
- current active Group;
- basic existing Child information already authorized;
- today's attendance status;
- next/active schedule items;
- links to diary, announcements, messages, polls and photos.

Do not add speculative profile fields.

## 7. Attendance

Stage 8 freezes PARENT read-only attendance.

PARENT may read attendance only for an actively linked Child.

Display:

- date;
- status;
- arrival time if recorded;
- departure time if recorded;
- historical Group snapshot only where needed for accurate history.

PARENT cannot:

- create/update attendance;
- provide or view medical diagnosis;
- view another Child;
- use historical group membership to gain access to other group data.

No absence-reason free text is introduced.

## 8. Schedule

PARENT may read schedule for the selected Child's current eligible Group.

Display:

- date/weekday;
- start/end time;
- title.

No schedule write.

If Child group relation changes, current schedule eligibility changes on the next request.

## 9. Announcements

Reuse the Stage 6 contract.

PARENT reads:

- active all-garden announcements;
- active announcements for currently eligible Child/Group context.

Deduplicate where one announcement can be eligible through more than one linked child/group path.

No PARENT announcement creation/edit/archive.

## 10. Group communication

Reuse Stage 6 canonical Group communication semantics.

PARENT may:

- read the current eligible Group thread;
- send messages as the authenticated PARENT where Stage 6 allows it.

Membership is derived server-side.

No client-supplied participant list.

Group communication must not expose a full guardian directory beyond the minimum sender presentation required for the conversation.

## 11. Direct PARENT↔TEACHER communication

Reuse Stage 6 participant scope exactly.

PARENT may communicate only where:

- active ChildGuardian relation exists;
- Child belongs to an active Group;
- TEACHER has an active assignment to that Group;
- both users and tenant are active/valid.

DIRECTOR/ADMIN still have no blanket access to direct-thread content.

## 12. Diary

Reuse Stage 6 read-only PARENT behavior.

PARENT may read diary entries only for actively linked Children.

Home/notification payloads may reference that a new diary entry exists, but must not duplicate diary free text.

No PARENT diary write in Stage 8.

## 13. Polls

Reuse Stage 6 eligibility.

PARENT may:

- read eligible active Group polls;
- cast one allowed vote under the frozen poll contract;
- view result only to the extent frozen by the poll API.

No cross-group vote, no second vote, no actor spoofing.

## 14. Photos

Reuse the Stage 6 consent-gated photo boundary.

PARENT may access photo metadata/content only when:

- Child relation is eligible;
- the asset is eligible under the frozen Group/child rules;
- every required consent condition is currently satisfied.

No public photo URL.

Consent withdrawal effects remain those frozen in Stage 6.

Stage 8 does not create a new legal consent flow or allow PARENT consent writes unless separately approved.

## 15. Notifications

PARENT sees only own Notifications.

Useful PARENT kinds may include:

- new eligible announcement;
- new direct/group message;
- diary update;
- poll awaiting vote;
- document notice;
- photo availability;
- Stage 7 charge/payment/receipt events when financially entitled.

Notification rows remain minimal references, not copies of business content.

## 16. Document Notices

Stage 8 may expose metadata-only Document Notices to PARENT when the existing model safely supports PARENT as recipient.

PARENT may:

- list own notices;
- read own notice metadata;
- acknowledge an own notice that requires acknowledgement.

No binary document storage is introduced.

A notice is not a substitute for authenticated legal-document delivery unless a later document architecture explicitly defines that behavior.

## 17. Stage 7 contracts and billing

Stage 8 does not redesign finance.

When Stage 7 exists, PARENT navigation may surface:

- My contracts;
- current balance;
- charges;
- payments;
- debt/overpayment;
- receipts.

Eligibility remains exactly the Stage 7 contracting-Guardian rule.

A Guardian linked to the Child but not the contracting Guardian must not see those financial surfaces for that Contract.

If Stage 7 is not implemented, these modules remain unavailable without breaking the rest of the PARENT cabinet.

## 18. Empty and revoked states

Required explicit UX states:

- no linked active children;
- child relation became inactive;
- no schedule;
- no announcements;
- no messages;
- no diary entries;
- no polls;
- no eligible photos;
- no notices;
- Stage 7 unavailable;
- financial access not entitled.

Do not reveal hidden resource existence in error text.

## 19. Mobile-first behavior

On phone widths:

- child selector remains obvious;
- important Today actions remain above low-frequency modules;
- tables become cards/lists;
- no horizontal overflow for normal operation;
- long message/announcement text wraps;
- no sensitive value is copied to persistent browser storage.

## 20. Product acceptance target

Future PARENT cabinet acceptance must demonstrate:

```text
PARENT login
→ sees only actively linked children
→ switches child safely
→ reads own-child attendance/schedule
→ reads eligible announcements
→ uses eligible group/direct communication
→ reads diary
→ votes in eligible poll
→ reads consent-gated photos
→ reads/acks own notice
→ sees Stage 7 finance only when contracting Guardian
→ cannot read another child/guardian/tenant
```

This acceptance is technical/product acceptance only.