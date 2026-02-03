import zipfile
import io
import json
from typing import Dict, List, Any, Optional
import logging

try:
    import hcl2
except ImportError:
    raise ImportError("Please install python-hcl2: pip install python-hcl2")

logger = logging.getLogger(__name__)


def parse_terraform_variables(zip_content: bytes) -> Dict[str, Any]:
    """
    Parse Terraform ZIP file and extract variable definitions.
    Returns a structured JSON format for frontend form generation.
    """
    variables = {}
    
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
            # Find all .tf files
            tf_files = [f for f in zip_ref.namelist() if f.endswith('.tf')]
            
            for tf_file in tf_files:
                try:
                    content = zip_ref.read(tf_file).decode('utf-8')
                    try:
                        parsed = hcl2.loads(content)
                    except Exception as e:
                        logger.warning(f"Failed to parse HCL2 in {tf_file}: {str(e)}")
                        continue
                    
                    # Extract variables
                    if 'variable' in parsed:
                        var_block = parsed['variable']
                        
                        # Handle both dict and list formats
                        if isinstance(var_block, dict):
                            var_items = var_block.items()
                        elif isinstance(var_block, list):
                            # HCL2 sometimes returns variables as a list of dicts
                            # Each dict typically has variable name as key: [{'var_name': {...}}, ...]
                            var_items = []
                            for var_item in var_block:
                                if isinstance(var_item, dict):
                                    # Extract key-value pairs where key is variable name
                                    for var_name, var_config in var_item.items():
                                        if isinstance(var_config, dict):
                                            var_items.append((var_name, var_config))
                                        else:
                                            # If value is not a dict, wrap it
                                            var_items.append((var_name, {}))
                                else:
                                    logger.warning(f"Unexpected variable item type in {tf_file}: {type(var_item)}")
                        else:
                            logger.warning(f"Unexpected variable block type in {tf_file}: {type(var_block)}")
                            continue
                        
                        for var_name, var_config in var_items:
                            var_info = {
                                'name': var_name,
                                'type': 'string',  # default
                                'description': '',
                                'default': None,
                                'required': True,
                                'sensitive': False
                            }
                            
                            # Parse variable block
                            if isinstance(var_config, dict):
                                if 'type' in var_config:
                                    var_type = var_config['type']
                                    if isinstance(var_type, list) and len(var_type) > 0:
                                        var_info['type'] = str(var_type[0]).replace('"', '')
                                    elif isinstance(var_type, str):
                                        var_info['type'] = var_type.replace('"', '')
                                
                                if 'description' in var_config:
                                    desc = var_config['description']
                                    if isinstance(desc, list) and len(desc) > 0:
                                        var_info['description'] = str(desc[0]).replace('"', '')
                                    elif isinstance(desc, str):
                                        var_info['description'] = desc.replace('"', '')
                                
                                if 'default' in var_config:
                                    default = var_config['default']
                                    if isinstance(default, list) and len(default) > 0:
                                        var_info['default'] = default[0]
                                    else:
                                        var_info['default'] = default
                                    var_info['required'] = False
                                
                                if 'sensitive' in var_config:
                                    sensitive = var_config['sensitive']
                                    if isinstance(sensitive, list) and len(sensitive) > 0:
                                        var_info['sensitive'] = bool(sensitive[0])
                                    else:
                                        var_info['sensitive'] = bool(sensitive)
                            
                            variables[var_name] = var_info
                
                except Exception as e:
                    logger.warning(f"Failed to parse {tf_file}: {str(e)}")
                    continue
    
    except Exception as e:
        logger.error(f"Failed to parse Terraform ZIP: {str(e)}")
        raise
    
    # Convert to list format for frontend
    variables_list = list(variables.values())
    
    return {
        'variables': variables_list,
        'variable_count': len(variables_list)
    }


def parse_ui_variables_json(zip_content: bytes) -> Optional[Dict[str, Any]]:
    """
    Extract ui-variables.json from Terraform ZIP if present.
    Returns the JSON content or None if file is missing/invalid.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_ref:
            candidates = [f for f in zip_ref.namelist() if f.rstrip('/').endswith('ui-variables.json')]
            if not candidates:
                return None
            raw = zip_ref.read(candidates[0]).decode('utf-8')
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"Could not parse ui-variables.json: {e}")
        return None
