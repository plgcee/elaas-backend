"""
Permissions and Roles Configuration
This config defines the permission matrix for all modules and their associated roles.
Used by seed scripts and nightly jobs to populate/update roles and permissions.
"""

# Define modules and their CRUD actions
MODULES = {
    "users": {
        "resource": "users",
        "actions": ["create", "read", "update", "delete"],
        "description": "User profile management"
    },
    "templates": {
        "resource": "templates",
        "actions": ["create", "read", "update", "delete", "upload"],
        "description": "Terraform template management"
    },
    "template_groups": {
        "resource": "template_groups",
        "actions": ["create", "read", "update", "delete", "assign"],
        "description": "Template group management"
    },
    "workshops": {
        "resource": "workshops",
        "actions": ["create", "read", "update", "delete", "deploy"],
        "description": "Workshop deployment management"
    },
    "deployments": {
        "resource": "deployments",
        "actions": ["create", "read", "update", "delete", "cancel"],
        "description": "Deployment management"
    },
    "groups": {
        "resource": "groups",
        "actions": ["create", "read", "update", "delete", "manage_members"],
        "description": "Group management"
    },
    "environments": {
        "resource": "environments",
        "actions": ["create", "read", "update", "delete"],
        "description": "Environment management for logical isolation of workshops"
    },
    "roles": {
        "resource": "roles",
        "actions": ["create", "read", "update", "delete", "assign"],
        "description": "Role and permission management"
    }
}

# Role definitions per module
ROLE_TYPES = {
    "ADMIN": {
        "permissions": ["create", "read", "update", "delete"],
        "description": "Full administrative access to the module"
    },
    "VIEWER": {
        "permissions": ["read"],
        "description": "Read-only access to the module"
    }
}

# Additional permissions for specific modules
MODULE_SPECIFIC_PERMISSIONS = {
    "templates": {
        "upload": "Upload template files"
    },
    "workshops": {
        "deploy": "Deploy workshops"
    },
    "deployments": {
        "cancel": "Cancel in-progress deployment"
    },
    "groups": {
        "manage_members": "Manage group members"
    },
    "roles": {
        "assign": "Assign roles to users/groups"
    },
    "template_groups": {
        "assign": "Assign/unassign templates to template groups"
    }
}

# Generate permission matrix
def get_permission_matrix():
    """
    Returns a dictionary with all permissions and their associated roles
    Format: {
        "permissions": [
            {"name": "users:create", "resource": "users", "action": "create", "description": "..."},
            ...
        ],
        "roles": [
            {
                "name": "users_admin",
                "description": "...",
                "permissions": ["users:create", "users:read", ...]
            },
            ...
        ]
    }
    """
    permissions = []
    roles = []
    
    # Generate permissions for each module
    for module_name, module_config in MODULES.items():
        resource = module_config["resource"]
        actions = module_config["actions"]
        
        for action in actions:
            permission_name = f"{resource}:{action}"
            description = f"{action.capitalize()} {resource}"
            
            # Add module-specific description if available
            if module_name in MODULE_SPECIFIC_PERMISSIONS and action in MODULE_SPECIFIC_PERMISSIONS[module_name]:
                description = MODULE_SPECIFIC_PERMISSIONS[module_name][action]
            
            permissions.append({
                "name": permission_name,
                "resource": resource,
                "action": action,
                "description": description
            })
    
    # Generate roles for each module
    for module_name, module_config in MODULES.items():
        resource = module_config["resource"]
        
        for role_type, role_config in ROLE_TYPES.items():
            role_name = f"{resource.upper()}_{role_type}"
            role_permissions = []
            
            # Add base permissions
            for action in role_config["permissions"]:
                if action in module_config["actions"]:
                    role_permissions.append(f"{resource}:{action}")
            
            # Add module-specific permissions for ADMIN role
            if role_type == "ADMIN":
                for action in module_config["actions"]:
                    if action not in role_config["permissions"]:
                        role_permissions.append(f"{resource}:{action}")
            
            roles.append({
                "name": role_name.lower(),
                "description": f"{role_config['description']} for {module_config['description']}",
                "permissions": sorted(role_permissions)
            })
    
    return {
        "permissions": permissions,
        "roles": roles
    }


# Export the matrix for use in seed scripts
PERMISSION_MATRIX = get_permission_matrix()
