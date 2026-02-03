from supabase import Client
from app.modules.users.schemas import (
    UserUpdate, UserResponse, UserWithGroupsResponse,
    UserGroupAdd, UserGroupResponse
)
from typing import List, Optional
from fastapi import HTTPException


class UserService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def get_user_by_id(self, user_id: str) -> UserResponse:
        """Get user profile by ID"""
        try:
            result = self.supabase.table("user_profiles")\
                .select("*")\
                .eq("id", user_id)\
                .single()\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="User not found")
            
            return UserResponse(**result.data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Get user profile by email"""
        try:
            result = self.supabase.table("user_profiles")\
                .select("*")\
                .eq("email", email)\
                .single()\
                .execute()
            
            if not result.data:
                return None
            
            return UserResponse(**result.data)
        except Exception:
            return None
    
    def update_user(self, user_id: str, user_data: UserUpdate) -> UserResponse:
        """Update user profile"""
        try:
            from datetime import datetime
            update_data = {"updated_at": datetime.utcnow().isoformat()}
            if user_data.full_name is not None:
                update_data["full_name"] = user_data.full_name
            if user_data.avatar_url is not None:
                update_data["avatar_url"] = user_data.avatar_url
            if user_data.phone is not None:
                update_data["phone"] = user_data.phone
            if user_data.bio is not None:
                update_data["bio"] = user_data.bio
            
            result = self.supabase.table("user_profiles")\
                .update(update_data)\
                .eq("id", user_id)\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="User not found")
            
            return UserResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def list_users(
        self,
        current_user_id: str,
        limit: int = 10,
        offset: int = 0,
        allow_all: bool = False
    ) -> List[UserResponse]:
        """List users: from token user_id get their groups, then return all group members' profiles. Super_user (allow_all) gets all users."""
        try:
            if allow_all:
                result = self.supabase.table("user_profiles")\
                    .select("*")\
                    .order("created_at", desc=True)\
                    .limit(limit)\
                    .offset(offset)\
                    .execute()
                return [UserResponse(**user) for user in result.data]
            # 1. Get group IDs for the current user (from token)
            groups_result = self.supabase.table("group_members")\
                .select("group_id")\
                .eq("user_id", current_user_id)\
                .execute()
            if not groups_result.data:
                return []
            group_ids = [g["group_id"] for g in groups_result.data]
            # 2. Get all user_ids that are members of those groups
            members_result = self.supabase.table("group_members")\
                .select("user_id")\
                .in_("group_id", group_ids)\
                .execute()
            if not members_result.data:
                return []
            user_ids = list({m["user_id"] for m in members_result.data})
            # 3. Return user_profiles for those user_ids
            result = self.supabase.table("user_profiles")\
                .select("*")\
                .in_("id", user_ids)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            return [UserResponse(**user) for user in result.data]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user profile and auth user"""
        try:
            # Remove user from all groups first
            self.supabase.table("group_members")\
                .delete()\
                .eq("user_id", user_id)\
                .execute()
            
            # Delete user profile (auth.users will be deleted via CASCADE)
            result = self.supabase.table("user_profiles")\
                .delete()\
                .eq("id", user_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_user_with_groups(self, user_id: str) -> UserWithGroupsResponse:
        """Get user with all associated groups"""
        try:
            # Get user profile
            user_result = self.supabase.table("user_profiles")\
                .select("*")\
                .eq("id", user_id)\
                .single()\
                .execute()
            
            if not user_result.data:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get groups for this user
            groups_result = self.supabase.table("group_members")\
                .select("group_id, role, groups(*)")\
                .eq("user_id", user_id)\
                .execute()
            
            groups = []
            if groups_result.data:
                for item in groups_result.data:
                    if item.get("groups"):
                        group_data = item["groups"].copy()
                        group_data["membership_role"] = item.get("role", "member")
                        groups.append(group_data)
            
            user_data = user_result.data
            user_data["groups"] = groups
            
            return UserWithGroupsResponse(**user_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_user_groups(self, user_id: str) -> List[dict]:
        """Get all groups for a user"""
        try:
            result = self.supabase.table("group_members")\
                .select("group_id, role, groups(*)")\
                .eq("user_id", user_id)\
                .execute()
            
            groups = []
            if result.data:
                for item in result.data:
                    if item.get("groups"):
                        group_data = item["groups"].copy()
                        group_data["membership_role"] = item.get("role", "member")
                        groups.append(group_data)
            
            return groups
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def add_user_to_group(self, user_id: str, group_data: UserGroupAdd) -> UserGroupResponse:
        """Add user to a group"""
        try:
            # Verify user exists
            self.get_user_by_id(user_id)
            
            # Verify group exists
            group_result = self.supabase.table("groups")\
                .select("*")\
                .eq("id", group_data.group_id)\
                .single()\
                .execute()
            
            if not group_result.data:
                raise HTTPException(status_code=404, detail="Group not found")
            
            # Check if already a member
            existing = self.supabase.table("group_members")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("group_id", group_data.group_id)\
                .execute()
            
            if existing.data:
                raise HTTPException(status_code=400, detail="User already a member of this group")
            
            # Add user to group
            result = self.supabase.table("group_members").insert({
                "user_id": user_id,
                "group_id": group_data.group_id,
                "role": group_data.role or "member"
            }).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to add user to group")
            
            return UserGroupResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def remove_user_from_group(self, user_id: str, group_id: str) -> bool:
        """Remove user from a group"""
        try:
            result = self.supabase.table("group_members")\
                .delete()\
                .eq("user_id", user_id)\
                .eq("group_id", group_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
