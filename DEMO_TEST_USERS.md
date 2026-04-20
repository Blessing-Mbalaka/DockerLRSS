# Demo Test Users

These accounts were created or updated for testing the released randomized learner flow and marker visibility.

## Assessment Seeded

- Assessment ID: `1`
- EISA ID: `EISA-8BA7BD53`
- Paper: `Maintenance Planner A Randomized 20260420-064600`
- Status: `Released to students`
- Learner submission created: `Yes`
- Latest submission ID: `4`
- Latest saved PDF path: `exam_submissions/2026/04/20/STU-DEMO-001_Maintenance_Planner_A_Randomized_20260420-06460_7VQ7hFU.pdf`

## Accounts

### Learner

- Email: `learner.demo@example.com`
- Password: `DemoLearner123!`
- Role: `learner`
- Student number: `STU-DEMO-001`

### Marker

- Email: `marker.demo@example.com`
- Password: `DemoMarker123!`
- Role: `assessor_marker`

### Internal Moderator

- Email: `internal.mod.demo@example.com`
- Password: `DemoInternal123!`
- Role: `internal_mod`

### External Moderator

- Email: `external.mod.demo@example.com`
- Password: `DemoExternal123!`
- Role: `external_mod`

## Expected Visibility

- The learner account should see the released randomized assessment on the learner dashboard.
- The learner submission was created through the live submission flow, so the marker dashboard should show that submission.
- The internal moderator dashboard will only show it after marker grading sets `marks`.
- The external moderator dashboard will only show it after internal moderation sets `internal_marks`.
- The latest generated learner submission PDF was used to verify the future-only PDF heading cleanup.