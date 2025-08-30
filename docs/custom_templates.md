# Custom Templates Support

The MCP Platform now supports custom templates through the `MCP_CUSTOM_TEMPLATES_DIR` environment variable. This allows organizations to maintain private or internal MCP server templates alongside the built-in ones.

## Overview

- **Built-in Templates**: Located in `mcp_platform/template/templates/`
- **Custom Templates**: Located in directory specified by `MCP_CUSTOM_TEMPLATES_DIR`
- **Override Behavior**: Custom templates with the same name override built-in templates
- **Backward Compatibility**: All existing functionality continues to work unchanged

## Usage

### Setting Custom Templates Directory

```bash
# Set the environment variable
export MCP_CUSTOM_TEMPLATES_DIR="/path/to/your/custom/templates"

# Or use a path relative to home directory
export MCP_CUSTOM_TEMPLATES_DIR="~/my-org-templates"
```

### Directory Structure

Your custom templates directory should follow the same structure as built-in templates:

```
/path/to/your/custom/templates/
├── my-internal-tool/
│   ├── template.json
│   ├── Dockerfile
│   ├── server.py
│   ├── requirements.txt
│   └── tests/
└── custom-demo/
    ├── template.json
    ├── Dockerfile
    └── ...
```

### Template Override Example

If you have a custom template with the same name as a built-in template, the custom one takes precedence:

**Built-in**: `mcp_platform/template/templates/demo/template.json`
```json
{
  "name": "Demo Hello MCP Server",
  "version": "1.0.0",
  "docker_image": "dataeverything/mcp-demo:latest"
}
```

**Custom**: `$MCP_CUSTOM_TEMPLATES_DIR/demo/template.json`
```json
{
  "name": "My Organization Demo",
  "version": "2.0.0", 
  "docker_image": "myorg/demo:latest"
}
```

When listing templates, the custom version will be shown instead of the built-in one.

## Template Discovery

The platform discovers templates in this order:

1. **Custom templates** (from `MCP_CUSTOM_TEMPLATES_DIR`)
2. **Built-in templates** (from `mcp_platform/template/templates/`)

Templates with the same name in custom directory override built-in ones.

## Example: Internal Organization Template

Create a custom template for your organization:

1. **Set up custom templates directory**:
   ```bash
   mkdir -p ~/my-company-templates/internal-api
   export MCP_CUSTOM_TEMPLATES_DIR="~/my-company-templates"
   ```

2. **Create template.json**:
   ```json
   {
     "name": "Internal API MCP Server",
     "description": "MCP server for internal company API",
     "version": "1.0.0",
     "docker_image": "company.registry.com/mcp-internal-api:latest",
     "tool_discovery": "dynamic",
     "has_image": true,
     "origin": "internal",
     "config_schema": {
       "type": "object",
       "properties": {
         "api_token": {
           "type": "string",
           "description": "Internal API authentication token",
           "env_mapping": "INTERNAL_API_TOKEN"
         },
         "environment": {
           "type": "string",
           "description": "Environment (dev/staging/prod)",
           "default": "dev",
           "env_mapping": "ENVIRONMENT"
         }
       },
       "required": ["api_token"]
     }
   }
   ```

3. **Template will be automatically discovered**:
   ```bash
   mcp-platform templates list
   # Will show both built-in and custom templates
   ```

## Programming Interface

You can also use the custom templates functionality programmatically:

```python
from mcp_platform.template.utils.discovery import TemplateDiscovery

# Discover all templates (built-in + custom)
discovery = TemplateDiscovery()
templates = discovery.discover_templates()

# Custom templates will override built-in ones with same name
for name, config in templates.items():
    print(f"{name}: {config['name']} from {config['source_directory']}")
```

## Benefits

- **Private Templates**: Keep proprietary templates private to your organization
- **Template Customization**: Override built-in templates with organization-specific versions  
- **Easy Management**: Simply set an environment variable to enable custom templates
- **No Code Changes**: Existing code continues to work without modification
- **Git Integration**: Store custom templates in private repositories
- **Team Collaboration**: Share custom templates across your organization

## Notes

- The custom templates directory is optional - if not set or doesn't exist, only built-in templates are used
- Template validation rules apply to custom templates just like built-in ones
- Custom templates should include all required files (template.json, Dockerfile, etc.)
- The `source_directory` field in template metadata indicates whether a template is custom or built-in