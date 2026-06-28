# Repository Cleanup Report - Warungio Marketplace

## Repository Metrics
*   **Total Folders**: 154 (excluding ignored system directories).
*   **Total Files**: 2,517 (excluding ignored system directories).
*   **Root Clutter Reduction**:
    *   **Root-level Files Before**: 36
    *   **Root-level Files Relocated**: 22
    *   **Root-level Files Remaining**: 14 (only configuration files, README, and runner compatibility files).

---

## Identified Organizational Problems & Resolutions

### 1. Root Clutter
- **Problem**: The root directory was littered with logs, batch scripts, single-use python debugging files, and markdown documents.
- **Resolution**: Documents were moved to `/docs`, logs to `/logs`, and maintenance tools to `/tools`.

### 2. Scattered Documentation
- **Problem**: Project roadmaps, analysis papers, and database models were stored directly in the root without structure.
- **Resolution**: Grouped under `/docs` inside specialized subdirectories (`architecture/`, `database/`, `deployment/`).

### 3. Displaced Diagnostic Logs
- **Problem**: Diagnostic text files from Cloud Run and local deployments were dumped in the root.
- **Resolution**: Relocated to the unified `/logs` folder.

### 4. Static Asset Duplication
- **Problem**: Identical image assets were duplicated across `/assets/images/`, `/django_backend/static/images/`, `/src/assets/images/`, and `/staticfiles/images/`.
- **Resolution**: Identified duplicates. Due to cross-referencing across pure HTML mockups and Django backend configurations, these files were preserved to maintain system compatibility.

---

## Duplicate Static Assets Audit

The following duplicate groups were identified (showing duplicates matching exactly in MD5 hash):

### Duplicated Placeholder / Empty Files (MD5: `d41d8cd98f00b204e9800998ecf8427e`)
- `backup_warungio.sql`
- `scaffold.bat`
- `.vscode/launch.json`
- Multiple placeholder images in `assets/images/`

### Duplicated Application Assets
- **av-ara.png, av-budi.png, av-kelvin.png, av-melinda.png, av-siti.png, av-stev.png**
  - Path 1: `assets/images/`
  - Path 2: `django_backend/static/images/`
  - Path 3: `django_backend/static/src/assets/images/`
  - Path 4: `src/assets/images/`
  - Path 5: `staticfiles/images/`
- **call.png, clock.png, shield.png, verified.png, google-playstore.png, appstore.png**
  - Path 1: `assets/images/`
  - Path 2: `django_backend/static/images/`
  - Path 3: `staticfiles/images/`

---

## Legacy and Experimental Review
- **PHP Backend**: Files inside `/backend` (including `api.php`, `config.php`, `verify_process.php`) represent legacy code from a previous deployment configuration. They have been flagged as **ARCHIVE ONLY** and remain untouched to avoid disruption of any hybrid operations.
- **Utility Scripts**: Single-use repair scripts (`_fix_login.py`, `cleanup_assets.py`, `fix_assets.py`) were archived to `/tools`.
