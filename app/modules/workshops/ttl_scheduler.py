import asyncio
import logging
from app.database.supabase_client import get_supabase
from app.modules.workshops.service import WorkshopService
from app.modules.deployments.destroy_worker import destroy_workshop_async
from app.modules.deployments.service import DeploymentService

logger = logging.getLogger(__name__)


async def check_and_destroy_expired_workshops():
    """Check for expired workshops and destroy them (single-template or template-group)."""
    try:
        supabase = get_supabase()
        workshop_service = WorkshopService(supabase)
        deployment_service = DeploymentService(supabase)
        expired_workshops = workshop_service.get_expired_workshops()
        if not expired_workshops:
            logger.debug("No expired workshops found")
            return
        logger.info(f"Found {len(expired_workshops)} expired workshop(s) to destroy")
        for workshop in expired_workshops:
            try:
                logger.info(f"Auto-destroying expired workshop: {workshop.id} (expired at {workshop.expires_at})")
                workshop_service.update_workshop_status(workshop.id, "destroying")
                # One state per (workshop_id, template_id): destroy latest deployment per template only
                deployments = deployment_service.list_deployments_by_workshop(workshop.id)
                eligible = [d for d in deployments if d.status in ("deployed", "failed")]
                if getattr(workshop, "template_group_id", None):
                    seen_templates = set()
                    to_destroy = []
                    for d in eligible:
                        if d.template_id not in seen_templates:
                            seen_templates.add(d.template_id)
                            to_destroy.append(d)
                    for deployment in to_destroy:
                        destroy_workshop_async(
                            workshop_id=workshop.id,
                            template_id=deployment.template_id,
                            supabase=supabase,
                            deployment_id=deployment.id,
                        )
                else:
                    if eligible:
                        deployment = eligible[0]
                        destroy_workshop_async(
                            workshop_id=workshop.id,
                            template_id=deployment.template_id,
                            supabase=supabase,
                            deployment_id=deployment.id,
                        )
                    else:
                        template_id = getattr(workshop, "template_id", None)
                        if template_id:
                            destroy_workshop_async(
                                workshop_id=workshop.id,
                                template_id=template_id,
                                supabase=supabase,
                            )
            except Exception as e:
                logger.error(f"Error auto-destroying workshop {workshop.id}: {str(e)}")
                try:
                    workshop_service.update_workshop_status(workshop.id, "failed")
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error in TTL scheduler: {str(e)}")


async def ttl_scheduler_loop():
    """Background task that periodically checks for expired workshops"""
    while True:
        try:
            await check_and_destroy_expired_workshops()
        except Exception as e:
            logger.error(f"Error in TTL scheduler loop: {str(e)}")
        
        # Check every 5 minutes
        await asyncio.sleep(300)
