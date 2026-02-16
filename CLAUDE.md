# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Agentic AI learning/prototyping project that demonstrates tool-calling patterns using a local vLLM inference server with an OpenAI-compatible API.

## Running Scripts

```bash
# Run the main agent with a hardcoded query
python tool-call.py

# Run the basic model connection test
python test-model.py

# Start the vLLM server (run on the GPU host)
bash run-vllm.sh
```

## Infrastructure

The project connects to a local vLLM server configured via `.env`:
- `VLLM_HOST`, `VLLM_PORT`, `VLLM_MODEL`, `VLLM_API_KEY`
- The server must be running before executing any Python scripts.
- The vLLM server is launched with `--tool-call-parser hermes` to enable tool calling.

## Architecture

**`tool-call.py`** — Core agent loop:
- Defines 5 tools as OpenAI-compatible JSON schemas: `calculator`, `web_scrape`, `run_python`, `file_reader`, `file_writer`
- Runs an iterative agent loop (max 5 iterations): sends query → receives tool calls → executes tools → feeds results back → repeats until a final answer is produced
- Uses the `openai` Python SDK pointed at the local vLLM endpoint

**`test-model.py`** — Minimal smoke test for the vLLM connection (no tool calling)

**`fib.py`** — Example script used as a target for the `run_python` tool demo

## Key Patterns

- All tool implementations are plain Python functions; the agent dispatches based on `tool_call.function.name`
- `run_python` executes arbitrary code via `subprocess.run` — be cautious about what queries are passed
- `web_scrape` uses `requests` + `BeautifulSoup`; output is capped before being sent back to the LLM
