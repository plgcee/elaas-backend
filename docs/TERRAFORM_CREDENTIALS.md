# Terraform Credentials Best Practices

## Dynamic Credential Passing from Application

When running Terraform from an application (like our deployment system), **always use environment variables** passed to the subprocess. This is the most secure and recommended approach.

### ✅ Best Practice: Environment Variables in Subprocess

```python
import subprocess
import os

# Create a clean environment copy
env = os.environ.copy()

# Set AWS credentials dynamically
env['AWS_ACCESS_KEY_ID'] = aws_access_key_id
env['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
env['AWS_DEFAULT_REGION'] = aws_region

# Run Terraform with the environment
result = subprocess.run(
    ['terraform', 'apply', '-auto-approve'],
    cwd=work_dir,
    env=env,  # Pass credentials via environment
    capture_output=True,
    text=True
)
```

### Why This is Best Practice:

1. **Security**: Credentials never appear in command line arguments (visible in process lists)
2. **Terraform Native**: Terraform AWS provider automatically reads from environment variables
3. **No File System**: No need to create temporary credential files
4. **Isolated**: Each subprocess gets its own environment, no cross-contamination
5. **Clean**: Credentials are cleared when subprocess exits

### ❌ Avoid These Approaches:

1. **Command Line Arguments** (INSECURE):
   ```python
   # DON'T DO THIS - credentials visible in process list
   subprocess.run(['terraform', 'apply', f'-var=aws_access_key={key}'])
   ```

2. **Hardcoded in Provider Block** (NOT DYNAMIC):
   ```hcl
   # DON'T DO THIS - credentials in code
   provider "aws" {
     access_key = "AKIA..."
     secret_key = "secret..."
   }
   ```

3. **Temporary Files** (COMPLEX, SECURITY RISK):
   ```python
   # AVOID - requires cleanup, file permissions, etc.
   with open('/tmp/creds', 'w') as f:
       f.write(credentials)
   ```

### Current Implementation

Our `TerraformDeployer` class in `app/modules/deployments/terraform_deployer.py` already follows best practices:

```python
# Environment variables are set per subprocess call
env = os.environ.copy()
env['AWS_ACCESS_KEY_ID'] = self.aws_access_key_id
env['AWS_SECRET_ACCESS_KEY'] = self.aws_secret_access_key
env['AWS_DEFAULT_REGION'] = self.aws_region

subprocess.run(['terraform', 'init'], env=env, ...)
subprocess.run(['terraform', 'apply'], env=env, ...)
```

### Additional Security Considerations

1. **Credential Source**: Store credentials securely (environment variables, secrets manager)
2. **Credential Rotation**: Support dynamic credential updates
3. **Least Privilege**: Use IAM roles with minimal required permissions
4. **Audit Logging**: Log deployment actions (not credentials)
5. **Credential Cleanup**: Ensure credentials are not logged or persisted

### Example: Enhanced Secure Implementation

```python
class SecureTerraformDeployer:
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, region: str):
        # Validate credentials are provided
        if not all([aws_access_key_id, aws_secret_access_key, region]):
            raise ValueError("AWS credentials required")
        
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_region = region
    
    def _get_terraform_env(self) -> dict:
        """Create isolated environment for Terraform subprocess"""
        env = os.environ.copy()
        
        # Set AWS credentials
        env['AWS_ACCESS_KEY_ID'] = self.aws_access_key_id
        env['AWS_SECRET_ACCESS_KEY'] = self.aws_secret_access_key
        env['AWS_DEFAULT_REGION'] = self.aws_region
        
        # Clear any existing AWS session tokens (if using temporary credentials)
        env.pop('AWS_SESSION_TOKEN', None)
        
        return env
    
    def apply(self, work_dir: str):
        env = self._get_terraform_env()
        
        result = subprocess.run(
            ['terraform', 'apply', '-auto-approve'],
            cwd=work_dir,
            env=env,
            capture_output=True,
            text=True
        )
        
        # Credentials are automatically cleared when subprocess exits
        return result
```

### Testing

When testing locally, you can still use the helper script:
```bash
source example-terraform/setup-aws-creds.sh
terraform apply
```

But in production, credentials come from your application's secure configuration (environment variables, secrets manager, etc.).
