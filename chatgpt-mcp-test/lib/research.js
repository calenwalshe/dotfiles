'use strict';

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { log } = require('./logger');
const { runJudge, formatMobileResponse } = require('./judge');
const { readLatestResearchDossier } = require('./cortex');

const JOBS_DIR = path.join(__dirname, '..', 'jobs');
fs.mkdirSync(JOBS_DIR, { recursive: true });

function jobPath(jobId) {
  return path.join(JOBS_DIR, `${jobId}.json`);
}

function readJob(jobId) {
  const p = jobPath(jobId);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, 'utf-8'));
}

function writeJob(jobId, data) {
  fs.writeFileSync(jobPath(jobId), JSON.stringify(data, null, 2));
}

/**
 * Launch a `claude -p "/cortex-research --phase {phase}"` subprocess in the project directory.
 * stdout+stderr are streamed to jobs/{jobId}.log
 * Returns jobId immediately — caller polls with getJobStatus().
 */
function launchResearch(projectPath, slug, phase) {
  const jobId = crypto.randomBytes(6).toString('hex');
  const logFile = path.join(JOBS_DIR, `${jobId}.log`);
  const prompt = `/cortex-research --phase ${phase}`;

  const meta = {
    jobId,
    type: 'research',
    slug,
    phase,
    projectPath,
    logFile,
    prompt,
    status: 'running',
    startedAt: new Date().toISOString(),
    finishedAt: null,
    exitCode: null
  };
  writeJob(jobId, meta);
  log.info('research_launch', { jobId, slug, phase, projectPath });

  const logStream = fs.createWriteStream(logFile, { flags: 'a' });

  const child = spawn('claude', ['-p', prompt], {
    cwd: projectPath,
    env: { ...process.env },
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false
  });

  child.stdout.pipe(logStream);
  child.stderr.pipe(logStream);

  child.on('close', (code) => {
    logStream.end();
    const updated = readJob(jobId);
    const elapsed = Date.now() - new Date(updated.startedAt).getTime();
    updated.exitCode = code;
    updated.finishedAt = new Date().toISOString();

    if (code !== 0) {
      updated.status = 'failed';
      writeJob(jobId, updated);
      log.error('research_fail', { jobId, slug, phase, exitCode: code, ms: elapsed });
      return;
    }

    // Research succeeded — set done and kick off async judge
    updated.status = 'done';
    updated.judge_status = 'running';
    writeJob(jobId, updated);
    log.info('research_done', { jobId, slug, phase, ms: elapsed });

    // Run judge asynchronously — do not block the close handler
    setImmediate(() => {
      const judgeStart = Date.now();
      const dossier = readLatestResearchDossier(projectPath, slug);

      if (!dossier) {
        const j = readJob(jobId);
        j.judge_status = 'failed';
        j.judge_error = 'No dossier file found after research completed';
        writeJob(jobId, j);
        log.error('judge_fail', { jobId, slug, error: j.judge_error });
        return;
      }

      const judgeResult = runJudge(slug, dossier.content);

      const j = readJob(jobId);
      if (judgeResult.ok) {
        j.judge_status = 'done';
        j.mobile_report = formatMobileResponse(slug, judgeResult.result);
        j.judge_scores = judgeResult.result.scores;
        writeJob(jobId, j);
        log.info('judge_ok', { jobId, slug, ms: Date.now() - judgeStart });
      } else {
        j.judge_status = 'failed';
        j.judge_error = judgeResult.error;
        writeJob(jobId, j);
        log.error('judge_fail', { jobId, slug, ms: Date.now() - judgeStart, error: judgeResult.error });
      }
    });
  });

  child.on('error', (spawnErr) => {
    logStream.end();
    const updated = readJob(jobId);
    updated.status = 'failed';
    updated.error = spawnErr.message;
    updated.finishedAt = new Date().toISOString();
    writeJob(jobId, updated);
    log.error('research_spawn_error', { jobId, slug, phase, error: spawnErr.message });
  });

  return jobId;
}

function getJobStatus(jobId) {
  const job = readJob(jobId);
  if (!job) return null;

  // Read last N lines of log for context
  let logTail = '';
  if (fs.existsSync(job.logFile)) {
    const content = fs.readFileSync(job.logFile, 'utf-8');
    const lines = content.split('\n').filter(Boolean);
    logTail = lines.slice(-20).join('\n');
  }

  return { ...job, logTail };
}

function listJobs() {
  return fs.readdirSync(JOBS_DIR)
    .filter(f => f.endsWith('.json'))
    .map(f => {
      try { return JSON.parse(fs.readFileSync(path.join(JOBS_DIR, f), 'utf-8')); } catch (_) { return null; }
    })
    .filter(Boolean)
    .sort((a, b) => b.startedAt.localeCompare(a.startedAt));
}

module.exports = { launchResearch, getJobStatus, listJobs };
