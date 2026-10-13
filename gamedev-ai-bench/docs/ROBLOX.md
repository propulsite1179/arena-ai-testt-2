# Roblox Benchmark Runner

## Official local connection

Source checked on 2026-10-13: https://create.roblox.com/docs/studio/mcp

Studio MCP is a **local** component. It is not a universal remote HTTP API and cannot be connected from an ordinary browser iframe. The native runner uses these documented entry points:

- Windows: `cmd.exe /c %LOCALAPPDATA%\Roblox\mcp.bat`
- macOS: `/Applications/RobloxStudio.app/Contents/MacOS/StudioMCP`

Install/update official Roblox Studio, enable its MCP feature, open an explicitly disposable project copy and verify the selected active Studio window. Linux cannot run the native Studio integration delivered here.

```sh
python apps/roblox-runner/runner.py discover --owner-consent
python apps/roblox-runner/runner.py execute --owner-consent --project-copy /absolute/copy.rbxlx --plan apps/roblox-runner/plan.example.json
```

Read `--help` for the exact arguments. Replace the example `project_copy` path with the real absolute copy path, and approve each step. Add `--allow-edits` only after reviewing the exact requested writes. No project copy is implicitly loaded or selected: the owner must confirm the active Studio is that copy before editing.

## Discovery, not invented calls

The adapter initializes MCP stdio, negotiates a supported protocol, paginates `tools/list`, validates every advertised JSON Schema, and validates each call's arguments against the installed server's schema. Tool names observed in official documentation include `get_studio_state`, `script_read`, `multi_edit`, `execute_luau`, `start_stop_play`, `get_console_output`, `screen_capture` and input/navigation controls. The runner does not assume every installed version exposes them.

Read-only inspection tools are allowlisted. Editing/play/input tools require `--allow-edits`. External HTTP, asset upload/generation/publishing tools are deliberately excluded. Server-initiated sampling/elicitation requests are rejected. Plan length and response size/time are bounded, though this runner is not a hardened hostile-MCP sandbox: install only the official trusted local bridge.

## Original starters and evidence

The ten `scenarios/*.luau` files generate a named isolated root and fail if it already exists. They do not delete unrelated project data or publish anything. Some are intentionally incomplete or defective repair inputs. Apply them only to a disposable copy in Edit mode using a reviewed plan whose arguments match the discovered tool schema.

The receipt records server metadata, tool schemas, argument hashes, durations, results and before/after file hashes. An unchanged saved file does not prove the live Studio data model was unchanged or saved. Real playtests, pure-module assertions and multi-client tests must be separately captured and reviewed.

`--upload` sends the private receipt to `GDB_BACKEND_ORIGIN` with `GDB_RUNNER_TOKEN`. HTTPS is mandatory for that upload. Backend receipt acceptance is not publication or scoring.

## Verification limits

MCP integration tests use `tests/mock_mcp.py`, explicitly named `explicit-test-mock-not-roblox`. They verify stdio framing, discovery, argument validation, permissions and receipt handling. No actual Roblox playtest, saved project, model-generated world or multiplayer run was verified during this delivery.

OpenGameEval and its public leaderboard were inspected as research references. No code/dataset was copied, and no compatibility or exclusive dependency on a Roblox-hosted evaluation service is claimed.
