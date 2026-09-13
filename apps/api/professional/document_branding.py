"""Shared 3DS identity and semantic document components for client exports."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentBrand:
    organization: str = "3DS Marketing Digital & Tecnologia"
    product: str = "Professional Project Studio"
    primary: str = "0057B8"
    graphite: str = "1C1C1C"
    accent: str = "FFA500"
    risk: str = "E63946"
    muted: str = "667085"
    pale_blue: str = "EAF2FB"
    pale_gray: str = "F3F4F6"
    font: str = "Arial"


BRAND = DocumentBrand()
ASSET_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSET_DIR / "logooficial.png"


@dataclass(frozen=True)
class DocumentSection:
    key: str
    title: str
    value: str | tuple[str, ...]
    kind: str = "standard"

    @property
    def items(self):
        return self.value if isinstance(self.value, tuple) else (self.value,)


def clean_text(value):
    return " ".join(str(value or "").split()).strip()


def clean_items(value):
    values = value if isinstance(value, (list, tuple)) else (value,)
    return tuple(text for item in values if (text := clean_text(item)))


def briefing_sections(briefing):
    definitions = (
        ("problem", "Contexto e desafio", "summary"),
        ("objective", "Objetivo", "highlight"),
        ("target_audience", "Público-alvo", "standard"),
        ("deliverables", "Entregáveis", "list"),
        ("functional_requirements", "Requisitos funcionais", "list"),
        ("non_functional_requirements", "Requisitos não funcionais", "list"),
        ("integrations", "Integrações", "list"),
        ("data_requirements", "Dados", "list"),
        ("infrastructure_requirements", "Infraestrutura", "list"),
        ("constraints", "Restrições", "alert"),
        ("dependencies", "Dependências", "list"),
        ("assumptions", "Premissas", "list"),
        ("scope_risks", "Riscos de escopo", "risk"),
        ("ambiguities", "Pontos a esclarecer", "alert"),
        ("client_questions", "Perguntas para alinhamento", "list"),
        ("acceptance_criteria", "Critérios de aceite", "checklist"),
    )
    sections = []
    for key, title, kind in definitions:
        value = getattr(briefing, key, None)
        cleaned = clean_items(value)
        if cleaned:
            sections.append(DocumentSection(key, title, cleaned if isinstance(value, (list, tuple)) else cleaned[0], kind))
    return tuple(sections)


def proposal_sections(proposal):
    definitions = (
        ("greeting", "Saudação", "standard"),
        ("understanding", "Entendimento da necessidade", "summary"),
        ("approach", "Abordagem proposta", "highlight"),
        ("deliverables", "Entregáveis", "list"),
        ("deadline", "Prazo", "standard"),
        ("essential_questions", "Perguntas essenciais", "list"),
        ("differentiators", "Diferenciais", "list"),
        ("closing", "Encerramento", "standard"),
    )
    sections = []
    for key, title, kind in definitions:
        value = getattr(proposal, key, None)
        cleaned = clean_items(value)
        if cleaned:
            sections.append(DocumentSection(key, title, cleaned if isinstance(value, (list, tuple)) else cleaned[0], kind))
    return tuple(sections)
