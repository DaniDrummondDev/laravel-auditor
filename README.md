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

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/laravel-auditor.git
cd laravel-auditor
```

### 2. Criar e ativar o ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -e .
```

> **Nota:** Não use `--break-system-packages`. Sempre instale dentro do venv.

### 4. Registrar no Claude Code (global — funciona em qualquer projeto)

Use `--` para separar as flags do `claude` dos argumentos do comando:

```bash
claude mcp add --scope user laravel-auditor -- /caminho/completo/para/laravel-auditor/.venv/bin/python -m laravel_auditor
```
> **Importante:** Use o caminho absoluto do Python do venv. Isso garante que o Claude Code
> encontre o interpretador correto com todas as dependências instaladas.

### 5. (Opcional) Com a API key para insights com IA

```bash
claude mcp add --scope user laravel-auditor \
  --env ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -- /caminho/completo/para/laravel-auditor/.venv/bin/python -m laravel_auditor
```

> **ANTHROPIC_API_KEY** é necessária apenas para os AI insights (roadmap gerado por IA).
> Sem ela, o auditor ainda funciona normalmente (análise estática).

### 6. Verificar a instalação

```bash
claude mcp list
```

Deve aparecer: `laravel-auditor: ... ✓ Connected`

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
source .venv/bin/activate
pip install -e .
```

Depois reinicie o Claude Code para recarregar o MCP server.
