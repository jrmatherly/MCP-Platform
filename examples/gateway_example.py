#!/usr/bin/env python3
"""
MCP Gateway Example - Unified access to multiple MCP servers.

This example demonstrates how to:
1. Start the MCP Gateway server
2. Register MCP server instances
3. Use load balancing across multiple instances
4. Monitor health and performance

Usage:
    python gateway_example.py
"""

import asyncio
import logging
import time
from pathlib import Path

import aiohttp

from mcp_platform.gateway import MCPGatewayServer, ServerRegistry
from mcp_platform.gateway.registry import LoadBalancerConfig, ServerInstance

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main example function."""

    print("🚀 MCP Gateway Example")
    print("=" * 50)

    # 1. Create and configure gateway
    registry_file = Path.home() / ".mcp" / "example_registry.json"
    registry_file.parent.mkdir(exist_ok=True)

    gateway = MCPGatewayServer(
        host="localhost",
        port=8080,
        registry_file=str(registry_file),
        health_check_interval=10,  # Fast health checks for demo
    )

    print(f"📋 Registry file: {registry_file}")

    # 2. Manually register some example server instances
    await register_example_servers(gateway.registry)

    # 3. Start the gateway server
    print("\n🌐 Starting gateway server...")
    await gateway.start()

    # Run in background for demo
    import threading

    server_thread = threading.Thread(
        target=lambda: gateway.run(log_level="warning"), daemon=True
    )
    server_thread.start()

    # Give server time to start
    await asyncio.sleep(2)

    # 4. Demonstrate gateway usage
    await demonstrate_gateway_usage()

    # 5. Show monitoring and stats
    await show_gateway_stats(gateway)

    # 6. Cleanup
    print("\n🧹 Cleaning up...")
    await gateway.stop()

    print("\n✅ Example completed!")


async def register_example_servers(registry: ServerRegistry):
    """Register example server instances."""
    print("\n📝 Registering example servers...")

    # Demo template with multiple HTTP instances (simulating load balancing)
    for i in range(1, 4):
        instance = ServerInstance(
            id=f"demo-{i}",
            template_name="demo",
            endpoint=f"http://httpbin.org/delay/{i}",  # Using httpbin for demo
            transport="http",
            backend="docker",
            container_id=f"mcp-demo-{i}",
            metadata={"weight": i},  # Different weights for weighted balancing
        )
        registry.register_server("demo", instance)

    # Filesystem template with stdio instance
    fs_instance = ServerInstance(
        id="filesystem-1",
        template_name="filesystem",
        command=["echo", "filesystem server"],  # Mock command for demo
        transport="stdio",
        backend="docker",
        container_id="mcp-filesystem-1",
        working_dir="/app",
        env_vars={"DATA_DIR": "/data"},
    )
    registry.register_server("filesystem", fs_instance)

    # Configure load balancer for demo template
    demo_lb_config = LoadBalancerConfig(
        strategy="weighted",  # Use weighted strategy
        health_check_interval=5,
        max_retries=2,
    )
    demo_template = registry.get_template("demo")
    if demo_template:
        demo_template.load_balancer = demo_lb_config

    print(f"✅ Registered {len(registry.list_all_instances())} server instances")
    print(f"   Templates: {', '.join(registry.list_templates())}")


async def demonstrate_gateway_usage():
    """Demonstrate using the gateway to access MCP servers."""
    print("\n🔄 Demonstrating gateway usage...")

    base_url = "http://localhost:8080"

    async with aiohttp.ClientSession() as session:
        # 1. Get gateway health
        try:
            async with session.get(f"{base_url}/gateway/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"🟢 Gateway health: {health_data['status']}")
                    print(f"   Uptime: {health_data['uptime_seconds']:.1f}s")
                else:
                    print(f"🔴 Gateway health check failed: {response.status}")
        except Exception as e:
            print(f"🔴 Could not connect to gateway: {e}")
            return

        # 2. List tools from demo template (load balanced)
        print("\n📋 Testing load balanced requests to demo template...")
        for i in range(5):
            try:
                start_time = time.time()
                async with session.get(f"{base_url}/mcp/demo/tools/list") as response:
                    duration = time.time() - start_time
                    if response.status == 200:
                        print(f"   Request {i + 1}: ✅ Success ({duration:.2f}s)")
                    else:
                        print(f"   Request {i + 1}: ❌ Failed ({response.status})")

                # Small delay between requests
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"   Request {i + 1}: ❌ Error - {e}")

        # 3. Check template health
        try:
            async with session.get(f"{base_url}/mcp/demo/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print("\n🏥 Demo template health:")
                    print(f"   Total instances: {health_data['total_instances']}")
                    print(f"   Healthy instances: {health_data['healthy_instances']}")
                    print(
                        f"   Health percentage: {health_data['health_percentage']:.1f}%"
                    )
        except Exception as e:
            print(f"❌ Template health check failed: {e}")

        # 4. Get registry status
        try:
            async with session.get(f"{base_url}/gateway/registry") as response:
                if response.status == 200:
                    registry_data = await response.json()
                    print("\n📊 Registry status:")
                    stats = registry_data["stats"]
                    print(f"   Total templates: {stats['total_templates']}")
                    print(f"   Total instances: {stats['total_instances']}")
                    print(f"   Healthy instances: {stats['healthy_instances']}")

                    # Show template details
                    for template_name, template_data in registry_data[
                        "templates"
                    ].items():
                        instances = template_data["instances"]
                        lb_strategy = template_data["load_balancer"]["strategy"]
                        print(
                            f"   📦 {template_name}: {len(instances)} instances ({lb_strategy})"
                        )

        except Exception as e:
            print(f"❌ Registry check failed: {e}")


async def show_gateway_stats(gateway: MCPGatewayServer):
    """Show detailed gateway statistics."""
    print("\n📈 Gateway Statistics:")

    # Registry stats
    registry_stats = gateway.registry.get_registry_stats()
    print(
        f"   Registry: {registry_stats['total_instances']} instances, "
        f"{registry_stats['healthy_instances']} healthy"
    )

    # Load balancer stats
    lb_stats = gateway.load_balancer.get_load_balancer_stats()
    print(f"   Load Balancer: {lb_stats['total_requests']} total requests")
    print(f"   Default strategy: {lb_stats['default_strategy']}")

    if lb_stats["requests_per_instance"]:
        print("   Requests per instance:")
        for instance_id, count in lb_stats["requests_per_instance"].items():
            print(f"     {instance_id}: {count}")

    # Health checker stats
    health_stats = gateway.health_checker.get_health_stats()
    print(
        f"   Health Checker: {health_stats['total_checks']} checks, "
        f"{health_stats['success_rate_percent']:.1f}% success rate"
    )


def integration_example():
    """Example of integrating gateway with existing deployments."""
    print("\n🔗 Integration Example:")
    print("The gateway can automatically sync with existing MCP Platform deployments:")
    print()
    print("# Sync with current deployments")
    print("mcpp gateway sync")
    print()
    print("# Start gateway with auto-sync")
    print("mcpp gateway start --sync")
    print()
    print("# Register manually")
    print("mcpp gateway register demo --endpoint http://localhost:7071")
    print()
    print("# Check status")
    print("mcpp gateway status")


if __name__ == "__main__":
    try:
        asyncio.run(main())

        # Show integration examples
        integration_example()

    except KeyboardInterrupt:
        print("\n👋 Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback

        traceback.print_exc()
