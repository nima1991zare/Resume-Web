# WhatsApp sender

The only piece of the Project Finder that runs on your own PC. It asks the
server for the next message it is allowed to send, sends it through your
WhatsApp session, reports back, and sleeps.

## Read this before you run it

This drives your logged-in WhatsApp Web session with an automated browser.
That is **against WhatsApp's terms of service**, and sending unsolicited
messages in volume to people who never contacted you is exactly the behaviour
their spam detection bans numbers for — permanently, with no appeal that works
in practice.

Nothing in this code can make that safe. It can only make it slower and more
careful than the obvious version:

- **Use a second SIM.** Not the number on your website, not the one existing
  clients use. If a number gets banned, it should be one you can replace.
- **Warm it up first.** Have real conversations on it for a week or two. A
  brand-new number whose first act is 25 messages to strangers is the clearest
  possible signal.
- **Keep the cap low.** 15–25 a day is a working business. 200 is a bot.
- **Watch for blocks.** If people start blocking or reporting you, the message
  is wrong — stop and change it. No cap saves a number that people report.

## Setup

Needs **Node 18 or newer** on the same machine, and that machine online while
it runs.

```bash
cd tools/whatsapp-sender
npm install
cp config.example.json config.json
```

Open `config.json` and set:

| field | what it is |
|---|---|
| `serverUrl` | `https://nimabuilds.pythonanywhere.com`, or `http://127.0.0.1:8000` when testing locally |
| `agentKey` | from **Admin → Project Finder → Autopilot → Sender setup**. Easier: press **Download config.json** there and drop the file in this folder — then `serverUrl` and `agentKey` are already right. |
| `dryRun` | `true` prints each message instead of sending it. **Leave it true for the first run.** |
| `headless` | `false` shows the browser window, which is useful the first time |

Then:

```bash
npm run check     # proves the server half; claims and sends nothing
npm start         # dry run: prints the queue, consumes nothing
npm run send      # actually sends (same as setting "dryRun": false)
```

The first run prints a QR code. Scan it with **WhatsApp → Linked devices →
Link a device**. The session is saved in `.session/`, so this happens once.

If `agentKey` is still the sentence from the example file, the sender stops
immediately and says so — that is the 401 you would otherwise chase later.

## Doing it in the right order

1. **Dry run first**, Autopilot **off** in the panel. `npm start` prints each
   message without claiming it, so nothing is marked sent and the daily cap is
   untouched.
2. Read the queue in the admin panel. Open ten messages and check each one says
   something true about that business. **This is the step that decides whether
   this works at all** — the messages are specific, which is the whole point,
   but a wrong specific claim is worse than a generic one.
3. Set the cap to about 10, turn Autopilot on, and run `npm run send`.
4. Read the replies. Adjust the wording in `app/research.py` if they are not
   landing, then raise the cap slowly.

## What stops it

- The **switch in the admin panel** — the sender is handed nothing while it is
  off, and it notices within seconds.
- **Quiet hours** and the **daily cap**, both server-side.
- **Three failures in a row** — the sender pauses the whole queue by itself,
  because repeated failures usually mean WhatsApp has started refusing you.
- **Ctrl-C**, obviously.

A reply from a business takes that lead out of the queue automatically, and an
opt-out ("stop", "لغو", "مزاحم") is recorded as such. From that point the
conversation is yours — the agent never answers anyone.

## Why the rules live on the server

The sender holds no state. It cannot send faster than the server hands work
out, so running it twice by accident does not double your rate, and a crash
cannot replay a burst — the send times are already written into the queue.

That also means the agent key is a credential. Anyone holding it can read your
outbox and pause your queue. It is not in git; keep it that way.
