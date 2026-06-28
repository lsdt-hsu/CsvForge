# AI Rules (From .antigravityrc)

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
  - MUST generate an implementation plan within Antigravity as the primary reference. A backup copy of this plan MUST be saved to a local file named LocalReports/AI_PLAN.md in the project root directory BEFORE requesting approval or editing.
  - No auto commit, no auto push.

## 3. Override Rule
- Execute `git commit`, `git push`, or Git workflows ONLY when explicitly commanded by the developer. Manual user commands override all restrictions above.
