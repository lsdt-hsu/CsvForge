# AI Rules

## 1. Language & Terminology
- Chat, implementation plans, and all reports MUST be in Traditional Chinese (繁體中文) by default.
- Do NOT translate technical terms into Chinese (especially avoid Simplified Chinese terms).
- Keep industry terms in English (e.g., Commit, Push, Branch, Merge, Thread, Callback, Instance, Repository, String, Constant).
- The AI MUST explicitly declare that it has loaded and is adhering to the rules in .agents/AGENTS.md only once, in the first response to the user's initial prompt of each conversation. Do not repeat this declaration in subsequent steps or intermediate tool execution explanations within the same conversation.

## 2. Action Flow & Git Policy
- **Codebase Baseline**: ALWAYS read and use the current local files in the working directory as the absolute baseline for analysis, planning, and editing. Do NEVER use `git commit` versions or git history as your codebase reference unless explicitly instructed by the developer to analyze git history.
- **If Minor Changes** (constants, strings, assets, variable/function renaming):
  - Direct edit allowed (no prior plan needed).
  - Auto local `git commit` allowed. No auto `git push`.
  - *Exception*: If the change is for a bug fix, follow "Logical Changes" rule below.
- **If Logical Changes** (new features, control flows, data processing, architecture, or **ANY bug fixes** including tiny changes like variable renaming or missing imports):
  - MUST generate an implementation plan within Antigravity as the primary reference. A backup copy of this plan MUST be saved to a local file named .local_reports/AI_PLAN.md in the project root directory BEFORE requesting approval or editing.
  - No auto commit, no auto push.

## 3. Override Rule
- Execute `git commit`, `git push`, or Git workflows ONLY when explicitly commanded by the developer. Manual user commands override all restrictions above.

## 4. SDK Architecture & Boundary Rules
- **Dual Facade Isolation**: The system strictly enforces the Interface Segregation Principle (ISP) between the Host (Main Program) and Plugins.
  - **Host View**: The Host (e.g., `LeftPanel`, `MainWindow`, Mixins) MUST ONLY interact with plugins via `PluginHostAdapter`. The Host is strictly forbidden from accessing `BasePluginPanel` instances directly (except during initial setup in `LeftPanel`).
  - **Plugin View**: Plugin developers MUST ONLY interact with the Host via `self.api` (an instance of `PluginAPI`). Plugins are strictly forbidden from calling Host lifecycle methods directly.

- **Host Constraints**:
  - When passing a plugin to a PyQt UI component (e.g., `QStackedWidget`), you MUST use `adapter.get_widget()`. Do NOT pass the `PluginHostAdapter` object directly to UI methods.
  - The Host MUST NOT manually trigger specific plugin internal logic (e.g., do not call `run_main_action()`). Plugins must auto-trigger via their own lifecycle hooks (e.g., `on_csv_data_refreshed`).

- **Plugin Constraints**:
  - All Host-bound requests (e.g., `start_task`, `finish_task`, `update_progress`, `write_log`, `lock_ui`) MUST be routed through `self.api.xxx()`. Do NOT call `self.update_progress()` directly on the panel.
  - Plugins MUST NOT directly emit `_` prefixed private signals defined in `BasePluginPanel` (e.g., `_task_started`).

- **Strict Anti-Patterns**:
  - DO NOT use `hasattr()` or `getattr()` to guess properties, state, or methods across the Host-Plugin boundary.
  - DO NOT export `PluginHostAdapter` in `plugin_sdk/__init__.py`. It must remain hidden from plugin developers.

## 5. Fail-Fast Principle
- NEVER use `try-except` to swallow programming errors or lifecycle bugs (e.g., deleted C++ objects), unless evaluated as an unavoidable exception and approved by the user.
- Validate parameters early (e.g., raise `ValueError` for invalid `parent` references) and crash immediately.
- Rely on active cleanup and weak references rather than defensive error swallowing.
