import { StitchToolClient, Stitch } from '/home/agent/.nvm/versions/node/v20.20.0/lib/node_modules/@google/stitch-sdk/dist/src/index.js';
import { writeFileSync } from 'fs';

const apiKey = process.env.STITCH_API_KEY;
if (!apiKey) {
  console.error('Error: STITCH_API_KEY not found in environment.');
  process.exit(1);
}

const client = new StitchToolClient({ apiKey });

console.log('Client created. Creating project...');
const projectRaw = await client.callTool('create_project', { title: 'stitch-smoke-test' });
const projectId = projectRaw.name?.replace('projects/', '') || projectRaw.projectId;
console.log('Project created:', projectId);

console.log('Generating login form screen...');
const genRaw = await client.callTool('generate_screen_from_text', {
  projectId,
  prompt: 'A simple login form with email and password fields and a submit button'
});

// Find the design component with screens
const designComponent = genRaw.outputComponents?.find(c => c.design?.screens?.length > 0);
if (!designComponent) {
  console.error('Error: No design component with screens found in response.');
  console.error('outputComponents:', JSON.stringify(genRaw.outputComponents?.map(c => Object.keys(c)), null, 2));
  process.exit(1);
}

const screenData = designComponent.design.screens[0];
const screenId = screenData.name?.split('/').pop() || screenData.screenId;
console.log('Screen generated, ID:', screenId);

console.log('Fetching screen HTML...');
const screenRaw = await client.callTool('get_screen', {
  projectId,
  screenId,
  name: `projects/${projectId}/screens/${screenId}`
});

// htmlCode is an object with a downloadUrl pointing to the actual HTML content
const htmlCodeField = screenRaw.htmlCode;
if (!htmlCodeField || !htmlCodeField.downloadUrl) {
  console.error('Error: htmlCode field missing or has no downloadUrl.');
  console.error('Screen raw keys:', Object.keys(screenRaw));
  process.exit(1);
}

console.log('Downloading HTML from:', htmlCodeField.downloadUrl.slice(0, 80) + '...');
const htmlResponse = await fetch(htmlCodeField.downloadUrl);
if (!htmlResponse.ok) {
  console.error('Error: Failed to download HTML. Status:', htmlResponse.status);
  process.exit(1);
}
const html = await htmlResponse.text();

if (!html || html.length === 0) {
  console.error('Error: HTML output was empty after download.');
  process.exit(1);
}

console.log('--- HTML OUTPUT ---');
console.log(html.slice(0, 500));
console.log(`--- TRUNCATED (total ${html.length} chars) ---`);

writeFileSync('/home/agent/stitch-output.html', html);
console.log('Full output saved to /home/agent/stitch-output.html');
