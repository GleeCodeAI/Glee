# PRD — Glee MCP Agent Runtime v1

## 1. Product Definition

Glee MCP Agent Runtime is a locally-running autonomous agent exposed to LLM tools (Claude Code, Codex, Cursor, etc.) through MCP.  
It allows LLMs to delegate complex, long-running, multi-step work to Glee instead of executing it inside the model’s own context.

Glee is not a collection of tools.  
Glee is a full Agent that can be called as a tool.

## 2. Core Goals

1. Decouple long work from model context  
2. Support long-running jobs  
3. Enable agentic execution  
4. Support human-in-the-loop

## 3. Architecture

Claude Code -> MCP -> Glee MCP Server -> Glee Agent Runtime

## 4. API Design

All functions live under one namespace: glee_job.*

Required:
- glee_job.submit
- glee_job.get
- glee_job.wait
- glee_job.result
- glee_job.needs_input
- glee_job.provide_input
- glee_job.latest

Optional:
- glee_job.list
- glee_job.cancel
