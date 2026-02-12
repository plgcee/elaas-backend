import subprocess
import tempfile
import zipfile
import io
import os
import json
import logging
import threading
from typing import Dict, Any, Optional, List
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from app.config import settings
from app.modules.templates.s3_storage import S3Storage
from app.modules.deployments import process_registry

logger = logging.getLogger(__name__)


class TerraformDeployer:
    def __init__(self, environment: Optional[str] = None):
        """
        Initialize TerraformDeployer with environment-specific credentials.
        
        Args:
            environment: Target environment (AWS, GCP, Azure, MongoDB, Snowflake, etc.)
                        If None, defaults to AWS for backward compatibility
        """
        self.environment = (environment or "AWS").upper()
        
        # S3 is still used for state storage for all environments
        if not all([settings.aws_access_key_id, settings.aws_secret_access_key, settings.s3_bucket_name]):
            raise ValueError("AWS credentials and S3 bucket must be configured for state storage")
        
        self.aws_access_key_id = settings.aws_access_key_id
        self.aws_secret_access_key = settings.aws_secret_access_key
        self.aws_region = settings.aws_region
        self.s3_bucket = settings.s3_bucket_name
        self.s3_storage = S3Storage()
        
        # Load environment-specific credentials
        self._load_environment_credentials()
    
    def _load_environment_credentials(self):
        """Load credentials for the target environment"""
        self.env_credentials = {}
        
        if self.environment == "AWS":
            if not all([settings.aws_access_key_id, settings.aws_secret_access_key]):
                raise ValueError(f"{self.environment} credentials not configured")
            self.env_credentials = {
                "AWS_ACCESS_KEY_ID": settings.aws_access_key_id,
                "AWS_SECRET_ACCESS_KEY": settings.aws_secret_access_key,
                "AWS_DEFAULT_REGION": settings.aws_region
            }
        elif self.environment == "GCP":
            if not all([settings.gcp_project_id, settings.gcp_service_account_key]):
                raise ValueError(f"{self.environment} credentials not configured")
            self.env_credentials = {
                "GOOGLE_PROJECT": settings.gcp_project_id,
                "GOOGLE_APPLICATION_CREDENTIALS": self._setup_gcp_credentials()
            }
        elif self.environment == "AZURE":
            if not all([settings.azure_subscription_id, settings.azure_client_id, 
                       settings.azure_client_secret, settings.azure_tenant_id]):
                raise ValueError(f"{self.environment} credentials not configured")
            self.env_credentials = {
                "ARM_SUBSCRIPTION_ID": settings.azure_subscription_id,
                "ARM_CLIENT_ID": settings.azure_client_id,
                "ARM_CLIENT_SECRET": settings.azure_client_secret,
                "ARM_TENANT_ID": settings.azure_tenant_id
            }
        elif self.environment == "MONGODB":
            if not all([settings.mongodb_public_key, settings.mongodb_private_key]):
                raise ValueError(f"{self.environment} credentials not configured")
            self.env_credentials = {
                "MONGODB_ATLAS_PUBLIC_KEY": settings.mongodb_public_key,
                "MONGODB_ATLAS_PRIVATE_KEY": settings.mongodb_private_key
            }
        elif self.environment == "SNOWFLAKE":
            if not all([settings.snowflake_account, settings.snowflake_user, 
                       settings.snowflake_password, settings.snowflake_warehouse]):
                raise ValueError(f"{self.environment} credentials not configured")
            self.env_credentials = {
                "SNOWFLAKE_ACCOUNT": settings.snowflake_account,
                "SNOWFLAKE_USER": settings.snowflake_user,
                "SNOWFLAKE_PASSWORD": settings.snowflake_password,
                "SNOWFLAKE_WAREHOUSE": settings.snowflake_warehouse
            }
        else:
            logger.warning(f"Unknown environment {self.environment}, using AWS credentials")
            self.env_credentials = {
                "AWS_ACCESS_KEY_ID": settings.aws_access_key_id,
                "AWS_SECRET_ACCESS_KEY": settings.aws_secret_access_key,
                "AWS_DEFAULT_REGION": settings.aws_region
            }
    
    def _setup_gcp_credentials(self) -> str:
        """Setup GCP service account key file and return path"""
        # Create temporary file for GCP credentials
        import tempfile
        creds_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        try:
            # If it's a JSON string, write it directly; if it's a path, use it
            if settings.gcp_service_account_key and settings.gcp_service_account_key.strip().startswith('{'):
                creds_file.write(settings.gcp_service_account_key)
            else:
                # Assume it's a file path
                if settings.gcp_service_account_key:
                    with open(settings.gcp_service_account_key, 'r') as f:
                        creds_file.write(f.read())
                else:
                    raise ValueError("GCP service account key not provided")
            creds_file.close()
            return creds_file.name
        except Exception as e:
            logger.error(f"Failed to setup GCP credentials: {str(e)}")
            raise
    
    def deploy(
        self,
        template_zip_content: bytes,
        terraform_vars: Dict[str, Any],
        deployment_id: str,
        workshop_id: str,
        template_id: str,
        template_name: str,
        log_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Deploy Terraform infrastructure asynchronously.

        Args:
            template_zip_content: ZIP file content of Terraform template
            terraform_vars: Terraform variables (credentials will be injected from env based on environment)
            deployment_id: Deployment ID for logging/tracking
            workshop_id: Workshop ID for state file management
            template_id: Template ID for per-template state (one state per workshop+template)
            template_name: Template name to use as subdirectory name
            log_callback: Optional callback function to receive log lines

        Returns:
            Dict with 'success' (bool), 'output' (dict), and 'error' (str)
        """
        work_dir = None
        try:
            # Create temporary directory for Terraform execution
            work_dir = tempfile.mkdtemp(prefix=f"terraform-{deployment_id}-")
            logger.info(f"Created work directory: {work_dir}")

            # Create template subdirectory
            template_dir = os.path.join(work_dir, template_name)
            os.makedirs(template_dir, exist_ok=True)
            logger.info(f"Created template directory: {template_dir}")

            # Extract template ZIP to template subdirectory
            self._extract_template(template_zip_content, template_dir)

            # Find directory containing .tf files
            terraform_dir = self._find_terraform_directory(template_dir, log_callback)
            if not terraform_dir:
                raise Exception("No .tf files found in extracted template")

            logger.info(f"Found Terraform files in: {terraform_dir}")

            # Prepare Terraform variables with AWS credentials from backend
            tf_vars = self._prepare_variables(terraform_vars)

            # One state file per (workshop_id, template_id) so redeploy and destroy target the same resources
            state_key = f"terraform-state/workshops/{workshop_id}/templates/{template_id}/terraform.tfstate"
            self._init_backend(terraform_dir, state_key, log_callback)
            
            # Create terraform.tfvars.json in terraform_dir
            self._create_tfvars(terraform_dir, tf_vars)
            
            # Check for phased apply manifest (e.g. RDS two-phase)
            apply_phases = self._load_apply_phases(terraform_dir)
            if apply_phases:
                if log_callback:
                    log_callback([f"Using phased apply ({len(apply_phases)} phase(s))"])
                output = self._apply_terraform_phased(
                    terraform_dir, apply_phases, log_callback, deployment_id=deployment_id
                )
            else:
                output = self._apply_terraform(terraform_dir, tf_vars, log_callback, deployment_id=deployment_id)
            
            # Read outputs from state (terraform output -json reads from state); normalize for DB
            output_display = self._format_output_for_display(output) if output else []
            outputs_flat = self._extract_output_values(output) if output else {}
            return {
                "success": True,
                "output": output,
                "outputs": outputs_flat,
                "output_display": output_display,
                "state_key": state_key,
            }
            
        except Exception as e:
            logger.error(f"Terraform deployment failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output": None
            }
        finally:
            # Cleanup
            if work_dir and os.path.exists(work_dir):
                import shutil
                try:
                    shutil.rmtree(work_dir)
                    logger.info(f"Cleaned up work directory: {work_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup work directory: {str(e)}")
    
    def _extract_template(self, zip_content: bytes, work_dir: str):
        """Extract Terraform template ZIP to work directory"""
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
                zip_ref.extractall(work_dir)
            logger.info(f"Extracted template to {work_dir}")
        except Exception as e:
            raise Exception(f"Failed to extract template: {str(e)}")
    
    def _find_terraform_directory(self, start_dir: str, log_callback: Optional[callable] = None) -> Optional[str]:
        """
        Recursively search for directory containing .tf files.
        Returns the first directory found with .tf files, or None if not found.
        """
        try:
            # Check if start_dir itself contains .tf files
            tf_files = [f for f in os.listdir(start_dir) if f.endswith('.tf') and os.path.isfile(os.path.join(start_dir, f))]
            if tf_files:
                return start_dir
            
            # Search recursively through subdirectories
            for root, dirs, files in os.walk(start_dir):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                tf_files = [f for f in files if f.endswith('.tf')]
                if tf_files:
                    return root
            
            return None
        except Exception as e:
            logger.error(f"Error searching for Terraform directory: {str(e)}")
            return None
    
    def _prepare_variables(self, user_vars: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare Terraform variables, removing credential variables from user input"""
        # Remove credential variables from user input (obfuscation)
        credential_keys = [
            'aws_access_key_id', 'aws_secret_access_key', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
            'gcp_project_id', 'gcp_service_account_key', 'GOOGLE_PROJECT', 'GOOGLE_APPLICATION_CREDENTIALS',
            'azure_subscription_id', 'azure_client_id', 'azure_client_secret', 'azure_tenant_id',
            'ARM_SUBSCRIPTION_ID', 'ARM_CLIENT_ID', 'ARM_CLIENT_SECRET', 'ARM_TENANT_ID',
            'mongodb_public_key', 'mongodb_private_key', 'MONGODB_ATLAS_PUBLIC_KEY', 'MONGODB_ATLAS_PRIVATE_KEY',
            'snowflake_account', 'snowflake_user', 'snowflake_password', 'snowflake_warehouse',
            'SNOWFLAKE_ACCOUNT', 'SNOWFLAKE_USER', 'SNOWFLAKE_PASSWORD', 'SNOWFLAKE_WAREHOUSE'
        ]
        safe_vars = {k: v for k, v in user_vars.items() if k not in credential_keys}
        
        # Credentials are set via environment variables for Terraform
        return safe_vars
    
    def _get_terraform_env(self) -> dict:
        """
        Create isolated environment for Terraform subprocess with environment-specific credentials.
        Best practice: Pass credentials via environment variables, not command line args.
        """
        env = os.environ.copy()
        
        # Add environment-specific credentials
        env.update(self.env_credentials)
        
        # Always add AWS credentials for S3 backend (state storage)
        env['AWS_ACCESS_KEY_ID'] = self.aws_access_key_id
        env['AWS_SECRET_ACCESS_KEY'] = self.aws_secret_access_key
        env['AWS_DEFAULT_REGION'] = self.aws_region
        
        # Clear any existing session tokens (if using temporary credentials)
        env.pop('AWS_SESSION_TOKEN', None)
        
        return env
    
    def _init_backend(self, template_dir: str, state_key: str, log_callback: Optional[callable] = None):
        """Initialize Terraform with S3 backend - creates backend.tf in template_dir and initializes"""
        self._ensure_s3_bucket()
        state_exists = self._check_state_exists(state_key)
        if log_callback:
            log_callback(["Initializing Terraform..."])
        
        # Create or update backend.tf file with S3 backend configuration
        backend_tf_content = f"""terraform {{
  backend "s3" {{
    bucket         = "{self.s3_bucket}"
    key            = "{state_key}"
    region         = "{self.aws_region}"
    encrypt        = true
  }}
}}
"""
        backend_tf_file = os.path.join(template_dir, "backend.tf")
        
        # Create/overwrite backend.tf in template directory
        with open(backend_tf_file, 'w') as f:
            f.write(backend_tf_content)
        
        logger.info(f"Created backend.tf in {template_dir}")
        
        # Run terraform init with credentials via environment variables (best practice)
        # Use -reconfigure if state exists to ensure we're using the correct backend
        env = self._get_terraform_env()
        
        try:
            init_cmd = ['terraform', 'init']
            if state_exists:
                init_cmd.append('-reconfigure')
            
            result = subprocess.run(
                init_cmd,
                cwd=template_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=300
            )
            
            if log_callback:
                for line in (result.stdout or "").splitlines():
                    if line.strip():
                        log_callback([line])
                if result.stderr and result.stderr.strip():
                    for line in result.stderr.splitlines():
                        if line.strip():
                            log_callback([line])
            
            if result.returncode != 0:
                raise Exception(f"Terraform init failed: {result.stderr}")
            
            logger.info("Terraform backend initialized successfully")
        except subprocess.TimeoutExpired:
            raise Exception("Terraform init timed out")
        except FileNotFoundError:
            raise Exception("Terraform not found. Please install Terraform from https://www.terraform.io/downloads")
    
    def _check_state_exists(self, state_key: str) -> bool:
        """Check if Terraform state file exists in S3"""
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
            
            # Try to head the object (check if it exists without downloading)
            s3_client.head_object(Bucket=self.s3_bucket, Key=state_key)
            return True
        except ClientError as e:
            # 404 means object doesn't exist
            if e.response['Error']['Code'] == '404':
                return False
            # Other errors (permissions, etc.) - log and assume state doesn't exist
            logger.warning(f"Error checking state file existence: {str(e)}")
            return False
        except Exception as e:
            logger.warning(f"Error checking state file existence: {str(e)}")
            return False
    
    def _create_tfvars(self, template_dir: str, tf_vars: Dict[str, Any]):
        """Create terraform.tfvars.json file in template directory"""
        tfvars_file = os.path.join(template_dir, "terraform.tfvars.json")
        with open(tfvars_file, 'w') as f:
            json.dump(tf_vars, f, indent=2)
        logger.info(f"Created terraform.tfvars.json in {template_dir}")

    def _extract_output_values(self, raw_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract a flat name -> value dict from Terraform output -json (reads from state).
        Every output is included; sensitive values are included as-is for DB storage and UI reveal.
        """
        if not raw_output or not isinstance(raw_output, dict):
            return {}
        flat = {}
        for key, entry in raw_output.items():
            if isinstance(entry, dict) and "value" in entry:
                flat[key] = entry["value"]
            else:
                flat[key] = entry
        return flat

    def _format_output_for_display(self, raw_output: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert Terraform output -json (or raw dict) into a user-friendly list for UI.
        Handles unknown output shapes: extracts value/sensitive from terraform wrapper, humanizes keys.
        """
        if not raw_output or not isinstance(raw_output, dict):
            return []
        display = []
        for key, entry in raw_output.items():
            if isinstance(entry, dict) and "value" in entry:
                value = entry["value"]
                sensitive = entry.get("sensitive", False)
            else:
                value = entry
                sensitive = False
            label = key.replace("_", " ").title()
            if sensitive:
                display_value = "••••••••"
            elif value is None:
                display_value = ""
            elif isinstance(value, (str, int, float, bool)):
                display_value = str(value)
            elif isinstance(value, list):
                if all(isinstance(x, (str, int, float, bool)) for x in value):
                    display_value = ", ".join(str(x) for x in value)
                else:
                    display_value = json.dumps(value, indent=2)
            elif isinstance(value, dict):
                display_value = json.dumps(value, indent=2)
            else:
                display_value = str(value)
            display.append({"label": label, "value": display_value, "sensitive": sensitive})
        return display

    def _load_apply_phases(self, terraform_dir: str) -> Optional[List[Dict[str, Any]]]:
        """Load apply_phases from elaas-deploy.json in terraform dir. Returns None if missing/invalid/empty."""
        path = os.path.join(terraform_dir, "elaas-deploy.json")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            phases = data.get("apply_phases")
            if not isinstance(phases, list) or len(phases) == 0:
                return None
            return phases
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load elaas-deploy.json: {e}")
            return None

    def _apply_terraform_phased(
        self,
        terraform_dir: str,
        apply_phases: List[Dict[str, Any]],
        log_callback: Optional[callable] = None,
        deployment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run terraform apply for each phase (optional -target), then terraform output -json."""
        env = self._get_terraform_env()
        for i, phase in enumerate(apply_phases):
            target = phase.get("target") if isinstance(phase, dict) else None
            target = target.strip() if isinstance(target, str) else None
            if log_callback:
                msg = f"Phase {i + 1}/{len(apply_phases)}: apply -target={target}" if target else f"Phase {i + 1}/{len(apply_phases)}: full apply"
                log_callback([msg])
            cmd = ["terraform", "apply", "-auto-approve", "-var-file", "terraform.tfvars.json"]
            if target:
                cmd.extend(["-target", target])
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=terraform_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                    bufsize=1,
                )
                if deployment_id:
                    process_registry.register(deployment_id, proc)
                def stream_output():
                    for line in iter(proc.stdout.readline, ''):
                        if log_callback and line.strip():
                            log_callback([line.rstrip()])
                stream_thread = threading.Thread(target=stream_output)
                stream_thread.start()
                proc.wait()
                stream_thread.join(timeout=5)
                if deployment_id:
                    process_registry.unregister(deployment_id)
                if proc.returncode != 0:
                    raise Exception(f"Terraform apply phase {i + 1} failed with return code {proc.returncode}")
            except Exception:
                if deployment_id:
                    process_registry.unregister(deployment_id)
                raise
        # Get outputs after all phases
        output_result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        outputs = {}
        if output_result.returncode == 0 and output_result.stdout:
            try:
                outputs = json.loads(output_result.stdout)
            except json.JSONDecodeError:
                logger.warning("Failed to parse Terraform outputs")
        return outputs

    def _apply_terraform(
        self,
        template_dir: str,
        tf_vars: Dict[str, Any],
        log_callback: Optional[callable] = None,
        deployment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply Terraform configuration with credentials via environment variables.
        Uses Popen so the process can be terminated via process_registry (hard cancel).
        """
        env = self._get_terraform_env()

        try:
            proc = subprocess.Popen(
                ['terraform', 'apply', '-auto-approve', '-var-file', 'terraform.tfvars.json'],
                cwd=template_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                bufsize=1,
            )
            if deployment_id:
                process_registry.register(deployment_id, proc)

            def stream_output():
                for line in iter(proc.stdout.readline, ''):
                    if log_callback and line.strip():
                        log_callback([line.rstrip()])

            stream_thread = threading.Thread(target=stream_output)
            stream_thread.start()
            proc.wait()
            stream_thread.join(timeout=5)

            if deployment_id:
                process_registry.unregister(deployment_id)

            if proc.returncode != 0:
                raise Exception(f"Terraform apply failed with return code {proc.returncode}")

            # Get outputs
            output_result = subprocess.run(
                ['terraform', 'output', '-json'],
                cwd=template_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=60
            )

            outputs = {}
            if output_result.returncode == 0 and output_result.stdout:
                try:
                    outputs = json.loads(output_result.stdout)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse Terraform outputs")

            logger.info("Terraform apply completed successfully")
            return outputs

        except Exception as e:
            if deployment_id:
                process_registry.unregister(deployment_id)
            raise Exception(f"Terraform apply error: {str(e)}")
    
    def destroy(
        self,
        template_zip_content: bytes,
        workshop_id: str,
        template_id: str,
        template_name: str,
        terraform_vars: Optional[Dict[str, Any]] = None,
        log_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Destroy Terraform infrastructure using existing state file.

        Args:
            template_zip_content: ZIP file content of Terraform template
            workshop_id: Workshop ID for state file management
            template_id: Template ID (same key as deploy so we target the same state)
            template_name: Template name to use as subdirectory name
            terraform_vars: Same vars used at deploy time (required so Terraform can evaluate the config)
            log_callback: Optional callback function to receive log lines

        Returns:
            Dict with 'success' (bool), 'output' (dict), and 'error' (str)
        """
        work_dir = None
        try:
            # Create temporary directory for Terraform execution
            work_dir = tempfile.mkdtemp(prefix=f"terraform-destroy-{workshop_id}-")
            logger.info(f"Created work directory for destroy: {work_dir}")

            # Create template subdirectory
            template_dir = os.path.join(work_dir, template_name)
            os.makedirs(template_dir, exist_ok=True)
            logger.info(f"Created template directory: {template_dir}")

            # Extract template ZIP to template subdirectory
            self._extract_template(template_zip_content, template_dir)

            # Find directory containing .tf files
            terraform_dir = self._find_terraform_directory(template_dir, log_callback)
            if not terraform_dir:
                raise Exception("No .tf files found in extracted template")

            logger.info(f"Found Terraform files in: {terraform_dir}")
            state_key = f"terraform-state/workshops/{workshop_id}/templates/{template_id}/terraform.tfstate"

            # Check if state exists
            state_exists = self._check_state_exists(state_key)
            if not state_exists:
                raise Exception(f"State file not found for workshop {workshop_id} template {template_id}. Cannot destroy infrastructure that doesn't exist.")
            
            # Initialize Terraform backend with existing state
            self._init_backend(terraform_dir, state_key, log_callback)

            # Write tfvars so destroy can evaluate required variables (e.g. RDS instance_identifier)
            tf_vars = self._prepare_variables(terraform_vars or {})
            self._create_tfvars(terraform_dir, tf_vars)
            
            # Destroy Terraform infrastructure
            output = self._destroy_terraform(terraform_dir, log_callback)
            
            return {
                "success": True,
                "output": output,
                "state_key": state_key,
                "work_dir": work_dir,
                "terraform_dir": terraform_dir
            }
            
        except Exception as e:
            logger.error(f"Terraform destroy failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output": None
            }
        finally:
            # Cleanup
            if work_dir and os.path.exists(work_dir):
                import shutil
                try:
                    shutil.rmtree(work_dir)
                    logger.info(f"Cleaned up work directory: {work_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup work directory: {str(e)}")
    
    def _destroy_terraform(self, terraform_dir: str, log_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Destroy Terraform configuration using existing state"""
        env = self._get_terraform_env()
        
        # Run terraform destroy with same var file as apply (required variables must be set)
        try:
            result = subprocess.run(
                ['terraform', 'destroy', '-auto-approve', '-var-file', 'terraform.tfvars.json'],
                cwd=terraform_dir,
                capture_output=True,
                text=True,
                env=env,
                timeout=1800  # 30 minutes
            )
            
            if log_callback:
                for line in (result.stdout or "").splitlines():
                    if line.strip():
                        log_callback([line])
                if result.stderr and result.stderr.strip():
                    for line in result.stderr.splitlines():
                        if line.strip():
                            log_callback([line])
            
            if result.returncode != 0:
                raise Exception(f"Terraform destroy failed: {result.stderr}")
            
            logger.info("Terraform destroy completed successfully")
            return {"message": "Infrastructure destroyed successfully"}
            
        except subprocess.TimeoutExpired:
            raise Exception("Terraform destroy timed out")
        except Exception as e:
            raise Exception(f"Terraform destroy error: {str(e)}")
    
    def _ensure_s3_bucket(self):
        """Ensure S3 bucket exists, create if it doesn't"""
        s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )
        
        try:
            s3_client.head_bucket(Bucket=self.s3_bucket)
            logger.info(f"S3 bucket {self.s3_bucket} exists")
        except ClientError:
            # Bucket doesn't exist, create it
            try:
                if self.aws_region == 'us-east-1':
                    s3_client.create_bucket(Bucket=self.s3_bucket)
                else:
                    s3_client.create_bucket(
                        Bucket=self.s3_bucket,
                        CreateBucketConfiguration={'LocationConstraint': self.aws_region}
                    )
                logger.info(f"Created S3 bucket {self.s3_bucket}")
            except ClientError as e:
                logger.error(f"Failed to create S3 bucket: {str(e)}")
                raise
