import os
import sys
from pathlib import Path

# Automatically inject monorepo package and app paths into sys.path
root_dir = Path(__file__).resolve().parents[3]
monorepo_paths = [
    str(root_dir / "packages" / "mcp-common" / "src"),
    str(root_dir / "packages" / "model-gateway" / "src"),
    str(root_dir / "apps" / "mcp-gateway"),
    str(root_dir / "apps" / "agent-runtime"),
    str(root_dir / "mcp-servers" / "mcp-hello"),
    str(root_dir / "mcp-servers" / "mcp-knowledge"),
    str(root_dir / "mcp-servers" / "mcp-gemini"),
    str(root_dir / "mcp-servers" / "mcp-media"),
]

for p in monorepo_paths:
    if p not in sys.path:
        sys.path.insert(0, p)
