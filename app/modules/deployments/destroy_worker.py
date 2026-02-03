import threading
import time
import logging
from typing import Dict, Any, Optional

LOG_FLUSH_INTERVAL_SEC = 30
from app.modules.deployments.terraform_deployer import TerraformDeployer
from app.modules.deployments.service import DeploymentService
from app.modules.deployments.schemas import DeploymentCreate
from app.modules.templates.service import TemplateService
from supabase import Client

logger = logging.getLogger(__name__)


def destroy_workshop_async(
    workshop_id: str,
    template_id: str,
    supabase: Client,
    deployment_id: Optional[str] = None
):
    """
    Asynchronous destroy worker function.
    Runs in a separate thread to destroy Terraform infrastructure.
    Uses service-role Supabase client when available so status updates succeed (RLS bypass).
    """
    from app.database.supabase_client import SupabaseClient
    client = SupabaseClient.get_service_client()
    deployment_service = DeploymentService(client)
    template_service = TemplateService(client)
    from app.modules.workshops.service import WorkshopService
    workshop_service = WorkshopService(client)
    
    try:
        # Get workshop to get user_id
        workshop = workshop_service.get_workshop_by_id(workshop_id)
        
        # Create deployment record if not provided (for auto-destroy from TTL)
        if not deployment_id:
            deployment_data = DeploymentCreate(
                workshop_id=workshop_id,
                template_id=template_id,
                terraform_vars={}  # Empty vars for destroy
            )
            deployment = deployment_service.create_deployment(deployment_data, workshop.user_id)
            deployment_id = deployment.id
        
        # Get template to retrieve environment
        template = template_service.get_template_by_id(template_id)
        environment = template.environment if hasattr(template, 'environment') and template.environment else "AWS"
        
        deployer = TerraformDeployer(environment=environment)
        
        # Update deployment status to destroying
        deployment_service.update_deployment_status(
            deployment_id,
            "deploying",  # Use "deploying" status for destroy operation
            logs=[f"Starting destroy for {environment} environment..."]
        )
        
        if not template.zip_file_path:
            raise Exception("Template ZIP file path not found")
        
        # Download template ZIP from S3
        zip_content = _download_template_zip(template.zip_file_path)

        # Batched log callback: flush every LOG_FLUSH_INTERVAL_SEC
        log_buffer = []
        last_flush_time = [time.monotonic()]

        def _flush_logs():
            if not log_buffer:
                return
            try:
                deployment_service.update_deployment_status(
                    deployment_id,
                    "deploying",
                    logs=list(log_buffer)
                )
                log_buffer.clear()
                last_flush_time[0] = time.monotonic()
            except Exception as e:
                logger.error(f"Error updating logs: {str(e)}")

        def log_callback(log_lines: list):
            filtered = [line for line in log_lines if line.strip()]
            if not filtered:
                return
            log_buffer.extend(filtered)
            if time.monotonic() - last_flush_time[0] >= LOG_FLUSH_INTERVAL_SEC:
                _flush_logs()

        # Destroy Terraform infrastructure
        try:
            result = deployer.destroy(
                template_zip_content=zip_content,
                workshop_id=workshop_id,
                template_id=template_id,
                template_name=template.name,
                log_callback=log_callback
            )
        finally:
            _flush_logs()

        if result["success"]:
            deployment_service.update_deployment_status(
                deployment_id,
                "deployed",
                terraform_state_key=result.get("state_key"),
                deployment_output=result.get("output")
            )
            _maybe_finalize_workshop_status(workshop_id, workshop_service, deployment_service)
            logger.info(f"Destroy deployment {deployment_id} completed successfully")
        else:
            deployment_service.update_deployment_status(
                deployment_id,
                "failed",
                error_message=result.get("error", "Unknown error")
            )
            _maybe_finalize_workshop_status(workshop_id, workshop_service, deployment_service)
            logger.error(f"Destroy deployment {deployment_id} failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Destroy worker error: {str(e)}")
        try:
            deployment_service.update_deployment_status(
                deployment_id,
                "failed",
                error_message=str(e)
            )
            _maybe_finalize_workshop_status(workshop_id, workshop_service, deployment_service)
        except Exception as update_error:
            logger.error(f"Failed to update deployment status: {str(update_error)}")


def _maybe_finalize_workshop_status(workshop_id: str, workshop_service, deployment_service):
    """Set workshop status to destroyed/failed when current destroy run is done. For template-group, only the latest N deployments (this run) must be terminal."""
    try:
        workshop = workshop_service.get_workshop_by_id(workshop_id)
    except Exception as e:
        logger.warning(f"Could not get workshop {workshop_id} for destroy finalize: {e}")
        return
    if not getattr(workshop, "template_group_id", None):
        try:
            workshop_service.update_workshop_status(workshop_id, "destroyed")
        except Exception as e:
            logger.warning(f"Could not update workshop {workshop_id} to destroyed: {e}")
        return
    try:
        template_ids = workshop_service.get_template_ids_for_workshop(workshop)
        deployments = deployment_service.list_deployments_by_workshop(workshop_id)
        current_batch_size = len(template_ids)
        current_batch = deployments[:current_batch_size] if len(deployments) >= current_batch_size else deployments
    except Exception as e:
        logger.warning(f"Could not list deployments for workshop {workshop_id} destroy finalize: {e}")
        return
    terminal = {"deployed", "failed", "cancelled"}
    if all(d.status in terminal for d in current_batch):
        any_failed = any(d.status == "failed" for d in current_batch)
        try:
            workshop_service.update_workshop_status(workshop_id, "failed" if any_failed else "destroyed")
        except Exception as e:
            logger.warning(f"Could not update workshop {workshop_id} to destroyed/failed: {e}")


def _download_template_zip(zip_file_path: str) -> bytes:
    """Download template ZIP file from S3 or Supabase Storage"""
    if zip_file_path.startswith("s3://"):
        # Download from S3
        path_parts = zip_file_path.replace("s3://", "").split("/", 1)
        bucket = path_parts[0]
        key = path_parts[1] if len(path_parts) > 1 else ""
        
        import boto3
        from app.config import settings
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read()
        except Exception as e:
            raise Exception(f"Failed to download from S3: {str(e)}")
    else:
        # Download from Supabase Storage
        from app.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        try:
            response = supabase.storage.from_("templates").download(zip_file_path)
            return response
        except Exception as e:
            raise Exception(f"Failed to download from Supabase Storage: {str(e)}")
