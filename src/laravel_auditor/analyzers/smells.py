"""
Laravel Code Smell Analyzer
Detects architectural anti-patterns specific to Laravel projects.
"""

from dataclasses import dataclass
from ..scanner import LaravelProject, PhpClass


@dataclass
class Smell:
    type: str
    severity: str           # critical | warning | info
    file: str
    class_name: str
    detail: str
    recommendation: str


@dataclass
class SmellReport:
    smells: list[Smell]
    critical_count: int
    warning_count: int
    info_count: int
    summary: dict[str, int]  # smell_type -> count


def analyze_smells(project: LaravelProject) -> SmellReport:
    smells: list[Smell] = []

    for cls in project.classes:
        smells += _check_fat_controller(cls)
        smells += _check_fat_model(cls)
        smells += _check_db_in_wrong_layer(cls)
        smells += _check_auth_in_domain(cls)
        smells += _check_request_in_service(cls)
        smells += _check_service_god_class(cls)
        smells += _check_session_in_domain(cls)

    critical = sum(1 for s in smells if s.severity == "critical")
    warning = sum(1 for s in smells if s.severity == "warning")
    info = sum(1 for s in smells if s.severity == "info")

    summary: dict[str, int] = {}
    for s in smells:
        summary[s.type] = summary.get(s.type, 0) + 1

    return SmellReport(
        smells=smells,
        critical_count=critical,
        warning_count=warning,
        info_count=info,
        summary=summary,
    )


# ─────────────────────────────────────────────
# Individual checks
# ─────────────────────────────────────────────

def _check_fat_controller(cls: PhpClass) -> list[Smell]:
    if cls.layer != "controller":
        return []
    smells = []

    # Too many methods
    if cls.method_count > 15:
        smells.append(Smell(
            type="fat_controller",
            severity="critical",
            file=cls.relative_path,
            class_name=cls.class_name,
            detail=f"{cls.method_count} métodos públicos — Controller fazendo mais do que deveria",
            recommendation="Extrair lógica de negócio para Services ou Actions. Controller deve apenas orquestrar Request → Response.",
        ))
    elif cls.method_count > 8:
        smells.append(Smell(
            type="fat_controller",
            severity="warning",
            file=cls.relative_path,
            class_name=cls.class_name,
            detail=f"{cls.method_count} métodos — Controller crescendo demais",
            recommendation="Considerar extrair casos de uso específicos para Actions ou Services.",
        ))

    # DB in controller = business logic inside
    if cls.has_db_calls and cls.method_count > 3:
        smells.append(Smell(
            type="db_in_controller",
            severity="critical",
            file=cls.relative_path,
            class_name=cls.class_name,
            detail="DB:: detectado diretamente no Controller",
            recommendation="Mover queries para Repository ou Service. Controller não deve conhecer detalhes de persistência.",
        ))

    return smells


def _check_fat_model(cls: PhpClass) -> list[Smell]:
    if cls.layer != "model":
        return []
    smells = []

    if cls.relationship_count > 10:
        smells.append(Smell(
            type="fat_model",
            severity="warning",
            file=cls.relative_path,
            class_name=cls.class_name,
            detail=f"{cls.relationship_count} relacionamentos Eloquent — Model com muitas responsabilidades",
            recommendation="Considerar quebrar em Aggregates menores ou usar Value Objects para grupos de atributos.",
        ))

    if cls.has_business_logic_keywords and cls.method_count > 5:
        smells.append(Smell(
            type="fat_model",
            severity="warning",
            file=cls.relative_path,
            class_name=cls.class_name,
            detail="Model contém lógica de negócio (métodos que não são getters/relacionamentos)",
            recommendation="Extrair regras de negócio para Services ou Domain Objects. Model deve ser responsável por persistência e estrutura.",
        ))

    if cls.line_count > 400:
        smells.append(Smell(
            type="fat_model",
            severity="warning",
            file=cls.relative_path,
            class_name=cls.class_name,
            detail=f"Model com {cls.line_count} linhas — muito grande",
            recommendation="Analisar responsabilidades e extrair Traits, Concerns ou classes separadas.",
        ))

    return smells


def _check_db_in_wrong_layer(cls: PhpClass) -> list[Smell]:
    if cls.layer not in ("service", "domain", "action"):
        return []
    if not cls.has_db_calls:
        return []

    return [Smell(
        type="db_in_service",
        severity="warning",
        file=cls.relative_path,
        class_name=cls.class_name,
        detail=f"DB:: usado diretamente em {cls.layer} — infraestrutura vazando para aplicação",
        recommendation="Extrair queries para um Repository. Services devem depender de contratos (interfaces), não de DB:: direto.",
    )]


def _check_auth_in_domain(cls: PhpClass) -> list[Smell]:
    if cls.layer not in ("service", "domain", "repository", "action"):
        return []
    if not cls.has_auth_calls:
        return []

    return [Smell(
        type="auth_in_domain",
        severity="warning",
        file=cls.relative_path,
        class_name=cls.class_name,
        detail=f"Auth:: detectado em {cls.layer} — dependência de infraestrutura no domínio",
        recommendation="Injetar o usuário como parâmetro ou usar um serviço de contexto. Domain/Services não devem depender de Auth:: diretamente.",
    )]


def _check_request_in_service(cls: PhpClass) -> list[Smell]:
    if cls.layer not in ("service", "domain", "repository"):
        return []
    if not cls.has_request_injection:
        return []

    return [Smell(
        type="request_in_service",
        severity="critical",
        file=cls.relative_path,
        class_name=cls.class_name,
        detail="Illuminate\\Http\\Request injetado em Service/Domain — HTTP vazando para lógica de negócio",
        recommendation="Extrair os dados necessários no Controller e passar como DTO ou parâmetros simples. Service não deve conhecer HTTP.",
    )]


def _check_service_god_class(cls: PhpClass) -> list[Smell]:
    if cls.layer != "service":
        return []
    smells = []

    if cls.line_count > 600:
        smells.append(Smell(
            type="god_service",
            severity="critical",
            file=cls.relative_path,
            class_name=cls.class_name,
            detail=f"Service com {cls.line_count} linhas — God Class",
            recommendation="Dividir em múltiplos Services ou Actions com responsabilidades únicas (Single Responsibility Principle).",
        ))
    elif cls.method_count > 15:
        smells.append(Smell(
            type="god_service",
            severity="warning",
            file=cls.relative_path,
            class_name=cls.class_name,
            detail=f"Service com {cls.method_count} métodos — responsabilidades demais",
            recommendation="Cada Service deve ter um propósito claro. Considerar Actions para operações específicas.",
        ))

    return smells


def _check_session_in_domain(cls: PhpClass) -> list[Smell]:
    if cls.layer not in ("service", "domain", "repository"):
        return []
    if not cls.has_session_calls:
        return []

    return [Smell(
        type="session_in_domain",
        severity="warning",
        file=cls.relative_path,
        class_name=cls.class_name,
        detail=f"Session:: detectado em {cls.layer} — estado HTTP no domínio",
        recommendation="Session é infraestrutura HTTP. Passar dados necessários como parâmetros ou usar contexto de aplicação.",
    )]
