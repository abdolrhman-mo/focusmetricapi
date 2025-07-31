# Project: Focus Metric - Backend API Specification

## 1. Tech Stack

-   **Backend Framework:** Django
-   **API Toolkit:** Django REST Framework (DRF)
-   **Database:** SQLite
-   **Authentication:** DRF Token-based Authentication & Google OAuth
-   **Environment Variables:** `python-decouple`

## 2. Database Schema

The database consists of three main tables: `Users`, `Reasons`, and `FocusEntries`.

#### Table: `User`

Stores user authentication and profile information. Integrates with Google OAuth and DRF Token authentication.

-   **`id`**: `Integer` - Primary Key (Auto-incrementing)
-   **`username`**: `String`- Set to email address (required by Django, not user-facing)
-   **`email`**: `String`- User's email address (unique, required for Google OAuth)
-   **`password`**: `String` - Field exists but remains unused (Django requirement)
-   **`first_name`**: `String` - User's first name (from Google profile)
-   **`last_name`**: `String` - User's last name (from Google profile)
-   **`is_active`**: `Boolean` - Whether user account is active (default: True)
-   **`date_joined`**: `DateTime` - Account creation timestamp
-   **`last_login`**: `DateTime` - Last login timestamp (nullable)
-   **`is_staff`**: `Boolean` - Django admin access (default: False, admin-only field)
-   **`is_superuser`**: `Boolean` - Full admin permissions (default: False, admin-only field)

#### Table: `Reason`

Stores user-defined reasons for focus or distraction. Each reason is owned by a user.

-   **`id`**: `UUID` - Primary Key
-   **`user_id`**: `Integer` - Foreign Key to `User` table
-   **`description`**: `Text`
-   **`created_at`**: `DateTime`

#### Table: `FocusEntry`

Represents a single day's focus data for a user.

-   **`id`**: `UUID` - Primary Key
-   **`user_id`**: `Integer` - Foreign Key to `User` table
-   **`date`**: `Date`
-   **`hours`**: `Float` (Optional)
-   **`reason_id`**: `UUID` (Optional) - Foreign Key to `Reason` table
-   **Constraint**: `(user_id, date)` must be unique.

## 3. API Endpoints

All endpoints will be versioned under `/api/`. Access to all endpoints (except auth) will require Token Authentication using `Authorization: Token <token>` header.

### Authentication (`/api/auth/`)

-   **`POST /google/`**
    -   **Description:** Authenticates user with Google OAuth token and returns DRF token.
    -   **Request Body:** `{ "token": "google-oauth-id-token-string" }`
    -   **Response:** `200 OK`
    ```json
    {
        "token": "drf-token-key-example",
        "user": {
            "id": 1,
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "name": "John Doe",
            "date_joined": "2024-01-15T10:30:00Z"
        },
        "is_new_user": true
    }
    ```
    -   **Error Response:** `400 Bad Request`
    ```json
    {
        "error": "Invalid Google token"
    }
    ```

-   **`GET /profile/`**
    -   **Description:** Retrieves current authenticated user's profile information including goal data.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK`
    ```json
    {
        "id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "name": "John Doe",
        "date_joined": "2024-01-15T10:30:00Z",
        "goal": {
            "is_activated": true,
            "hours": 8,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    }
    ```
    -   **Response (no goal):** `200 OK`
    ```json
    {
        "id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "name": "John Doe",
        "date_joined": "2024-01-15T10:30:00Z",
        "goal": null
    }
    ```

-   **`PUT /profile/`**
    -   **Description:** Updates current user's profile information.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** `{ "first_name": "John", "last_name": "Smith" }`
    -   **Response:** `200 OK`
    ```json
    {
        "id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Smith",
        "name": "John Smith",
        "date_joined": "2024-01-15T10:30:00Z"
    }
    ```

-   **`POST /logout/`**
    -   **Description:** Deletes the user's auth token from the server (invalidates token).
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK`
    ```json
    {
        "message": "Successfully logged out"
    }
    ```

-   **`GET /stats/`**
    -   **Description:** Retrieves user's focus tracking statistics.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK`
    ```json
    {
        "total_focus_entries": 45,
        "total_focus_hours": 180.5,
        "current_streak": 7,
        "longest_streak": 12,
        "average_daily_hours": 4.2,
        "most_used_reason": {
            "id": "uuid-string",
            "description": "Work focus",
            "usage_count": 25
        },
        "account_created": "2024-01-15T10:30:00Z",
        "days_since_signup": 30
    }
    ```

-   **`DELETE /profile/`**
    -   **Description:** Deletes current user's account and all associated data.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `204 No Content`

### Focus Entries (`/api/entries/`)

-   **`GET /`**
    -   **Description:** Lists all focus entries for the authenticated user. Supports filtering by date range.
    -   **Headers:** `Authorization: Token <token>`
    -   **Query Params:** `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&reason=uuid&min_hours=2&max_hours=8&ordering=-date&page=1`
    -   **Response:** `200 OK`
    ```json
    {
        "count": 45,
        "next": "http://localhost:8000/api/entries/?page=2",
        "previous": null,
        "results": [
            {
                "id": "uuid-string",
                "date": "2024-01-15",
                "hours": 6.5,
                "reason_id": "uuid-string",
                "reason_description": "Work focus"
            }
        ]
    }
    ```

-   **`POST /`**
    -   **Description:** Creates a single new focus entry. Supports both `reason_id` (existing reason) and `reason_text` (new reason) in single request.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** 
    ```json
    {
        "date": "2024-01-15",
        "hours": 6.5,
        "reason_id": "uuid-string"
    }
    ```
    OR
    ```json
    {
        "date": "2024-01-15",
        "hours": 6.5,
        "reason_text": "New reason created in single request"
    }
    ```
    -   **Response:** `201 Created`
    ```json
    {
        "id": "uuid-string",
        "date": "2024-01-15",
        "hours": 6.5,
        "reason": {
            "id": "uuid-string",
            "description": "Work focus",
            "created_at": "2024-01-15T10:30:00Z"
        }
    }
    ```

-   **`POST /bulk-update/`**
    -   **Description:** Updates multiple focus entries at once. Supports both `reason_id` and `reason_text`.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** 
    ```json
    {
        "dates": ["2024-01-15", "2024-01-16"],
        "reason_text": "Bulk update reason",
        "hours": 8.0
    }
    ```
    -   **Response:** `200 OK`
    ```json
    {
        "message": "Successfully processed 2 dates",
        "updated_count": 1,
        "created_count": 1,
        "entries": [
            {
                "id": "uuid-string",
                "date": "2024-01-15",
                "hours": 8.0,
                "reason_id": "uuid-string"
            }
        ]
    }
    ```

-   **`GET /<uuid:id>/`**
    -   **Description:** Retrieve a specific focus entry.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK`
    ```json
    {
        "id": "uuid-string",
        "date": "2024-01-15",
        "hours": 6.5,
        "reason": {
            "id": "uuid-string",
            "description": "Work focus",
            "created_at": "2024-01-15T10:30:00Z"
        }
    }
    ```

-   **`PUT /<uuid:id>/`**
    -   **Description:** Update a focus entry (full update). Supports both `reason_id` and `reason_text`.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** Same as POST
    -   **Response:** `200 OK` (same as POST response)

-   **`PATCH /<uuid:id>/`**
    -   **Description:** Partially update a focus entry. Supports both `reason_id` and `reason_text`.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** Partial data (same fields as POST)
    -   **Response:** `200 OK` (same as POST response)

-   **`DELETE /<uuid:id>/`**
    -   **Description:** Delete a focus entry.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `204 No Content`

### Bulk Delete Focus Entries (`/api/entries/bulk-delete/`)

#### **Purpose**
Allow users to delete multiple focus entries in a single atomic request, by specifying either a list of entry IDs or a list of dates.

#### **Endpoint**
- **URL:** `/api/entries/bulk-delete/`
- **Method:** `POST`
- **Auth:** `Authorization: Token <token>` (required)

#### **Request Body**
- **Delete by IDs:**
    ```json
    {
      "ids": ["uuid-1", "uuid-2", "uuid-3"]
    }
    ```
- **Delete by Dates:**
    ```json
    {
      "dates": ["2024-07-01", "2024-07-02"]
    }
    ```
- **Delete by Both (optional, union):**
    ```json
    {
      "ids": ["uuid-1", "uuid-2"],
      "dates": ["2024-07-01"]
    }
    ```

#### **Request Fields**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| ids   | array of UUID | No | List of FocusEntry IDs to delete |
| dates | array of date (YYYY-MM-DD) | No | List of dates to delete all entries for the user |
- At least one of `ids` or `dates` must be provided.
- If both are provided, delete the union of all specified entries.

#### **Response**
- **Success:** `200 OK`
    ```json
    {
      "deleted_count": 3,
      "deleted_ids": ["uuid-1", "uuid-2", "uuid-3"]
    }
    ```
- **Partial Success:** (if some IDs/dates not found)
    ```json
    {
      "deleted_count": 2,
      "deleted_ids": ["uuid-1", "uuid-2"],
      "not_found": ["uuid-3", "2024-07-01"]
    }
    ```
- **Error:** `400 Bad Request`
    ```json
    {
      "error": "You must provide at least one of 'ids' or 'dates'."
    }
    ```

#### **Validation & Behavior**
- Only entries belonging to the authenticated user are deleted.
- If an ID or date does not match any entry, it is ignored or reported in `not_found`.
- The operation is atomic: either all specified entries are deleted, or none if an error occurs.
- Maximum allowed: 50 IDs and/or 31 dates per request (to prevent abuse).

#### **Error Responses**
- `400 Bad Request` if neither `ids` nor `dates` is provided, or if both are empty.
- `401 Unauthorized` if not authenticated.
- `500 Internal Server Error` for unexpected failures.

### Reasons (`/api/reasons/`)

-   **`GET /`**
    -   **Description:** Lists all reasons created by the authenticated user.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK`
    ```json
    [
        {
            "id": "uuid-string",
            "description": "Work focus",
            "created_at": "2024-01-15T10:30:00Z",
            "usage_count": 25
        }
    ]
    ```

-   **`POST /`**
    -   **Description:** Creates a new reason.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** `{ "description": "A new reason" }`
    -   **Response:** `201 Created`
    ```json
    {
        "id": "uuid-string",
        "description": "A new reason",
        "created_at": "2024-01-15T10:30:00Z"
    }
    ```

-   **`GET /<uuid:id>/`**
    -   **Description:** Retrieve a specific reason with detailed information.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK`
    ```json
    {
        "id": "uuid-string",
        "description": "Work focus",
        "created_at": "2024-01-15T10:30:00Z",
        "usage_count": 25,
        "recent_entries": [
            {
                "date": "2024-01-15",
                "hours": 6.5
            }
        ]
    }
    ```

-   **`PUT /<uuid:id>/`**
    -   **Description:** Update a reason (full update).
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** `{ "description": "Updated reason description" }`
    -   **Response:** `200 OK` (same as POST response)

-   **`PATCH /<uuid:id>/`**
    -   **Description:** Partially update a reason.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** `{ "description": "Updated reason description" }`
    -   **Response:** `200 OK` (same as POST response)

-   **`DELETE /<uuid:id>/`**
    -   **Description:** Delete a reason. Cannot delete if reason is used in focus entries.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `204 No Content` (success) OR `400 Bad Request`
    ```json
    {
        "error": "Cannot delete reason 'Work focus' because it is used in 25 focus entries. Please remove it from all entries first.",
        "usage_count": 25
    }
    ```

### Feedback (`/api/feedback/`)

-   **`POST /`**
    -   **Description:** Creates a new feedback entry with star rating and/or text. At least one field (rating or text) is required.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** 
    ```json
    {
        "rating": 5,
        "text": "Great app! Really helps me stay focused."
    }
    ```
    OR
    ```json
    {
        "rating": 4
    }
    ```
    OR
    ```json
    {
        "text": "The app could use some improvements."
    }
    ```
    -   **Response:** `201 Created`
    ```json
    {
        "id": "uuid-string",
        "rating": 5,
        "text": "Great app! Really helps me stay focused.",
        "created_at": "2024-01-15T10:30:00Z"
    }
    ```
    -   **Error Response:** `400 Bad Request`
    ```json
    {
        "error": "At least one of 'rating' or 'text' must be provided.",
        "rating": ["Rating must be between 1 and 5."]
    }
    ```

### Goals (`/api/goals/`)

-   **`GET /`**
    -   **Description:** Retrieves current user's goal status.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK`
    ```json
    {
        "is_activated": true,
        "hours": 8,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
    ```
    -   **Response (no goal):** `200 OK`
    ```json
    {
        "is_activated": false,
        "hours": 2,
        "created_at": null,
        "updated_at": null
    }
    ```

-   **`POST /activate/`**
    -   **Description:** Activates user's goal. Creates goal if it doesn't exist.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** (optional)
    ```json
    {
        "hours": 8
    }
    ```
    -   **Response:** `200 OK`
    ```json
    {
        "is_activated": true,
        "hours": 8,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
    ```
    -   **Error Response:** `400 Bad Request`
    ```json
    {
        "hours": ["Hours must be a positive integer."]
    }
    ```

-   **`POST /deactivate/`**
    -   **Description:** Deactivates user's goal (preserves hours setting).
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** None required
    -   **Response:** `200 OK`
    ```json
    {
        "is_activated": false,
        "hours": 8,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
    ```

### Common HTTP Status Codes

- **200**: Success
- **201**: Created
- **204**: No Content (successful deletion)
- **400**: Bad Request (validation errors, invalid Google token)
- **401**: Unauthorized (missing/invalid DRF token)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found
- **500**: Internal Server Error

### Common Error Responses

#### Validation Errors (400 Bad Request)
```json
{
    "date": ["Cannot create entries for future dates."],
    "hours": ["Hours must be a positive number."],
    "reason_id": ["You can only use reasons that you created."],
    "reason_text": ["Cannot provide both reason_id and reason_text."]
}
```

#### Authentication Errors (401 Unauthorized)
```json
{
    "detail": "Authentication credentials were not provided."
}
```

#### Not Found Errors (404 Not Found)
```json
{
    "detail": "Not found."
}
```

#### Server Errors (500 Internal Server Error)
```json
{
    "error": "Unexpected error during Google OAuth: [error details]"
}
```

### Authentication Flow

1. **Frontend** receives Google OAuth token from Google Sign-In
2. **Frontend** sends Google token to `POST /api/auth/google/`
3. **Backend** verifies Google token and creates/finds user
4. **Backend** returns DRF token
5. **Frontend** stores DRF token and uses it for all subsequent API calls
6. **Frontend** includes `Authorization: Token <drf-token>` header in all protected requests

### Single-Request API Design

The API supports creating and updating focus entries with either existing reasons (`reason_id`) or new reasons (`reason_text`) in a single atomic request. This eliminates the need for multiple HTTP requests and ensures data consistency.

#### Key Features:
- **Atomic Operations**: All database operations are wrapped in transactions
- **Automatic Reason Management**: Uses `get_or_create()` for reason handling
- **Deduplication**: Same reason text creates the same reason object
- **Backward Compatibility**: Existing `reason_id` approach still works
- **Validation**: Prevents conflicts and ensures data integrity

#### Usage Examples:

**Create with existing reason:**
```json
POST /api/entries/
{
    "date": "2024-01-15",
    "hours": 6.5,
    "reason_id": "uuid-string"
}
```

**Create with new reason:**
```json
POST /api/entries/
{
    "date": "2024-01-15",
    "hours": 6.5,
    "reason_text": "New reason created in single request"
}
```

**Bulk update with reason text:**
```json
POST /api/entries/bulk-update/
{
    "dates": ["2024-01-15", "2024-01-16"],
    "reason_text": "Bulk update reason",
    "hours": 8.0
}
```

# Backend Development Checklist Plan

## Core Principles (Apply to Every Task)
- ✅ **Break into small chunks** - Each task should take 1-2 hours max
- ✅ **Test before moving on** - Every feature must work before next task
- ✅ **Update AI agent** - Share progress, blockers, and next steps
- ✅ **Request code review** - Get AI feedback on critical implementations
- ✅ **Document decisions** - Record why you chose specific approaches
- ✅ **Refactor constantly** - Clean code before adding new features
- ✅ **Commit** - Commit code after each section

---

## Phase 1: Project Foundation

### 1.1 Django Project Setup
- [X] Create Django project structure
- [X] Install required packages (`djangorestframework`, `django-cors-headers`, `python-decouple`, `google-auth`, `drf-yasg`)
- [X] Configure `settings.py` (CORS, DRF, environment variables, Swagger)
- [X] Create `.env` file with Google OAuth credentials
- [X] **TEST**: `python manage.py runserver` works

### 1.2 Swagger Documentation Setup
- [X] Add `drf-yasg` to INSTALLED_APPS
- [X] Configure Swagger URLs in main `urls.py`
- [X] Add API documentation settings (title, description, version)
- [X] Create custom Swagger schema configurations
- [X] **TEST**: Access `/swagger/` and `/redoc/` successfully
- [X] **AI REVIEW**: Documentation configuration and security
- [X] **DOCUMENT**: API documentation standards
- [X] **REFACTOR**: Organize documentation settings

### 1.3 Database Models
- [X] Create `authentication` app
- [X] Create `core` app for main business logic
- [X] Use Django's built-in `User` model for authentication
- [X] Implement `Reason` model with UUID primary key
- [X] Implement `FocusEntry` model with UUID primary key and constraints
- [X] Add proper `__str__` methods for admin display
- [X] **TEST**: `python manage.py makemigrations` and `python manage.py migrate`
- [ ] **TEST**: Create test data in Django shell
- [ ] **AI REVIEW**: Model design and relationships
- [ ] **DOCUMENT**: Model decisions and constraints in docstrings
- [ ] **REFACTOR**: Optimize model field choices and add Meta classes

### 1.4 Django Admin Configuration
- [X] Create `admin.py` for User model (if custom)
- [X] Create `admin.py` for Reason model with list display, filters, search
- [X] Create `admin.py` for FocusEntry model with list display, filters, date hierarchy
- [ ] Add inline editing for related models
- [X] Customize admin interface (titles, headers)
- [X] Create superuser account
- [X] **TEST**: Admin interface displays all models correctly
- [X] **TEST**: Can perform CRUD operations via admin
- [ ] **AI REVIEW**: Admin configuration and usability
- [ ] **REFACTOR**: Enhance admin interface with custom actions

---

## Phase 2: Authentication System

### 2.1 Authentication Serializers
- [X] Create `UserSerializer` for profile responses
- [X] Create `UserUpdateSerializer` for profile updates
- [X] Create `GoogleAuthSerializer` for OAuth token validation
- [X] Add proper field validation and error messages
- [X] **TEST**: Serializer validation with various inputs
- [X] **AI REVIEW**: Serializer design and validation logic
- [X] **DOCUMENT**: Serializer field choices and validation rules
- [X] **REFACTOR**: Extract common validation patterns

### 2.2 Google OAuth Authentication (Critical - Needs Review)
- [X] Create `GoogleOAuthView` class-based view
- [X] Implement Google token verification logic
- [X] Add user creation/retrieval logic with proper error handling
- [X] Add DRF token generation and response
- [X] Add Swagger documentation with examples
- [X] **TEST**: Endpoint with mock Google token using Swagger UI
- [X] **TEST**: Error cases (invalid token, network issues)
- [X] **AI REVIEW**: Security implementation and error handling
- [X] **DOCUMENT**: Authentication flow and security decisions
- [X] **REFACTOR**: Extract reusable functions, improve error messages

### 2.3 User Profile Views
- [X] Create `UserProfileView` class-based view (GET)
- [X] Create `UserProfileUpdateView` class-based view (PUT/PATCH)
- [X] Add proper permissions and authentication
- [X] Add Swagger documentation with request/response examples
- [X] **TEST**: Profile CRUD operations via Swagger UI
- [X] **TEST**: Authentication required (401 without token)
- [X] **AI REVIEW**: ViewSet design and permissions
- [X] **REFACTOR**: Consistent response formatting

### 2.4 Auth Support Views
- [X] Create `LogoutView` class-based view
- [X] Create `UserStatsView` class-based view (focus statistics)
- [X] Create `DeleteAccountView` class-based view
- [X] Add proper permissions and cascade deletion logic
- [X] Add comprehensive Swagger documentation
- [X] **TEST**: Each endpoint individually via Swagger
- [X] **TEST**: Data cleanup on account deletion via admin
- [X] **AI REVIEW**: Token invalidation and data cleanup logic
- [X] **REFACTOR**: Consistent error handling across auth views
- [X] **COMMIT**: `feat(auth): implement auth support views (logout, stats, delete)`

### 2.5 Authentication URLs & Integration
- [X] Create `authentication/urls.py` with proper URL patterns
- [X] Add authentication URLs to main `urls.py`
- [X] Test all auth endpoints via Swagger UI
- [X] Verify admin integration works with authentication
- [X] **TEST**: Complete authentication flow via admin and Swagger
- [X] **AI REVIEW**: URL structure and naming conventions
- [X] **REFACTOR**: Organize URL patterns logically
- [X] **COMMIT**: `feat(auth): check and refactor authentication URLs`

---

## Phase 3: Reasons Management

### 3.1 Reason Serializers & Views
- [X] Create `ReasonSerializer` for CRUD operations
- [X] Create `ReasonViewSet` with full CRUD operations
- [X] Add proper permissions (user can only access own reasons)
- [X] Add validation to prevent deletion of reasons in use
- [X] Add Swagger documentation
- [X] **TEST**: Full CRUD operations via Swagger UI
- [X] **TEST**: Deletion constraints (reason used in entries)
- [X] **AI REVIEW**: Simple CRUD implementation and constraints
- [X] **REFACTOR**: Consistent with entry patterns
- [X] **COMMIT**: `feat(reasons): implement reason serializers and views`

### 3.2 Reason Admin & Integration
- [X] Enhance `ReasonAdmin` with user filtering
- [X] Add reason usage statistics in admin
- [X] Test reason integration with focus entries
- [X] **TEST**: Reason management workflow via admin
- [X] **TEST**: Reason-FocusEntry relationships
- [X] **AI REVIEW**: Admin integration patterns
- [X] **REFACTOR**: Optimize reason queries
- [X] **COMMIT**: `feat(reasons): enhance reason admin and integration`

---

## Phase 4: Core Features - Focus Entries

### 4.1 Focus Entry Serializers
- [X] Create `FocusEntrySerializer` for CRUD operations
- [X] Create `FocusEntryListSerializer` for optimized list views
- [X] Create `BulkUpdateSerializer` for bulk operations
- [X] Add nested reason serialization
- [X] Add validation for date uniqueness per user
- [X] Add validation for hours (positive numbers, reasonable limits)
- [X] **TEST**: Serializer validation with various inputs via Django shell
- [X] **AI REVIEW**: Serializer relationships and validation logic
- [X] **DOCUMENT**: Business rules and validation decisions
- [X] **REFACTOR**: Optimize serializer performance
- [X] **COMMIT**: `feat(entries): implement focus entry serializers`

### 4.2 Focus Entry ViewSets (Critical - Needs Review)
- [X] Create `FocusEntryViewSet` with full CRUD operations
- [X] Add date range filtering (`start_date`, `end_date` query params)
- [X] Add ordering and pagination
- [X] Add proper permissions (user can only access own entries)
- [X] Optimize queries with `select_related` and `prefetch_related`
- [X] **TEST**: All CRUD operations via Swagger UI
- [X] **TEST**: Filtering and pagination via Swagger UI
- [X] **AI REVIEW**: ViewSet implementation and query optimization
- [X] **REFACTOR**: Extract common patterns and optimize database hits
- [X] **COMMIT**: `feat(entries): implement focus entry viewsets`

### 4.3 Focus Entry URLs & Integration
- [X] Add focus entry ViewSet to core router
- [X] Add bulk update endpoint to core URLs
- [X] Test all focus entry endpoints via Swagger UI
- [X] Verify admin integration works with focus entries
- [X] **TEST**: Complete focus entry workflow via admin and Swagger
- [X] **AI REVIEW**: URL structure and naming conventions
- [X] **REFACTOR**: Organize URL patterns logically
- [X] **COMMIT**: `feat(entries): add and integrate focus entry URLs`

### 4.4 Bulk Operations (Critical - Needs Review)
- [X] Create `BulkUpdateView` class-based view
- [X] Add validation for bulk date operations
- [X] Handle race conditions and data integrity
- [X] Add transaction management for consistency
- [X] Add comprehensive Swagger documentation
- [X] **TEST**: Bulk update with various date ranges via Swagger
- [X] **TEST**: Edge cases (overlapping dates, invalid data)
- [X] **AI REVIEW**: Performance and data consistency
- [X] **DOCUMENT**: Bulk operation design decisions and limitations
- [X] **REFACTOR**: Optimize bulk operations for performance
- [X] **COMMIT**: `feat(entries): implement bulk update operations`

### 4.5 Focus Entry Admin Enhancement
- [X] Enhance `FocusEntryAdmin` with advanced filtering
- [X] Add date hierarchy and custom list display
- [X] Add bulk actions for common operations
- [X] Add data validation in admin forms
- [X] **TEST**: Admin interface for focus entry management
- [X] **TEST**: Bulk operations via admin
- [X] **AI REVIEW**: Admin usability and data integrity
- [X] **REFACTOR**: Improve admin interface UX
- [X] **COMMIT**: `feat(entries): enhance focus entry admin`

### 4.6 Bulk Delete Focus Entries
- [X] Add `BulkDeleteSerializer` to validate input (`ids`, `dates`).
- [X] Create `BulkDeleteView` (APIView) in `core/views.py`.
- [X] Implement atomic deletion logic for IDs and/or dates.
- [X] Add endpoint to `core/urls.py` as `/entries/bulk-delete/`.
- [X] Add Swagger documentation with request/response examples.
- [X] Add tests for:
    - Deleting by IDs
    - Deleting by dates
    - Mixed/invalid input
    - Permission checks
    - Edge cases (not found, empty input)
- [X] **COMMIT:** `feat(entries): add bulk delete endpoint for focus entries`

### 4.7 Feedback System
- [X] Create `Feedback` model with fields:
  - `id`: UUID primary key
  - `user_id`: Foreign key to User
  - `rating`: Integer (1-5 stars, optional)
  - `text`: Text field for feedback content (optional)
  - `created_at`: DateTime
- [X] Create `FeedbackSerializer` for CRUD operations
- [X] Create `FeedbackViewSet` with POST endpoint for creating feedback
- [X] Add proper permissions (user can only create feedback for themselves)
- [X] Add validation for rating (1-5 range when provided)
- [X] Add validation that at least one field (rating or text) is required
- [X] Add Swagger documentation with request/response examples
- [X] Add endpoint to `core/urls.py` as `/feedback/`
- [X] **TEST**: Feedback creation via Swagger UI (rating only, text only, both)
- [X] **TEST**: Rating validation (invalid values, out of range)
- [X] **TEST**: Validation when neither rating nor text provided
- [X] **TEST**: Authentication required (401 without token)
- [X] **AI REVIEW**: Feedback system design and validation
- [X] **DOCUMENT**: Feedback system requirements and constraints
- [X] **REFACTOR**: Consistent with existing API patterns
- [X] **COMMIT**: `feat(feedback): implement feedback system with star rating`

### 4.8 Goal System
- [ ] Create `Goal` model with fields:
  - `user`: ForeignKey to User (OneToOne relationship)
  - `is_activated`: BooleanField (default=False)
  - `hours`: IntegerField (default=2)
  - `created_at`: DateTimeField (auto_now_add=True)
  - `updated_at`: DateTimeField (auto_now=True)
- [ ] Create and run migration for Goal model
- [ ] Add `__str__` method to Goal model for admin interface
- [ ] Create `GoalSerializer` with validation for hours (positive integers)
- [ ] Update `UserProfileSerializer` to include goal data
- [ ] Create goal URLs in `core/urls.py`:
  - `GET /goals/` - get current user's goal status
  - `POST /goals/activate/` - activate goal (optional hours parameter)
  - `POST /goals/deactivate/` - deactivate goal
- [ ] Create goal views:
  - `get_goal_status()` - returns current goal state
  - `activate_goal()` - activates goal with hours (auto-create if doesn't exist)
  - `deactivate_goal()` - deactivates goal (preserves hours)
- [ ] Add proper authentication and permissions
- [ ] Update profile view to include goal data with `select_related('goal')`
- [ ] Add Swagger documentation with request/response examples
- [ ] **TEST**: Goal model creation and relationships
- [ ] **TEST**: Goal activation/deactivation via Swagger UI
- [ ] **TEST**: Profile endpoint includes goal data
- [ ] **TEST**: Authentication required (401 without token)
- [ ] **TEST**: Edge cases (no goal, invalid hours, multiple activations)
- [ ] **AI REVIEW**: Goal system design and OneToOne relationship
- [ ] **DOCUMENT**: Goal system requirements and API structure
- [ ] **REFACTOR**: Consistent with existing API patterns
- [ ] **COMMIT**: `feat(goals): implement goal system with activation/deactivation`

---

## Phase 5: Advanced Features & Statistics

### 5.1 User Statistics API (Critical - Needs Review)
- [ ] Enhance `UserStatsView` with detailed metrics calculation
- [ ] Add streak calculation logic (current and longest)
- [ ] Add trend analysis (weekly/monthly averages)
- [ ] Add most used reasons statistics
- [ ] Add performance optimization with database aggregations
- [ ] Add comprehensive Swagger documentation
- [ ] **TEST**: Statistics accuracy with sample data via admin
- [ ] **TEST**: Performance with large datasets
- [ ] **AI REVIEW**: Calculation logic and performance
- [ ] **DOCUMENT**: Statistics algorithm decisions and formulas
- [ ] **REFACTOR**: Optimize database queries and caching
- [ ] **COMMIT**: `feat(stats): implement user statistics API`

### 5.2 Data Export & Reporting
- [ ] Create `DataExportView` for CSV/JSON export
- [ ] Add date range filtering for exports
- [ ] Add proper permissions and rate limiting
- [ ] Add admin action for data export
- [ ] **TEST**: Data export functionality via admin and API
- [ ] **AI REVIEW**: Export performance and security
- [ ] **REFACTOR**: Optimize export queries
- [ ] **COMMIT**: `feat(data): implement data export and reporting`

---

## Phase 6: API Polish & Production Ready

### 6.1 Error Handling & Validation (Critical - Needs Review)
- [ ] Create custom exception handler for consistent error responses
- [ ] Add comprehensive input validation across all serializers
- [ ] Add proper HTTP status codes for all scenarios  
- [ ] Add rate limiting to API endpoints
- [ ] Enhance Swagger documentation with error examples
- [ ] **TEST**: Error scenarios and edge cases via Swagger
- [ ] **TEST**: Rate limiting behavior
- [ ] **AI REVIEW**: Security and robustness
- [ ] **REFACTOR**: Consistent error handling patterns
- [ ] **COMMIT**: `fix(api): implement global error handling and validation`

### 6.2 Performance Optimization
- [ ] Add database indexes for frequently queried fields
- [ ] Optimize API queries with `select_related` and `prefetch_related`
- [ ] Add pagination to all list endpoints
- [ ] Add database query logging and optimization
- [ ] **TEST**: Performance with large amounts of test data
- [ ] **TEST**: Database query efficiency via Django debug toolbar
- [ ] **AI REVIEW**: Scalability considerations
- [ ] **REFACTOR**: Remove N+1 queries and performance bottlenecks
- [ ] **COMMIT**: `perf(api): optimize database queries and performance`

### 6.3 API Documentation & Testing
- [ ] Enhance Swagger documentation with detailed examples
- [ ] Add request/response schema documentation
- [ ] Create comprehensive API testing via Swagger UI
- [ ] Add API versioning headers
- [ ] **TEST**: All endpoints documented and working via Swagger
- [ ] **TEST**: API documentation accuracy
- [ ] **AI REVIEW**: Documentation completeness and clarity
- [ ] **REFACTOR**: Improve API documentation organization
- [ ] **COMMIT**: `docs(api): enhance and finalize API documentation`

### 6.4 Admin Interface Polish
- [ ] Add custom admin dashboard with statistics
- [ ] Add data visualization in admin (charts, graphs)
- [ ] Add export functionality to admin
- [ ] Add user management tools
- [ ] **TEST**: Complete admin workflow for app management
- [ ] **AI REVIEW**: Admin interface usability
- [ ] **REFACTOR**: Optimize admin performance
- [ ] **COMMIT**: `feat(admin): polish and enhance admin interface`

### 6.5 Security & Production Setup
- [ ] Add API authentication security headers
- [ ] Configure CORS properly for production
- [ ] Add logging and monitoring
- [ ] Add database backup considerations
- [ ] Create production settings configuration
- [ ] **TEST**: Security headers and CORS configuration
- [ ] **AI REVIEW**: Production security configuration
- [ ] **DOCUMENT**: Production deployment requirements
- [ ] **COMMIT**: `chore(deploy): configure security and production settings`

---

## Testing & Quality Assurance

### 6.6 Manual Testing via Admin & Swagger
- [ ] Create comprehensive test data via admin interface
- [ ] Test complete user workflows via admin
- [ ] Test all API endpoints via Swagger UI
- [ ] Test error scenarios and edge cases
- [ ] Test data consistency and integrity
- [ ] **AI REVIEW**: Test coverage and scenarios
- [ ] **DOCUMENT**: Manual testing procedures

### 6.7 Code Quality & Documentation
- [ ] Add docstrings to all views, serializers, and models
- [ ] Add type hints where appropriate
- [ ] Run code linting and formatting
- [ ] Create comprehensive README with setup instructions
- [ ] **AI REVIEW**: Code quality and documentation
- [ ] **REFACTOR**: Final code cleanup and optimization

---

## Daily Workflow Checklist

### Start of Each Session
- [ ] **AI UPDATE**: Share current progress and today's goals
- [ ] **REVIEW**: Check previous session's refactoring notes
- [ ] **PLAN**: Choose 1-3 small tasks from current phase

### During Development
- [ ] **TEST FREQUENTLY**: Use Swagger UI and admin after each change
- [ ] **COMMIT OFTEN**: With descriptive messages
- [ ] **ASK FOR HELP**: When stuck for >30 minutes

### End of Each Session
- [ ] **AI REVIEW**: Get feedback on completed work
- [ ] **DOCUMENT**: Record any important decisions
- [ ] **REFACTOR**: Clean up code before finishing
- [ ] **UPDATE PROGRESS**: Mark completed tasks
- [ ] **PLAN**: Identify next session's focus

---

## Weekly Review Checklist

### Every Friday
- [ ] **OVERALL REVIEW**: Request AI code review of week's work
- [ ] **REFACTOR SESSION**: Dedicated time for code cleanup
- [ ] **PROGRESS ASSESSMENT**: Update project timeline
- [ ] **ADMIN TESTING**: Comprehensive testing via admin interface
- [ ] **API TESTING**: Comprehensive testing via Swagger UI
- [ ] **BLOCKERS**: Document and plan solutions for issues
- [ ] **NEXT WEEK**: Plan focus areas and priorities