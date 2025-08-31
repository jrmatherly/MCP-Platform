#!/usr/bin/env python3
"""
Documentation builder for MCP Platform.

This script:
1. Uses the existing TemplateDiscovery utility to find usable templates
2. Generates navigation for template documentation
3. Copies template docs to the main docs directory
4. Builds the documentation with mkdocs
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict

import yaml

# Import the TemplateDiscovery utility
sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_platform.template.utils.discovery import TemplateDiscovery
from mcp_platform.utils import ROOT_DIR, TEMPLATES_DIR


def cleanup_old_docs(docs_dir: Path):
    """Clean up old generated documentation."""
    print("🧹 Cleaning up old docs...")

    templates_docs_dir = docs_dir / "server-templates"
    if templates_docs_dir.exists():
        for item in templates_docs_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        print("  🗑️  Cleaned up old server-templates docs")


def scan_template_docs(templates_dir: Path) -> Dict[str, Dict]:
    """Scan template directories for documentation using TemplateDiscovery."""
    print("🔍 Using TemplateDiscovery to find usable templates...")

    template_docs = {}

    # Use the existing TemplateDiscovery utility to find working templates
    discovery = TemplateDiscovery()
    try:
        templates = discovery.discover_templates()
        print(f"✅ TemplateDiscovery found {len(templates)} usable templates")
    except Exception as e:
        print(f"❌ Error using TemplateDiscovery: {e}")
        return {}

    for template_name, template_config in templates.items():
        template_dir = templates_dir / template_name
        docs_index = template_dir / "docs" / "index.md"

        if docs_index.exists():
            template_docs[template_name] = {
                "name": template_config.get("name", template_name.title()),
                "description": template_config.get("description", ""),
                "docs_file": docs_index,
                "config": template_config,
            }
            print(f"  ✅ Found docs for {template_name}")
        else:
            print(f"  ⚠️  Template {template_name} is usable but missing docs/index.md")

    print(f"📋 Found documentation for {len(template_docs)} templates")
    return template_docs


def generate_usage_md(template_id: str, template_info: Dict) -> str:
    """Generate standardized usage.md content for a template."""
    template_config = template_info["config"]
    template_name = template_config.get("name", template_id.title())
    tools = template_config.get("tools", [])
    
    usage_content = f"""# {template_name} Usage Guide

## Overview

This guide shows how to use the {template_name} with different MCP clients and integration methods.

## Tool Discovery

### Interactive CLI
```bash
# Start interactive mode
python -m mcp_platform interactive

# List available tools
mcpp> tools {template_id}
```

### Regular CLI
```bash
# Discover tools using CLI
python -m mcp_platform tools {template_id}
```

### Python Client
```python
from mcp_platform.client import MCPClient

async def discover_tools():
    async with MCPClient() as client:
        tools = await client.list_tools("{template_id}")
        for tool in tools:
            print(f"Tool: {{tool['name']}} - {{tool['description']}}")
```

## Available Tools

"""
    
    # Add tool documentation
    for tool in tools:
        tool_name = tool.get("name", "unknown_tool")
        tool_desc = tool.get("description", "No description available")
        tool_params = tool.get("parameters", [])
        
        usage_content += f"""### {tool_name}

**Description**: {tool_desc}

**Parameters**:
"""
        if tool_params:
            for param in tool_params:
                param_name = param.get("name", "unknown")
                param_desc = param.get("description", "No description")
                param_type = param.get("type", "string")
                param_required = " (required)" if param.get("required", False) else " (optional)"
                usage_content += f"- `{param_name}` ({param_type}){param_required}: {param_desc}\n"
        else:
            usage_content += "- No parameters required\n"
        
        usage_content += "\n"
    
    # Add usage examples section
    usage_content += f"""## Usage Examples

### Interactive CLI

```bash
# Start interactive mode
python -m mcp_platform interactive

# Deploy the template (if not already deployed)
mcpp> deploy {template_id}
```

Then call tools:
"""
    
    # Add interactive CLI examples for each tool
    for tool in tools[:3]:  # Show examples for first 3 tools
        tool_name = tool.get("name", "unknown_tool")
        tool_params = tool.get("parameters", [])
        
        if tool_params:
            # Create example parameters
            example_params = {}
            for param in tool_params:
                param_name = param.get("name", "param")
                param_type = param.get("type", "string")
                if param_type == "string":
                    example_params[param_name] = "example_value"
                elif param_type == "boolean":
                    example_params[param_name] = True
                elif param_type == "number":
                    example_params[param_name] = 123
                else:
                    example_params[param_name] = "example_value"
            
            params_json = json.dumps(example_params)
            usage_content += f"""```bash
mcpp> call {template_id} {tool_name} '{params_json}'
```

"""
        else:
            usage_content += f"""```bash
mcpp> call {template_id} {tool_name}
```

"""
    
    # Add CLI deployment section
    usage_content += f"""### Regular CLI

```bash
# Deploy the template
python -m mcp_platform deploy {template_id}

# Check deployment status
python -m mcp_platform status

# View logs
python -m mcp_platform logs {template_id}

# Stop the template
python -m mcp_platform stop {template_id}
```

### Python Client

```python
import asyncio
from mcp_platform.client import MCPClient

async def use_{template_id.replace('-', '_')}():
    async with MCPClient() as client:
        # Start the server
        deployment = await client.start_server("{template_id}", {{}})
        
        if deployment["success"]:
            deployment_id = deployment["deployment_id"]
            
            try:
"""
    
    # Add Python client examples for each tool
    for tool in tools[:2]:  # Show examples for first 2 tools
        tool_name = tool.get("name", "unknown_tool")
        tool_params = tool.get("parameters", [])
        
        if tool_params:
            example_params = {}
            for param in tool_params:
                param_name = param.get("name", "param")
                param_type = param.get("type", "string")
                if param_type == "string":
                    example_params[param_name] = "example_value"
                elif param_type == "boolean":
                    example_params[param_name] = True
                elif param_type == "number":
                    example_params[param_name] = 123
                else:
                    example_params[param_name] = "example_value"
            
            usage_content += f"""                # Call {tool_name}
                result = await client.call_tool("{template_id}", "{tool_name}", {example_params})
                print(f"{tool_name} result: {{result}}")
                
"""
        else:
            usage_content += f"""                # Call {tool_name}
                result = await client.call_tool("{template_id}", "{tool_name}", {{}})
                print(f"{tool_name} result: {{result}}")
                
"""
    
    usage_content += f"""            finally:
                # Clean up
                await client.stop_server(deployment_id)
        else:
            print("Failed to start server")

# Run the example
asyncio.run(use_{template_id.replace('-', '_')}())
```

## Integration Examples

### Claude Desktop

Add this configuration to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\\Claude\\claude_desktop_config.json`

```json
{{
  "mcpServers": {{
    "{template_id}": {{
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "{template_id}", "--stdio"],
      "env": {{
        "LOG_LEVEL": "info"
      }}
    }}
  }}
}}
```

### VS Code

Install the MCP extension and add this to your VS Code settings (`.vscode/settings.json`):

```json
{{
  "mcp.servers": {{
    "{template_id}": {{
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "{template_id}", "--stdio"],
      "env": {{
        "LOG_LEVEL": "info"
      }}
    }}
  }}
}}
```

### Manual Connection

```bash
# Get connection details for other integrations
python -m mcp_platform connect {template_id} --llm claude
python -m mcp_platform connect {template_id} --llm vscode
```

## Configuration

For template-specific configuration options, see the main template documentation. Common configuration methods:

```bash
# Deploy with configuration
python -m mcp_platform deploy {template_id} --config key=value

# Deploy with environment variables  
python -m mcp_platform deploy {template_id} --env KEY=VALUE

# Deploy with config file
python -m mcp_platform deploy {template_id} --config-file config.json
```

## Troubleshooting

### Common Issues

1. **Template not found**: Ensure the template name is correct
   ```bash
   python -m mcp_platform list  # List available templates
   ```

2. **Connection issues**: Check if the server is running
   ```bash
   python -m mcp_platform status
   ```

3. **Tool discovery fails**: Try refreshing the tool cache
   ```bash
   mcpp> tools {template_id} --refresh
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Interactive CLI with debug
LOG_LEVEL=debug python -m mcp_platform interactive

# Deploy with debug logging
python -m mcp_platform deploy {template_id} --config log_level=debug
```

For more help, see the [main documentation](../../) or open an issue in the repository.
"""
    
    return usage_content


def copy_template_docs(template_docs: Dict[str, Dict], docs_dir: Path):
    """Copy template documentation to docs directory and fix CLI commands."""
    print("📄 Copying template documentation...")

    templates_docs_dir = docs_dir / "server-templates"
    templates_docs_dir.mkdir(exist_ok=True)

    for template_id, template_info in template_docs.items():
        template_doc_dir = templates_docs_dir / template_id
        template_doc_dir.mkdir(exist_ok=True)

        # Generate usage.md file
        usage_content = generate_usage_md(template_id, template_info)
        with open(template_doc_dir / "usage.md", "w", encoding="utf-8") as f:
            f.write(usage_content)
        print(f"  📝 Generated usage.md for {template_id}")

        # Copy the index.md file and fix CLI commands
        dest_file = template_doc_dir / "index.md"
        with open(template_info["docs_file"], "r", encoding="utf-8") as f:
            content = f.read()

        # Fix CLI commands - add 'python -m' prefix and 'deploy' command
        content = content.replace(
            f"mcpp deploy {template_id}",
            f"python -m mcp_platform deploy {template_id}",
        )
        content = content.replace(
            f"mcpp {template_id}",
            f"python -m mcp_platform deploy {template_id}",
        )
        content = content.replace("mcpp create", "python -m mcp_platform create")
        content = content.replace("mcpp list", "python -m mcp_platform list")
        content = content.replace("mcpp stop", "python -m mcp_platform stop")
        content = content.replace("mcpp logs", "python -m mcp_platform logs")
        content = content.replace("mcpp shell", "python -m mcp_platform shell")
        content = content.replace("mcpp cleanup", "python -m mcp_platform cleanup")

        # Remove existing usage sections and replace with link to usage.md
        content = remove_usage_sections_and_add_link(content, template_id)

        # Add configuration information from template schema if not present
        config_schema = template_info["config"].get("config_schema", {})
        properties = config_schema.get("properties", {})

        if properties and "## Configuration" in content:
            # Generate configuration table
            config_section = "\n## Configuration Options\n\n"
            config_section += (
                "| Property | Type | Environment Variable | Default | Description |\n"
            )
            config_section += (
                "|----------|------|---------------------|---------|-------------|\n"
            )

            for prop_name, prop_config in properties.items():
                prop_type = prop_config.get("type", "string")
                env_mapping = prop_config.get("env_mapping", "")
                default = str(prop_config.get("default", ""))
                description = prop_config.get("description", "")

                config_section += f"| `{prop_name}` | {prop_type} | `{env_mapping}` | `{default}` | {description} |\n"

            config_section += "\n### Usage Examples\n\n"
            config_section += "```bash\n"
            config_section += "# Deploy with configuration\n"
            config_section += (
                f"python -m mcp_platform deploy {template_id} --show-config\n\n"
            )
            if properties:
                first_prop = next(iter(properties.keys()))
                first_prop_config = properties[first_prop]
                if first_prop_config.get("env_mapping"):
                    config_section += "# Using environment variables\n"
                    config_section += f"python -m mcp_platform deploy {template_id} --env {first_prop_config['env_mapping']}=value\n\n"
                config_section += "# Using CLI configuration\n"
                config_section += "python -m mcp_platform deploy {template_id} --config {first_prop}=value\n\n"
                config_section += "# Using nested configuration\n"
                config_section += "python -m mcp_platform deploy {template_id} --config category__property=value\n"
            config_section += "```\n"

            # Replace or append configuration section
            if "## Configuration" in content and "This template supports" in content:
                # Replace simple configuration section with detailed one
                import re

                pattern = r"## Configuration.*?(?=##|\Z)"
                content = re.sub(
                    pattern, config_section.strip(), content, flags=re.DOTALL
                )
            else:
                # Append before Development section or at end
                if "## Development" in content:
                    content = content.replace(
                        "## Development", config_section + "\n## Development"
                    )
                else:
                    content += "\n" + config_section

        with open(dest_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Copy any other documentation files if they exist
        template_docs_source = template_info["docs_file"].parent
        for doc_file in template_docs_source.iterdir():
            if doc_file.name != "index.md" and doc_file.is_file():
                shutil.copy2(doc_file, template_doc_dir / doc_file.name)

        print(f"  📄 Copied and enhanced docs for {template_id}")


def remove_usage_sections_and_add_link(content: str, template_id: str) -> str:
    """Remove usage sections from content and add link to usage.md."""
    import re
    
    # Common usage section patterns to remove
    usage_patterns = [
        r"### Usage\s*\n.*?(?=### |## |\Z)",  # ### Usage section
        r"## Usage\s*\n.*?(?=### |## |\Z)",   # ## Usage section  
        r"### Available Tools\s*\n.*?(?=### |## |\Z)",  # ### Available Tools section
        r"## Available Tools\s*\n.*?(?=### |## |\Z)",   # ## Available Tools section
        r"### API Reference\s*\n.*?(?=### |## |\Z)",    # ### API Reference section
        r"## API Reference\s*\n.*?(?=### |## |\Z)",     # ## API Reference section
        r"### Usage Examples\s*\n.*?(?=### |## |\Z)",   # ### Usage Examples section
        r"## Usage Examples\s*\n.*?(?=### |## |\Z)",    # ## Usage Examples section
        r"### Client Integration\s*\n.*?(?=### |## |\Z)", # ### Client Integration section
        r"## Client Integration\s*\n.*?(?=### |## |\Z)",  # ## Client Integration section
        r"### Integration Examples\s*\n.*?(?=### |## |\Z)", # ### Integration Examples section
        r"## Integration Examples\s*\n.*?(?=### |## |\Z)",  # ## Integration Examples section
        r"### FastMCP Client\s*\n.*?(?=### |## |\Z)",    # ### FastMCP Client section
        r"## FastMCP Client\s*\n.*?(?=### |## |\Z)",     # ## FastMCP Client section
        r"### Claude Desktop Integration\s*\n.*?(?=### |## |\Z)", # ### Claude Desktop Integration section
        r"## Claude Desktop Integration\s*\n.*?(?=### |## |\Z)",  # ## Claude Desktop Integration section
        r"### VS Code Integration\s*\n.*?(?=### |## |\Z)", # ### VS Code Integration section
        r"## VS Code Integration\s*\n.*?(?=### |## |\Z)",  # ## VS Code Integration section
        r"### cURL Testing\s*\n.*?(?=### |## |\Z)",      # ### cURL Testing section
        r"## cURL Testing\s*\n.*?(?=### |## |\Z)",       # ## cURL Testing section
    ]
    
    # Remove usage-related sections
    for pattern in usage_patterns:
        content = re.sub(pattern, "", content, flags=re.DOTALL)
    
    # Clean up multiple consecutive newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Add link to usage.md before troubleshooting, contributing, or at the end
    usage_link = f"\n## Usage\n\nFor detailed usage examples, tool documentation, and integration guides, see the **[Usage Guide](usage.md)**.\n\n"
    
    # Insert before common end sections
    insert_patterns = [
        "## Troubleshooting",
        "## Contributing", 
        "## License",
        "## Support",
        "## Development"
    ]
    
    inserted = False
    for pattern in insert_patterns:
        if pattern in content:
            content = content.replace(pattern, usage_link + pattern)
            inserted = True
            break
    
    # If no suitable place found, add at the end
    if not inserted:
        content = content.rstrip() + "\n" + usage_link
    
    return content


def generate_templates_index(template_docs: Dict[str, Dict], docs_dir: Path):
    """Generate an index page for all templates."""
    print("📝 Generating templates index...")

    templates_docs_dir = docs_dir / "server-templates"

    # Generate the main index.md for the templates section
    index_md = templates_docs_dir / "index.md"
    index_content = """# MCP Platform Templates

Welcome to the MCP Platform Templates documentation! This section provides comprehensive information about available Model Context Protocol (MCP) server templates that you can use to quickly deploy MCP servers for various use cases.

## What are MCP Platform Templates?

MCP Platform Templates are pre-configured, production-ready templates that implement the Model Context Protocol specification. Each template is designed for specific use cases and comes with:

- 🔧 **Complete configuration files**
- 📖 **Comprehensive documentation**
- 🧪 **Built-in tests**
- 🐳 **Docker support**
- ☸️ **Kubernetes deployment manifests**

## Available Templates

Browse our collection of templates:

- [Available Templates](available.md) - Complete list of all available templates

## Quick Start

1. **Choose a template** from our [available templates](available.md)
2. **Deploy locally** using Docker Compose or our deployment tools
3. **Configure** the template for your specific needs
4. **Deploy to production** using Kubernetes or your preferred platform

## Template Categories

Our templates are organized by functionality:

- **Database Connectors** - Connect to various database systems
- **File Servers** - File management and sharing capabilities
- **API Integrations** - Third-party service integrations
- **Demo Servers** - Learning and testing examples

## Getting Help

If you need assistance with any template:

1. Check the template-specific documentation
2. Review the troubleshooting guides
3. Visit our GitHub repository for issues and discussions

## Contributing

Interested in contributing a new template? See our contribution guidelines to get started.
"""

    with open(index_md, "w", encoding="utf-8") as f:
        f.write(index_content)

    # Generate the available.md file
    available_md = templates_docs_dir / "available.md"

    content = """# Available Templates

This page lists all available MCP Platform server templates.

"""

    # Sort templates by name
    sorted_templates = sorted(template_docs.items(), key=lambda x: x[1]["name"])

    for template_id, template_info in sorted_templates:
        content += f"""## [{template_info["name"]}]({template_id}/index.md)

{template_info["description"]}

**Template ID:** `{template_id}`

**Version:** {template_info["config"].get("version", "1.0.0")}

**Author:** {template_info["config"].get("author", "Unknown")}

---

"""

    with open(available_md, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ Templates index generated")


def update_mkdocs_nav(template_docs: Dict[str, Dict], mkdocs_file: Path):
    """Update mkdocs.yml navigation with template pages."""
    print("⚙️  Updating mkdocs navigation...")

    with open(mkdocs_file, "r", encoding="utf-8") as f:
        mkdocs_config = yaml.safe_load(f)

    # Find the Templates section in nav
    nav = mkdocs_config.get("nav", [])

    # Build template navigation
    template_nav_items = [
        {"Overview": "server-templates/index.md"},
        {"Available Templates": "server-templates/available.md"},
    ]

    # Add individual template pages
    sorted_templates = sorted(template_docs.items(), key=lambda x: x[1]["name"])
    for template_id, template_info in sorted_templates:
        template_nav_items.append(
            {template_info["name"]: f"server-templates/{template_id}/index.md"}
        )

    # Update the nav structure
    for i, section in enumerate(nav):
        if isinstance(section, dict) and "Templates" in section:
            nav[i]["Templates"] = template_nav_items
            break

    # Write back the updated config
    with open(mkdocs_file, "w", encoding="utf-8") as f:
        yaml.dump(
            mkdocs_config,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        )

    print("✅ MkDocs navigation updated")


def build_docs():
    """Build the documentation with mkdocs."""
    print("🏗️  Building documentation with MkDocs...")

    try:
        result = subprocess.run(
            ["mkdocs", "build"], check=True, capture_output=True, text=True
        )
        print("✅ Documentation built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Documentation build failed: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print(
            "❌ mkdocs command not found. Please install mkdocs: pip install mkdocs mkdocs-material"
        )
        return False


def main():
    """Main function to build documentation."""
    project_root = ROOT_DIR
    templates_dir = TEMPLATES_DIR
    docs_dir = project_root / "docs"
    mkdocs_file = project_root / "mkdocs.yml"

    print("🚀 Starting documentation build process...")

    # Ensure docs directory exists
    docs_dir.mkdir(exist_ok=True)

    # Clean docs directory
    cleanup_old_docs(docs_dir)

    # Scan for template documentation
    template_docs = scan_template_docs(templates_dir)

    if not template_docs:
        print("❌ No template documentation found. Exiting.")
        sys.exit(1)

    # Copy template docs
    copy_template_docs(template_docs, docs_dir)

    # Generate templates index
    generate_templates_index(template_docs, docs_dir)

    # Update mkdocs navigation
    update_mkdocs_nav(template_docs, mkdocs_file)

    # Build documentation
    if build_docs():
        print("🎉 Documentation build completed successfully!")
        print("📁 Documentation available in site/ directory")
    else:
        print("❌ Documentation build failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
