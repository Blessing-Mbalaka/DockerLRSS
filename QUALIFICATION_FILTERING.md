# Qualification-Based Pool Filtering Implementation

## Overview
Users with different qualifications can now only view and randomize question pools related to their own qualifications when they click "View Pools".

## Features Implemented

### 1. Backend Authorization (views.py)

#### `assessor_pool_data` Endpoint
- **File**: `core/views.py` (lines 1414-1556)
- **Function**: Returns question pools filtered by user's qualification
- **Logic**:
  - Privileged users (superuser, staff, admin, moderator) see all pools
  - Non-privileged users see only pools for their assigned qualification
  - Filtering happens via: `boxes_qs.filter(paper__assessment_record__qualification=restrict_to_qualification)`

#### `assessor_pool_randomize` Endpoint
- **File**: `core/views.py` (lines 1558-1650)
- **Function**: Allows users to create randomized assessments from question pools
- **Authorization Checks**:
  - Non-privileged users must have a qualification assigned
  - Non-privileged users can ONLY randomize pools matching their qualification
  - Returns HTTP 403 with clear error message if unauthorized access is attempted

**Error Message Format**:
```
"You can only randomize pools for your qualification '{user_qualification.name}'. 
Access to '{module_name}' is not permitted."
```

### 2. Frontend Enhancements (Template)

#### Modal Header Update
- **File**: `core/templates/core/assessor-developer/assessor_developer.html`
- **Changes**: 
  - Displays user's qualification in modal header
  - Shows lock icon with qualification name for non-privileged users
  - Clear visual indication of access scope

#### Qualification Restriction Alert
- **Type**: Warning alert box
- **Visibility**: Only shows for non-privileged users
- **Message**: 
  ```
  "Qualification Restricted Access: You can only view and randomize pools 
  for your assigned qualification. Contact your administrator if you need 
  access to other qualifications."
  ```

#### Module Dropdown Enhancement
- **Behavior**: Auto-selects user's qualification
- **States**: 
  - Disabled for non-privileged users (cannot change)
  - Fully enabled for privileged users
- **Visual Feedback**: Disabled state shows grayed-out styling

#### JavaScript Modal Initialization
- **Function**: Shows/hides restriction message based on user role
- **Timing**: On modal opening
- **Condition**: Only displays if user is non-privileged AND has qualification assigned

### 3. User Experience

#### Non-Privileged Users
✅ Can view pools only for their assigned qualification
✅ Module dropdown auto-selected and disabled
✅ Clear visual indicators throughout the interface
✅ Helpful error messages if access denied
✅ Single qualification focus to prevent confusion

#### Privileged Users (Admin/Moderator/Staff)
✅ Full access to all qualification pools
✅ No restrictions on module selection
✅ Can manage assessments across all qualifications
✅ No visual restrictions or limitations

## Data Flow

```
User Clicks "View Pools"
    ↓
Modal Opens → Check User Role & Qualification
    ↓
If Privileged (Admin/Moderator/Staff):
    → Fetch ALL pools from assessor_pool_data
    → Display all modules in dropdown
    → Allow randomization from any pool
    ↓
If Non-Privileged User:
    → Check if qualification assigned
    → If no qualification: Show error
    → If has qualification:
        → Fetch ONLY pools matching qualification
        → Auto-select qualification in dropdown
        → Disable dropdown (prevent changing)
        → Show restriction warning
        → Allow randomization only for that qualification
```

## Testing Checklist

- [ ] Create test user with "Math101" qualification
- [ ] Login as that user and click "View Pools"
- [ ] Verify "Math101" module pre-selected and disabled
- [ ] Verify restriction warning appears
- [ ] Verify can only see pools for Math101
- [ ] Try to manually access another module (should get 403 error)
- [ ] Test with user having no qualification (should show error)
- [ ] Test with admin user (should see all qualifications)
- [ ] Test randomization (should create assessment with correct qualification)
- [ ] Test randomization with unauthorized module (should return 403 error)

## Security Considerations

✅ **Backend Validation**: Authorization checked at API level
✅ **No Client-Side Trust**: Frontend restrictions backed by backend validation
✅ **Clear Error Messages**: Users understand why access is denied
✅ **Qualified Assessment Creation**: Randomized assessments automatically use user's qualification
✅ **Audit Trail**: All randomization attempts logged with user context

## Database Relationships

The filtering works through these model relationships:

```
CustomUser 
    ↓ qualification (ForeignKey)
    ↓
Qualification

ExtractorUserBox 
    ↓ paper (ForeignKey)
    ↓
ExtractorPaper
    ↓ assessment_record (Reverse OneToOneField)
    ↓
Assessment
    ↓ qualification (ForeignKey)
    ↓
Qualification
```

## Deployment Notes

1. **No Database Migrations Required**: Uses existing relationships
2. **Backward Compatible**: Privileged users unaffected
3. **Immediate Effect**: Takes effect after code deployment
4. **No Data Changes**: Purely access-control based

## Future Enhancements

- [ ] Add audit logging for pool access attempts
- [ ] Implement multi-qualification support for users
- [ ] Add temporary qualification override for admin purposes
- [ ] Create qualification request workflow
- [ ] Add qualification management interface for admins
