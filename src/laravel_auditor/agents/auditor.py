"""
Laravel System Auditor Agent
Orchestrates all analyzers and uses Claude AI for deep insights.
"""

import os
from dataclasses import dataclass
from ..scanner import LaravelProject
from ..maturity import MaturityResult, calculate_maturity
from ..analyzers.smells import SmellReport, analyze_smells
from ..analyzers.domains import DomainMap, infer_domains


@dataclass
class AuditReport:
    project_name: str
    laravel_version: str
    maturity: MaturityResult
    smells: SmellReport
    domains: DomainMap
    ai_insights: str        # Claude-generated narrative
    roadmap: str            # Claude-generated roadmap


def run_audit(project: LaravelProject, use_ai: bool = True) -> AuditReport:
    """Run all analyzers and optionally enrich with AI insights."""

    maturity = calculate_maturity(project)
    smells = analyze_smells(project)
    domains = infer_domains(project)

    ai_insights = ""
    roadmap = ""

    if use_ai:
        try:
            context = _build_ai_context(project, maturity, smells, domains)
            ai_insights, roadmap = _call_claude(context)
        except Exception as e:
            ai_insights = f"⚠️ AI insights indisponíveis: {e}"
            roadmap = _generate_static_roadmap(maturity)
    else:
        roadmap = _generate_static_roadmap(maturity)

    return AuditReport(
        project_name=project.composer_name,
        laravel_version=project.laravel_version,
        maturity=maturity,
        smells=smells,
        domains=domains,
        ai_insights=ai_insights,
        roadmap=roadmap,
    )


def _build_ai_context(
    project: LaravelProject,
    maturity: MaturityResult,
    smells: SmellReport,
    domains: DomainMap,
) -> str:
    top_smells = smells.smells[:10]
    smell_lines = "\n".join(
        f"  [{s.severity.upper()}] {s.type} em {s.class_name}: {s.detail}"
        for s in top_smells
    )

    domain_lines = "\n".join(
        f"  - {d.name}: {len(d.classes)} classes, layers={d.layers_present}, risco={d.coupling_risk}"
        for d in domains.domains[:8]
    )

    layout = project.layout

    return f"""
Projeto Laravel: {project.composer_name}
Versão Laravel: {project.laravel_version}

MÉTRICAS ESTRUTURAIS:
- Controllers: {len(project.controllers)}
- Models: {len(project.models)}
- Services: {len(project.services)}
- Repositories: {len(project.repositories)}
- Actions: {len(project.actions)}
- Domain classes: {len(project.domain_classes)}
- Total de classes analisadas: {len(project.classes)}

LAYOUT DETECTADO:
- has_services: {layout.has_services}
- has_repositories: {layout.has_repositories}
- has_actions: {layout.has_actions}
- has_domain: {layout.has_domain}
- has_modules: {layout.has_modules}
- has_dtos: {layout.has_dtos}
- has_value_objects: {layout.has_value_objects}
- has_events: {layout.has_events}
- has_form_requests: {layout.has_form_requests}

MATURIDADE:
- Nível: {maturity.level} — {maturity.label}
- Score: {maturity.score}/100
- Evidências: {', '.join(maturity.evidence[:5])}
- Ausências: {', '.join(maturity.missing[:5])}

DOMÍNIOS INFERIDOS:
{domain_lines if domain_lines else "  Nenhum domínio claro detectado"}

PROBLEMAS DE CROSS-CONTEXT:
{chr(10).join('  - ' + i for i in domains.cross_context_issues) if domains.cross_context_issues else '  Nenhum detectado'}

CODE SMELLS (top 10):
{smell_lines if smell_lines else "  Nenhum smell crítico detectado"}

RESUMO DE SMELLS:
- Críticos: {smells.critical_count}
- Warnings: {smells.warning_count}
- Tipos: {dict(list(smells.summary.items())[:6])}
""".strip()


def _call_claude(context: str) -> tuple[str, str]:
    """Call Claude API for AI-powered insights."""
    import anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    SYSTEM = """Você é um arquiteto de software especialista em Laravel e DDD.
Analisa projetos Laravel e fornece diagnósticos pragmáticos — não acadêmicos.

Regras fundamentais:
- NUNCA diga "o projeto está errado por não usar DDD"
- SEMPRE diga "o projeto está no nível X → próximo passo é Y"
- Seja pragmático: sugira passos incrementais, não rewrites
- Use exemplos concretos baseados nos dados fornecidos
- Escreva em português do Brasil
- Seja objetivo e direto, sem floreios

Formato da resposta: JSON com dois campos:
{
  "insights": "análise narrativa dos principais pontos (3-5 parágrafos)",
  "roadmap": "roadmap em 3 fases (Curto/Médio/Longo prazo) com ações concretas"
}
Responda APENAS com o JSON, sem markdown ou texto extra."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Analise este projeto Laravel e gere insights + roadmap:\n\n{context}"
        }]
    )

    import json
    text = response.content[0].text.strip()
    # Strip markdown fences if present
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    data = json.loads(text)
    return data.get("insights", ""), data.get("roadmap", "")


def _generate_static_roadmap(maturity: MaturityResult) -> str:
    """Fallback roadmap without AI, based purely on maturity level."""
    roadmaps = {
        0: """**Fase 1 — Organização básica (Curto prazo)**
- Mover lógica do Controller para Services
- Criar Form Requests para validação
- Separar queries em métodos no Model ou Scope

**Fase 2 — Separação de responsabilidades (Médio prazo)**
- Introduzir Services para toda lógica de negócio
- Criar Repositories para acesso a dados
- Remover DB:: e Auth:: dos Controllers

**Fase 3 — Estrutura sólida (Longo prazo)**
- Introduzir DTOs para transferência de dados
- Organizar por contexto/módulo
- Considerar Events para operações cross-context""",

        1: """**Fase 1 — Adicionar Services (Curto prazo)**
- Extrair regras de negócio dos Controllers para Services
- Criar Form Requests para validação (se não existir)
- Padronizar nomenclatura

**Fase 2 — Separar persistência (Médio prazo)**
- Introduzir Repositories (ou Query Objects)
- Criar Actions para operações simples e isoladas
- Remover DB:: dos Controllers

**Fase 3 — Modularizar (Longo prazo)**
- Agrupar por domínio de negócio
- Introduzir DTOs
- Considerar módulos por contexto""",

        2: """**Fase 1 — Fortalecer Services (Curto prazo)**
- Remover Request dos Services
- Remover Auth:: dos Services (injetar usuário)
- Criar DTOs para transferência entre Controller → Service

**Fase 2 — Introduzir Repositories (Médio prazo)**
- Abstrair acesso a dados dos Services
- Criar interfaces para os Repositories
- Adicionar Actions para operações específicas

**Fase 3 — Modularizar por domínio (Longo prazo)**
- Agrupar classes por Bounded Context
- Introduzir Domain Events
- Considerar Value Objects para conceitos do domínio""",

        3: """**Fase 1 — Consolidar módulos (Curto prazo)**
- Garantir que módulos não se acessem diretamente
- Criar DTOs para comunicação entre módulos
- Mapear Aggregates por módulo

**Fase 2 — Introduzir DDD leve (Médio prazo)**
- Identificar Aggregates root em cada módulo
- Criar Value Objects para atributos complexos
- Introduzir Domain Events para operações cross-module

**Fase 3 — DDD completo (Longo prazo)**
- Camada de Application (Use Cases)
- Domain Services para lógica cross-aggregate
- Infraestrutura separada por contrato""",

        4: """**Fase 1 — Completar padrões DDD (Curto prazo)**
- Garantir invariantes nos Aggregates
- Value Objects para todos primitivos do domínio
- Domain Events para todas operações de negócio

**Fase 2 — Camada de Application (Médio prazo)**
- Use Cases / Command Handlers explícitos
- CQRS leve (separar reads de writes)
- Testes unitários nos Aggregates

**Fase 3 — Excelência arquitetural (Longo prazo)**
- Event Sourcing onde aplicável
- Ports & Adapters (Hexagonal)
- Bounded Contexts com contratos explícitos""",

        5: """**Projeto em nível avançado — manutenção e evolução:**
- Revisar se os Aggregates ainda refletem o domínio atual
- Garantir que Domain Events cobrem todos os side effects
- Manter testes de unidade nos Aggregates
- Revisar acoplamento entre Bounded Contexts periodicamente""",
    }

    return roadmaps.get(maturity.level, roadmaps[0])
