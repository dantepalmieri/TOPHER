# TOPHER

**T.O.P.H.E.R.** — Totally Open Personal Home Environment Robot. A personal AI
assistant system, built in phases: it starts as a simple Obsidian vault search tool
and grows into a multi-agent system with a live dashboard. As of Phase 4, it can
search and write to your vault, remember conversations short- and long-term, run as
an MCP server for Claude Desktop/Code, and hand a goal to a five-agent team
(Architect, Research, Developer, Testing, Analytics) that plans, investigates, builds,
reviews, and reports on it end to end.

### About the name

Topher (or "Toph") is the assistant's identity across every part of this project —
the core vault assistant and every team agent operate under that one name, each in
their own distinct voice, the same way JARVIS is one assistant across every system
it runs. `second_brain/identity.py` holds the shared identity text every agent's
system prompt is built from.

## Table of contents

- [Roadmap](#roadmap)
- [Setup](#setup)
- [Usage](#usage)
- [Project structure](#project-structure)
- [Code style conventions](#code-style-conventions)
- [Known limitations](#known-limitations)
- [Development history](#development-history)
- [Next steps](#next-steps)

## Roadmap

1. **Obsidian second-brain integration** — the assistant reads and writes to a personal Obsidian vault, so notes become a live knowledge base it can search and add to — ✅ complete (Phase 1)
2. **Core assistant with memory** — semantic search over notes plus persistent conversation memory — ✅ complete (Phase 2)
3. **Subagent framework** — one specialized agent (Research) that can be invoked by an orchestrator to handle a narrow task end-to-end — ✅ complete (Phase 3)
4. **Multi-agent team** — a full set of specialized agents (Architect, Research, Developer, Testing, Analytics) that communicate and hand work off to each other — ✅ complete (Phase 4)
5. **Dashboard UI** — a visual control-room style app to watch the agents work: multiple panels, live data, dark theme with glowing accents — not started

Each phase builds directly on the last. The vault access layer (Phase 1) is the
foundation everything else depends on, so it was built and tested first before
touching agents or orchestration.

### Architecture direction (for later phases)

```
                     +-------------------+
                     |   2D Dashboard    |
                     |  (control-room    |
                     |   style UI)       |
                     +---------+---------+
                               |
                       (WebSocket / IPC)
                               |
                     +---------v---------+
                     |    Orchestrator    |
                     |  (routes requests, |
                     |  spawns subagents) |
                     +----+----+----+-----+
                          |    |    |
             +------------+  +----+  +------------+
             |               |               |
      +------v-----+  +------v-----+  +------v-----+
      |  Research  |  | Development|  |  Analytics |
      |   Agent    |  |    Agent   |  |    Agent   |
      +------+-----+  +------+-----+  +------+-----+
             |               |               |
             +-------+-------+-------+-------+
                     |               |
             +-------v------+  +-----v------+
             |  Vector DB   |  |  Obsidian  |
             | (note search)|  |    Vault   |
             +--------------+  +------------+
```

**Build-vs-buy decision:** the orchestrator, agent definitions, and prompts are
custom (the project-specific part). Existing tools are used for infrastructure —
Chroma for vector search, MCP for Obsidian access, the Claude Agent SDK for the
Research agent — and a coordination framework like LangGraph is deliberately
deferred until Phase 4, when multiple agents actually need to coordinate.

## Setup

```powershell
cd obsidian-claude
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

`.env` contents:

```
ANTHROPIC_API_KEY=your-api-key-here
OBSIDIAN_VAULT_PATH=C:/Users/you/Documents/YourVaultName
```

- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `OBSIDIAN_VAULT_PATH` — absolute path to your vault folder. Use forward slashes
  (`C:/Users/...`) even on Windows, to avoid backslash-escaping issues.
- `HF_TOKEN` — optional. Not read by this project's own code; picked up implicitly
  by `sentence-transformers`/`huggingface_hub` when downloading the embedding model.

### Windows-specific notes

- `python3` isn't recognized on Windows even with Python installed — Windows
  intercepts it as a Microsoft Store shortcut. Use `python` instead.
- PowerShell may block venv activation (`venv\Scripts\Activate.ps1`) due to
  execution policy — fix with `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

## Usage

```powershell
python -m second_brain.cli            # vault Q&A with memory (Phases 1-2)
python -m second_brain.research_cli   # deep research agent, live web + vault (Phase 3)
python -m second_brain.team_cli       # full agent team: plan, research, build, review, report (Phase 4)
```

`second_brain.cli` is the original assistant: ask it about your notes, it searches
the vault semantically, answers with citations, remembers the conversation (both
within a session and across separate runs), and can create/append vault notes when
you ask it to.

`second_brain.research_cli` is a separate tool for open-ended research questions —
"what's the latest on X", "look into Y for me" — that need live web search rather
than just your existing notes. It can also search your vault when relevant.

`second_brain.team_cli` hands a goal to the full five-agent team — Architect plans
it, Research investigates open questions, Developer builds it, Testing reviews it,
Analytics reports on the result — printing each stage's output as it completes. Talk
to one agent directly instead of the whole pipeline by prefixing your message with
its name, e.g. `architect: plan a REST API for a todo app`.

### Registering the vault as an MCP server

`.mcp.json` registers the vault as an MCP server for Claude Code (project-scoped
config). It's gitignored, since it contains a machine-specific absolute path — copy
the example and fill in your own path:

```powershell
copy .mcp.json.example .mcp.json
```

```json
{
  "mcpServers": {
    "second-brain-vault": {
      "command": "C:\\path\\to\\obsidian-claude\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\obsidian-claude\\run_mcp_server.py"]
    }
  }
}
```

The self-locating launcher means no `cwd` field is needed. Use the **venv's** `python.exe` directly, not the system `python` — the server
depends on packages (`mcp`, `chromadb`, `sentence-transformers`) only installed in
the venv. Claude Code needs a restart/reload (or first-use approval) to pick up a
new `.mcp.json`. If Claude Desktop is ever installed, the same command/args go in
`%APPDATA%\Claude\claude_desktop_config.json` instead.

Exposes 5 tools: `search_vault`, `list_vault_notes`, `read_vault_note`,
`create_vault_note`, `append_to_vault_note` — confirmed working both via a
standalone stdio test client and from inside a live Claude Code session.

## Project structure

```
second_brain/
  identity.py               - TOPHER_IDENTITY_TEXT, the shared identity text every agent's
                              system prompt is built from (client.py and all 5 team agents)
  config.py                - all constants (model name, vault path, limits, embedding model,
                              chroma collection name, history file path/context window,
                              assistant memory folder name, summarization token limit,
                              research agent's venv/launcher paths, every team agent's
                              model name, the team's sandbox workspace path);
                              locates .env/conversation_history.json relative to its own
                              file location, not the process's working directory
  types.py                  - shared dataclasses: NoteMatch (match_score is float), ClaudeAnswer,
                              ConversationTurn (role, content), PipelineStageResult
                              (agent_name, output_text)
  vault/
    vault_reader.py         - ALL filesystem reads: list_note_files (skips hidden dirs like
                              .trash/.obsidian), read_note_content, get_note_title,
                              find_note_file_path_by_title (title -> path, for the write tools)
    semantic_search.py      - embeds vault notes + question via sentence-transformers, searches
                              an in-memory Chroma collection (search_notes_by_semantic_similarity);
                              the only module that touches chromadb/sentence-transformers
    vault_writer.py         - ALL filesystem writes: create_note, append_to_note,
                              create_or_append_note_in_folder (used by assistant_memory.py)
  claude/
    client.py               - builds a multi-turn message list from prior turns + this turn's
                              vault context, calls the Claude API with vault-write tools
                              available (create_note/append_to_note via a tool-use loop),
                              reports what was written back to the caller; also
                              summarize_conversation_for_memory
  conversation_history.py   - the ONLY module that touches conversation_history.json (short-term
                              rolling-window replay buffer): load_conversation_history,
                              append_turns_to_history
  assistant_memory.py       - long-term memory: save_session_to_memory distills a session via
                              client.py and writes it into the vault's Assistant Memory/ folder
                              via vault_writer.py, so it's searchable like any other note
  agents/
    research_agent.py       - Research: investigates open questions and gathers sources for a
                              plan or goal. Built on the Claude Agent SDK (not the raw anthropic
                              client), gets WebSearch/WebFetch for free plus the vault's own MCP
                              tools. Explicitly scoped to never attempt building/writing files,
                              even when handed a plan full of build milestones (see Phase 4
                              development history for why that scoping exists)
    architect_agent.py      - Architect: turns a goal into a scoped, milestoned plan through
                              collaboration with the user, then hands it to Research. Read-only
                              tools + vault MCP only - no write/edit/bash, so it can never build
                              anything itself
    developer_agent.py      - Developer: builds whatever the plan calls for - code, scripts,
                              configs. The first agent with real Write/Edit/Bash access, sandboxed
                              by cwd to the workspace/ directory (team_workspace.py) rather than
                              this project's own source or an arbitrary path
    testing_agent.py        - Testing: security/correctness/quality review. Deliberately has no
                              write or edit tools - it reports what's wrong, Developer fixes it
                              on the next pass. Shares Developer's sandbox workspace via cwd so
                              it inspects real output, not a description of it
    analytics_agent.py      - Analytics: the data/metrics expert - calculates, organizes, and
                              reports on what the team produced. Read/Write/Bash scoped to the
                              same sandbox workspace, plus the vault's MCP tools for organizing
                              findings back into notes
    team_workspace.py       - ensure_team_workspace_directory_exists(), the shared sandbox
                              directory helper used by developer/testing/analytics
  orchestrator.py            - routes a request to a subagent, or all five in sequence via
                              run_full_team_pipeline(goal, on_stage_complete=...) - Architect ->
                              Research -> Developer -> Testing -> Analytics, each stage's output
                              threaded into the next stage's input as context. Every agent stays
                              independently callable too (handle_architect_request, etc.)
  research_cli.py            - second, separate interactive entry point for the research
                              agent; owns all of its own terminal I/O, mirrors cli.py's loop
  team_cli.py                 - third interactive entry point, for the full agent team: runs
                              the whole pipeline on a plain goal, or dispatches to one agent
                              directly via an "agentname:" prefix; owns all of its own terminal I/O
  cli.py                     - the ONLY file touching stdin/stdout for the main assistant;
                              interactive loop (input()/print()), saves session memory on
                              exit, prints a "Vault changes:" section whenever Claude writes
                              to the vault
  mcp_server.py               - exposes vault_reader/vault_writer/semantic_search as 5 MCP
                              tools; registered with Claude Code via .mcp.json
run_mcp_server.py              - self-locating launcher for mcp_server.py; works regardless
                              of the spawning process's working directory
workspace/                     - sandbox directory developer/testing/analytics operate in;
                              created on demand, not committed by default - the team's actual
                              deliverables land here
.mcp.json                      - Claude Code project-scoped MCP server registration (gitignored -
                              contains a machine-specific absolute path; copy .mcp.json.example)
requirements.txt              - anthropic, python-dotenv, chromadb, sentence-transformers,
                              mcp (pinned <2.0.0 - claude-agent-sdk requires it), claude-agent-sdk
.env.example                  - ANTHROPIC_API_KEY, OBSIDIAN_VAULT_PATH
conversation_history.json     - short-term memory: persisted chat log at the project root
                              (gitignored — personal data, never commit this)
```

**Vault structure note:** the vault gets an `Assistant Memory/` folder (created
automatically on first use) containing one dated note per day (`YYYY-MM-DD.md`) of
distilled session summaries — long-term memory, separate from
`conversation_history.json` above.

**Models in use:** `cli.py`'s direct API calls use `claude-sonnet-4-6`. The
research agent, built on the Claude Agent SDK, uses the `"sonnet"` model alias.

## Code style conventions

Applies to all code in this project:

- No non-self-documenting or single-letter variable names, except loop counters, math formulas, or established conventions (`x`/`y` coordinates) — this project favors descriptive names even in loops (e.g. `file_index`, not `i`)
- No state mutation inside function calls or subscripts (no `array[index++]`)
- No incomplete/empty for-loop headers
- `True`/`False`, never `1`/`0`, for booleans
- Constants instead of magic numbers or repeated literals (see `config.py`)
- No global variables
- No `break` (Python has no switch statement, so loops rely on natural exit conditions)
- No `continue`
- 4-space indentation, no tabs
- I/O isolated to designated modules: `cli.py`, `research_cli.py`, and `team_cli.py` each own all of their own terminal I/O (the orchestrator takes an optional callback for progress reporting rather than printing itself); `vault_reader.py`/`vault_writer.py` own all filesystem access
- No calling one function directly inside another function's call — always assign an intermediate variable
- No empty `if`/`else` blocks
- No extremely long lines
- No ternary/conditional expressions
- Prefer explicit indexed loops (`for i in range(len(collection))`) over implicit iteration
- No unspecified/undefined utility functions — every helper must be defined in the codebase

## Known limitations

Intentional, not bugs to silently "fix":

- Index is rebuilt from scratch (in-memory, no persistence) on every search call — fine for a small vault, would need incremental/persistent indexing if the vault grows much larger
- `conversation_history.json` grows unboundedly on disk (only the context sent to Claude per call is capped) — no pruning of old turns yet; `Assistant Memory/` notes also just accumulate, one dated note per day, with no consolidation of older days
- Search-query context-folding for follow-ups only looks one question back, not the full conversation
- Notes are embedded whole, not chunked by heading — fine for short personal notes, would dilute relevance on much longer notes
- `vault_writer.py` writes raw text with no awareness of Obsidian conventions (`[[wikilinks]]`, tags, frontmatter)
- MCP tools have no destructive-action confirmation beyond refusing to overwrite an existing note title
- The CLI's own write tools (separate from MCP) write immediately with no confirmation gate, by explicit user choice — guarded only by a prompt instruction telling Claude to write only when clearly asked, plus always printing what changed
- `create_note`/`append_to_note` only support whole-file create and blind append — no way to edit a specific section/heading of an existing note
- `run_full_team_pipeline` always runs the full Architect → Research → Developer → Testing → Analytics chain — no way to start partway through or skip a stage yet, beyond addressing one agent directly outside the pipeline
- Developer/Testing/Analytics are sandboxed to a single shared `workspace/` directory, not a per-goal or per-project directory — running two unrelated goals back to back means the second run's agents can see the first run's files

## Development history

### Phase 1 — vault search CLI

A minimal command-line tool: ask a question, keyword-search the vault, send the
top matches plus the question to Claude, print the answer and its sources. No
embeddings, no MCP server, no orchestrator — deliberately minimal, to validate the
read → retrieve → ask → answer loop before adding complexity.

Originally scaffolded in TypeScript, then rewritten in Python 3.11 after the user
said they weren't comfortable in TypeScript — same architecture and logic, nothing
lost.

**Two bugs found and fixed during testing:**

1. A note titled `d2d` scored zero on the query `d2d`, because keyword scoring only checked note *body* content, never the title/filename. Fixed by also scoring title matches, weighted 10x, so a filename match outranks incidental body mentions.
2. Multi-word questions like *"What do I need to do in my d2d?"* never matched anything, because the whole question was searched as one literal phrase. Fixed by extracting individual search terms (lowercased, punctuation-stripped, stop words removed) and scoring each note against every remaining term.

### Phase 2 — semantic search, conversation memory, MCP server, vault writes

**Semantic search:** swapped keyword search for embedding-based search — Chroma
(in-memory, rebuilt on every call — the vault is small enough that this is cheap)
with local `sentence-transformers` embeddings (`all-MiniLM-L6-v2`), so nothing
leaves the machine and no new API account is needed. Two bugs found while
verifying against the real vault: notes in the vault's `.trash`/`.obsidian`
folders were being embedded and returned as matches (fixed by skipping any
directory starting with `.`), and reusing the Chroma client within one process
threw on "collection already exists" (fixed with `get_or_create_collection` plus
explicit clearing before re-adding).

**Conversation memory:** an interactive loop that keeps prompting until `exit`/
`quit`/EOF, persisting to `conversation_history.json` after every turn — giving
both in-session follow-ups and cross-run memory from the same mechanism. Only the
most recent turns are replayed to Claude each call to bound token usage, but the
full history persists on disk. Two bugs found while testing multi-turn behavior:
vague follow-ups ("which one should I start with?") pulled irrelevant notes
because the vector search had nothing to go on — fixed by folding the previous
question into the search query for follow-ups; and a `UnicodeEncodeError` crashed
the CLI when an answer contained non-ASCII characters, because Windows' default
terminal codepage (cp1252) can't encode them — fixed with
`sys.stdout.reconfigure(encoding="utf-8")`.

**MCP server:** wrapped the vault as 5 MCP tools using the official Anthropic MCP
Python SDK, verified over a real stdio client session against the actual vault
(list, search, create, duplicate-create error handling, append, read). One real
deployment gotcha: the project isn't installed as a package, so imports and
`.env` loading only resolved correctly when launched from the project root — an
MCP client won't necessarily do that. Fixed by having `config.py` locate files
relative to its own file location rather than the process's working directory,
plus a self-locating `run_mcp_server.py` launcher — re-verified from an unrelated
working directory with no `cwd` or `PYTHONPATH` help.

**Long-term memory as vault notes:** each session's new turns get distilled by
Claude into a short summary and written to a dated note under `Assistant Memory/`
in the vault — additive to the short-term `conversation_history.json`, not a
replacement. Because it's a real vault note, it's automatically picked up by
semantic search with no special-casing. Verified end-to-end across three separate
process runs: a session distilled into a real summary note, that note ranked #1
for a related semantic search, and a brand-new process correctly recalled and
cited it.

**Vault writes wired into the CLI:** Claude can create/append vault notes directly
from a conversation via a tool-use loop in `client.py`, using a write-immediately-
report-after policy (the user's explicit choice over a confirmation gate) —
guarded by a prompt instruction to only write when clearly asked, plus always
printing a `Vault changes:` section. Verified create, append-by-title, and the
duplicate-title error path all work against the real vault.

### Phase 3 — the Research agent

The Research agent is Phase 3's first subagent, built on the **Claude Agent SDK**
(`claude-agent-sdk`) rather than the raw `anthropic` client — it ships a built-in
`WebSearch` tool for free, and can attach the vault's existing MCP server directly
via `mcp_servers`, so one agent can search the live web and the user's own notes
in the same tool-use loop.

`second_brain/agents/research_agent.py` restricts the agent to exactly
`WebSearch`, `WebFetch`, and the vault's `mcp__vault__*` tools, with a system
prompt built around deep, rigorous, source-verified research: deconstruct the
query into sub-questions, search broad-to-narrow, cross-verify conflicting data
points across sources, and cite every key figure with an inline source URL.

**One real dependency conflict found while installing the SDK:** `claude-agent-sdk`
pins `mcp<2.0.0`, so installing it silently downgraded the project's `mcp` package
from 2.0.0 to 1.29.0 — which broke `mcp_server.py`, since the 2.0.0-specific
`mcp.server.mcpserver.MCPServer` class no longer exists in 1.x. Fixed by switching
to the 1.x equivalent, `mcp.server.fastmcp.FastMCP`, which has an identical
`.tool()`/`.run(transport="stdio")` API — confirmed identical, not assumed; the
existing tool decorators needed zero changes. `requirements.txt` now pins
`mcp<2.0.0,>=1.23.0` so this can't silently regress again.

A minimal orchestrator (`orchestrator.py`) and a second interactive entry point
(`research_cli.py`, mirroring `cli.py`'s own loop structure) complete the phase.
With only one subagent, the orchestrator is intentionally a plain function
(`handle_research_request`) rather than an SDK-level coordinator agent — real
routing logic is Phase 4's job, once there's a second agent to route between.

**Verified end-to-end, not just that the modules import:** asked the research
agent a real question requiring live web search — it searched, returned a
correctly cited answer. Separately, asked it to search the vault only — it used
the vault's MCP tool for real, correctly reported the actual vault contents, and
caught and explicitly flagged a fabricated note left over from an old Phase 2 test
session rather than repeating it as fact, direct evidence the system prompt's
"never assume facts, cross-verify" instruction is actually shaping behavior. The
full CLI path (`python -m second_brain.research_cli`) was also verified with real
piped input, including the EOF-as-clean-exit path.

### Phase 4 — the agent team

Four new agents joined Research to form the full team, each with a distinct
personality the user specified directly: **Architect** (strategic, structured,
plans with the user then hands off — no execution tools at all), **Developer**
(pragmatic, decisive, the first agent with real Write/Edit/Bash access),
**Testing** (skeptical by default, security/quality-focused, deliberately has no
write access — it reports, Developer fixes), and **Analytics** (precise,
quantitative, defaults to tables and shown work over prose).

**Tool scoping was the main design decision, not the personalities.** Developer
and Testing needed real filesystem/command-execution access for the first time in
this project — rather than guess at a target directory or leave them unscoped, both
(plus Analytics) are sandboxed via `cwd` to a dedicated `workspace/` directory
(`team_workspace.py`), never this project's own source or an arbitrary path.
Testing shares Developer's exact workspace so it reviews real files, not a
description of them.

`orchestrator.py` was rewritten with the real routing logic the Phase 3 writeup
called out as premature until a second subagent existed: every agent stays
independently callable (`handle_architect_request`, etc.), and
`run_full_team_pipeline(goal, on_stage_complete=...)` chains all five in their
natural handoff order, threading each completed stage into the next stage's input
as context. The callback parameter keeps the orchestrator itself free of I/O — the
printing happens in whatever the caller passes in, matching the project's I/O-
ownership convention rather than bending it. A hand-rolled Python orchestrator was
kept over adopting LangGraph or a similar framework — five agents in a fixed
handoff order don't yet need a graph framework's complexity; revisit if routing
gets meaningfully non-linear.

**One real bug found and fixed during verification, not just a clean pass:** running
the full pipeline end-to-end, Research responded to Architect's plan with *"I don't
have write permission for this directory yet. Please grant permission..."* —
confusing, since Research was never given write tools at all. Root cause: Research's
system prompt had no concept of operating inside a team pipeline, so when handed a
plan full of build milestones ("Create `add.py`...") it tried to act on them
directly, hit the SDK's tool restriction, and misreported a role mismatch as a
permissions problem. Fixed by adding an explicit "Your role on a team" section to
`RESEARCH_AGENT_SYSTEM_PROMPT`: build steps belong to Developer, never to Research,
and if a plan has nothing left to research, say so in a sentence and stop — don't
describe that as a permissions issue. Re-verified with the exact context that
triggered the bug: Research now correctly stays in its lane, attempts what it
actually can do (checking tool availability), and hands off cleanly.

**Verified end-to-end against a real (intentionally tiny) goal**, not just that the
modules import: *"Build a tiny Python function that adds two numbers, with one test
file that verifies it"* ran through all five agents for real. Architect produced a
scoped plan and correctly skipped unnecessary clarifying questions since the task
was trivial. Research (post-fix) correctly assessed nothing further was needed.
Developer wrote real files into `workspace/` (`add.py`, `test_add.py`) and ran the
test itself, confirmed passing. Testing independently re-ran the test rather than
trusting Developer's claim, reviewed the code, and reported a clean verdict with
one honestly-labeled non-blocking coverage gap. Analytics independently re-verified
the same test run, then produced a metrics rollup (LOC, test counts, plan-vs-actual
milestone tracking) with sourced figures, not estimates. Test artifacts were
removed from `workspace/` afterward to leave a clean slate.

**Naming, after the repo went public:** the project and its GitHub repo were named
TOPHER (T.O.P.H.E.R.), with the assistant going by "Topher" or "Toph" — a nod to
JARVIS, one consistent assistant identity across every surface. `second_brain/identity.py`
holds that identity text once; every team agent's system prompt and `client.py`'s
raw API calls now build on top of it, so the name applies everywhere without
duplicating the text five times or overwriting any agent's own distinct personality.

## Next steps

**Phase 5 — dashboard UI (not started):**

- A visual control-room style app to watch the agent team work: multiple panels, live data, dark theme with glowing accents
- Needs a way to stream pipeline progress out of `run_full_team_pipeline`'s `on_stage_complete` callback to a UI instead of (or alongside) the CLI's print callback — the callback shape should already support this without changing the orchestrator
- TypeScript/JS is back on the table specifically for this layer, regardless of the Python backend — see the original language decision in Phase 1's history

**Also identified, not urgent, no particular priority:**

- Chunking notes by heading section instead of embedding them whole
- Richer per-note metadata (tags, modified time) for filtering/re-ranking search results
- File-watcher + incremental re-indexing, instead of rebuilding the whole embedding index every call
- Frontmatter/wikilink-aware writes in `vault_writer.py`
- Per-goal or per-project workspace directories instead of one shared `workspace/`, if running unrelated goals back to back turns out to matter in practice
- A way to start the pipeline partway through (e.g. skip Architect when a plan already exists) or skip a stage

**Do not start yet:**

- Don't land any single change across multiple unrelated concerns at once — test each item in isolation, the same discipline used through Phases 1-4
