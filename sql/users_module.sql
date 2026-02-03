-- Users Module Tables
-- This file creates the user profiles table
-- Compatible with Supabase PostgreSQL
-- Note: Authentication is handled by Supabase Auth (auth.users table)
-- This table stores additional user profile information

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User Profiles table
-- References auth.users for authentication data
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    phone TEXT,
    bio TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT user_profiles_email_unique UNIQUE (email)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_created_at ON user_profiles(created_at DESC);

-- Function to automatically create user profile when user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NULL)
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create user profile on signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Add comments for documentation
COMMENT ON TABLE user_profiles IS 'Stores user profile information, references auth.users for authentication';
COMMENT ON COLUMN user_profiles.id IS 'References auth.users.id (primary key)';
COMMENT ON COLUMN user_profiles.email IS 'User email address (synced from auth.users)';
COMMENT ON COLUMN user_profiles.full_name IS 'User full name';
COMMENT ON COLUMN user_profiles.avatar_url IS 'URL to user avatar image';
COMMENT ON COLUMN user_profiles.phone IS 'User phone number';
COMMENT ON COLUMN user_profiles.bio IS 'User biography/description';
