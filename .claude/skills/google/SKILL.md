# Google — Gmail, Drive, Stitch

Google services skill. Routes to Gmail (read/send email), Google Drive (read public files), or Stitch (generate UI components). Works in any session independent of Cortex state.

## User-invocable

When the user types `/google`, run this skill.

Also trigger — WITHOUT requiring the slash command — when the user says any of:
- "read my email", "check my inbox", "what emails do I have", "show my latest emails", "search my email for" (→ Gmail IMAP read)
- "send an email", "email X", "send a message to", "compose an email" (→ Gmail SMTP send)
- "read this Drive file", "open this Google Drive link", "get the content of this Drive doc" (→ Google Drive)
- "generate a UI", "build a component with Stitch", "use Stitch to create", "generate a form", "generate a dashboard" (→ Stitch)

## Arguments

- `/google mail read [--count N] [--search <query>]` — read inbox (default 10 most recent) or search emails
- `/google mail send --to <addr> --subject <subject> --body <body>` — send an email
- `/google drive read <url>` — read a public Google Drive file
- `/google stitch <description>` — generate a UI component via Stitch SDK
- `--save <path>` — write output to file (optional; defaults to chat)

## Instructions

### Routing logic

| User intent | Tool |
|---|---|
| Read email / check inbox / search email | Gmail IMAP |
| Send email / compose message | Gmail SMTP |
| Google Drive file URL provided | Google Drive API |
| Generate UI / build component / Stitch | Stitch SDK |

### Gmail — Read (IMAP)

Credentials at `~/.gmail_creds.json` — format: `{"email": "...", "password": "..."}` (app password).

```python
import imaplib, email, json

with open(os.path.expanduser('~/.gmail_creds.json')) as f:
    creds = json.load(f)

mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login(creds['email'], creds['password'])
mail.select('inbox')

_, data = mail.search(None, 'ALL')
ids = data[0].split()[-count:]  # most recent N

for uid in reversed(ids):
    _, msg_data = mail.fetch(uid, '(RFC822)')
    msg = email.message_from_bytes(msg_data[0][1])
    print(f"From: {msg['From']}\nSubject: {msg['Subject']}\nDate: {msg['Date']}\n")
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                print(part.get_payload(decode=True).decode())
    else:
        print(msg.get_payload(decode=True).decode())
    print('---')

mail.logout()
```

For search: replace `mail.search(None, 'ALL')` with `mail.search(None, f'SUBJECT "{query}"')` or `mail.search(None, f'FROM "{query}"')`.

### Gmail — Send (SMTP)

```python
import smtplib, json
from email.mime.text import MIMEText

with open(os.path.expanduser('~/.gmail_creds.json')) as f:
    creds = json.load(f)

msg = MIMEText(body)
msg['Subject'] = subject
msg['From'] = creds['email']
msg['To'] = to_addr

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
    server.login(creds['email'], creds['password'])
    server.send_message(msg)

print(f"Email sent to {to_addr}")
```

### Google Drive (public files only — v1)

```python
import os, requests

# Extract file ID from URL (format: /d/{FILE_ID}/)
file_id = url.split('/d/')[1].split('/')[0]
api_key = os.environ.get('GOOGLE_API_KEY', '')

resp = requests.get(
    f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={api_key}'
)
print(resp.text)
```

**Note:** Google Drive access is limited to publicly shared files in v1. Private files require OAuth2, which is not currently configured. If the file is private, output: `Drive v1 limitation: this file requires OAuth2 access, which is not yet configured. Only public files are supported.`

### Stitch SDK

Requires `STITCH_API_KEY` in environment. SDK is ESM-only — use `import`, not `require`.
Global install: `npm install -g @google/stitch-sdk`
Import path: `/home/agent/.nvm/versions/node/v20.20.0/lib/node_modules/@google/stitch-sdk/dist/src/index.js`

```javascript
// stitch-gen.mjs (save and run with: node stitch-gen.mjs)
import { StitchToolClient } from '/home/agent/.nvm/versions/node/v20.20.0/lib/node_modules/@google/stitch-sdk/dist/src/index.js';
import { writeFileSync } from 'fs';

const client = new StitchToolClient({ apiKey: process.env.STITCH_API_KEY });

// 1. Create project
const projectRaw = await client.callTool('create_project', { title: 'my-project' });
const projectId = projectRaw.name?.replace('projects/', '') || projectRaw.projectId;

// 2. Generate screen from text prompt
const genRaw = await client.callTool('generate_screen_from_text', {
  projectId,
  prompt: description  // e.g. "A login form with email and password fields"
});

// 3. Find design component with screens
const designComponent = genRaw.outputComponents?.find(c => c.design?.screens?.length > 0);
const screenData = designComponent.design.screens[0];
const screenId = screenData.name?.split('/').pop() || screenData.screenId;

// 4. Get screen — htmlCode is { downloadUrl: "..." }, not a string
const screenRaw = await client.callTool('get_screen', {
  projectId, screenId,
  name: `projects/${projectId}/screens/${screenId}`
});
const htmlResponse = await fetch(screenRaw.htmlCode.downloadUrl);
const html = await htmlResponse.text();

// 5. Output
console.log(html.slice(0, 500));
writeFileSync('stitch-output.html', html);  // or use --save path
```

If `STITCH_API_KEY` is not set: `Error: STITCH_API_KEY not found in environment. Add to ~/agent-stack/.env.`

**Working reference:** `/home/agent/stitch-test.js` (confirmed working, full error handling).

### --save flag

If `--save <path>` provided, write output to that path. Relative paths resolve from CWD.
If omitted, output goes to chat.

### Error handling

Credential errors: `Error: Gmail credentials not found or invalid at ~/.gmail_creds.json`
Missing env vars: `Error: {KEY_NAME} not found in environment.`
No tracebacks.

## Rules

- Never attempt to access private Drive files — surface the v1 limitation message clearly.
- Always confirm before sending email: show To, Subject, and first 100 chars of body, ask "Send? (yes/no)".
- Stitch output is HTML — display inline in chat or save with --save.
