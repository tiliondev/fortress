# tilion-mcp

> A stealth-browser MCP for AI agents. When a fetch gets blocked — Cloudflare, DataDome,
> PerimeterX, a 403, or a CAPTCHA — your agent calls these tools and gets the page, driving a
> real, recompiled Chromium (**Fortress**) locally.

`npx tilion-mcp` runs the server. It launches the Python `tilion` MCP under the hood (via
`uvx`, so nothing is permanently installed).

## Use it in a client

**Claude Desktop / Cursor / Cline / Windsurf** — add to the MCP config:

```json
{ "mcpServers": { "fortress": { "command": "npx", "args": ["-y", "tilion-mcp"] } } }
```

**Claude Code (CLI):**
```bash
claude mcp add fortress -- npx -y tilion-mcp
```

Requires Python available on PATH (the shim prefers [`uv`](https://astral.sh/uv); falls back to
`pipx`, a pre-installed `tilion-mcp`, or `python -m tilion.mcp`). Or install directly:
`pip install "tilion[mcp]"`.

## What you get

29 tools: `fetch_protected_page`, `read_page`, `extract_page`, `crawl_site`,
`recon_site_apis`, `search_web`, `run_browser_task`, `screenshot_page`, `save_page`,
`save_profile` / `load_profile`, `get_stealth_cdp_endpoint`, and more. Pre-warmed,
concurrency-safe, timeout- and SSRF-guarded.

Full docs: **https://github.com/tiliondev/fortress/tree/main/mcp**

Fortress Source Available License 1.1 · hosted cloud with residential egress coming soon.
