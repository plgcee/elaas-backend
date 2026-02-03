from supabase import Client
from app.modules.templates.schemas import (
    TemplateCreate, TemplateUpdate, TemplateResponse,
    TemplateUploadWithDataRequest, TemplateUploadWithDataResponse
)
from app.modules.templates.terraform_parser import parse_terraform_variables, parse_ui_variables_json
from app.modules.templates.terraform_validator import TerraformValidator
from app.modules.templates.s3_storage import S3Storage
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, UploadFile
import uuid
import os
import logging

logger = logging.getLogger(__name__)


class TemplateService:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.upload_path = "templates"
        try:
            self.validator = TerraformValidator()
        except Exception as e:
            logger.warning(f"TerraformValidator initialization failed: {e}")
            self.validator = None
        
        # Initialize S3 storage if credentials are available
        self.s3_storage = None
        try:
            from app.config import settings
            if all([settings.aws_access_key_id, settings.aws_secret_access_key, settings.s3_bucket_name]):
                self.s3_storage = S3Storage()
                logger.info("S3 storage initialized successfully")
            else:
                logger.warning("S3 credentials not fully configured, will use Supabase Storage")
        except Exception as e:
            logger.warning(f"S3 storage initialization failed ({str(e)}), will use Supabase Storage")
            self.s3_storage = None
    
    def create_template(self, template_data: TemplateCreate, user_id: str) -> TemplateResponse:
        """Create a new template"""
        try:
            result = self.supabase.table("templates").insert({
                "name": template_data.name,
                "description": template_data.description,
                "version": template_data.version,
                "environment": template_data.environment,
                "user_id": user_id
            }).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create template")
            
            return TemplateResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def get_template_by_id(self, template_id: str, include_groups: bool = False) -> TemplateResponse:
        """Get template by ID."""
        try:
            result = self.supabase.table("templates").select("*").eq("id", template_id).maybe_single().execute()
            if not result.data:
                raise HTTPException(status_code=404, detail="Template not found")
            resp = TemplateResponse(**result.data)
            if include_groups:
                resp.group_ids = self._get_template_group_ids([template_id]).get(template_id) or []
            return resp
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def update_template(self, template_id: str, template_data: TemplateUpdate) -> TemplateResponse:
        """Update template"""
        try:
            update_data = {}
            if template_data.name:
                update_data["name"] = template_data.name
            if template_data.description is not None:
                update_data["description"] = template_data.description
            if template_data.version:
                update_data["version"] = template_data.version
            if template_data.environment is not None:
                update_data["environment"] = template_data.environment
            
            result = self.supabase.table("templates")\
                .update(update_data)\
                .eq("id", template_id)\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=404, detail="Template not found")
            
            return TemplateResponse(**result.data[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    def list_templates(
        self,
        user_id: Optional[str] = None,
        template_group_id: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        include_groups: bool = False,
    ) -> List[TemplateResponse]:
        """List templates, optionally filtered by user or template group."""
        try:
            if template_group_id:
                assign_result = self.supabase.table("template_group_assignments").select("template_id").eq("template_group_id", template_group_id).execute()
                template_ids = [r["template_id"] for r in assign_result.data] if assign_result.data else []
                if not template_ids:
                    return []
                query = self.supabase.table("templates").select("*").in_("id", template_ids)
            else:
                query = self.supabase.table("templates").select("*")
            if user_id:
                query = query.eq("user_id", user_id)
            result = query.order("created_at", desc=True).limit(limit).offset(offset).execute()
            items = [TemplateResponse(**t) for t in result.data]
            if include_groups and items:
                group_map = self._get_template_group_ids([t.id for t in items])
                for t in items:
                    t.group_ids = group_map.get(t.id) or []
            return items
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def _get_template_group_ids(self, template_ids: List[str]) -> Dict[str, List[str]]:
        """Return map template_id -> list of template_group_id."""
        if not template_ids:
            return {}
        result = self.supabase.table("template_group_assignments").select("template_id, template_group_id").in_("template_id", template_ids).execute()
        out = {}
        for r in result.data or []:
            tid, gid = r["template_id"], r["template_group_id"]
            out.setdefault(tid, []).append(gid)
        return out
    
    def delete_template(self, template_id: str) -> bool:
        """Delete template and its ZIP file from S3 or Supabase Storage."""
        try:
            row = self.supabase.table("templates").select("zip_file_path").eq("id", template_id).maybe_single().execute()
            if not row.data:
                raise HTTPException(status_code=404, detail="Template not found")
            zip_file_path = row.data.get("zip_file_path")
            if zip_file_path:
                if self.s3_storage and zip_file_path.startswith("s3://"):
                    s3_key = zip_file_path.replace(f"s3://{self.s3_storage.bucket_name}/", "", 1)
                    try:
                        self.s3_storage.delete_file(s3_key)
                        logger.info(f"Deleted template ZIP from S3: {s3_key}")
                    except Exception as e:
                        logger.warning(f"Failed to delete template ZIP from S3 ({s3_key}): {e}")
                else:
                    try:
                        self.supabase.storage.from_("templates").remove([zip_file_path])
                        logger.info(f"Deleted template ZIP from Supabase Storage: {zip_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete template ZIP from Supabase Storage ({zip_file_path}): {e}")
            result = self.supabase.table("templates").delete().eq("id", template_id).execute()
            return len(result.data) > 0
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    async def upload_template_file(self, template_id: str, file: UploadFile) -> str:
        """Upload template ZIP file to S3 or Supabase Storage"""
        try:
            # Verify template exists
            template = self.get_template_by_id(template_id)
            
            # Generate unique file name
            file_extension = os.path.splitext(file.filename)[1] or ".zip"
            file_name = f"{template_id}{file_extension}"
            s3_key = f"{self.upload_path}/{file_name}"
            
            # Read file content
            file_content = await file.read()
            
            # Upload to S3 if configured, otherwise use Supabase Storage
            if self.s3_storage:
                logger.info(f"Uploading to S3: {s3_key}")
                try:
                    zip_file_path = self.s3_storage.upload_file(file_content, s3_key)
                    logger.info(f"Successfully uploaded to S3: {zip_file_path}")
                except Exception as e:
                    logger.error(f"S3 upload failed: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to upload to S3: {str(e)}"
                    )
            else:
                # Fallback to Supabase Storage
                logger.info(f"Using Supabase Storage (S3 not configured)")
                try:
                    zip_file_path = f"{self.upload_path}/{file_name}"
                    self.supabase.storage.from_("templates").upload(
                        zip_file_path,
                        file_content,
                        file_options={"content-type": "application/zip"}
                    )
                    logger.info(f"Successfully uploaded to Supabase Storage: {zip_file_path}")
                except Exception as e:
                    logger.error(f"Supabase Storage upload failed: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to upload to storage: {str(e)}"
                    )
            
            # Update template with file path
            self.supabase.table("templates")\
                .update({"zip_file_path": zip_file_path})\
                .eq("id", template_id)\
                .execute()
            
            return zip_file_path
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    
    async def upload_and_process_template(
        self,
        template_data: TemplateUploadWithDataRequest,
        file: UploadFile,
        user_id: str
    ) -> TemplateUploadWithDataResponse:
        """Upload Terraform ZIP, validate, parse variables, and store in S3 and Postgres"""
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="File must be a ZIP file")
        
        # Read file content
        zip_content = await file.read()
        
        # Validate Terraform files
        is_valid, validation_issues = self.validator.validate(zip_content)
        
        # Parse variables from Terraform files
        try:
            variables_json = parse_terraform_variables(zip_content)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse Terraform variables: {str(e)}"
            )
        ui_variables_json = parse_ui_variables_json(zip_content)

        # Create template record
        template_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1] or ".zip"
        file_name = f"{template_id}{file_extension}"
        s3_key = f"{self.upload_path}/{file_name}"
        
        # Upload to S3 or Supabase Storage
        if self.s3_storage:
            logger.info(f"Uploading to S3: {s3_key}")
            try:
                zip_file_path = self.s3_storage.upload_file(zip_content, s3_key)
                logger.info(f"Successfully uploaded to S3: {zip_file_path}")
            except Exception as e:
                logger.error(f"S3 upload failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload to S3: {str(e)}"
                )
        else:
            # Fallback to Supabase Storage
            logger.info(f"Using Supabase Storage (S3 not configured)")
            try:
                zip_file_path = f"{self.upload_path}/{file_name}"
                self.supabase.storage.from_("templates").upload(
                    zip_file_path,
                    zip_content,
                    file_options={"content-type": "application/zip"}
                )
                logger.info(f"Successfully uploaded to Supabase Storage: {zip_file_path}")
            except Exception as e:
                logger.error(f"Supabase Storage upload failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload to storage: {str(e)}"
                )
        
        # Store template with variables_json and ui_variables_json in Postgres
        try:
            result = self.supabase.table("templates").insert({
                "id": template_id,
                "name": template_data.name,
                "description": template_data.description,
                "version": template_data.version,
                "environment": template_data.environment,
                "user_id": user_id,
                "zip_file_path": zip_file_path,
                "variables_json": variables_json,
                "ui_variables_json": ui_variables_json,
                "validation_issues": validation_issues if validation_issues else None
            }).execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create template")
            
            return TemplateUploadWithDataResponse(
                template_id=template_id,
                name=template_data.name,
                description=template_data.description,
                version=template_data.version,
                zip_file_path=zip_file_path,
                variables_json=variables_json,
                ui_variables_json=ui_variables_json,
                validation_passed=is_valid,
                validation_issues=validation_issues,
                environment=template_data.environment,
                message="Template uploaded and processed successfully"
            )
        except Exception as e:
            # Cleanup: delete uploaded file if template creation fails
            if self.s3_storage:
                try:
                    self.s3_storage.delete_file(s3_key)
                except:
                    pass
            raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")
    
    async def update_template_with_file(
        self,
        template_id: str,
        file: UploadFile,
        version: Optional[str],
        user_id: str
    ) -> TemplateUploadWithDataResponse:
        """Update an existing template with a new ZIP file version"""
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="File must be a ZIP file")
        
        # Check if template exists and get current version
        try:
            existing_result = self.supabase.table("templates")\
                .select("version")\
                .eq("id", template_id)\
                .single()\
                .execute()
            
            if not existing_result.data:
                raise HTTPException(status_code=404, detail="Template not found")
            
            current_version = existing_result.data.get("version", "1.0.0")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Read file content
        zip_content = await file.read()
        
        # Validate Terraform files
        is_valid, validation_issues = self.validator.validate(zip_content)
        
        # Parse variables from Terraform files
        try:
            variables_json = parse_terraform_variables(zip_content)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse Terraform variables: {str(e)}"
            )
        ui_variables_json = parse_ui_variables_json(zip_content)

        # Determine new version
        if version:
            new_version = version
        else:
            # Auto-increment version if not provided
            try:
                parts = current_version.split(".")
                if len(parts) >= 3:
                    # Increment patch version
                    parts[2] = str(int(parts[2]) + 1)
                    new_version = ".".join(parts)
                else:
                    new_version = f"{current_version}.1"
            except:
                new_version = "1.0.1"
        
        # Generate new file name for the updated version
        file_extension = os.path.splitext(file.filename)[1] or ".zip"
        file_name = f"{template_id}{file_extension}"
        s3_key = f"{self.upload_path}/{file_name}"
        
        # Upload to S3 or Supabase Storage (replaces existing file)
        if self.s3_storage:
            logger.info(f"Uploading updated file to S3: {s3_key}")
            try:
                zip_file_path = self.s3_storage.upload_file(zip_content, s3_key)
                logger.info(f"Successfully uploaded updated file to S3: {zip_file_path}")
            except Exception as e:
                logger.error(f"S3 upload failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload to S3: {str(e)}"
                )
        else:
            # Fallback to Supabase Storage
            logger.info(f"Using Supabase Storage (S3 not configured)")
            try:
                zip_file_path = f"{self.upload_path}/{file_name}"
                # Remove existing file if it exists
                try:
                    self.supabase.storage.from_("templates").remove([zip_file_path])
                except:
                    pass  # File might not exist
                
                self.supabase.storage.from_("templates").upload(
                    zip_file_path,
                    zip_content,
                    file_options={"content-type": "application/zip", "upsert": "true"}
                )
                logger.info(f"Successfully uploaded updated file to Supabase Storage: {zip_file_path}")
            except Exception as e:
                logger.error(f"Supabase Storage upload failed: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload to storage: {str(e)}"
                )
        
        # Update template record
        try:
            update_data = {
                "version": new_version,
                "zip_file_path": zip_file_path,
                "variables_json": variables_json,
                "ui_variables_json": ui_variables_json,
                "validation_issues": validation_issues if validation_issues else None
            }

            result = self.supabase.table("templates")\
                .update(update_data)\
                .eq("id", template_id)\
                .execute()
            
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to update template")
            
            updated_template = result.data[0]
            
            return TemplateUploadWithDataResponse(
                template_id=template_id,
                name=updated_template["name"],
                description=updated_template.get("description"),
                version=new_version,
                zip_file_path=zip_file_path,
                variables_json=variables_json,
                ui_variables_json=ui_variables_json,
                validation_passed=is_valid,
                validation_issues=validation_issues,
                environment=updated_template.get("environment"),
                message="Template updated successfully with new version"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update template: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")
