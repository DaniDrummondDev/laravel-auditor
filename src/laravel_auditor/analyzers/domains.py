"""
Laravel Domain Inference
Infers bounded contexts from class names — even without explicit DDD structure.
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from ..scanner import LaravelProject, PhpClass


@dataclass
class InferredDomain:
    name: str
    classes: list[str]
    layers_present: list[str]
    coupling_risk: str          # low | medium | high
    coupling_notes: list[str]


@dataclass
class DomainMap:
    domains: list[InferredDomain]
    cross_context_issues: list[str]
    ungrouped_classes: list[str]


# Common domain keywords found in class names
DOMAIN_PREFIXES_SUFFIXES = [
    # E-commerce
    "Order", "Product", "Cart", "Checkout", "Inventory", "Catalog",
    "Payment", "Invoice", "Billing", "Subscription",
    # User management
    "User", "Auth", "Role", "Permission", "Profile", "Account", "Team",
    # Content
    "Post", "Article", "Comment", "Category", "Tag", "Media", "Upload",
    # Notifications
    "Notification", "Email", "Message", "Chat",
    # Scheduling
    "Schedule", "Booking", "Appointment", "Reservation",
    # Reporting
    "Report", "Analytics", "Dashboard", "Metric",
    # Social
    "Follow", "Like", "Share", "Feed",
    # Shipping/Delivery
    "Shipping", "Delivery", "Address", "Location",
    # Config
    "Setting", "Config", "Feature", "Flag",
]


def infer_domains(project: LaravelProject) -> DomainMap:
    groups: dict[str, list[PhpClass]] = defaultdict(list)
    ungrouped: list[str] = []

    for cls in project.classes:
        domain = _extract_domain(cls.class_name)
        if domain:
            groups[domain].append(cls)
        else:
            ungrouped.append(cls.class_name)

    domains = []
    for domain_name, classes in sorted(groups.items(), key=lambda x: -len(x[1])):
        layers = list(set(c.layer for c in classes))
        coupling_risk, coupling_notes = _assess_coupling(domain_name, classes, project)
        domains.append(InferredDomain(
            name=domain_name,
            classes=[c.class_name for c in classes],
            layers_present=layers,
            coupling_risk=coupling_risk,
            coupling_notes=coupling_notes,
        ))

    cross_issues = _detect_cross_context_issues(groups, project)

    return DomainMap(
        domains=domains,
        cross_context_issues=cross_issues,
        ungrouped_classes=ungrouped[:20],  # cap to avoid noise
    )


def _extract_domain(class_name: str) -> str | None:
    """Extract likely domain name from class name."""
    # Strip common layer suffixes
    stripped = re.sub(
        r'(Controller|Service|Repository|Repo|Request|Resource|Policy|'
        r'Observer|Event|Listener|Job|Notification|Factory|Seeder|Migration|'
        r'Action|DTO|ValueObject|VO|Aggregate|Command|Handler|Query)$',
        '',
        class_name
    )

    if not stripped or stripped == class_name and len(class_name) < 4:
        return None

    # Try to match known domain keywords
    for keyword in DOMAIN_PREFIXES_SUFFIXES:
        if stripped.startswith(keyword) or stripped == keyword:
            return keyword
        # Also check plurals
        if stripped.startswith(keyword + "s"):
            return keyword

    # If it's a clean PascalCase single word (likely a domain entity)
    if re.match(r'^[A-Z][a-z]+$', stripped) and len(stripped) > 3:
        return stripped

    # CamelCase like "SocialPost" → SocialPost
    if re.match(r'^[A-Z][a-zA-Z]+$', stripped) and len(stripped) > 4:
        return stripped

    return None


def _assess_coupling(
    domain_name: str,
    classes: list[PhpClass],
    project: LaravelProject
) -> tuple[str, list[str]]:
    notes = []
    risk = "low"

    # Check if this domain's classes import from other domains
    domain_class_names = {c.class_name for c in classes}
    other_domain_namespaces = []

    for cls in classes:
        for use in cls.uses:
            # Check if it imports from another domain
            parts = use.split("\\")
            for other_keyword in DOMAIN_PREFIXES_SUFFIXES:
                if other_keyword != domain_name and other_keyword in parts:
                    other_domain_namespaces.append(f"{cls.class_name} → {other_keyword}")
                    break

    if len(other_domain_namespaces) > 3:
        risk = "high"
        notes.append(f"Alto acoplamento: {domain_name} importa de outros {len(other_domain_namespaces)} contextos")
        notes += other_domain_namespaces[:3]
    elif other_domain_namespaces:
        risk = "medium"
        notes.append(f"Acoplamento moderado entre contextos: {', '.join(other_domain_namespaces[:2])}")

    # Check Auth/DB in domain classes
    domain_smells = [c for c in classes if c.has_auth_calls or c.has_db_calls]
    if domain_smells and any(c.layer in ("service", "domain") for c in domain_smells):
        notes.append(f"Infraestrutura vazando em {len(domain_smells)} classe(s) do contexto")
        if risk == "low":
            risk = "medium"

    return risk, notes


def _detect_cross_context_issues(
    groups: dict[str, list[PhpClass]],
    project: LaravelProject
) -> list[str]:
    issues = []
    # Detect models being used across domain boundaries via relationships
    for domain_name, classes in groups.items():
        models = [c for c in classes if c.layer == "model"]
        for model in models:
            if model.relationship_count > 6:
                issues.append(
                    f"{model.class_name} (domínio {domain_name}) tem {model.relationship_count} "
                    f"relacionamentos — possível God Aggregate ou boundary mal definido"
                )

    return issues
