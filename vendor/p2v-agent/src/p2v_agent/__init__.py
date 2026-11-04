"""p2v-agent: prompt-to-video orchestration with an AgentScope ReActAgent.

This package is a refactor of the original ``prompt2video`` CLI: instead of
driving Claude Code, it scaffolds a Remotion project, installs the official
Remotion agent skills and the bundled ``prompt2video`` skill, and lets an
AgentScope agent do the coding/render work.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
