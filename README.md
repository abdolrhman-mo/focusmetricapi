# Troubleshooting Guide

## Google OAuth Issues

### Problem 1:

**Swagger**
when trying to send google retrieved token in the request the response that swagger gives me is:
{
  "error": "Authentication failed. Please try again."
}
**Terminal**
Unexpected error during Google OAuth: type object 'Token' has no attribute 'objects'
Internal Server Error: /api/auth/google/

### Solution: 
'rest_framework.authtoken' was missing from INSTALLED_APPS list in settings.py


### Problem 2:

A Django web application has a suboptimal API design where creating a single logical entity (a focus entry with hours and reason) requires two sequential HTTP requests from the client:

Client sends reason text → Server creates reason record → Returns reason UUID
Client sends hours + reason UUID → Server creates focus entry → Returns success

This creates multiple technical and user experience issues including unnecessary network latency, potential data inconsistency, and increased complexity.

### Solution ✅ IMPLEMENTED

**Single Atomic Endpoint**
Replace the two-request pattern with a single endpoint that accepts all required data and handles the complete operation atomically.

**Implementation Details:**

1. **Enhanced FocusEntrySerializer** - Now supports both `reason_id` and `reason_text` fields
2. **Atomic Transactions** - All database operations wrapped in `@transaction.atomic`
3. **Automatic Reason Management** - Uses `get_or_create()` for reason handling
4. **Comprehensive Validation** - Prevents conflicts and ensures data integrity
5. **Updated API Documentation** - Swagger docs reflect new dual approach

**API Usage Examples:**

**Create with existing reason:**
```json
POST /api/entries/
{
  "date": "2025-07-26",
  "hours": 6.5,
  "reason_id": "f9768cf7-0b87-4ae5-a60e-9ce63e9d54a8"
}
```

**Create with new reason:**
```json
POST /api/entries/
{
  "date": "2025-07-26",
  "hours": 6.5,
  "reason_text": "New reason created in single request"
}
```

**Bulk update with reason text:**
```json
POST /api/entries/bulk-update/
{
  "dates": ["2025-07-26", "2025-07-27"],
  "reason_text": "Bulk update reason",
  "hours": 8.0
}
```

**Benefits:**
- ✅ **Single Request** - No more two-step process
- ✅ **Atomic Operations** - Data consistency guaranteed
- ✅ **Automatic Deduplication** - Same reason text creates same reason
- ✅ **Backward Compatible** - Existing `reason_id` still works
- ✅ **Enhanced UX** - Faster, more reliable API calls