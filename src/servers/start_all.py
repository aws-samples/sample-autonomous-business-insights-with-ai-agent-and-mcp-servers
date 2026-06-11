# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Start all MCP servers for local development.

In production, each MCP server would be deployed independently to AgentCore
Runtime, registered in the AgentCore Registry, and discovered automatically
by the Agent through the Gateway.

For local development, this script starts all servers as subprocesses.
"""

import subprocess
import sys
import signal
import os
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SERVERS = [
    {
        "name": "Semantic Layer Server",
        "module": "src.servers.semantic_layer_server",
        "port_env": "SEMANTIC_LAYER_SERVER_PORT",
        "default_port": "8005",
    },
    {
        "name": "Equipment Server",
        "module": "src.servers.equipment_server",
        "port_env": "EQUIPMENT_SERVER_PORT",
        "default_port": "8001",
    },
    {
        "name": "IoT Telemetry Server",
        "module": "src.servers.iot_telemetry_server",
        "port_env": "IOT_TELEMETRY_SERVER_PORT",
        "default_port": "8002",
    },
    {
        "name": "Supply Chain Server",
        "module": "src.servers.supply_chain_server",
        "port_env": "SUPPLY_CHAIN_SERVER_PORT",
        "default_port": "8003",
    },
    {
        "name": "Analytics Server",
        "module": "src.servers.analytics_server",
        "port_env": "ANALYTICS_SERVER_PORT",
        "default_port": "8004",
    },
]


def start_servers() -> list[subprocess.Popen]:
    """Start all MCP servers as subprocesses."""
    processes = []

    for server in SERVERS:
        port = os.getenv(server["port_env"], server["default_port"])
        env = os.environ.copy()
        env[server["port_env"]] = port

        logger.info("Starting %s on port %s...", server["name"], port)

        proc = subprocess.Popen(
            [sys.executable, "-m", server["module"]],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        processes.append(proc)
        logger.info("  ✓ %s started (PID: %d)", server["name"], proc.pid)

    return processes


def shutdown_servers(processes: list[subprocess.Popen]) -> None:
    """Gracefully shut down all server processes."""
    logger.info("\nShutting down MCP servers...")
    for proc in processes:
        proc.terminate()
    for proc in processes:
        proc.wait(timeout=5)
    logger.info("All servers stopped.")


if __name__ == "__main__":
    processes = start_servers()

    logger.info("\n" + "=" * 60)
    logger.info("All MCP servers are running. Press Ctrl+C to stop.")
    logger.info("=" * 60)
    logger.info("  Equipment Server:     http://localhost:%s/mcp/", os.getenv("EQUIPMENT_SERVER_PORT", "8001"))
    logger.info("  IoT Telemetry Server: http://localhost:%s/mcp/", os.getenv("IOT_TELEMETRY_SERVER_PORT", "8002"))
    logger.info("  Supply Chain Server:  http://localhost:%s/mcp/", os.getenv("SUPPLY_CHAIN_SERVER_PORT", "8003"))
    logger.info("  Analytics Server:     http://localhost:%s/mcp/", os.getenv("ANALYTICS_SERVER_PORT", "8004"))
    logger.info("=" * 60 + "\n")

    def signal_handler(sig, frame):
        shutdown_servers(processes)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            # Check if any server has crashed
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    logger.error(
                        "%s exited unexpectedly (code: %d)",
                        SERVERS[i]["name"],
                        proc.returncode,
                    )
            time.sleep(2)
    except KeyboardInterrupt:
        shutdown_servers(processes)
