"""Response schema for the application metadata endpoint (`/meta`).

The frontend footer consumes this to display the application name and the PM
Accelerator attribution; both values come straight from settings so they are
configurable without a code change (ARCHITECTURE §5).
"""

from pydantic import BaseModel


class MetaResponse(BaseModel):
    """Application name and description shown in the frontend footer."""

    name: str
    description: str
