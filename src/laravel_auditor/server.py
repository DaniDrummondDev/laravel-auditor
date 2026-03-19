"""
Laravel Auditor — MCP Server
Exposes 4 tools to Claude Code for auditing any Laravel project.
"""

import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .scanner import scan_project
from .maturity import calculate_maturity
from .analyzers.smells import analyze_smells
from .analyzers.domains import infer_domains
from .agents.auditor import run_audit
from .report import format_report

app = Server("laravel-auditor")


# ─────────────────────────────────────────────
# Tool registry
# ─────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="audit_laravel_project",
            description=(
                "Audita um projeto Laravel completo. Analisa maturidade arquitetural (nível 0–5), "
                "infere domínios/bounded contexts, detecta code smells e gera um roadmap de evolução. "
                "Usa IA para insights profundos. Use quando quiser um diagnóstico completo do projeto."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Caminho absoluto ou relativo para a raiz do projeto Laravel"
                    },
                    "use_ai": {
                        "type": "boolean",
                        "description": "Se deve usar IA para enriquecer o relatório (padrão: true)",
                        "default": True
                    }
                },
                "required": ["project_path"]
            }
        ),
        Tool(
            name="analyze_laravel_structure",
            description=(
                "Analisa apenas a estrutura do projeto Laravel — sem IA. "
                "Retorna o nível de maturidade, evidências encontradas e o que está faltando. "
                "Rápido e leve, ideal para uma visão inicial."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Caminho para a raiz do projeto Laravel"
                    }
                },
                "required": ["project_path"]
            }
        ),
        Tool(
            name="detect_laravel_smells",
            description=(
                "Detecta code smells específicos de Laravel: Fat Controllers, Fat Models, "
                "God Services, DB:: em camada errada, Auth:: no domínio, Request em Services, etc. "
                "Retorna lista priorizada com recomendações concretas."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Caminho para a raiz do projeto Laravel"
                    }
                },
                "required": ["project_path"]
            }
        ),
        Tool(
            name="infer_laravel_domains",
            description=(
                "Infere bounded contexts/domínios do projeto Laravel mesmo sem DDD explícito. "
                "Agrupa classes por contexto (Order, Payment, User, etc.), avalia acoplamento "
                "entre contextos e detecta problemas cross-boundary."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Caminho para a raiz do projeto Laravel"
                    }
                },
                "required": ["project_path"]
            }
        ),
    ]


# ─────────────────────────────────────────────
# Tool handlers
# ─────────────────────────────────────────────

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    project_path = arguments.get("project_path", ".")

    try:
        project = scan_project(project_path)
    except ValueError as e:
        return [TextContent(type="text", text=f"❌ Erro ao escanear projeto: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Erro inesperado ao escanear: {e}")]

    # ── Full audit
    if name == "audit_laravel_project":
        use_ai = arguments.get("use_ai", True)
        try:
            report = run_audit(project, use_ai=use_ai)
            output = format_report(report)
        except Exception as e:
            output = f"❌ Erro durante auditoria: {e}"
        return [TextContent(type="text", text=output)]

    # ── Structure only
    elif name == "analyze_laravel_structure":
        maturity = calculate_maturity(project)
        layout = project.layout

        result = {
            "project": project.composer_name,
            "laravel_version": project.laravel_version,
            "maturity_level": maturity.level,
            "maturity_label": maturity.label,
            "score": maturity.score,
            "description": maturity.description,
            "evidence": maturity.evidence,
            "missing": maturity.missing,
            "class_counts": {
                "controllers": len(project.controllers),
                "models": len(project.models),
                "services": len(project.services),
                "repositories": len(project.repositories),
                "actions": len(project.actions),
                "domain_classes": len(project.domain_classes),
                "total": len(project.classes),
            },
            "layout": {
                "has_services": layout.has_services,
                "has_repositories": layout.has_repositories,
                "has_actions": layout.has_actions,
                "has_domain": layout.has_domain,
                "has_modules": layout.has_modules,
                "has_dtos": layout.has_dtos,
                "has_value_objects": layout.has_value_objects,
                "has_events": layout.has_events,
                "has_form_requests": layout.has_form_requests,
            }
        }

        # Format nicely
        lines = [
            f"## 📊 Estrutura: {project.composer_name}",
            f"",
            f"**Nível de maturidade:** {maturity.level} — {maturity.label} (score: {maturity.score}/100)",
            f"",
            f"> {maturity.description}",
            f"",
            f"**Classes encontradas:**",
            f"- Controllers: {result['class_counts']['controllers']}",
            f"- Models: {result['class_counts']['models']}",
            f"- Services: {result['class_counts']['services']}",
            f"- Repositories: {result['class_counts']['repositories']}",
            f"- Actions: {result['class_counts']['actions']}",
            f"- Total escaneado: {result['class_counts']['total']}",
            f"",
            f"**Evidências:**",
        ]
        for ev in maturity.evidence:
            lines.append(f"- ✅ {ev}")
        lines.append("")
        lines.append("**Ausências:**")
        for miss in maturity.missing:
            lines.append(f"- ❌ {miss}")

        return [TextContent(type="text", text="\n".join(lines))]

    # ── Code smells
    elif name == "detect_laravel_smells":
        smells = analyze_smells(project)

        lines = [
            f"## 🧪 Code Smells: {project.composer_name}",
            f"",
            f"🔴 Críticos: **{smells.critical_count}** | 🟡 Warnings: **{smells.warning_count}** | 🔵 Info: **{smells.info_count}**",
            "",
        ]

        if not smells.smells:
            lines.append("_Nenhum smell detectado. Bom sinal!_")
        else:
            for severity in ("critical", "warning", "info"):
                s_list = [s for s in smells.smells if s.severity == severity]
                if not s_list:
                    continue
                emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}[severity]
                lines.append(f"### {emoji} {severity.capitalize()} ({len(s_list)})")
                for smell in s_list:
                    lines += [
                        f"**`{smell.class_name}`** — `{smell.file}`",
                        f"> {smell.detail}",
                        f"💡 {smell.recommendation}",
                        "",
                    ]

        return [TextContent(type="text", text="\n".join(lines))]

    # ── Domain inference
    elif name == "infer_laravel_domains":
        domains = infer_domains(project)

        lines = [
            f"## 🧩 Domínios Inferidos: {project.composer_name}",
            f"",
            f"**{len(domains.domains)} domínio(s) identificado(s)**",
            "",
        ]

        if not domains.domains:
            lines.append("_Nenhum domínio claro inferido. O projeto pode estar em nível 0-1 de maturidade._")
        else:
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            for d in domains.domains:
                re_ = risk_emoji.get(d.coupling_risk, "🔵")
                lines.append(f"### {re_} {d.name}")
                lines.append(f"- Classes: `{'`, `'.join(d.classes[:8])}`")
                lines.append(f"- Layers: {', '.join(d.layers_present)}")
                lines.append(f"- Acoplamento: **{d.coupling_risk}**")
                for note in d.coupling_notes:
                    lines.append(f"  - ⚠️ {note}")
                lines.append("")

        if domains.cross_context_issues:
            lines.append("### ⚠️ Problemas Cross-Context")
            for issue in domains.cross_context_issues:
                lines.append(f"- {issue}")

        return [TextContent(type="text", text="\n".join(lines))]

    else:
        return [TextContent(type="text", text=f"❌ Tool desconhecida: {name}")]


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

async def serve():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


def main():
    asyncio.run(serve())
