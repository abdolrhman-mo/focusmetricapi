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