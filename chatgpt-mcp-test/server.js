'use strict';

const express = require('express');
const fs = require('fs');
const path = require('path');

const { listProjects, setActiveProject, requireActiveProject, session } = require('./lib/context');
const { readState, readCurrentState, listArtifacts, writeClarifyBrief, readLatestResearchDossier } = require('./lib/cortex');
const { launchResearch, getJobStatus, listJobs } = require('./lib/research');
const { runJudge, formatMobileResponse } = require('./lib/judge'); // kept for legacy inline fallback
const { log, tail, summary } = require('./lib/logger');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 8787;
const SERVER_INFO = { name: 'devserver-cortex', version: '2.0.0' };

// ─────────────────────────────────────────────
// Auth
// ─────────────────────────────────────────────
const MCP_TOKEN = process.env.MCP_TOKEN;
if (!MCP_TOKEN) {
  log.warn('server_start', { warning: 'MCP_TOKEN not set — server is unauthenticated' });
}

app.use((req, res, next) => {
  if (!MCP_TOKEN) return next();
  const bearer = (req.headers['authorization'] || '').replace('Bearer ', '');
  const query  = req.query.token || '';
  if (bearer === MCP_TOKEN || query === MCP_TOKEN) return next();
  log.warn('auth_fail', { ip: req.ip, path: req.path, ua: req.headers['user-agent'] });
  res.status(401).json({ error: 'Unauthorized' });
});

// ─────────────────────────────────────────────
// Tool definitions
// ─────────────────────────────────────────────

// Annotation presets — signal to ChatGPT how safe each tool is
const READ_ONLY   = { readOnlyHint: true,  destructiveHint: false, idempotentHint: true  };
const WRITE_SAFE  = { readOnlyHint: false, destructiveHint: false, idempotentHint: false };
const SIDE_EFFECT = { readOnlyHint: false, destructiveHint: false, idempotentHint: false };

const TOOLS = [

  // ── Filesystem ────────────────────────────────────────────────────────────
  {
    name: 'list_repo_files',
    description: 'List files and directories at a path under the active repo root (MCP_ROOT).',
    annotations: READ_ONLY,
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'Relative path within repo root. Use "." for root.', default: '.' }
      }
    }
  },
  {
    name: 'read_text_file',
    description: 'Read the contents of a text or code file under the active repo root.',
    annotations: READ_ONLY,
    inputSchema: {
      type: 'object',
      properties: {
        path: { type: 'string', description: 'Relative path to the file within the repo root.' }
      },
      required: ['path']
    }
  },

  // ── Project context ───────────────────────────────────────────────────────
  {
    name: 'cortex_list_projects',
    description: 'List all projects under ~/projects/ with their Cortex mode and status.',
    annotations: READ_ONLY,
    inputSchema: { type: 'object', properties: {} }
  },
  {
    name: 'cortex_set_project',
    description: 'Set the active project for this session. Must be called before any cortex_ tools that operate on a project.',
    annotations: READ_ONLY,
    inputSchema: {
      type: 'object',
      properties: {
        slug: { type: 'string', description: 'Project directory name under ~/projects/' }
      },
      required: ['slug']
    }
  },
  {
    name: 'cortex_status',
    description: 'Return the full Cortex state for the active project — slug, mode, gates, artifacts, open questions.',
    annotations: READ_ONLY,
    inputSchema: { type: 'object', properties: {} }
  },

  // ── Clarify phase ─────────────────────────────────────────────────────────
  {
    name: 'cortex_clarify_write',
    description: 'Write a completed Cortex clarify brief for the active project. Call this after gathering the idea, goals, non-goals, constraints, and open questions through conversation. Advances project to research mode.',
    annotations: WRITE_SAFE,
    inputSchema: {
      type: 'object',
      properties: {
        slug:          { type: 'string', description: 'Slug for this clarify session (lowercase-hyphenated)' },
        idea:          { type: 'string', description: 'One paragraph describing the idea or problem' },
        goal:          { type: 'string', description: 'The concrete success condition — what done looks like' },
        non_goals:     { type: 'string', description: 'Explicit out-of-scope items, one per line' },
        constraints:   { type: 'string', description: 'Hard constraints (technical, time, auth, etc)' },
        open_questions:{ type: 'string', description: 'Unanswered questions, one per line' },
        next_steps:    { type: 'string', description: 'Suggested next research steps' }
      },
      required: ['slug', 'idea', 'goal']
    }
  },

  // ── Research phase ────────────────────────────────────────────────────────
  {
    name: 'cortex_research_launch',
    description: 'Launch a real Cortex research job (claude -p /cortex-research) in the active project. Returns a job_id to poll with cortex_research_poll.',
    annotations: SIDE_EFFECT,
    inputSchema: {
      type: 'object',
      properties: {
        phase: {
          type: 'string',
          description: 'Research phase to run.',
          enum: ['concept', 'technical', 'competitive', 'evals']
        }
      },
      required: ['phase']
    }
  },
  {
    name: 'cortex_research_poll',
    description: 'Check the status of a running research job. When status is "done", automatically runs the Codex judge and returns a mobile-optimized report. When "running", returns progress info.',
    annotations: READ_ONLY,
    inputSchema: {
      type: 'object',
      properties: {
        job_id: { type: 'string', description: 'Job ID returned by cortex_research_launch' }
      },
      required: ['job_id']
    }
  },
  {
    name: 'cortex_jobs_list',
    description: 'List all research jobs (running and completed) with their status.',
    annotations: READ_ONLY,
    inputSchema: { type: 'object', properties: {} }
  },

  // ── Artifact reader ───────────────────────────────────────────────────────
  {
    name: 'cortex_read_artifact',
    description: 'Read any Cortex artifact file from the active project by relative path (e.g. "docs/cortex/research/my-slug/dossier.md").',
    annotations: READ_ONLY,
    inputSchema: {
      type: 'object',
      properties: {
        artifact_path: { type: 'string', description: 'Path relative to project root (e.g. docs/cortex/research/slug/file.md)' }
      },
      required: ['artifact_path']
    }
  }
];

// ─────────────────────────────────────────────
// Filesystem helpers (original)
// ─────────────────────────────────────────────

const MCP_ROOT = path.resolve(process.env.MCP_ROOT || path.join(process.env.HOME, 'mcp-safe', 'repo'));

function safeResolve(relPath) {
  const abs = path.resolve(MCP_ROOT, relPath || '.');
  if (!abs.startsWith(MCP_ROOT + path.sep) && abs !== MCP_ROOT) return null;
  return abs;
}

// ─────────────────────────────────────────────
// Tool handlers
// ─────────────────────────────────────────────

function handleTool(name, args) {
  // ── list_repo_files ──────────────────────────────────────────────────────
  if (name === 'list_repo_files') {
    const abs = safeResolve(args.path || '.');
    if (!abs) return err('Path outside repo root');
    try {
      const entries = fs.readdirSync(abs, { withFileTypes: true });
      const lines = entries
        .sort((a, b) => a.name.localeCompare(b.name))
        .map(e => e.isDirectory() ? e.name + '/' : e.name);
      return ok(lines.join('\n'));
    } catch (e) { return err(e.message); }
  }

  // ── read_text_file ───────────────────────────────────────────────────────
  if (name === 'read_text_file') {
    const abs = safeResolve(args.path);
    if (!abs) return err('Path outside repo root');
    try {
      const stat = fs.statSync(abs);
      if (stat.size > 512 * 1024) return err('File too large (>512KB)');
      return ok(fs.readFileSync(abs, 'utf-8'));
    } catch (e) { return err(e.message); }
  }

  // ── cortex_list_projects ─────────────────────────────────────────────────
  if (name === 'cortex_list_projects') {
    try {
      const projects = listProjects();
      const lines = projects.map(p => {
        const tag = p.hasCortex ? `[cortex:${p.cortexMode || '?'}]` : '[no-cortex]';
        return `${p.slug}  ${tag}`;
      });
      const active = session.activeProject ? `\nActive: ${session.activeProject}` : '\nActive: (none — call cortex_set_project)';
      return ok(lines.join('\n') + active);
    } catch (e) { return err(e.message); }
  }

  // ── cortex_set_project ───────────────────────────────────────────────────
  if (name === 'cortex_set_project') {
    try {
      const projectPath = setActiveProject(args.slug);
      const state = readState(projectPath);
      const stateInfo = state
        ? `mode: ${state.mode}, slug: ${state.slug}`
        : 'no cortex state yet';
      return ok(`Active project set to: ${args.slug} (${stateInfo})`);
    } catch (e) { return err(e.message); }
  }

  // ── cortex_status ────────────────────────────────────────────────────────
  if (name === 'cortex_status') {
    try {
      const { slug, projectPath } = requireActiveProject();
      const state = readState(projectPath);
      const current = readCurrentState(projectPath);
      const artifacts = listArtifacts(projectPath);

      const lines = [
        `Project: ${slug}`,
        `Path: ${projectPath}`,
        '',
        state ? `Mode: ${state.mode}` : 'Mode: (not initialized)',
        state ? `Cortex slug: ${state.slug}` : '',
        state ? `Approval: ${state.approval_status || 'pending'}` : '',
        '',
        'Gates:',
        state?.gates ? Object.entries(state.gates).map(([k, v]) => `  ${k}: ${v}`).join('\n') : '  (none)',
        '',
        `Artifacts (${artifacts.length}):`,
        artifacts.map(a => `  ${a}`).join('\n') || '  (none)',
        '',
        current ? '--- current-state.md ---\n' + current : ''
      ].filter(l => l !== undefined);

      return ok(lines.join('\n'));
    } catch (e) { return err(e.message); }
  }

  // ── cortex_clarify_write ─────────────────────────────────────────────────
  if (name === 'cortex_clarify_write') {
    try {
      const { projectPath } = requireActiveProject();
      const { slug, idea, goal, non_goals = '', constraints = '', open_questions = '', next_steps = '' } = args;

      const ts = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, 'Z');
      const content = `---
initial_terminal_set:
  - commit-to-build
  - experiment-required
ruled_out: []
---

# Clarify Brief: ${slug}

<!-- ART-01: Clarify Brief — produced via ChatGPT MCP interface -->

**Slug:** ${slug}
**Timestamp:** ${ts}
**Status:** draft
**Complexity:** standard

---

## Idea

${idea}

---

## Goal

${goal}

---

## Non-Goals

${non_goals || '(none specified)'}

---

## Constraints

${constraints || '(none specified)'}

---

## Open Questions

${open_questions || '(none)'}

---

## Next Research Steps

${next_steps || '(run /cortex-research --phase concept)'}
`;

      const artifactPath = writeClarifyBrief(projectPath, slug, content);
      return ok(`Clarify brief written: ${artifactPath}\nProject is now in research mode. Use cortex_research_launch to begin.`);
    } catch (e) { return err(e.message); }
  }

  // ── cortex_research_launch ───────────────────────────────────────────────
  if (name === 'cortex_research_launch') {
    try {
      const { slug, projectPath } = requireActiveProject();
      const phase = args.phase || 'concept';
      const jobId = launchResearch(projectPath, slug, phase);
      return ok([
        `Research job launched.`,
        `job_id: ${jobId}`,
        `phase: ${phase}`,
        `project: ${slug}`,
        ``,
        `INSTRUCTIONS: Automatically call cortex_research_poll with job_id "${jobId}" every 60 seconds until status is "done" or "failed". Do not wait for the user to ask — just keep polling and report back when the result arrives. Tell the user you are polling and will report when ready.`
      ].join('\n'));
    } catch (e) { return err(e.message); }
  }

  // ── cortex_research_poll ─────────────────────────────────────────────────
  if (name === 'cortex_research_poll') {
    try {
      const job = getJobStatus(args.job_id);
      if (!job) return err(`Job not found: ${args.job_id}`);

      if (job.status === 'running') {
        const elapsed = Math.round((Date.now() - new Date(job.startedAt).getTime()) / 1000);
        return ok([
          `Status: running`,
          `Elapsed: ${elapsed}s`,
          `Phase: ${job.phase}`,
          `Project: ${job.slug}`,
          ``,
          `Recent output:`,
          job.logTail || '(no output yet)'
        ].join('\n'));
      }

      if (job.status === 'failed') {
        return ok([
          `Status: FAILED (exit code ${job.exitCode})`,
          `Phase: ${job.phase}`,
          ``,
          `Last output:`,
          job.logTail || '(no output)'
        ].join('\n'));
      }

      // Done — read cached judge report (judge ran async after research completed)
      if (job.status === 'done') {
        const judgeStatus = job.judge_status;

        // Judge still running — ask caller to poll again
        if (judgeStatus === 'running') {
          return ok([
            `Status: done`,
            `Report: generating... poll again in 15s`,
            `Phase: ${job.phase}`,
            `Project: ${job.slug}`
          ].join('\n'));
        }

        // Judge completed — return cached mobile report
        if (judgeStatus === 'done') {
          return ok(job.mobile_report);
        }

        // Judge failed — fall back to raw dossier with warning
        if (judgeStatus === 'failed') {
          const dossier = readLatestResearchDossier(job.projectPath, job.slug);
          return ok([
            `Status: done`,
            `⚠ Judge failed: ${job.judge_error}`,
            `Returning raw dossier instead:`,
            ``,
            dossier ? dossier.content : '(dossier not found)'
          ].join('\n'));
        }

        // Legacy fallback: no judge_status field (old job format) — run inline
        if (!judgeStatus) {
          const dossier = readLatestResearchDossier(job.projectPath, job.slug);
          if (!dossier) {
            return ok([
              `Status: done (exit 0) but no dossier file found.`,
              `Check: ${job.projectPath}/docs/cortex/research/${job.slug}/`,
              ``,
              `Raw log tail:`,
              job.logTail
            ].join('\n'));
          }
          const judgeResult = runJudge(job.slug, dossier.content);
          if (!judgeResult.ok) {
            return ok([
              `Status: done`,
              `⚠ Judge failed: ${judgeResult.error}`,
              `Returning raw dossier instead:`,
              ``,
              dossier.content
            ].join('\n'));
          }
          return ok(formatMobileResponse(job.slug, judgeResult.result));
        }

        return ok(`Status: done (unknown judge_status: ${judgeStatus})`);
      }

      return ok(`Unknown status: ${job.status}`);
    } catch (e) { return err(e.message); }
  }

  // ── cortex_jobs_list ─────────────────────────────────────────────────────
  if (name === 'cortex_jobs_list') {
    try {
      const jobs = listJobs();
      if (!jobs.length) return ok('No jobs found.');
      const lines = jobs.map(j => {
        const elapsed = j.finishedAt
          ? `${Math.round((new Date(j.finishedAt) - new Date(j.startedAt)) / 1000)}s`
          : `${Math.round((Date.now() - new Date(j.startedAt).getTime()) / 1000)}s (running)`;
        return `${j.jobId}  ${j.status.padEnd(8)}  ${j.slug}:${j.phase}  ${elapsed}`;
      });
      return ok(lines.join('\n'));
    } catch (e) { return err(e.message); }
  }

  // ── cortex_read_artifact ─────────────────────────────────────────────────
  if (name === 'cortex_read_artifact') {
    try {
      const { projectPath } = requireActiveProject();
      const fullPath = path.join(projectPath, args.artifact_path);
      if (!fullPath.startsWith(projectPath + path.sep) && fullPath !== projectPath) {
        return err('Path escapes project root');
      }
      if (!fs.existsSync(fullPath)) return err(`File not found: ${args.artifact_path}`);
      const stat = fs.statSync(fullPath);
      if (stat.size > 512 * 1024) return err('File too large (>512KB)');
      return ok(fs.readFileSync(fullPath, 'utf-8'));
    } catch (e) { return err(e.message); }
  }

  return { error: { code: -32601, message: `Unknown tool: ${name}` } };
}

// ─────────────────────────────────────────────
// Response helpers
// ─────────────────────────────────────────────

function ok(text) {
  return { result: { content: [{ type: 'text', text: String(text) }] } };
}
function err(msg) {
  return { error: { code: -32600, message: msg } };
}

// ─────────────────────────────────────────────
// MCP message dispatcher
// ─────────────────────────────────────────────

function handleMessage(msg) {
  const { id, method, params } = msg;

  if (method === 'initialize') {
    log.info('mcp_init', { id });
    return {
      jsonrpc: '2.0', id,
      result: {
        protocolVersion: '2025-03-26',
        capabilities: { tools: {} },
        serverInfo: SERVER_INFO
      }
    };
  }

  if (method === 'ping') return { jsonrpc: '2.0', id, result: {} };

  if (method === 'tools/list') {
    log.info('tools_list', { count: TOOLS.length });
    return { jsonrpc: '2.0', id, result: { tools: TOOLS } };
  }

  if (method === 'tools/call') {
    const { name, arguments: args = {} } = params || {};
    const done = log.timer('tool_call', { tool: name, project: session.activeProject });
    const { result, error } = handleTool(name, args);
    if (error) {
      done({ status: 'error', error: error.message });
      log.error('tool_error', { tool: name, error: error.message });
      return { jsonrpc: '2.0', id, error };
    }
    done({ status: 'ok' });
    return { jsonrpc: '2.0', id, result };
  }

  if (id === undefined || id === null) return null;
  log.warn('method_not_found', { method });
  return { jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } };
}

// ─────────────────────────────────────────────
// Express routes
// ─────────────────────────────────────────────

app.get('/', (req, res) => {
  res.json({
    status: 'ok',
    server: SERVER_INFO.name,
    version: SERVER_INFO.version,
    mcpEndpoint: '/mcp',
    activeProject: session.activeProject || null,
    tools: TOOLS.map(t => t.name)
  });
});

app.post('/mcp', (req, res) => {
  const body = req.body;
  if (!body) return res.status(400).json({ error: 'empty body' });
  const msgs = Array.isArray(body) ? body : [body];
  const responses = msgs.map(handleMessage).filter(Boolean);
  if (responses.length === 0) return res.status(202).end();
  if (responses.length === 1) return res.json(responses[0]);
  res.json(responses);
});

// ── Debug endpoints (auth-protected same as /mcp) ─────────────────────────

app.get('/logs', (req, res) => {
  const n = Math.min(parseInt(req.query.n || '100'), 500);
  res.json(tail(n));
});

app.get('/logs/summary', (req, res) => {
  res.json(summary());
});

// ─────────────────────────────────────────────
// Start
// ─────────────────────────────────────────────

app.listen(PORT, '0.0.0.0', () => {
  log.info('server_start', {
    version: SERVER_INFO.version,
    port: PORT,
    mcp_root: MCP_ROOT,
    projects: require('./lib/context').PROJECTS_ROOT,
    auth: MCP_TOKEN ? 'token' : 'none',
    tools: TOOLS.map(t => t.name)
  });
  console.log(`\nMCP Cortex server ready — v${SERVER_INFO.version}`);
  console.log(`  Endpoint   : http://0.0.0.0:${PORT}/mcp`);
  console.log(`  Logs       : http://0.0.0.0:${PORT}/logs`);
  console.log(`  Summary    : http://0.0.0.0:${PORT}/logs/summary\n`);
});
