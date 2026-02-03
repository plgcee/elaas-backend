# Supabase Auth
# This module uses Supabase's built-in authentication system
# No custom tables are required - Supabase Auth handles:
# - User registration (auth.users table)
# - User login and session management
# - JWT token generation and validation
# - Password hashing and security

"""
Supabase Auth provides:
- auth.sign_up() - Register new users
- auth.sign_in_with_password() - Authenticate users
- auth.get_user() - Get current user from JWT token
- auth.sign_out() - Logout users

All user data is stored in Supabase's auth.users table automatically.
User metadata can be stored in user_metadata field during registration.
"""
