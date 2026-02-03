from supabase import Client
from app.modules.environments.schemas import (
    EnvironmentCreate, EnvironmentUpdate, EnvironmentResponse, EnvironmentWithWorkshopsResponse
)
from typing import List, Optional
from fastapi import HTTPException


class EnvironmentService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def create_environment(self, environment_data: EnvironmentCreate, user_id: str) -> EnvironmentResponse:
        """Create a new environment"""
        try:
            # Verify group exists
            group_result = self.supabase.table("groups")\
                .select("id")\
                .eq("id", environment_data.group_id)\
                .single()\
                .execute()
            
            if not group_result.data:
                raise HTTPException(status_code=404, detail="Group not found")
            
            # Verify user is member of the group
            member_result = self.supabase.table("group_members")\
                .select("id")\
                .eq("group_id", environment_data.group_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if not member_result.data:
                raise HTTPException(
                    status_code=403,
                    detail="You must be a member of this group to create an environment"
                )
            
            # Create environment
            result = self.supabase.table("environments").insert({
                "name": environment_data.name,
                "description": environment_data.description,
                "group_id": environment_data.group_id,
                "user_id": user_id
            }).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create environment")
            
            return EnvironmentResponse(**result.data[0])
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_environment_by_id(self, environment_id: str) -> EnvironmentResponse:
        """Get environment by ID"""
        try:
            result = self.supabase.table("environments")\
                .select("*")\
                .eq("id", environment_id)\
                .single()\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Environment not found")
            
            return EnvironmentResponse(**result.data)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def update_environment(self, environment_id: str, environment_data: EnvironmentUpdate) -> EnvironmentResponse:
        """Update environment"""
        try:
            update_data = {}
            if environment_data.name:
                update_data["name"] = environment_data.name
            if environment_data.description is not None:
                update_data["description"] = environment_data.description
            
            if not update_data:
                # No changes, return existing
                return self.get_environment_by_id(environment_id)
            
            update_data["updated_at"] = "now()"
            
            result = self.supabase.table("environments")\
                .update(update_data)\
                .eq("id", environment_id)\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Environment not found")
            
            return EnvironmentResponse(**result.data[0])
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def list_environments(self, user_id: str, group_id: Optional[str] = None, limit: int = 10, offset: int = 0) -> List[EnvironmentResponse]:
        """List environments for user's groups"""
        try:
            # Get user's group memberships
            groups_result = self.supabase.table("group_members")\
                .select("group_id")\
                .eq("user_id", user_id)\
                .execute()
            
            if not groups_result.data:
                return []
            
            user_group_ids = [g["group_id"] for g in groups_result.data]
            
            # Filter by user's groups
            query = self.supabase.table("environments")\
                .select("*")\
                .in_("group_id", user_group_ids)
            
            # Optional group filter
            if group_id:
                if group_id not in user_group_ids:
                    raise HTTPException(
                        status_code=403,
                        detail="You must be a member of this group to view its environments"
                    )
                query = query.eq("group_id", group_id)
            
            result = query.order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            
            return [EnvironmentResponse(**env) for env in result.data]
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def delete_environment(self, environment_id: str) -> bool:
        """Delete environment"""
        try:
            result = self.supabase.table("environments")\
                .delete()\
                .eq("id", environment_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_environment_with_workshops(self, environment_id: str) -> EnvironmentWithWorkshopsResponse:
        """Get environment with nested workshops"""
        try:
            # Get environment
            env_result = self.supabase.table("environments")\
                .select("*")\
                .eq("id", environment_id)\
                .single()\
                .execute()
            
            if not env_result.data:
                raise HTTPException(status_code=404, detail="Environment not found")
            
            # Get workshops in this environment
            workshops_result = self.supabase.table("workshops")\
                .select("*")\
                .eq("environment_id", environment_id)\
                .order("created_at", desc=True)\
                .execute()
            
            env_data = env_result.data
            env_data["workshops"] = workshops_result.data if workshops_result.data else []
            
            return EnvironmentWithWorkshopsResponse(**env_data)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
