# Security

Causal Repair is an instruction and orchestration plugin. It does not ship executable repair code, but it can cause Claude Code to inspect, edit, and test repositories when the user authorizes those actions.

## Reporting issues

Open a GitHub issue with:

- affected version or commit
- reproduction steps
- expected behavior
- actual behavior
- any unsafe instruction pattern you observed

## Safety expectations

- Review the `SKILL.md` and agent definitions before enabling the plugin in sensitive repositories.
- Run the plugin in trusted workspaces only.
- Do not grant automatic edit or shell permissions unless you trust the repository and task.
- Prefer review mode or manual approval for high-risk codebases.
