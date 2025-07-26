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
    -   **Response:** `200 OK` with `{ "token": "drf-token-key", "user": { "id": "uuid", "email": "user@example.com", "name": "John Doe", "is_new_user": true } }`.
    -   **Error Response:** `400 Bad Request` with `{ "error": "Invalid Google token" }`.

-   **`GET /profile/`**
    -   **Description:** Retrieves current authenticated user's profile information.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK` with `{ "id": "uuid", "email": "user@example.com", "name": "John Doe", "date_joined": "2024-01-15T10:30:00Z" }`.

-   **`PUT /profile/`**
    -   **Description:** Updates current user's profile information.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** `{ "first_name": "John", "last_name": "Smith" }`
    -   **Response:** `200 OK` with updated user profile data.

-   **`POST /logout/`**
    -   **Description:** Deletes the user's auth token from the server (invalidates token).
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK` with `{ "message": "Successfully logged out" }`.

-   **`GET /stats/`**
    -   **Description:** Retrieves user's focus tracking statistics.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK` with `{ "total_focus_entries": 45, "total_focus_hours": 180.5, "current_streak": 7, "longest_streak": 12, "average_daily_hours": 4.2, "most_used_reason": {...}, "account_created": "...", "days_since_signup": 30 }`.

-   **`DELETE /profile/`**
    -   **Description:** Deletes current user's account and all associated data.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `204 No Content`.

### Focus Entries (`/api/entries/`)

-   **`GET /`**
    -   **Description:** Lists all focus entries for the authenticated user. Supports filtering by date range.
    -   **Headers:** `Authorization: Token <token>`
    -   **Query Params:** `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
    -   **Response:** `200 OK` with a list of focus entry objects.

-   **`POST /`**
    -   **Description:** Creates a single new focus entry.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** `{ "date": "YYYY-MM-DD", "hours": 2.5, "reason_id": "uuid..." }`
    -   **Response:** `201 Created` with the new focus entry object.

-   **`PUT /bulk-update/`**
    -   **Description:** Updates multiple focus entries at once. Primarily used for the multi-day selection feature.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** `{ "dates": ["YYYY-MM-DD", "YYYY-MM-DD"], "reason_id": "uuid..." }`
    -   **Response:** `200 OK` with a list of the updated focus entry objects.

-   **`GET, PUT, PATCH, DELETE /<uuid:id>/`**
    -   **Description:** Standard Retrieve, Update, and Delete operations for a single focus entry.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK` (for GET/PUT/PATCH), `204 No Content` (for DELETE).

### Reasons (`/api/reasons/`)

-   **`GET /`**
    -   **Description:** Lists all reasons created by the authenticated user.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK` with a list of reason objects.

-   **`POST /`**
    -   **Description:** Creates a new reason.
    -   **Headers:** `Authorization: Token <token>`
    -   **Request Body:** `{ "description": "A new reason" }`
    -   **Response:** `201 Created` with the new reason object.

-   **`GET, PUT, PATCH, DELETE /<uuid:id>/`**
    -   **Description:** Standard Retrieve, Update, and Delete operations for a single reason.
    -   **Headers:** `Authorization: Token <token>`
    -   **Response:** `200 OK` (for GET/PUT/PATCH), `204 No Content` (for DELETE).

### Common HTTP Status Codes

- **200**: Success
- **201**: Created
- **204**: No Content (successful deletion)
- **400**: Bad Request (validation errors, invalid Google token)
- **401**: Unauthorized (missing/invalid DRF token)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found
- **500**: Internal Server Error

### Authentication Flow

1. **Frontend** receives Google OAuth token from Google Sign-In
2. **Frontend** sends Google token to `POST /api/auth/google/`
3. **Backend** verifies Google token and creates/finds user
4. **Backend** returns DRF token
5. **Frontend** stores DRF token and uses it for all subsequent API calls
6. **Frontend** includes `Authorization: Token <drf-token>` header in all protected requests

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
- [ ] Create `BulkUpdateView` class-based view
- [ ] Add validation for bulk date operations
- [ ] Handle race conditions and data integrity
- [ ] Add transaction management for consistency
- [ ] Add comprehensive Swagger documentation
- [ ] **TEST**: Bulk update with various date ranges via Swagger
- [ ] **TEST**: Edge cases (overlapping dates, invalid data)
- [ ] **AI REVIEW**: Performance and data consistency
- [ ] **DOCUMENT**: Bulk operation design decisions and limitations
- [ ] **REFACTOR**: Optimize bulk operations for performance
- [ ] **COMMIT**: `feat(entries): implement bulk update operations`

### 4.5 Focus Entry Admin Enhancement
- [ ] Enhance `FocusEntryAdmin` with advanced filtering
- [ ] Add date hierarchy and custom list display
- [ ] Add bulk actions for common operations
- [ ] Add data validation in admin forms
- [ ] **TEST**: Admin interface for focus entry management
- [ ] **TEST**: Bulk operations via admin
- [ ] **AI REVIEW**: Admin usability and data integrity
- [ ] **REFACTOR**: Improve admin interface UX
- [ ] **COMMIT**: `feat(entries): enhance focus entry admin`

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