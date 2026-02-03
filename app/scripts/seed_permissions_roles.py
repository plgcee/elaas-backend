"""
Seed Permissions and Roles Script
This script populates the permissions and roles tables using the config.
Can be run manually or as part of a nightly job.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config.permissions_config import PERMISSION_MATRIX
from app.database.supabase_client import get_supabase
from supabase import Client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_permissions(supabase: Client):
    """Seed permissions from config"""
    logger.info("Seeding permissions...")
    
    permissions = PERMISSION_MATRIX["permissions"]
    created_count = 0
    updated_count = 0
    
    for perm in permissions:
        try:
            # Check if permission exists
            existing = supabase.table("permissions")\
                .select("id")\
                .eq("name", perm["name"])\
                .execute()
            
            if existing.data:
                # Update existing permission
                supabase.table("permissions")\
                    .update({
                        "resource": perm["resource"],
                        "action": perm["action"],
                        "description": perm["description"]
                    })\
                    .eq("name", perm["name"])\
                    .execute()
                updated_count += 1
                logger.debug(f"Updated permission: {perm['name']}")
            else:
                # Create new permission
                supabase.table("permissions").insert({
                    "name": perm["name"],
                    "resource": perm["resource"],
                    "action": perm["action"],
                    "description": perm["description"]
                }).execute()
                created_count += 1
                logger.debug(f"Created permission: {perm['name']}")
        except Exception as e:
            logger.error(f"Error processing permission {perm['name']}: {e}")
    
    logger.info(f"Permissions seeded: {created_count} created, {updated_count} updated")
    return created_count + updated_count


def seed_roles(supabase: Client):
    """Seed roles from config"""
    logger.info("Seeding roles...")
    
    roles = PERMISSION_MATRIX["roles"]
    created_count = 0
    updated_count = 0
    
    for role in roles:
        try:
            # Check if role exists
            existing = supabase.table("roles")\
                .select("id")\
                .eq("name", role["name"])\
                .execute()
            
            if existing.data:
                # Update existing role
                supabase.table("roles")\
                    .update({
                        "description": role["description"]
                    })\
                    .eq("name", role["name"])\
                    .execute()
                role_id = existing.data[0]["id"]
                updated_count += 1
                logger.debug(f"Updated role: {role['name']}")
            else:
                # Create new role
                result = supabase.table("roles").insert({
                    "name": role["name"],
                    "description": role["description"]
                }).execute()
                role_id = result.data[0]["id"]
                created_count += 1
                logger.debug(f"Created role: {role['name']}")
            
            # Assign permissions to role
            assign_permissions_to_role(supabase, role_id, role["name"], role["permissions"])
            
        except Exception as e:
            logger.error(f"Error processing role {role['name']}: {e}")
    
    logger.info(f"Roles seeded: {created_count} created, {updated_count} updated")
    return created_count + updated_count


def assign_permissions_to_role(supabase: Client, role_id: str, role_name: str, permission_names: list):
    """Assign permissions to a role"""
    try:
        # Get permission IDs
        permission_result = supabase.table("permissions")\
            .select("id")\
            .in_("name", permission_names)\
            .execute()
        
        if not permission_result.data:
            logger.warning(f"No permissions found for role {role_name}")
            return
        
        permission_ids = [p["id"] for p in permission_result.data]
        
        # Get existing assignments
        existing_result = supabase.table("role_permissions")\
            .select("permission_id")\
            .eq("role_id", role_id)\
            .execute()
        
        existing_permission_ids = {p["permission_id"] for p in existing_result.data} if existing_result.data else set()
        
        # Insert new assignments
        new_assignments = [
            {"role_id": role_id, "permission_id": pid}
            for pid in permission_ids
            if pid not in existing_permission_ids
        ]
        
        if new_assignments:
            supabase.table("role_permissions").insert(new_assignments).execute()
            logger.debug(f"Assigned {len(new_assignments)} permissions to role {role_name}")
        
        # Remove permissions that are no longer in the config
        permissions_to_remove = existing_permission_ids - set(permission_ids)
        if permissions_to_remove:
            supabase.table("role_permissions")\
                .delete()\
                .eq("role_id", role_id)\
                .in_("permission_id", list(permissions_to_remove))\
                .execute()
            logger.debug(f"Removed {len(permissions_to_remove)} permissions from role {role_name}")
            
    except Exception as e:
        logger.error(f"Error assigning permissions to role {role_name}: {e}")


def main():
    """Main function to seed permissions and roles"""
    try:
        supabase = get_supabase()
        
        logger.info("Starting permissions and roles seeding...")
        
        # Seed permissions first
        perm_count = seed_permissions(supabase)
        
        # Then seed roles (which depend on permissions)
        role_count = seed_roles(supabase)
        
        logger.info(f"Seeding completed successfully!")
        logger.info(f"Total: {perm_count} permissions, {role_count} roles processed")
        
    except Exception as e:
        logger.error(f"Error during seeding: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
