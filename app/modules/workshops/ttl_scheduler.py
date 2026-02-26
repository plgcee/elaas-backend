import asyncio
import logging
from app.config import settings
from app.database.supabase_client import get_supabase
from app.modules.workshops.service import WorkshopService
from app.modules.workshops.schemas import WorkshopResponse
from app.modules.deployments.executor import submit_destroy
from app.modules.deployments.service import DeploymentService
from app.modules.environments.service import EnvironmentService

logger = logging.getLogger(__name__)


def _enqueue_destroys_for_workshop(workshop, workshop_service: WorkshopService, deployment_service: DeploymentService):
    """Set workshop to destroying and submit destroy jobs via bounded executor."""
    workshop_service.update_workshop_status(workshop.id, "destroying")
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
            submit_destroy(workshop_id=workshop.id, template_id=deployment.template_id, deployment_id=deployment.id)
    else:
        if eligible:
            deployment = eligible[0]
            submit_destroy(workshop_id=workshop.id, template_id=deployment.template_id, deployment_id=deployment.id)
        else:
            template_id = getattr(workshop, "template_id", None)
            if template_id:
                submit_destroy(workshop_id=workshop.id, template_id=template_id)


async def check_and_destroy_expired_workshops():
    """Check for expired environments (TTL); enqueue destroy jobs for their workshops (non-blocking)."""
    try:
        supabase = get_supabase()
        workshop_service = WorkshopService(supabase)
        deployment_service = DeploymentService(supabase)
        environment_service = EnvironmentService(supabase)

        # Expired environments (environment-level TTL): destroy all workshops in env
        expired_envs = environment_service.get_expired_environments()
        if expired_envs:
            logger.info("Found %s expired environment(s) to destroy", len(expired_envs))
        for env in expired_envs:
            try:
                workshops_data = environment_service.get_workshops_for_ttl_destroy(env.id)
                for w in workshops_data:
                    workshop = WorkshopResponse(**w)
                    try:
                        logger.info("Auto-destroying workshop %s (environment %s TTL reached)", workshop.id, env.id)
                        _enqueue_destroys_for_workshop(workshop, workshop_service, deployment_service)
                    except Exception as e:
                        logger.error("Error auto-destroying workshop %s for env TTL: %s", workshop.id, e)
                        try:
                            workshop_service.update_workshop_status(workshop.id, "failed")
                        except Exception:
                            pass
            except Exception as e:
                logger.error("Error processing expired environment %s: %s", env.id, e)
    except Exception as e:
        logger.error("Error in TTL scheduler: %s", e)


async def ttl_scheduler_loop():
    """Background task that periodically checks for expired environments (TTL) and destroys their workshops."""
    while True:
        try:
            await check_and_destroy_expired_workshops()
        except Exception as e:
            logger.error("Error in TTL scheduler loop: %s", e)
        await asyncio.sleep(settings.ttl_check_interval_seconds)
