"""
Laravel Architecture Maturity Model
Scores a project from 0–5 based on structural evidence.
Pure heuristics — no AI needed.
"""

from dataclasses import dataclass
from .scanner import LaravelProject


@dataclass
class MaturityResult:
    level: int
    label: str
    description: str
    score: int          # raw score (0–100)
    evidence: list[str]
    missing: list[str]


LEVEL_LABELS = {
    0: "Código Caótico",
    1: "MVC Padrão Laravel",
    2: "Service Layer",
    3: "Modularização Parcial",
    4: "DDD Parcial",
    5: "DDD Bem Aplicado",
}

LEVEL_DESCRIPTIONS = {
    0: "Controllers e Models com lógica misturada. Alto acoplamento, sem separação de responsabilidades.",
    1: "MVC Laravel padrão com alguma organização básica, mas lógica concentrada nos Controllers.",
    2: "Presença de Services com separação parcial de responsabilidades. Evolução significativa.",
    3: "Modularização ou Actions introduzidos. Contextos começam a ganhar forma.",
    4: "Estrutura de Domain visível, com alguns padrões DDD presentes (Repos, DTOs, VOs).",
    5: "DDD bem aplicado: Aggregates, Value Objects, Domain Events, camada de Application clara.",
}


def calculate_maturity(project: LaravelProject) -> MaturityResult:
    score = 0
    evidence = []
    missing = []

    layout = project.layout

    # ── Camada básica MVC (até 10 pts)
    has_controllers = len(project.controllers) > 0
    has_models = len(project.models) > 0

    if has_controllers:
        score += 5
        evidence.append(f"Controllers encontrados ({len(project.controllers)})")
    if has_models:
        score += 5
        evidence.append(f"Models encontrados ({len(project.models)})")

    # ── Form Requests (até 5 pts) - nível 1
    if layout.has_form_requests:
        score += 5
        evidence.append("Form Requests presentes (validação separada)")
    else:
        missing.append("Form Requests ausentes (validação misturada nos Controllers)")

    # ── API Resources (até 5 pts) - nível 1/2
    if layout.has_resources:
        score += 5
        evidence.append("API Resources presentes (serialização separada)")

    # ── Services (até 15 pts) - nível 2
    if layout.has_services:
        score += 15
        evidence.append(f"Services encontrados ({len(project.services)}) — separação de lógica de negócio")
    else:
        missing.append("Camada de Services ausente — lógica provavelmente no Controller")

    # ── Repositories (até 10 pts) - nível 2/3
    if layout.has_repositories:
        score += 10
        evidence.append(f"Repositories encontrados ({len(project.repositories)}) — acesso a dados abstraído")
    else:
        missing.append("Repositories ausentes — acesso direto ao Model/DB na lógica")

    # ── Actions (até 8 pts) - nível 3
    if layout.has_actions:
        score += 8
        evidence.append(f"Actions encontradas ({len(project.actions)}) — operações de negócio encapsuladas")

    # ── Modules (até 10 pts) - nível 3
    if layout.has_modules:
        score += 10
        evidence.append(f"Estrutura modular detectada: {layout.module_paths[:3]}")
    else:
        missing.append("Sem modularização — tudo em app/ global")

    # ── Events/Listeners (até 5 pts) - nível 3/4
    if layout.has_events:
        score += 5
        evidence.append("Events/Listeners presentes (domain events primitivos)")

    # ── DTOs (até 8 pts) - nível 4
    if layout.has_dtos:
        score += 8
        evidence.append("DTOs encontrados — transferência de dados tipada")
    else:
        missing.append("DTOs ausentes — dados trafegam como array ou Request diretamente")

    # ── Value Objects (até 10 pts) - nível 4/5
    if layout.has_value_objects:
        score += 10
        evidence.append("Value Objects encontrados — primitivos do domínio encapsulados")
    else:
        missing.append("Value Objects ausentes — tipos primitivos no domínio")

    # ── Domain folder (até 9 pts) - nível 4/5
    if layout.has_domain:
        score += 9
        evidence.append(f"Camada de Domain explícita: {layout.domain_paths[:2]}")
    else:
        missing.append("Sem pasta Domain explícita")

    # ── Normalize
    score = min(score, 100)

    # ── Map score to level
    level = _score_to_level(score, layout)

    return MaturityResult(
        level=level,
        label=LEVEL_LABELS[level],
        description=LEVEL_DESCRIPTIONS[level],
        score=score,
        evidence=evidence,
        missing=missing,
    )


def _score_to_level(score: int, layout) -> int:
    """Map score + structural signals to maturity level."""
    if layout.has_domain and layout.has_value_objects and layout.has_dtos:
        return 5
    if layout.has_domain and (layout.has_dtos or layout.has_value_objects):
        return 4
    if layout.has_modules or (layout.has_repositories and layout.has_actions):
        return 3
    if layout.has_services:
        return 2
    if score >= 10:
        return 1
    return 0
