from supabase import Client
from app.modules.deployments.schemas import DeploymentCreate, DeploymentResponse
from typing import List, Optional
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class DeploymentService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def create_deployment(self, deployment_data: DeploymentCreate, user_id: str) -> DeploymentResponse:
        """Create a new deployment"""
        try:
            result = self.supabase.table("deployments").insert({
                "workshop_id": deployment_data.workshop_id,
                "template_id": deployment_data.template_id,
                "user_id": user_id,
                "terraform_vars": deployment_data.terraform_vars,
                "status": "pending",
                "deployment_logs": []
            }).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create deployment")
            
            return DeploymentResponse(**result.data[0])
        except Exception as e:
            logger.error(f"Error creating deployment: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_deployment_by_id(self, deployment_id: str) -> DeploymentResponse:
        """Get deployment by ID"""
        try:
            result = self.supabase.table("deployments")\
                .select("*")\
                .eq("id", deployment_id)\
                .maybe_single()\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Deployment not found")
            
            return DeploymentResponse(**result.data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting deployment: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def update_deployment_status(
        self, 
        deployment_id: str, 
        status: str,
        logs: Optional[List[str]] = None,
        terraform_state_key: Optional[str] = None,
        deployment_output: Optional[dict] = None,
        error_message: Optional[str] = None
    ) -> Optional[DeploymentResponse]:
        """Update deployment status and related fields. May return None if update succeeded but fetch of updated row failed."""
        from datetime import datetime
        try:
            update_data = {"status": status, "updated_at": datetime.utcnow().isoformat()}
            
            if logs is not None:
                # Append new logs to existing logs (read may fail in worker context; still update status)
                try:
                    current = self.get_deployment_by_id(deployment_id)
                    existing_logs = current.deployment_logs or []
                    update_data["deployment_logs"] = existing_logs + logs
                except Exception:
                    # From background worker get may fail (e.g. RLS); still update status only (preserve logs)
                    pass
            
            if terraform_state_key:
                update_data["terraform_state_key"] = terraform_state_key
            
            if deployment_output:
                update_data["deployment_output"] = deployment_output
            
            if error_message:
                update_data["error_message"] = error_message
            
            if status in ["deployed", "failed", "cancelled"]:
                update_data["completed_at"] = datetime.utcnow().isoformat()
            
            result = self.supabase.table("deployments")\
                .update(update_data)\
                .eq("id", deployment_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return DeploymentResponse(**result.data[0])
            # Empty response can happen (e.g. PostgREST config); assume update succeeded
            try:
                return self.get_deployment_by_id(deployment_id)
            except Exception:
                return None
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating deployment: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def list_deployments_by_workshop(self, workshop_id: str) -> List[DeploymentResponse]:
        """List all deployments for a workshop"""
        try:
            result = self.supabase.table("deployments")\
                .select("*")\
                .eq("workshop_id", workshop_id)\
                .order("created_at", desc=True)\
                .execute()
            
            return [DeploymentResponse(**deployment) for deployment in result.data]
        except Exception as e:
            logger.error(f"Error listing deployments: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
