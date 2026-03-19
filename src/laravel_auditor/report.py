"""
Report Formatter
Converts AuditReport into human-readable Markdown.
"""

from .agents.auditor import AuditReport


SEVERITY_EMOJI = {
    "critical": "🔴",
    "warning": "🟡",
    "info": "🔵",
}

LEVEL_EMOJI = ["💀", "🧱", "⚙️", "🧩", "🏗️", "🏛️"]
RISK_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🔴"}


def format_report(report: AuditReport) -> str:
    lines = []

    # ── Header
    lines += [
        f"# 🔍 Laravel Architecture Audit",
        f"",
        f"**Projeto:** `{report.project_name}`  ",
        f"**Laravel:** `{report.laravel_version}`",
        f"",
        "---",
        "",
    ]

    # ── 1. Diagnóstico Geral
    m = report.maturity
    level_emoji = LEVEL_EMOJI[min(m.level, 5)]
    lines += [
        "## 📊 1. Diagnóstico Geral",
        "",
        f"| Campo | Valor |",
        f"|-------|-------|",
        f"| Nível atual | {level_emoji} **{m.level} — {m.label}** |",
        f"| Score | `{m.score}/100` |",
        f"| Risco geral | {'🔴 Alto' if report.smells.critical_count > 3 else '🟡 Médio' if report.smells.critical_count > 0 else '🟢 Baixo'} |",
        "",
        f"> {m.description}",
        "",
        "**Evidências encontradas:**",
    ]
    for ev in m.evidence:
        lines.append(f"- ✅ {ev}")

    lines.append("")
    lines.append("**Ausências identificadas:**")
    for miss in m.missing:
        lines.append(f"- ❌ {miss}")
    lines += ["", "---", ""]

    # ── 2. Domínios Inferidos
    lines += [
        "## 🧩 2. Domínios Identificados",
        "",
    ]

    if report.domains.domains:
        for d in report.domains.domains:
            risk_e = RISK_EMOJI.get(d.coupling_risk, "🔵")
            lines.append(f"### {risk_e} {d.name}")
            lines.append(f"- **Classes:** {', '.join(d.classes[:6])}{'...' if len(d.classes) > 6 else ''}")
            lines.append(f"- **Layers:** {', '.join(d.layers_present)}")
            lines.append(f"- **Acoplamento:** {d.coupling_risk}")
            for note in d.coupling_notes:
                lines.append(f"  - ⚠️ {note}")
            lines.append("")
    else:
        lines.append("_Nenhum domínio claro detectado. Projeto provavelmente sem separação por contexto._")
        lines.append("")

    if report.domains.cross_context_issues:
        lines.append("**⚠️ Problemas de Cross-Context:**")
        for issue in report.domains.cross_context_issues:
            lines.append(f"- {issue}")
        lines.append("")

    lines += ["---", ""]

    # ── 3. Code Smells
    lines += [
        "## 🧪 3. Code Smells",
        "",
        f"| Severidade | Quantidade |",
        f"|-----------|-----------|",
        f"| 🔴 Críticos | {report.smells.critical_count} |",
        f"| 🟡 Warnings | {report.smells.warning_count} |",
        f"| 🔵 Info | {report.smells.info_count} |",
        "",
    ]

    if report.smells.smells:
        # Group by severity
        for severity in ("critical", "warning", "info"):
            s_list = [s for s in report.smells.smells if s.severity == severity]
            if not s_list:
                continue
            emoji = SEVERITY_EMOJI[severity]
            lines.append(f"### {emoji} {severity.capitalize()}")
            for smell in s_list:
                lines += [
                    f"**`{smell.class_name}`** (`{smell.file}`)",
                    f"> {smell.detail}",
                    f"💡 *{smell.recommendation}*",
                    "",
                ]
    else:
        lines.append("_Nenhum smell detectado estaticamente._")
        lines.append("")

    lines += ["---", ""]

    # ── 4. AI Insights
    if report.ai_insights:
        lines += [
            "## 🧠 4. Análise Inteligente",
            "",
            report.ai_insights,
            "",
            "---",
            "",
        ]

    # ── 5. Roadmap
    lines += [
        "## 🚀 5. Roadmap de Evolução",
        f"_Partindo do nível atual {m.level} → {m.level + 1 if m.level < 5 else 5}_",
        "",
        report.roadmap,
        "",
        "---",
        "",
        "_Gerado por **laravel-auditor** — MCP Server para Claude Code_",
    ]

    return "\n".join(lines)
