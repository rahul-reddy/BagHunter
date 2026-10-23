import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1,
  reporter: [['list'], ['html', {open: 'never'}]],
  use: {baseURL: 'http://127.0.0.1:5173', browserName: 'chromium', trace: 'retain-on-failure'},
  webServer: [
    {command: 'uv run baghunter demo && uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000', cwd: '../..', url: 'http://127.0.0.1:8000/health', reuseExistingServer: !process.env.CI, timeout: 120000},
    {command: 'npm run dev', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI},
  ],
});
