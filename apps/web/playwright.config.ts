import { defineConfig } from '@playwright/test';
import { apiPort, webPort } from './serverPorts';

export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1,
  reporter: [['list'], ['html', {open: 'never'}]],
  use: {baseURL: `http://127.0.0.1:${webPort}`, browserName: 'chromium', trace: 'retain-on-failure'},
  webServer: [
    {command: `uv run baghunter demo && uv run uvicorn apps.api.main:app --host 127.0.0.1 --port ${apiPort}`, cwd: '../..', url: `http://127.0.0.1:${apiPort}/health`, reuseExistingServer: !process.env.CI, timeout: 120000},
    {command: 'npm run dev', url: `http://127.0.0.1:${webPort}`, reuseExistingServer: !process.env.CI},
  ],
});
