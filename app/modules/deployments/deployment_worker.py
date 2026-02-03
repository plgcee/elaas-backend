import threading
import time
import logging
from typing import Any, Dict

LOG_FLUSH_INTERVAL_SEC = 30
from app.modules.deployments.terraform_deployer import TerraformDeployer
from app.modules.deployments.service import DeploymentService
from app.modules.deployments import process_registry
from app.modules.templates.service import TemplateService
from app.modules.templates.s3_storage import S3Storage
from supabase import Client

logger = logging.getLogger(__name__)


def deploy_workshop_async(
    deployment_id: str,
    workshop_id: str,
    template_id: str,
    terraform_vars: Dict[str, Any],
    supabase: Client
):
    """
    Asynchronous deployment worker function.
    Runs in a separate thread to deploy Terraform infrastructure.
    Uses service-role Supabase client when available so status updates succeed (RLS bypass).
    """
    from app.database.supabase_client import SupabaseClient
    client = SupabaseClient.get_service_client()
    deployment_service = DeploymentService(client)
    template_service = TemplateService(client)

    try:
        deployment = deployment_service.get_deployment_by_id(deployment_id)
        if deployment.status == "cancelled":
            return

        # Get template to retrieve environment
        template = template_service.get_template_by_id(template_id)
        environment = template.environment if hasattr(template, 'environment') and template.environment else "AWS"

        deployer = TerraformDeployer(environment=environment)

        # Update status to deploying
        deployment_service.update_deployment_status(
            deployment_id,
            "deploying",
            logs=[f"Starting deployment for {environment} environment..."]
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

        try:
            # Deploy Terraform
            result = deployer.deploy(
                template_zip_content=zip_content,
                terraform_vars=terraform_vars,
                deployment_id=deployment_id,
                workshop_id=workshop_id,
                template_id=template_id,
                template_name=template.name,
                log_callback=log_callback
            )
        finally:
            _flush_logs()
            process_registry.unregister(deployment_id)

        if result["success"]:
            # Update status first (minimal payload) so status is set even if output update fails
            try:
                deployment_service.update_deployment_status(
                    deployment_id,
                    "deployed",
                    terraform_state_key=result.get("state_key"),
                )
            except Exception as status_err:
                logger.error(f"Failed to set deployment status to deployed: {status_err}")
                raise
            deployment_output = result.get("output")
            output_display = result.get("output_display")
            outputs_flat = result.get("outputs")
            if output_display is not None or outputs_flat is not None:
                payload = {"output": deployment_output, "output_display": output_display or []}
                if outputs_flat is not None:
                    payload["outputs"] = outputs_flat
                deployment_output = payload
            if deployment_output:
                try:
                    deployment_service.update_deployment_status(
                        deployment_id,
                        "deployed",
                        deployment_output=deployment_output,
                    )
                except Exception as output_err:
                    logger.warning(f"Failed to store deployment output (status already set): {output_err}")
            from app.modules.workshops.service import WorkshopService
            workshop_service = WorkshopService(client)
            _maybe_finalize_workshop_deploy_status(workshop_id, workshop_service, deployment_service, "deployed", deployment_output or result.get("output"))
            logger.info(f"Deployment {deployment_id} completed successfully")
        else:
            try:
                deployment = deployment_service.get_deployment_by_id(deployment_id)
                if deployment.status == "cancelled":
                    from app.modules.workshops.service import WorkshopService
                    workshop_service = WorkshopService(client)
                    workshop_service.update_workshop_status(workshop_id, "pending")
                    return
            except Exception:
                pass  # Proceed to set failed so deployment is not stuck in "deploying"
            try:
                deployment_service.update_deployment_status(
                    deployment_id,
                    "failed",
                    error_message=result.get("error", "Unknown error")
                )
            except Exception as status_err:
                logger.error(f"Failed to set deployment status to failed: {status_err}")
            try:
                from app.modules.workshops.service import WorkshopService
                workshop_service = WorkshopService(client)
                _maybe_finalize_workshop_deploy_status(workshop_id, workshop_service, deployment_service, "failed")
            except Exception as finalize_err:
                logger.error(f"Failed to finalize workshop status: {str(finalize_err)}")
            logger.error(f"Deployment {deployment_id} failed: {result.get('error')}")

    except Exception as e:
        logger.error(f"Deployment worker error: {str(e)}")
        try:
            deployment = deployment_service.get_deployment_by_id(deployment_id)
            if deployment.status == "cancelled":
                from app.modules.workshops.service import WorkshopService
                workshop_service = WorkshopService(client)
                workshop_service.update_workshop_status(workshop_id, "pending")
                return
            deployment_service.update_deployment_status(
                deployment_id,
                "failed",
                error_message=str(e)
            )
        except Exception as update_error:
            logger.error(f"Failed to update deployment status: {str(update_error)}")
        try:
            from app.modules.workshops.service import WorkshopService
            workshop_service = WorkshopService(client)
            _maybe_finalize_workshop_deploy_status(workshop_id, workshop_service, deployment_service, "failed")
        except Exception as finalize_error:
            logger.error(f"Failed to finalize workshop status: {str(finalize_error)}")


def _maybe_finalize_workshop_deploy_status(workshop_id: str, workshop_service, deployment_service, desired_status: str, deployment_output: Any = None):
    """For group workshops, set workshop status only when all deployments in the current run are done. For single-template, set immediately."""
    try:
        workshop = workshop_service.get_workshop_by_id(workshop_id)
    except Exception as e:
        logger.warning(f"Could not get workshop {workshop_id} for finalize: {e}")
        return
    if not getattr(workshop, "template_group_id", None):
        try:
            workshop_service.update_workshop_status(workshop_id, desired_status, deployment_output=deployment_output)
        except Exception as e:
            logger.warning(f"Could not update workshop {workshop_id} status to {desired_status}: {e}")
        return
    # Group: consider only the current run's deployments (most recent N where N = template count)
    try:
        template_ids = workshop_service.get_template_ids_for_workshop(workshop)
        deployments = deployment_service.list_deployments_by_workshop(workshop_id)
        current_batch_size = len(template_ids)
        current_batch = deployments[:current_batch_size] if len(deployments) >= current_batch_size else deployments
    except Exception as e:
        logger.warning(f"Could not list deployments for workshop {workshop_id}: {e}")
        return
    terminal = {"deployed", "failed", "cancelled"}
    if all(d.status in terminal for d in current_batch):
        any_failed = any(d.status == "failed" for d in current_batch)
        try:
            workshop_service.update_workshop_status(workshop_id, "failed" if any_failed else "deployed", deployment_output=deployment_output)
        except Exception as e:
            logger.warning(f"Could not update workshop {workshop_id} status: {e}")


def _download_template_zip(zip_file_path: str) -> bytes:
    """Download template ZIP file from S3 or Supabase Storage"""
    if zip_file_path.startswith("s3://"):
        # Download from S3
        # Extract bucket and key from s3://bucket/key
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
            # Extract bucket and path
            # Assuming format: templates/filename.zip
            response = supabase.storage.from_("templates").download(zip_file_path)
            return response
        except Exception as e:
            raise Exception(f"Failed to download from Supabase Storage: {str(e)}")
