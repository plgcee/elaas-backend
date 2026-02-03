from supabase import Client
from app.modules.workshops.schemas import WorkshopCreate, WorkshopUpdate, WorkshopResponse
from typing import List, Optional
from fastapi import HTTPException
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class WorkshopService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def _get_template_ids_for_group(self, template_group_id: str) -> List[str]:
        """Return template IDs assigned to this template group. Raises if group has no templates."""
        result = self.supabase.table("template_group_assignments").select("template_id").eq("template_group_id", template_group_id).execute()
        ids = [r["template_id"] for r in (result.data or [])]
        if not ids:
            raise HTTPException(status_code=400, detail="Template group has no templates assigned")
        return ids

    def get_template_ids_for_workshop(self, workshop: WorkshopResponse) -> List[str]:
        """Return template IDs that this workshop deploys (one for single-template, many for group)."""
        if getattr(workshop, "template_group_id", None):
            return self._get_template_ids_for_group(workshop.template_group_id)
        if getattr(workshop, "template_id", None):
            return [workshop.template_id]
        raise HTTPException(status_code=400, detail="Workshop has neither template_id nor template_group_id")

    def create_workshop(self, workshop_data: WorkshopCreate, user_id: str) -> WorkshopResponse:
        """Create a new workshop (single-template or template-group)."""
        try:
            # Calculate expiration time based on TTL
            ttl_hours = workshop_data.ttl_hours or 48
            expires_at = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat()

            if workshop_data.template_group_id:
                # Group workshop: validate group exists and has templates
                group_result = self.supabase.table("template_groups").select("id").eq("id", workshop_data.template_group_id).maybe_single().execute()
                if not group_result.data:
                    raise HTTPException(status_code=404, detail="Template group not found")
                self._get_template_ids_for_group(workshop_data.template_group_id)  # raises if empty
                insert_data = {
                    "name": workshop_data.name,
                    "description": workshop_data.description,
                    "template_id": None,
                    "template_group_id": workshop_data.template_group_id,
                    "user_id": user_id,
                    "terraform_vars": workshop_data.terraform_vars or {},
                    "status": "pending",
                    "ttl_hours": ttl_hours,
                    "expires_at": expires_at,
                }
            else:
                # Single-template workshop (legacy)
                insert_data = {
                    "name": workshop_data.name,
                    "description": workshop_data.description,
                    "template_id": workshop_data.template_id,
                    "template_group_id": None,
                    "user_id": user_id,
                    "terraform_vars": workshop_data.terraform_vars or {},
                    "status": "pending",
                    "ttl_hours": ttl_hours,
                    "expires_at": expires_at,
                }

            # Add environment_id if provided
            if workshop_data.environment_id:
                # Verify environment exists and user has access
                env_result = self.supabase.table("environments")\
                    .select("group_id")\
                    .eq("id", workshop_data.environment_id)\
                    .single()\
                    .execute()
                
                if not env_result.data:
                    raise HTTPException(status_code=404, detail="Environment not found")
                
                # Verify user is member of environment's group
                member_result = self.supabase.table("group_members")\
                    .select("id")\
                    .eq("group_id", env_result.data["group_id"])\
                    .eq("user_id", user_id)\
                    .execute()
                
                if not member_result.data:
                    raise HTTPException(
                        status_code=403,
                        detail="You must be a member of this environment's group to create workshops in it"
                    )
                
                insert_data["environment_id"] = workshop_data.environment_id
            
            result = self.supabase.table("workshops").insert(insert_data).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create workshop")
            
            return WorkshopResponse(**result.data[0])
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_workshop_by_id(self, workshop_id: str) -> WorkshopResponse:
        """Get workshop by ID"""
        try:
            result = self.supabase.table("workshops")\
                .select("*")\
                .eq("id", workshop_id)\
                .maybe_single()\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Workshop not found")
            
            return WorkshopResponse(**result.data)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def update_workshop(self, workshop_id: str, workshop_data: WorkshopUpdate) -> WorkshopResponse:
        """Update workshop"""
        try:
            update_data = {}
            if workshop_data.name:
                update_data["name"] = workshop_data.name
            if workshop_data.description is not None:
                update_data["description"] = workshop_data.description
            if workshop_data.terraform_vars is not None:
                update_data["terraform_vars"] = workshop_data.terraform_vars
            if workshop_data.ttl_hours is not None:
                # Recalculate expiration time if TTL is updated
                update_data["ttl_hours"] = workshop_data.ttl_hours
                update_data["expires_at"] = (datetime.utcnow() + timedelta(hours=workshop_data.ttl_hours)).isoformat()
            
            result = self.supabase.table("workshops")\
                .update(update_data)\
                .eq("id", workshop_id)\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Workshop not found")
            
            return WorkshopResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_expired_workshops(self) -> List[WorkshopResponse]:
        """Get all workshops that have expired and need to be destroyed"""
        try:
            now = datetime.utcnow().isoformat()
            # Get expired workshops that are deployed or failed (not already destroying/destroyed)
            # Query for deployed status
            result_deployed = self.supabase.table("workshops")\
                .select("*")\
                .lt("expires_at", now)\
                .eq("status", "deployed")\
                .execute()
            
            # Query for failed status
            result_failed = self.supabase.table("workshops")\
                .select("*")\
                .lt("expires_at", now)\
                .eq("status", "failed")\
                .execute()
            
            # Combine results
            workshops = []
            if result_deployed.data:
                workshops.extend(result_deployed.data)
            if result_failed.data:
                workshops.extend(result_failed.data)
            
            return [WorkshopResponse(**workshop) for workshop in workshops]
        except Exception as e:
            logger.error(f"Error getting expired workshops: {str(e)}")
            return []
    
    def update_workshop_status(self, workshop_id: str, status: str, fargate_task_arn: Optional[str] = None, deployment_output: Optional[dict] = None) -> Optional[WorkshopResponse]:
        """Update workshop deployment status. May return None if update succeeded but fetch of updated row failed."""
        try:
            update_data = {"status": status}
            if fargate_task_arn:
                update_data["fargate_task_arn"] = fargate_task_arn
            if deployment_output:
                update_data["deployment_output"] = deployment_output

            result = self.supabase.table("workshops")\
                .update(update_data)\
                .eq("id", workshop_id)\
                .execute()

            if result.data and len(result.data) > 0:
                return WorkshopResponse(**result.data[0])
            try:
                return self.get_workshop_by_id(workshop_id)
            except Exception:
                return None
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def list_workshops(
        self,
        user_id: Optional[str] = None,
        environment_id: Optional[str] = None,
        accessible_environment_ids: Optional[List[str]] = None,
        current_user_id: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[WorkshopResponse]:
        """List workshops. When accessible_environment_ids is set, only workshops in those environments or owned by current_user_id when no environment."""
        try:
            if accessible_environment_ids is not None:
                # Workshops in user's groups' environments, or standalone (no env) owned by current user
                if not accessible_environment_ids and not current_user_id:
                    return []
                results = []
                if accessible_environment_ids:
                    r1 = self.supabase.table("workshops")\
                        .select("*")\
                        .in_("environment_id", accessible_environment_ids)\
                        .order("created_at", desc=True)\
                        .execute()
                    results.extend(r1.data or [])
                if current_user_id:
                    r2 = self.supabase.table("workshops")\
                        .select("*")\
                        .is_("environment_id", "null")\
                        .eq("user_id", current_user_id)\
                        .order("created_at", desc=True)\
                        .execute()
                    results.extend(r2.data or [])
                # Dedupe by id (workshop can't be in both), sort by created_at desc, then paginate
                seen = set()
                unique = []
                for w in sorted(results, key=lambda x: x.get("created_at") or "", reverse=True):
                    if w["id"] not in seen:
                        seen.add(w["id"])
                        unique.append(w)
                page = unique[offset:offset + limit]
                return [WorkshopResponse(**workshop) for workshop in page]
            query = self.supabase.table("workshops").select("*")
            if user_id:
                query = query.eq("user_id", user_id)
            if environment_id:
                env_result = self.supabase.table("environments")\
                    .select("group_id")\
                    .eq("id", environment_id)\
                    .single()\
                    .execute()
                if not env_result.data:
                    raise HTTPException(status_code=404, detail="Environment not found")
                if user_id:
                    member_result = self.supabase.table("group_members")\
                        .select("id")\
                        .eq("group_id", env_result.data["group_id"])\
                        .eq("user_id", user_id)\
                        .execute()
                    if not member_result.data:
                        raise HTTPException(
                            status_code=403,
                            detail="You must be a member of this environment's group to view its workshops"
                        )
                query = query.eq("environment_id", environment_id)
            result = query.order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            return [WorkshopResponse(**workshop) for workshop in result.data]
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def delete_workshop(self, workshop_id: str) -> bool:
        """Delete workshop"""
        try:
            result = self.supabase.table("workshops")\
                .delete()\
                .eq("id", workshop_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
