const { test, expect } = require('@playwright/test');
const { ai } = require('./nix-ai.js');

test('Log in to the app (THIN-19)', async ({ page }) => {
    // Navigate to the application login page
    await page.goto('https://web.test.evergreen.run/auth/login');

    // Verify that the login page has loaded
    await expect(page).toHaveURL(/.*login/);

    // Use ZeroStep AI agent to handle the interactions based on natural language
    await ai('Enter ezplustest2@yopmail.com into the email field', { page, test });

    // Wait for a brief moment for the 'Next' button to be enabled (if there's a React transition)
    await page.waitForTimeout(1000);

    await ai('Click the next button', { page, test });

    // Wait for the password UI to load
    await page.waitForTimeout(1000);

    // Enter the password
    await ai('Enter Test@1234 into the password field', { page, test });
    await page.waitForTimeout(500); // brief pause

    // Submit the form
    await ai('Click the login or submit button', { page, test });

    // Finally, wait for the app to authenticate and redirect to the home page Let's just wait for URL change
    // We can do this traditionally or with AI, but traditionally is faster for assertions
    await expect(page).not.toHaveURL(/.*login/, { timeout: 15000 });

    console.log('Login successful! Home page reached.');
});
