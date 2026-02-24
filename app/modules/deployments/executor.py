"""
Bounded thread-pool executor for deploy and destroy workers.
Ensures max_concurrent_destroy and max_concurrent_deploy are respected so API + TTL scheduler do not exhaust CPU/memory.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from app.config import settings
from app.modules.deployments.destroy_worker import destroy_workshop_async
from app.modules.deployments.deployment_worker import deploy_workshop_async

logger = logging.getLogger(__name__)

_destroy_executor: Optional[ThreadPoolExecutor] = None
_deploy_executor: Optional[ThreadPoolExecutor] = None


def _get_destroy_executor() -> ThreadPoolExecutor:
    global _destroy_executor
    if _destroy_executor is None:
        _destroy_executor = ThreadPoolExecutor(
            max_workers=settings.max_concurrent_destroy,
            thread_name_prefix="destroy-worker-",
        )
        logger.info("Destroy executor started with max_workers=%s", settings.max_concurrent_destroy)
    return _destroy_executor


def _get_deploy_executor() -> ThreadPoolExecutor:
    global _deploy_executor
    if _deploy_executor is None:
        _deploy_executor = ThreadPoolExecutor(
            max_workers=settings.max_concurrent_deploy,
            thread_name_prefix="deploy-worker-",
        )
        logger.info("Deploy executor started with max_workers=%s", settings.max_concurrent_deploy)
    return _deploy_executor


def submit_destroy(
    workshop_id: str,
    template_id: str,
    supabase: Optional[Any] = None,
    deployment_id: Optional[str] = None,
) -> None:
    """
    Submit a destroy job to the bounded executor. Non-blocking.
    Worker thread uses SupabaseClient.get_service_client() so supabase arg is ignored (kept for API compatibility).
    """
    executor = _get_destroy_executor()
    executor.submit(
        destroy_workshop_async,
        workshop_id=workshop_id,
        template_id=template_id,
        supabase=supabase,
        deployment_id=deployment_id,
    )


def submit_deploy(
    deployment_id: str,
    workshop_id: str,
    template_id: str,
    terraform_vars: Dict[str, Any],
    supabase: Optional[Any] = None,
) -> None:
    """
    Submit a deploy job to the bounded executor. Non-blocking.
    Worker thread uses SupabaseClient.get_service_client() so supabase arg is ignored (kept for API compatibility).
    """
    executor = _get_deploy_executor()
    executor.submit(
        deploy_workshop_async,
        deployment_id=deployment_id,
        workshop_id=workshop_id,
        template_id=template_id,
        terraform_vars=terraform_vars,
        supabase=supabase,
    )
