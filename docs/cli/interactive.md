# Interactive Command

The `interactive` command launches a comprehensive CLI session for deployment management and direct interaction with MCP servers.

## Usage

```bash
mcpp interactive
```

## Description

The interactive mode provides a unified interface for managing MCP server deployments and executing tools directly from the command line. This modern CLI includes command history, tab completion, and template session management for an enhanced user experience.

This is the primary way to:

- **Manage Deployments**: List, monitor, and control running MCP server deployments
- **Discover Tools**: Automatically discover available tools from deployed servers
- **Execute Tools**: Run MCP server tools directly without writing integration code
- **Interactive Debugging**: Test and debug MCP server functionality in real-time
- **Template Selection**: Select a template once and use all commands without repeating the template name

## Key Features

### Enhanced User Experience
- **Command History**: Use up/down arrow keys to navigate through previous commands
- **Tab Completion**: Auto-complete commands, template names, and configuration keys
- **Dynamic Prompts**: Visual indication of currently selected template
- **Rich Formatting**: Beautiful tables and colored output for better readability

### Template Session Management
- **Template Selection**: Use `select <template>` to set a default template for the session
- **Session Persistence**: Selected template persists across commands until changed
- **Smart Arguments**: Commands automatically use selected template when no template is specified

### Deployment Management
- List active deployments and their status
- Monitor deployment health and logs
- Start, stop, and manage server lifecycles
- View deployment configuration and metadata

### Tool Discovery & Execution
- Automatically discover tools available in deployed MCP servers
- Execute tools with real-time feedback and error handling
- Pass arguments and configuration dynamically
- Support for both simple and complex tool interactions

### Session Management
- Persistent session across multiple commands
- Command history and tab completion (readline support)
- Context-aware help and suggestions
- Graceful error handling and recovery

## Command History & Completion

The interactive CLI includes built-in support for command history and tab completion:

- **Command History**: Use ↑/↓ arrow keys to navigate through previous commands
  - History is maintained during the session
  - Commands are saved to `~/.mcp/.mcpp_history` and restored between sessions
  - The prompt stays visible when navigating history
- **Tab Completion**: Press Tab to auto-complete:
  - Commands (e.g., `tem[Tab]` → `templates`)
  - Template names (e.g., `select dem[Tab]` → `select demo`)
  - Configuration keys (e.g., `config back[Tab]` → `config backend`)
- **History Persistence**: Command history is saved and restored between sessions
- **Clean Prompt Display**: The prompt remains stable when using arrow keys

mcpp(demo)> tools        # No need to specify template
## Template Usage

Commands that operate on a template now require the template name to be provided explicitly.

```bash
# Example: List tools for a template
mcpp> tools demo

# Call a tool for a specific template
mcpp> call demo say_hello '{"name": "Alice"}'

# Configure a template
mcpp> configure demo port=8080
```

## Example Session

```bash
# Start interactive session
mcpp interactive
✨ Command history and tab completion enabled

# List available templates
mcpp> templates

```bash
# Start interactive session
mcpp interactive
✨ Command history and tab completion enabled

# List available templates
mcpp> templates

# Call a tool
mcpp> call demo say_hello '{"name": "World"}'

# View servers for a template
mcpp> servers --template demo

# Exit session
mcpp> exit
Goodbye!
```
```

## Available Commands

The interactive CLI supports all standard MCP operations plus enhanced session management:

### Core Commands
- `help` - Show help information
- `templates` - List available templates
- `servers` - List running servers
- `tools [template] [--force-refresh] [--help-info]` - List tools
- `call <template|tool> <tool> <args> [-C key=value] [-e key=value]` - Execute a tool
- `deploy <template>` - Deploy a template
- `logs <deployment>` - View deployment logs
- `stop <deployment>` - Stop a deployment
- `remove <deployment>` - Remove a deployment
- `cleanup` - Clean up stopped containers

### Session Management
- `select <template>` - Select template for session
- `unselect` - Unselect current template
- `config [template] <key>=<value>` - Set configuration
- `exit` / `quit` - Exit interactive session

### Enhanced Call Command Features

The `call` command now supports flexible argument ordering and multiple override options:

**Syntax:**
```bash
call [template] <tool_name> [JSON_args] [-C key=value] [-e key=value] [-b backend]
```

**Multi-Backend Tool Calling:**
The call command now supports multi-backend tool execution with automatic discovery:

1. **Priority-based execution**: Existing deployment → stdio support → deployment required message
2. **Backend selection**: Use `--backend` flag to force specific backend (docker, kubernetes, mock)
3. **Enhanced error reporting**: Shows which backend was used and helpful deployment commands

**Examples:**
```bash
# Basic usage (multi-backend auto-discovery)
call say_hello '{"name": "Alice"}'
call demo say_hello '{"name": "Alice"}'

# With config overrides (GitHub integration example)
call github list_pull_requests -C github_token="ghp_xxx" '{"owner": "Data-Everything", "repo": "MCP-Platform"}'

# Force specific backend
call demo say_hello --backend docker
call demo say_hello --backend kubernetes

# With environment variables
call say_hello -e MCP_HELLO_FROM="EnvValue" '{"name": "Alice"}'

# Multiple overrides (flags can appear anywhere)
call -C github_token="ghp_xxx" github list_pull_requests '{"owner": "user", "repo": "project"}'
call github list_pull_requests -C github_token="ghp_xxx" -e DEBUG="true" '{"owner": "user", "repo": "project"}'

# Complex example with all options
call github list_pull_requests \
  -C github_token="ghp_xxx" \
  -C github_host="api.github.com" \
  -e DEBUG=true \
  --backend docker \
  '{"owner": "Data-Everything", "repo": "MCP-Platform"}'
```

**Available Flags:**
- `-C, --config KEY=VALUE`: Configuration overrides
- `-e, --env KEY=VALUE`: Environment variables
- `-b, --backend NAME`: Force specific backend (docker, kubernetes, mock)
- `--stdio`: Force stdio transport
- `--raw`: Show raw JSON response
- `--no-pull`: Don't pull Docker images for stdio calls

**Multi-Backend Error Handling:**
Enhanced error messages now show:
- Which backend was attempted
- Whether template supports stdio transport
- Exact deployment command if deployment is required

```bash
# Example error messages
❌ Tool execution failed: Backend 'kubernetes' not available
Backend used: kubernetes

❌ Tool execution failed: Template 'github' does not support stdio transport and no running deployment found
💡 Try deploying first: mcpp deploy github
```

### Enhanced Features
- **Multi-backend Support**: Automatic discovery and execution across Docker, Kubernetes, and other backends
- **Backend Selection**: Force specific backend using `--backend` flag
- **Flexible Argument Parsing**: Config overrides (`-C`) and environment variables (`-e`) can appear anywhere in the command
- **Smart Template Detection**: Commands automatically detect whether the first argument is a template name or parameter
- **Priority-based Discovery**: Find existing deployments first, fallback to stdio support
- **Enhanced Error Reporting**: Detailed error messages with backend information and helpful suggestions
- **Rich Output**: All commands feature beautiful tables and colored output with backend details
- **Error Recovery**: Graceful error handling with deployment guidance## Benefits

- **Faster development**: No need to retype `mcp-template` for each command
- **Better testing**: Quickly iterate between deploy, test, and debug
- **Tool integration**: Direct access to template tools via `call` command
- **User-friendly**: More intuitive for extended usage sessions

## Related Commands

- [`call`](../interactive-cli/call.md) - Execute template tools (available in interactive mode)
- [`deploy`](deploy.md) - Deploy templates for tool calling
- [`list`](list.md) - List available templates
