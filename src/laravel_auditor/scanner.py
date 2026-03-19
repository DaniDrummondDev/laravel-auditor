"""
Laravel Project Scanner
Reads the filesystem and extracts structural metadata from a Laravel project.
No AI involved — pure static analysis.
"""

import os
import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────

@dataclass
class PhpClass:
    path: str
    relative_path: str
    class_name: str
    namespace: str
    layer: str          # controller | model | service | repository | action | domain | other
    uses: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    method_count: int = 0
    line_count: int = 0
    # Smell indicators
    has_db_calls: bool = False
    has_auth_calls: bool = False
    has_request_injection: bool = False
    has_session_calls: bool = False
    eloquent_relationships: list[str] = field(default_factory=list)
    relationship_count: int = 0
    has_business_logic_keywords: bool = False


@dataclass
class DirectoryLayout:
    has_services: bool = False
    has_repositories: bool = False
    has_actions: bool = False
    has_domain: bool = False
    has_modules: bool = False
    has_dtos: bool = False
    has_value_objects: bool = False
    has_events: bool = False
    has_jobs: bool = False
    has_form_requests: bool = False
    has_resources: bool = False
    has_policies: bool = False
    domain_paths: list[str] = field(default_factory=list)
    module_paths: list[str] = field(default_factory=list)
    all_folders: list[str] = field(default_factory=list)


@dataclass
class LaravelProject:
    root_path: str
    layout: DirectoryLayout
    classes: list[PhpClass] = field(default_factory=list)
    composer_name: str = "unknown"
    laravel_version: str = "unknown"

    @property
    def controllers(self) -> list[PhpClass]:
        return [c for c in self.classes if c.layer == "controller"]

    @property
    def models(self) -> list[PhpClass]:
        return [c for c in self.classes if c.layer == "model"]

    @property
    def services(self) -> list[PhpClass]:
        return [c for c in self.classes if c.layer == "service"]

    @property
    def repositories(self) -> list[PhpClass]:
        return [c for c in self.classes if c.layer == "repository"]

    @property
    def actions(self) -> list[PhpClass]:
        return [c for c in self.classes if c.layer == "action"]

    @property
    def domain_classes(self) -> list[PhpClass]:
        return [c for c in self.classes if c.layer == "domain"]


# ─────────────────────────────────────────────
# Regex patterns
# ─────────────────────────────────────────────

RE_CLASS = re.compile(r'\bclass\s+(\w+)', re.MULTILINE)
RE_NAMESPACE = re.compile(r'^namespace\s+([\w\\]+);', re.MULTILINE)
RE_USE = re.compile(r'^use\s+([\w\\]+);', re.MULTILINE)
RE_METHOD = re.compile(r'(public|protected|private)\s+function\s+(\w+)', re.MULTILINE)
RE_DB = re.compile(r'\bDB::', re.MULTILINE)
RE_AUTH = re.compile(r'\bAuth::', re.MULTILINE)
RE_SESSION = re.compile(r'\bSession::|session\(\)', re.MULTILINE)
RE_REQUEST_INJECT = re.compile(r'Illuminate\\Http\\Request|use Request', re.MULTILINE)
RE_RELATIONSHIP = re.compile(
    r'public\s+function\s+\w+\s*\(\s*\)[^{]*\{[^}]*\b(hasMany|hasOne|belongsTo|belongsToMany|hasManyThrough|morphTo|morphMany|morphOne)\s*\(',
    re.DOTALL
)
RE_BUSINESS_KEYWORDS = re.compile(
    r'\b(calculateTotal|processOrder|sendEmail|chargeCard|validatePayment|applyDiscount|'
    r'generateInvoice|updateStatus|assignRole|processPayment)\b',
    re.IGNORECASE
)

ELOQUENT_RELATIONSHIP_NAMES = [
    'hasMany', 'hasOne', 'belongsTo', 'belongsToMany',
    'hasManyThrough', 'morphTo', 'morphMany', 'morphOne',
    'hasOneThrough', 'morphToMany', 'morphedByMany'
]


# ─────────────────────────────────────────────
# Layer classification
# ─────────────────────────────────────────────

def classify_layer(relative_path: str, class_name: str, namespace: str) -> str:
    rp = relative_path.replace("\\", "/").lower()
    ns = namespace.lower()
    cn = class_name.lower()

    if "http/controllers" in rp or cn.endswith("controller"):
        return "controller"
    if "app/models" in rp or "models/" in rp or (
        "eloquent" in ns or (not any(x in rp for x in ["services", "repositories", "actions", "domain"]) and cn[0].isupper() and "controller" not in cn and "service" not in cn)
    ):
        # Only classify as model if actually in models dir
        if "models" in rp:
            return "model"
    if "services" in rp or cn.endswith("service"):
        return "service"
    if "repositories" in rp or cn.endswith("repository") or cn.endswith("repo"):
        return "repository"
    if "actions" in rp or cn.endswith("action"):
        return "action"
    if any(x in rp for x in ["domain/", "/domain/", "domains/", "/domains/"]):
        return "domain"
    if "modules/" in rp or "/module/" in rp:
        return "module"

    return "other"


# ─────────────────────────────────────────────
# PHP file parser
# ─────────────────────────────────────────────

def parse_php_file(abs_path: str, root_path: str) -> Optional[PhpClass]:
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return None

    class_match = RE_CLASS.search(content)
    if not class_match:
        return None

    class_name = class_match.group(1)
    ns_match = RE_NAMESPACE.search(content)
    namespace = ns_match.group(1) if ns_match else ""

    uses = RE_USE.findall(content)
    methods = [m.group(2) for m in RE_METHOD.finditer(content)]
    method_count = len(methods)
    line_count = content.count('\n')

    relative_path = os.path.relpath(abs_path, root_path)
    layer = classify_layer(relative_path, class_name, namespace)

    # Relationships
    rel_matches = []
    for name in ELOQUENT_RELATIONSHIP_NAMES:
        rel_matches += re.findall(rf'\b{name}\b', content)

    # Business logic detection (for non-domain layers — smell if in wrong place)
    has_biz = bool(RE_BUSINESS_KEYWORDS.search(content))

    return PhpClass(
        path=abs_path,
        relative_path=relative_path,
        class_name=class_name,
        namespace=namespace,
        layer=layer,
        uses=uses,
        methods=methods,
        method_count=method_count,
        line_count=line_count,
        has_db_calls=bool(RE_DB.search(content)),
        has_auth_calls=bool(RE_AUTH.search(content)),
        has_request_injection=bool(RE_REQUEST_INJECT.search(content)),
        has_session_calls=bool(RE_SESSION.search(content)),
        eloquent_relationships=list(set(rel_matches)),
        relationship_count=len(rel_matches),
        has_business_logic_keywords=has_biz,
    )


# ─────────────────────────────────────────────
# Directory layout scanner
# ─────────────────────────────────────────────

def scan_directory_layout(root_path: str) -> DirectoryLayout:
    layout = DirectoryLayout()
    all_folders = []

    for dirpath, dirnames, _ in os.walk(root_path):
        # Skip vendor, node_modules, .git, storage/logs
        dirnames[:] = [d for d in dirnames if d not in (
            'vendor', 'node_modules', '.git', 'storage', '.idea', '__pycache__'
        )]
        rel = os.path.relpath(dirpath, root_path).replace("\\", "/")
        all_folders.append(rel)

    layout.all_folders = all_folders
    rl = [f.lower() for f in all_folders]

    layout.has_services = any("services" in f for f in rl)
    layout.has_repositories = any("repositor" in f for f in rl)
    layout.has_actions = any("/actions" in f or f.endswith("actions") for f in rl)
    layout.has_dtos = any("dto" in f for f in rl)
    layout.has_value_objects = any("valueobject" in f or "value_object" in f for f in rl)
    layout.has_events = any("/events" in f or f.endswith("events") for f in rl)
    layout.has_jobs = any("/jobs" in f or f.endswith("jobs") for f in rl)
    layout.has_form_requests = any("requests" in f for f in rl)
    layout.has_resources = any("resources" in f and "http" in f for f in rl)
    layout.has_policies = any("polic" in f for f in rl)

    domain_like = [f for f in all_folders if any(
        x in f.lower() for x in ["/domain", "/domains", "src/domain"]
    )]
    module_like = [f for f in all_folders if any(
        x in f.lower() for x in ["/modules", "/module", "src/modules"]
    )]

    layout.has_domain = bool(domain_like)
    layout.has_modules = bool(module_like)
    layout.domain_paths = domain_like[:10]
    layout.module_paths = module_like[:10]

    return layout


# ─────────────────────────────────────────────
# Composer.json reader
# ─────────────────────────────────────────────

def read_composer(root_path: str) -> tuple[str, str]:
    composer_path = os.path.join(root_path, "composer.json")
    try:
        with open(composer_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        name = data.get("name", "unknown")
        laravel_version = (
            data.get("require", {}).get("laravel/framework", "unknown")
        )
        return name, laravel_version
    except Exception:
        return "unknown", "unknown"


# ─────────────────────────────────────────────
# Main scanner entry point
# ─────────────────────────────────────────────

def scan_project(project_path: str, max_files: int = 500) -> LaravelProject:
    root = os.path.abspath(project_path)
    if not os.path.isdir(root):
        raise ValueError(f"Path does not exist or is not a directory: {root}")

    layout = scan_directory_layout(root)
    composer_name, laravel_version = read_composer(root)

    classes: list[PhpClass] = []
    count = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (
            'vendor', 'node_modules', '.git', 'storage', '.idea', '__pycache__'
        )]
        for fname in filenames:
            if not fname.endswith('.php'):
                continue
            if count >= max_files:
                break
            abs_path = os.path.join(dirpath, fname)
            php_class = parse_php_file(abs_path, root)
            if php_class:
                classes.append(php_class)
                count += 1

    return LaravelProject(
        root_path=root,
        layout=layout,
        classes=classes,
        composer_name=composer_name,
        laravel_version=laravel_version,
    )
