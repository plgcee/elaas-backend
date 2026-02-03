import zipfile
import io
from typing import Dict, List, Tuple
import logging

try:
    import hcl2
except ImportError:
    raise ImportError("Please install python-hcl2: pip install python-hcl2")

logger = logging.getLogger(__name__)


class TerraformValidator:
    """Validate Terraform files against best practices"""
    
    @staticmethod
    def validate(zip_content: bytes) -> Tuple[bool, List[str]]:
        """
        Validate Terraform ZIP file.
        Returns (is_valid, list_of_errors_or_warnings)
        """
        errors = []
        warnings = []
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
                tf_files = [f for f in zip_ref.namelist() if f.endswith('.tf')]
                
                if not tf_files:
                    errors.append("No .tf files found in the ZIP archive")
                    return False, errors
                
                # Check for main.tf or main configuration file
                has_main = any('main.tf' in f.lower() for f in tf_files)
                if not has_main:
                    warnings.append("No main.tf file found. Consider having a main configuration file.")
                
                # Validate each .tf file
                for tf_file in tf_files:
                    try:
                        content = zip_ref.read(tf_file).decode('utf-8')
                        parsed = hcl2.loads(content)
                        
                        # Check for variables.tf
                        if 'variables.tf' in tf_file.lower() or 'variable.tf' in tf_file.lower():
                            if 'variable' not in parsed:
                                warnings.append(f"{tf_file} contains no variable definitions")
                        
                        # Validate variable definitions
                        if 'variable' in parsed:
                            var_block = parsed['variable']
                            
                            # Handle both dict and list formats
                            if isinstance(var_block, dict):
                                var_items = var_block.items()
                            elif isinstance(var_block, list):
                                # HCL2 sometimes returns variables as a list of dicts
                                var_items = []
                                for var_item in var_block:
                                    if isinstance(var_item, dict):
                                        for var_name, var_config in var_item.items():
                                            if isinstance(var_config, dict):
                                                var_items.append((var_name, var_config))
                            else:
                                continue
                            
                            for var_name, var_config in var_items:
                                if not isinstance(var_config, dict):
                                    continue
                                
                                # Check for description
                                if 'description' not in var_config:
                                    warnings.append(f"Variable '{var_name}' is missing a description")
                                
                                # Check for type
                                if 'type' not in var_config:
                                    warnings.append(f"Variable '{var_name}' is missing a type definition")
                        
                        # Check for outputs.tf
                        if 'outputs.tf' in tf_file.lower() or 'output.tf' in tf_file.lower():
                            if 'output' not in parsed:
                                warnings.append(f"{tf_file} contains no output definitions")
                    
                    except Exception as e:
                        error_type = type(e).__name__
                        if 'Hcl2' in error_type or 'hcl2' in str(type(e)):
                            errors.append(f"Syntax error in {tf_file}: {str(e)}")
                        else:
                            warnings.append(f"Could not parse {tf_file}: {str(e)}")
        
        except zipfile.BadZipFile:
            errors.append("Invalid ZIP file format")
            return False, errors
        except Exception as e:
            errors.append(f"Failed to validate Terraform files: {str(e)}")
            return False, errors
        
        all_issues = errors + warnings
        return len(errors) == 0, all_issues
