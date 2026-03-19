# 🔍 Laravel Auditor — MCP Server para Claude Code

Auditor arquitetural para qualquer projeto Laravel. Funciona de **MVC bagunçado** até **DDD bem aplicado**.

> Não julga. Diagnostica evolução.

---

## 📊 Modelo de Maturidade

| Nível | Label | Descrição |
|-------|-------|-----------|
| 0 | Código Caótico | Controllers + Models com tudo |
| 1 | MVC Padrão Laravel | Separação básica |
| 2 | Service Layer | Lógica de negócio nos Services |
| 3 | Modularização Parcial | Actions, Repos, módulos |
| 4 | DDD Parcial | Domain folder, DTOs, VOs |
| 5 | DDD Bem Aplicado | Aggregates, Events, Application layer |

---

## 🚀 Instalação

### 1. Instalar dependências

```bash
cd laravel-auditor
pip install -e . --break-system-packages
```

### 2. Registrar no Claude Code (global — funciona em qualquer projeto)

```bash
claude mcp add --scope user laravel-auditor python -m laravel_auditor
```

> **ANTHROPIC_API_KEY** precisa estar no ambiente para os AI insights.
> Sem ela, o auditor ainda funciona (análise estática), mas sem o roadmap gerado por IA.

### 3. (Opcional) Com a API key configurada

```bash
claude mcp add --scope user laravel-auditor \
  --env ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  python -m laravel_auditor
```

---

## 🛠️ Tools Disponíveis

### `audit_laravel_project`
Auditoria completa com IA. Gera relatório Markdown completo.

```
Parâmetros:
- project_path (string): caminho para o projeto Laravel
- use_ai (boolean): usar IA para insights (padrão: true)
```

### `analyze_laravel_structure`
Análise estrutural rápida — sem IA.

```
Parâmetros:
- project_path (string): caminho para o projeto Laravel
```

### `detect_laravel_smells`
Detecta code smells específicos de Laravel.

```
Parâmetros:
- project_path (string): caminho para o projeto Laravel
```

### `infer_laravel_domains`
Infere bounded contexts mesmo sem DDD explícito.

```
Parâmetros:
- project_path (string): caminho para o projeto Laravel
```

---

## 💬 Uso no Claude Code

```
# Auditoria completa
"Audita o projeto Laravel em /home/daniel/projetos/meu-app"

# Estrutura rápida
"Analisa a estrutura do projeto em ~/projetos/legado"

# Só os smells
"Detecta code smells em /var/www/projeto"

# Só os domínios
"Infere os domínios do projeto em ~/projetos/social-media"
```

---

## 🧱 Estrutura do Projeto

```
laravel-auditor/
├── src/laravel_auditor/
│   ├── server.py           # MCP Server (entry point)
│   ├── scanner.py          # PHP file scanner (puro, sem IA)
│   ├── maturity.py         # Modelo de maturidade (heurísticas)
│   ├── report.py           # Formatador de relatório Markdown
│   ├── analyzers/
│   │   ├── smells.py       # Code smell detector
│   │   └── domains.py      # Domain inference
│   └── agents/
│       └── auditor.py      # Orquestrador + Claude API
└── pyproject.toml
```

---

## 🔄 Atualizar

```bash
cd laravel-auditor
git pull
pip install -e . --break-system-packages
# Reiniciar Claude Code para recarregar o MCP server
```
