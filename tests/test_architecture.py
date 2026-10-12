"""AST static analysis architectural boundary tests.

Enforces:
1. Selectors contain pure reads and NEVER write to the database (no save, create, update, delete).
2. Views do not access the ORM (.objects) directly; they must call selectors or services.
3. Models do not contain OpenCV, requests, or Celery task calls.
4. AI Engine is stateless and defines zero Django ORM models.
"""
import ast
import os
from pathlib import Path
import pytest

APPS_DIR = Path(__file__).resolve().parent.parent / "apps"


def _get_python_files(pattern: str):
    return list(APPS_DIR.glob(f"*/{pattern}"))


def test_selectors_never_write():
    """Asserts no database write methods are invoked inside any selectors.py file."""
    selector_files = _get_python_files("selectors.py")
    assert len(selector_files) > 0, "No selectors.py files discovered in apps/"

    prohibited_methods = {
        "save",
        "create",
        "update",
        "delete",
        "bulk_create",
        "bulk_update",
        "update_or_create",
        "get_or_create",
    }

    violations = []
    for fpath in selector_files:
        tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check method calls like obj.save(), Model.objects.create()
                if isinstance(node.func, ast.Attribute) and node.func.attr in prohibited_methods:
                    violations.append(f"{fpath.name}:{node.lineno} calls prohibited write '{node.func.attr}'")

    assert not violations, f"Architectural violation: Selectors must be read-only:\n" + "\n".join(violations)


def test_views_do_not_touch_the_orm_directly():
    """Asserts no views.py file accesses '.objects' directly."""
    view_files = _get_python_files("views.py")
    assert len(view_files) > 0, "No views.py files discovered in apps/"

    violations = []
    for fpath in view_files:
        tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "objects":
                violations.append(f"{fpath.name}:{node.lineno} directly accesses '.objects'")

    assert not violations, (
        f"Architectural violation: Views must use selectors or services, not '.objects':\n"
        + "\n".join(violations)
    )


def test_models_contain_no_heavy_logic():
    """Asserts models.py contains no cv2, requests, or Celery triggers."""
    model_files = _get_python_files("models.py")
    assert len(model_files) > 0, "No models.py files discovered in apps/"

    prohibited_modules = {"cv2", "requests", "celery", "urllib"}

    violations = []
    for fpath in model_files:
        tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
        for node in ast.walk(tree):
            # Check prohibited imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in prohibited_modules:
                        violations.append(f"{fpath.name}:{node.lineno} imports '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in prohibited_modules:
                    violations.append(f"{fpath.name}:{node.lineno} imports from '{node.module}'")
            # Check calls to .delay()
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "delay":
                violations.append(f"{fpath.name}:{node.lineno} triggers Celery .delay()")

    assert not violations, (
        f"Architectural violation: Models must be pure schemas without heavy logic:\n"
        + "\n".join(violations)
    )


def test_ai_engine_is_stateless():
    """Asserts apps/ai_engine defines zero Django ORM models."""
    ai_engine_models = APPS_DIR / "ai_engine" / "models.py"
    if not ai_engine_models.exists():
        # Clean: no models.py file
        return

    tree = ast.parse(ai_engine_models.read_text(encoding="utf-8"), filename=str(ai_engine_models))
    model_classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Attribute) and base.attr == "Model":
                    model_classes.append(node.name)

    assert not model_classes, f"apps/ai_engine must be stateless but defines models: {model_classes}"
