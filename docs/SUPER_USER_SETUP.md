# Super User Setup Guide

## Overview
Super users have full access to all resources and can bypass all permission checks. The super user status is stored in `app_metadata.type` in Supabase Auth.

## Setting Super User Status

### Method 1: Supabase Dashboard (Recommended for Initial Setup)

1. Go to your Supabase project dashboard
2. Navigate to **Authentication** → **Users**
3. Find the user you want to make a super user
4. Click on the user to open their details
5. Scroll down to **App Metadata** section
6. Click **Edit** and add:
   ```json
   {
     "type": "super_user"
   }
   ```
7. Click **Save**

### Method 2: Using the API Endpoint

**Endpoint:** `POST /api/v1/auth/set-super-user`

**Requirements:**
- You must be a super user to set other users as super users
- Requires `SUPABASE_SERVICE_ROLE_KEY` in your `.env` file

**Request Body:**
```json
{
  "user_id": "user-uuid-here",
  "is_super_user": true
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/set-super-user" \
  -H "Authorization: Bearer YOUR_SUPER_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "is_super_user": true
  }'
```

### Method 3: Using Supabase Admin API Directly

You can use the Supabase Admin API with your service role key:

```python
from supabase import create_client

supabase_url = "your-project-url"
service_role_key = "your-service-role-key"

admin_client = create_client(supabase_url, service_role_key)

# Set super user
admin_client.auth.admin.update_user_by_id(
    "user-uuid",
    {"app_metadata": {"type": "super_user"}}
)

# Remove super user
admin_client.auth.admin.update_user_by_id(
    "user-uuid",
    {"app_metadata": {}}
)
```

## Environment Configuration

Add to your `.env` file:
```env
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

**Important:** The service role key has admin privileges. Keep it secure and never expose it in client-side code.

## How It Works

1. When a user logs in, their JWT token includes `app_metadata`
2. The `is_super_user()` function checks if `app_metadata.type == "super_user"`
3. Super users bypass all permission checks in route dependencies
4. Super users can add users to any group and perform any action

## Security Notes

- `app_metadata` is server-side only and cannot be modified by users
- Only users with super_user status (or service role key) can set super_user status
- The service role key should only be used server-side
- Consider implementing additional audit logging for super user actions
