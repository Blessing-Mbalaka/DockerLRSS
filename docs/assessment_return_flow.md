# Assessment Return Flow

This documents the current live status flow used by the views before and after the return/rejection patch.

## Forward Order

1. Admin/assessor uploads or creates a randomized paper.
2. Assessor developer validates/corrects the paper and forwards it with status `Submitted to Moderator`.
3. Moderator reviews `Submitted to Moderator`.
4. Moderator approval forwards to QCTO with status `Submitted to QCTO`.
5. QCTO approval forwards to QDD with status `QDD Review`.
6. QDD approval forwards to ETQA with status `Submitted to ETQA`.
7. ETQA/release views continue the existing final flow.

## Send Back Order

1. Moderator return sends the paper back to the assessor/developer with status `Returned for Changes`.
2. Assessor/developer can correct and forward the same paper back to moderator as `Submitted to Moderator`.
3. QCTO reject/return sends the paper back one step to moderator as `Submitted to Moderator`, with `forward_to_moderator=True`.
4. QDD return sends the paper back one step to moderator as `pending_moderation`.

## Notification Triggers

Status changes are sent by `Assessment.save()` through `send_personalized_status_notifications`.

The relevant templates are:

- `Submitted to Moderator`: notifies users with role `moderator`.
- `Submitted to QCTO`: notifies users with role `qcto`.
- `QDD Review`: notifies users with role `qdd`.
- `Submitted to ETQA`: notifies users with role `etqa`.
- `Returned for Changes`: notifies users with role `assessor_dev`.
- `pending_moderation`: notifies users with role `moderator`.

Return comments are stored as `Feedback` records and appended to `Assessment.comment` so the feedback trail remains visible during back-and-forth corrections.

The notification panel is rendered on the main role dashboards for administrator, assessor developer, moderator, QCTO, QDD, ETQA, and assessment center users.
