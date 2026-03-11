// @ts-check
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  retries: 0,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:8787',
    trace: 'off',
  },
  webServer: {
    command: 'npx http-server . -p 8787 -c-1 --silent --ext html',
    port: 8787,
    reuseExistingServer: false,
  },
});
