from supabase import Client
from app.modules.groups.schemas import (
    GroupCreate, GroupUpdate, GroupResponse, GroupWithRolesResponse,
    GroupMemberAdd, GroupMemberResponse, GroupRoleAssign, GroupRoleResponse
)
from typing import List, Optional
from fastapi import HTTPException


class GroupService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def create_group(self, group_data: GroupCreate, user_id: str) -> GroupResponse:
        """Create a new group"""
        try:
            result = self.supabase.table("groups").insert({
                "name": group_data.name,
                "description": group_data.description,
                "user_id": user_id
            }).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create group")
            
            # Add creator as owner
            self.supabase.table("group_members").insert({
                "group_id": result.data[0]["id"],
                "user_id": user_id,
                "role": "owner"
            }).execute()
            
            return GroupResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_group_by_id(self, group_id: str) -> GroupResponse:
        """Get group by ID"""
        try:
            result = self.supabase.table("groups")\
                .select("*")\
                .eq("id", group_id)\
                .single()\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Group not found")
            
            return GroupResponse(**result.data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def update_group(self, group_id: str, group_data: GroupUpdate) -> GroupResponse:
        """Update group"""
        try:
            update_data = {}
            if group_data.name:
                update_data["name"] = group_data.name
            if group_data.description is not None:
                update_data["description"] = group_data.description
            
            result = self.supabase.table("groups")\
                .update(update_data)\
                .eq("id", group_id)\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Group not found")
            
            return GroupResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def list_groups(
        self,
        member_of_user_id: Optional[str] = None,
        created_by_me: bool = False,
        group_ids: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[GroupResponse]:
        """List groups: by default only groups the user is a member of; optional created_by_me to restrict to groups they created. Pass group_ids to avoid extra group_members query."""
        try:
            if member_of_user_id is not None or group_ids is not None:
                if group_ids is None:
                    members_result = self.supabase.table("group_members")\
                        .select("group_id")\
                        .eq("user_id", member_of_user_id)\
                        .execute()
                    if not members_result.data:
                        return []
                    group_ids = [m["group_id"] for m in members_result.data]
                if not group_ids:
                    return []
                query = self.supabase.table("groups").select("*").in_("id", group_ids)
                if created_by_me and member_of_user_id:
                    query = query.eq("user_id", member_of_user_id)
            else:
                query = self.supabase.table("groups").select("*")
            result = query.order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            return [GroupResponse(**group) for group in result.data]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def delete_group(self, group_id: str) -> bool:
        """Delete group"""
        try:
            # Delete group members first
            self.supabase.table("group_members")\
                .delete()\
                .eq("group_id", group_id)\
                .execute()
            
            # Delete group roles
            self.supabase.table("group_roles")\
                .delete()\
                .eq("group_id", group_id)\
                .execute()
            
            # Delete group
            result = self.supabase.table("groups")\
                .delete()\
                .eq("id", group_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def add_member(self, group_id: str, member_data: GroupMemberAdd) -> GroupMemberResponse:
        """Add a member to the group"""
        try:
            # Verify group exists
            self.get_group_by_id(group_id)
            
            result = self.supabase.table("group_members").insert({
                "group_id": group_id,
                "user_id": member_data.user_id,
                "role": "member"
            }).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to add member")
            
            return GroupMemberResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def remove_member(self, group_id: str, user_id: str) -> bool:
        """Remove a member from the group"""
        try:
            result = self.supabase.table("group_members")\
                .delete()\
                .eq("group_id", group_id)\
                .eq("user_id", user_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def list_members(self, group_id: str) -> List[GroupMemberResponse]:
        """List all members of a group"""
        try:
            result = self.supabase.table("group_members")\
                .select("*")\
                .eq("group_id", group_id)\
                .execute()
            
            return [GroupMemberResponse(**member) for member in result.data]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_group_with_roles(self, group_id: str) -> GroupWithRolesResponse:
        """Get group with all associated roles"""
        try:
            # Get group
            group_result = self.supabase.table("groups")\
                .select("*")\
                .eq("id", group_id)\
                .single()\
                .execute()
            
            if not group_result.data:
                raise HTTPException(status_code=404, detail="Group not found")
            
            # Get roles for this group
            roles_result = self.supabase.table("group_roles")\
                .select("role_id, roles(*)")\
                .eq("group_id", group_id)\
                .execute()
            
            roles = []
            if roles_result.data:
                for item in roles_result.data:
                    if item.get("roles"):
                        roles.append(item["roles"])
            
            group_data = group_result.data
            group_data["roles"] = roles
            
            return GroupWithRolesResponse(**group_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def assign_role_to_group(self, group_id: str, role_id: str) -> GroupRoleResponse:
        """Assign a role to a group"""
        try:
            # Verify group exists
            self.get_group_by_id(group_id)
            
            # Verify role exists
            role_result = self.supabase.table("roles")\
                .select("*")\
                .eq("id", role_id)\
                .single()\
                .execute()
            
            if not role_result.data:
                raise HTTPException(status_code=404, detail="Role not found")
            
            # Check if already assigned
            existing = self.supabase.table("group_roles")\
                .select("*")\
                .eq("group_id", group_id)\
                .eq("role_id", role_id)\
                .execute()
            
            if existing.data:
                raise HTTPException(status_code=400, detail="Role already assigned to group")
            
            # Assign role
            result = self.supabase.table("group_roles").insert({
                "group_id": group_id,
                "role_id": role_id
            }).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to assign role")
            
            return GroupRoleResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def remove_role_from_group(self, group_id: str, role_id: str) -> bool:
        """Remove a role from a group"""
        try:
            result = self.supabase.table("group_roles")\
                .delete()\
                .eq("group_id", group_id)\
                .eq("role_id", role_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_group_roles(self, group_id: str) -> List[dict]:
        """Get all roles for a group"""
        try:
            result = self.supabase.table("group_roles")\
                .select("role_id, roles(*)")\
                .eq("group_id", group_id)\
                .execute()
            
            roles = []
            if result.data:
                for item in result.data:
                    if item.get("roles"):
                        roles.append(item["roles"])
            
            return roles
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
