const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

const apiKey = process.env.OPENAI_API_KEY;
const baseUrl = process.env.OPENAI_BASE_URL || 'https://api.openai.com/v1';
const model = process.env.OPENAI_MODEL || 'gpt-4o';

/**
 * A tiny Open Source clone of ZeroStep using Claude/OpenAI
 * 
 * @param {string} prompt - The natural language instruction (e.g. "Click the Login button")
 * @param {object} options - Options containing the Playwright page object and the test string
 */
async function ai(prompt, { page }) {
    // 1. Scrape the active, interactive DOM elements on the current page
    const elementsJSON = await page.evaluate(() => {
        const interactables = Array.from(document.querySelectorAll('button, input, a, select, textarea, [role="button"]'));
        return interactables.map((el, index) => {
            // Find a usable CSS selector (ID is best, then fallback to traits)
            let selector = '';
            if (el.id) {
                selector = `#${el.id}`;
            } else if (el.name) {
                selector = `${el.tagName.toLowerCase()}[name="${el.name}"]`;
            } else {
                // Fallback to text or type if no ID exists
                selector = `${el.tagName.toLowerCase()}[type="${el.type || ''}"]`;
            }

            return {
                index,
                tag: el.tagName.toLowerCase(),
                id: el.id,
                text: el.innerText || el.value || el.placeholder || '',
                type: el.type || null,
                selector: selector
            };
        }).filter(e => e.text || e.id || e.type);
    });

    // 2. Call the LLM to process the request
    const systemPrompt = `You are a Playwright automation assistant. 
Here is a list of interactive elements on the current web page (in JSON): 
${JSON.stringify(elementsJSON)}

The user wants to perform the following action: "${prompt}"

Your job is to figure out EXACTLY which element the user means, and what action to perform on it.
You must respond with ONLY a raw JSON object string (nothing else, no markdown fences) containing:
1. "action": either "click", "fill", "press", or "wait"
2. "selector": the exact Playwright CSS selector (from the list above)
3. "value": the string to type/fill (if action is "fill", otherwise null)

Example response:
{"action": "fill", "selector": "#some-random-id", "value": "hello_world"}`;

    // Use fetch to bypass SDK requirements (OpenAI/OpenRouter API example)
    const response = await fetch(`${baseUrl}/chat/completions`, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${apiKey}`,
            "content-type": "application/json"
        },
        body: JSON.stringify({
            model: model,
            temperature: 0,
            messages: [
                { role: "system", "content": systemPrompt },
                { role: "user", "content": prompt }
            ]
        })
    });

    const data = await response.json();

    if (data.error) {
        console.error("LLM Error:", data.error);
        throw new Error(`LLM API Error: ${data.error.message}`);
    }

    // Parses the response: {"action": "fill", "selector": "...", "value": "..."}
    const llmText = data.choices[0].message.content.replace(/```json|```/g, '').trim();
    const decision = JSON.parse(llmText);

    console.log(`🤖 nix-ai executing: ${decision.action} on "${decision.selector}" ${decision.value ? 'with "' + decision.value + '"' : ''}`);

    // 3. Execute the Playwright Action Natively!
    const locator = page.locator(decision.selector).first();
    await locator.waitFor({ state: 'attached', timeout: 5000 }).catch(() => { });

    if (decision.action === 'click') {
        await locator.click();
    } else if (decision.action === 'fill') {
        await locator.fill(decision.value);
    } else if (decision.action === 'press') {
        await locator.press(decision.value);
    }
}

module.exports = { ai };
