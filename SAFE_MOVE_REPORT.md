# Safe Move Report - Warungio Marketplace

This document lists the completed safe move operations and files left in place to verify compliance with constraints.

## Completed SAFE Relocations

| Original Path | Reorganized Path | Category | Status |
| :--- | :--- | :--- | :--- |
| `ARCHITECTURE.md` | `docs/architecture/ARCHITECTURE.md` | Documentation | **MOVED** |
| `Database.md` | `docs/database/Database.md` | Documentation | **MOVED** |
| `DEPLOYMENT.md` | `docs/deployment/DEPLOYMENT.md` | Documentation | **MOVED** |
| `CLEANUP-PLAN.md` | `docs/CLEANUP-PLAN.md` | Documentation | **MOVED** |
| `Task_Roadmap.md` | `docs/Task_Roadmap.md` | Documentation | **MOVED** |
| `analisis-spec.md` | `docs/analisis-spec.md` | Documentation | **MOVED** |
| `warungio-spec.md` | `docs/warungio-spec.md` | Documentation | **MOVED** |
| `builds.txt` | `logs/builds.txt` | Logs | **MOVED** |
| `cloudrun_logs.txt` | `logs/cloudrun_logs.txt` | Logs | **MOVED** |
| `deploy_output.txt` | `logs/deploy_output.txt` | Logs | **MOVED** |
| `service_describe.txt`| `logs/service_describe.txt` | Logs | **MOVED** |
| `_fix_login.py` | `tools/_fix_login.py` | Utility Script | **MOVED** |
| `check_builds.py` | `tools/check_builds.py` | Utility Script | **MOVED** |
| `check_logs.py` | `tools/check_logs.py` | Utility Script | **MOVED** |
| `cleanup_assets.py` | `tools/cleanup_assets.py` | Utility Script | **MOVED** |
| `find_large_django.py`| `tools/find_large_django.py` | Utility Script | **MOVED** |
| `fix_assets.py` | `tools/fix_assets.py` | Utility Script | **MOVED** |
| `scaffold.bat` | `tools/scaffold.bat` | Utility Script | **MOVED** |
| `powershell.bat` | `tools/powershell.bat` | Runner Helper | **COPIED** |

---

## Files Left in Root (REVIEW REQUIRED / DO NOT MOVE)

The following files were left in the project root to guarantee runtime compatibility, local environment configurations, or runner stability:
- **`powershell.bat`** (Kept in root to allow the IDE environment runner to execute PowerShell commands successfully).
- **`deploy_run.py`** (Left in root to prevent disruption to any deployment/build hooks).
- **`describe_service.py`** (Left in root for service diagnostics).
- **`eval_settings.py`** (Left in root to support Django configuration tests).
- **`print_settings.py`** (Left in root to support Django config print tasks).
- **`backup_warungio.sql`** (Left in root as it was not part of the approved safe moves list).

---

## Non-Relocatable Configuration Directories (DO NOT TOUCH)
- **`/django_backend`** (Core Django codebase, static files, and templates).
- **`Dockerfile`, `docker-compose.yml`, `docker-entrypoint.sh`, `cloudrun.yaml`** (Docker and Cloud Run infrastructure specs).
- **`.env`, `.gitignore`, `.dockerignore`, `.gcloudignore`, `.hintrc`** (Environment and tool configurations).
- **`package.json`, `skills-lock.json`** (Dependency locks).
- **`/assets`, `/shared`, `/auth`, `/buyer`, `/seller`, `/home`, `/src`, `/backend`** (Runtime static resources, templates, and active codebases).
