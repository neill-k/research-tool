from __future__ import annotations

from dataclasses import dataclass

from frontier_research.discovery.models import PaperMetadata, PaperRole
from frontier_research.discovery.providers import PaperMetadataProvider


@dataclass(slots=True)
class PaperMetadataService:
    provider: PaperMetadataProvider

    def fetch(self, identifier: str, role: PaperRole) -> PaperMetadata:
        return self.provider.fetch_minimal_paper(identifier=identifier, role=role)
