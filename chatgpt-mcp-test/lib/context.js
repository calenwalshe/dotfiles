'use strict';

const fs = require('fs');
const path = require('path');
const { log } = require('./logger');

const PROJECTS_ROOT = process.env.PROJECTS_ROOT || path.join(process.env.HOME, 'projects');

const SESSION_FILE = path.join(__dirname, '..', '.mcp-session.json');

// In-memory session state — persisted to SESSION_FILE
const session = {
  activeProject: null,   // slug string
  activeProjectPath: null // absolute path
};

// Restore session from disk on module load (server startup)
try {
  if (fs.existsSync(SESSION_FILE)) {
    const saved = JSON.parse(fs.readFileSync(SESSION_FILE, 'utf-8'));
    if (saved && saved.activeProject) {
      session.activeProject = saved.activeProject;
      session.activeProjectPath = saved.activeProjectPath;
      log.info('session_restored', { slug: saved.activeProject });
    } else {
      log.info('session_fresh', {});
    }
  } else {
    log.info('session_fresh', {});
  }
} catch (_) {
  log.info('session_fresh', {});
}

function listProjects() {
  const entries = fs.readdirSync(PROJECTS_ROOT, { withFileTypes: true });
  const projects = [];
  for (const e of entries) {
    if (!e.isDirectory()) continue;
    const projectPath = path.join(PROJECTS_ROOT, e.name);
    const stateFile = path.join(projectPath, '.cortex', 'state.json');
    let cortexState = null;
    if (fs.existsSync(stateFile)) {
      try { cortexState = JSON.parse(fs.readFileSync(stateFile, 'utf-8')); } catch (_) {}
    }
    projects.push({
      slug: e.name,
      path: projectPath,
      hasCortex: cortexState !== null,
      cortexMode: cortexState?.mode || null,
      cortexSlug: cortexState?.slug || null
    });
  }
  return projects;
}

function setActiveProject(slug) {
  const projectPath = path.join(PROJECTS_ROOT, slug);
  if (!fs.existsSync(projectPath)) {
    throw new Error(`Project not found: ${slug} (looked in ${PROJECTS_ROOT})`);
  }
  session.activeProject = slug;
  session.activeProjectPath = projectPath;
  // Persist session to disk so it survives server restarts
  fs.writeFileSync(SESSION_FILE, JSON.stringify({ activeProject: slug, activeProjectPath: projectPath }, null, 2));
  return projectPath;
}

function clearSession() {
  session.activeProject = null;
  session.activeProjectPath = null;
  try { fs.unlinkSync(SESSION_FILE); } catch (_) {}
}

function requireActiveProject() {
  if (!session.activeProject) {
    throw new Error('No active project. Call cortex_set_project first.');
  }
  return { slug: session.activeProject, projectPath: session.activeProjectPath };
}

module.exports = { PROJECTS_ROOT, session, listProjects, setActiveProject, requireActiveProject, clearSession };
