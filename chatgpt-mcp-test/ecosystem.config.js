'use strict';

module.exports = {
  apps: [{
    name: 'mcp-server',
    script: 'server.js',
    cwd: '/home/agent/chatgpt-mcp-test',
    env: {
      PORT: '8787',
      MCP_ROOT: '/home/agent/mcp-safe/repo',
      MCP_TOKEN: process.env.MCP_TOKEN  // loaded from shell env at startup
    },
    watch: false,
    restart_delay: 2000,
    max_restarts: 10,
    log_file: '/home/agent/chatgpt-mcp-test/logs/pm2.log',
    error_file: '/home/agent/chatgpt-mcp-test/logs/pm2-error.log',
    out_file: '/home/agent/chatgpt-mcp-test/logs/pm2-out.log',
    merge_logs: true
  }]
};
