from supabase import Client
from app.modules.template_groups.schemas import (
    TemplateGroupCreate, TemplateGroupUpdate, TemplateGroupResponse, TemplateGroupWithCount,
    TemplateInGroupSummary,
)
from typing import List, Optional
from fastapi import HTTPException


class TemplateGroupService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    def create(self, data: TemplateGroupCreate) -> TemplateGroupResponse:
        try:
            result = self.supabase.table("template_groups").insert({
                "name": data.name,
                "description": data.description
            }).execute()
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create template group")
            return TemplateGroupResponse(**result.data[0])
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def get_by_id(self, group_id: str) -> TemplateGroupResponse:
        try:
            result = self.supabase.table("template_groups").select("*").eq("id", group_id).maybe_single().execute()
            if not result.data:
                raise HTTPException(status_code=404, detail="Template group not found")
            return TemplateGroupResponse(**result.data)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def list_groups(
        self,
        limit: int = 10,
        offset: int = 0,
        include_template_count: bool = False
    ) -> List[TemplateGroupResponse] | List[TemplateGroupWithCount]:
        try:
            result = self.supabase.table("template_groups").select("*").order("created_at", desc=True).limit(limit).offset(offset).execute()
            if not include_template_count:
                return [TemplateGroupResponse(**row) for row in result.data]
            out = []
            for row in result.data:
                count_result = self.supabase.table("template_group_assignments").select("id").eq("template_group_id", row["id"]).execute()
                count = len(count_result.data) if count_result.data else 0
                out.append(TemplateGroupWithCount(**row, template_count=count))
            return out
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def update(self, group_id: str, data: TemplateGroupUpdate) -> TemplateGroupResponse:
        try:
            update_data = {}
            if data.name is not None:
                update_data["name"] = data.name
            if data.description is not None:
                update_data["description"] = data.description
            if not update_data:
                return self.get_by_id(group_id)
            result = self.supabase.table("template_groups").update(update_data).eq("id", group_id).execute()
            if not result.data:
                raise HTTPException(status_code=404, detail="Template group not found")
            return TemplateGroupResponse(**result.data[0])
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def delete(self, group_id: str) -> None:
        try:
            self.supabase.table("template_groups").delete().eq("id", group_id).execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def assign_template(self, group_id: str, template_id: str) -> None:
        self.get_by_id(group_id)
        try:
            self.supabase.table("template_group_assignments").insert({
                "template_group_id": group_id,
                "template_id": template_id
            }).execute()
        except Exception as e:
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                return
            raise HTTPException(status_code=500, detail=str(e))

    def unassign_template(self, group_id: str, template_id: str) -> None:
        try:
            self.supabase.table("template_group_assignments").delete().eq("template_group_id", group_id).eq("template_id", template_id).execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def get_group_ids_for_template(self, template_id: str) -> List[str]:
        try:
            result = self.supabase.table("template_group_assignments").select("template_group_id").eq("template_id", template_id).execute()
            return [r["template_group_id"] for r in result.data]
        except Exception:
            return []

    def list_templates_in_group(self, group_id: str) -> List[TemplateInGroupSummary]:
        """Return minimal template info (id, name, description) for templates in this group."""
        self.get_by_id(group_id)
        assign_result = self.supabase.table("template_group_assignments").select("template_id").eq("template_group_id", group_id).execute()
        template_ids = [r["template_id"] for r in (assign_result.data or [])]
        if not template_ids:
            return []
        result = self.supabase.table("templates").select("id, name, description").in_("id", template_ids).execute()
        return [TemplateInGroupSummary(**row) for row in (result.data or [])]
