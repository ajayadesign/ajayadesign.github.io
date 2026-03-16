// @ts-check
const { defineConfig, devices } = require('@playwright/test');

const BASE_URL = 'http://127.0.0.1:3011/the-magnet-guy/';

const chromiumArgs = ['--no-sandbox', '--disable-setuid-sandbox'];

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 2,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'desktop-chrome',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: { args: chromiumArgs },
      },
    },
    {
      name: 'mobile-iphone',
      use: {
        ...devices['iPhone 14'],
        defaultBrowserType: 'chromium',            // use chromium instead of webkit
        launchOptions: { args: chromiumArgs },
      },
    },
    {
      name: 'mobile-android',
      use: {
        ...devices['Pixel 7'],
        launchOptions: { args: chromiumArgs },
      },
    },
  ],
  webServer: {
    command: 'python3 -m http.server 3011 --directory /home/aj/website/ajayadesign.github.io',
    url: BASE_URL,
    reuseExistingServer: true,
    timeout: 10000,
  },
});
