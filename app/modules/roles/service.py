from supabase import Client
from app.modules.roles.schemas import (
    PermissionCreate, PermissionUpdate, PermissionResponse,
    RoleCreate, RoleUpdate, RoleResponse, RoleWithPermissionsResponse,
    RolePermissionAssign, RolePermissionResponse,
    BulkPermissionAssign, BulkPermissionAssignResponse, BulkPermissionUpdate
)
from typing import List, Optional
from fastapi import HTTPException


class PermissionService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def create_permission(self, permission_data: PermissionCreate) -> PermissionResponse:
        """Create a new permission"""
        try:
            result = self.supabase.table("permissions").insert({
                "name": permission_data.name,
                "resource": permission_data.resource,
                "action": permission_data.action,
                "description": permission_data.description
            }).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create permission")
            
            return PermissionResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_permission_by_id(self, permission_id: str) -> PermissionResponse:
        """Get permission by ID"""
        try:
            result = self.supabase.table("permissions")\
                .select("*")\
                .eq("id", permission_id)\
                .single()\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Permission not found")
            
            return PermissionResponse(**result.data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def update_permission(self, permission_id: str, permission_data: PermissionUpdate) -> PermissionResponse:
        """Update permission"""
        try:
            update_data = {}
            if permission_data.name:
                update_data["name"] = permission_data.name
            if permission_data.resource:
                update_data["resource"] = permission_data.resource
            if permission_data.action:
                update_data["action"] = permission_data.action
            if permission_data.description is not None:
                update_data["description"] = permission_data.description
            
            result = self.supabase.table("permissions")\
                .update(update_data)\
                .eq("id", permission_id)\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Permission not found")
            
            return PermissionResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def list_permissions(
        self,
        resource: Optional[str] = None,
        permission_ids: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PermissionResponse]:
        """List permissions, optionally filtered by resource and/or permission_ids (group-scoped)"""
        try:
            if permission_ids is not None and len(permission_ids) == 0:
                return []
            query = self.supabase.table("permissions").select("*")
            if resource:
                query = query.eq("resource", resource)
            if permission_ids is not None:
                query = query.in_("id", permission_ids)
            result = query.order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            return [PermissionResponse(**permission) for permission in result.data]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def delete_permission(self, permission_id: str) -> bool:
        """Delete permission"""
        try:
            # Remove from role_permissions first
            self.supabase.table("role_permissions")\
                .delete()\
                .eq("permission_id", permission_id)\
                .execute()
            
            # Delete permission
            result = self.supabase.table("permissions")\
                .delete()\
                .eq("id", permission_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


class RoleService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def create_role(self, role_data: RoleCreate) -> RoleResponse:
        """Create a new role"""
        try:
            result = self.supabase.table("roles").insert({
                "name": role_data.name,
                "description": role_data.description
            }).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create role")
            
            return RoleResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_role_by_id(self, role_id: str) -> RoleResponse:
        """Get role by ID"""
        try:
            result = self.supabase.table("roles")\
                .select("*")\
                .eq("id", role_id)\
                .single()\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Role not found")
            
            return RoleResponse(**result.data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_role_with_permissions(self, role_id: str) -> RoleWithPermissionsResponse:
        """Get role with all associated permissions"""
        try:
            # Get role
            role_result = self.supabase.table("roles")\
                .select("*")\
                .eq("id", role_id)\
                .single()\
                .execute()
            
            if not role_result.data:
                raise HTTPException(status_code=404, detail="Role not found")
            
            # Get permissions for this role
            permissions_result = self.supabase.table("role_permissions")\
                .select("permission_id, permissions(*)")\
                .eq("role_id", role_id)\
                .execute()
            
            permissions = []
            if permissions_result.data:
                for item in permissions_result.data:
                    if item.get("permissions"):
                        permissions.append(PermissionResponse(**item["permissions"]))
            
            role_data = role_result.data
            role_data["permissions"] = permissions
            
            return RoleWithPermissionsResponse(**role_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def update_role(self, role_id: str, role_data: RoleUpdate) -> RoleResponse:
        """Update role"""
        try:
            update_data = {}
            if role_data.name:
                update_data["name"] = role_data.name
            if role_data.description is not None:
                update_data["description"] = role_data.description
            
            result = self.supabase.table("roles")\
                .update(update_data)\
                .eq("id", role_id)\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Role not found")
            
            return RoleResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def list_roles(
        self,
        limit: int = 10,
        offset: int = 0,
        role_ids: Optional[List[str]] = None
    ) -> List[RoleResponse]:
        """List roles, optionally filtered by role_ids (group-scoped)"""
        try:
            if role_ids is not None and len(role_ids) == 0:
                return []
            query = self.supabase.table("roles").select("*")
            if role_ids is not None:
                query = query.in_("id", role_ids)
            result = query.order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            return [RoleResponse(**role) for role in result.data]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def delete_role(self, role_id: str) -> bool:
        """Delete role"""
        try:
            # Remove role_permissions first
            self.supabase.table("role_permissions")\
                .delete()\
                .eq("role_id", role_id)\
                .execute()
            
            # Delete role
            result = self.supabase.table("roles")\
                .delete()\
                .eq("id", role_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def assign_permission_to_role(self, role_id: str, permission_id: str) -> RolePermissionResponse:
        """Assign a permission to a role"""
        try:
            # Verify role exists
            self.get_role_by_id(role_id)
            
            # Verify permission exists
            permission_service = PermissionService(self.supabase)
            permission_service.get_permission_by_id(permission_id)
            
            # Check if already assigned
            existing = self.supabase.table("role_permissions")\
                .select("*")\
                .eq("role_id", role_id)\
                .eq("permission_id", permission_id)\
                .execute()
            
            if existing.data:
                raise HTTPException(status_code=400, detail="Permission already assigned to role")
            
            # Assign permission
            result = self.supabase.table("role_permissions").insert({
                "role_id": role_id,
                "permission_id": permission_id
            }).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to assign permission")
            
            return RolePermissionResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def remove_permission_from_role(self, role_id: str, permission_id: str) -> bool:
        """Remove a permission from a role"""
        try:
            result = self.supabase.table("role_permissions")\
                .delete()\
                .eq("role_id", role_id)\
                .eq("permission_id", permission_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_role_permissions(self, role_id: str) -> List[PermissionResponse]:
        """Get all permissions for a role"""
        try:
            result = self.supabase.table("role_permissions")\
                .select("permission_id, permissions(*)")\
                .eq("role_id", role_id)\
                .execute()
            
            permissions = []
            if result.data:
                for item in result.data:
                    if item.get("permissions"):
                        permissions.append(PermissionResponse(**item["permissions"]))
            
            return permissions
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def bulk_assign_permissions_to_role(self, role_id: str, permission_ids: List[str]) -> BulkPermissionAssignResponse:
        """Bulk assign multiple permissions to a role"""
        try:
            # Verify role exists
            self.get_role_by_id(role_id)
            
            # Verify all permissions exist
            permission_service = PermissionService(self.supabase)
            for permission_id in permission_ids:
                permission_service.get_permission_by_id(permission_id)
            
            # Get existing assignments to skip duplicates
            existing_result = self.supabase.table("role_permissions")\
                .select("permission_id")\
                .eq("role_id", role_id)\
                .in_("permission_id", permission_ids)\
                .execute()
            
            existing_permission_ids = {item["permission_id"] for item in existing_result.data} if existing_result.data else set()
            
            # Prepare bulk insert data (excluding already assigned)
            insert_data = [
                {"role_id": role_id, "permission_id": pid}
                for pid in permission_ids
                if pid not in existing_permission_ids
            ]
            
            assigned_permissions = []
            skipped_count = len(existing_permission_ids)
            
            if insert_data:
                # Bulk insert
                result = self.supabase.table("role_permissions").insert(insert_data).execute()
                if result.data:
                    assigned_permissions = [RolePermissionResponse(**item) for item in result.data]
            
            return BulkPermissionAssignResponse(
                role_id=role_id,
                assigned_count=len(assigned_permissions),
                skipped_count=skipped_count,
                assigned_permissions=assigned_permissions,
                message=f"Assigned {len(assigned_permissions)} permissions, skipped {skipped_count} already assigned"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def bulk_update_role_permissions(self, role_id: str, permission_ids: List[str]) -> BulkPermissionAssignResponse:
        """Bulk update/replace all permissions for a role"""
        try:
            # Verify role exists
            self.get_role_by_id(role_id)
            
            # Verify all permissions exist
            permission_service = PermissionService(self.supabase)
            for permission_id in permission_ids:
                permission_service.get_permission_by_id(permission_id)
            
            # Remove all existing permissions for this role
            self.supabase.table("role_permissions")\
                .delete()\
                .eq("role_id", role_id)\
                .execute()
            
            # Insert new permissions
            assigned_permissions = []
            if permission_ids:
                insert_data = [
                    {"role_id": role_id, "permission_id": pid}
                    for pid in permission_ids
                ]
                
                result = self.supabase.table("role_permissions").insert(insert_data).execute()
                if result.data:
                    assigned_permissions = [RolePermissionResponse(**item) for item in result.data]
            
            return BulkPermissionAssignResponse(
                role_id=role_id,
                assigned_count=len(assigned_permissions),
                skipped_count=0,
                assigned_permissions=assigned_permissions,
                message=f"Updated role with {len(assigned_permissions)} permissions"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
