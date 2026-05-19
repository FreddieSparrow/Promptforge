# PromptForge Schools

PromptForge Schools is a school-network edition of PromptForge designed for a **central local QA server**.

Thin clients send requests to one trusted on-premise server. The server runs the local AI/QA stack and applies a school-safe academic integrity policy before answering.

This edition is designed for:

- classrooms
- supervised computer suites
- local school networks
- revision support
- teacher-controlled AI assistance

It is **not** designed for spying on students, bypassing device restrictions, hidden monitoring, or covert control of thin clients.

---

# Architecture

```text
Thin Client Browser
        ↓
School LAN / VLAN
        ↓
PromptForge Schools QA Server
        ↓
Local Ollama / Approved Provider
        ↓
Student-safe response
```

The thin clients only need a browser.

The server handles:

- request validation
- school anti-cheating policy injection
- logging of service health
- model routing
- local AI calls
- teacher/admin configuration

---

# Anti-Cheating Approach

PromptForge Schools should not block learning. It should stop shortcut abuse.

The policy is prompt-based and transparent:

- explain concepts
- give hints
- ask guiding questions
- refuse to write full assessed coursework answers
- refuse exam impersonation
- refuse plagiarism assistance
- encourage original work
- suggest revision steps
- support accessibility and learning needs

It does **not**:

- spy on screens
- capture keystrokes
- hide processes on clients
- bypass school IT controls
- perform surveillance

---

# Network Model

Recommended deployment:

```text
Server IP: 10.0.0.50
Port: 7474
Client URL: http://10.0.0.50:7474
```

Use firewall rules so only the school LAN can access the service.

Do not expose this directly to the public internet.

---

# Recommended Server

Minimum:

- 8-core CPU
- 32GB RAM
- SSD storage
- Ubuntu Server or Debian

For local models:

- NVIDIA GPU recommended
- 12GB+ VRAM preferred

For small schools, CPU-only models may work but will be slower.

---

# Deployment Notes

1. Install Python 3.11+
2. Install Ollama
3. Pull an approved model
4. Configure firewall rules
5. Run PromptForge Schools on the central server
6. Point thin clients to the server URL

Example:

```bash
ollama pull llama3.1:8b
python main.py
```

---

# Teacher/Admin Controls

Recommended future controls:

- approved model list
- banned coursework mode
- exam-mode policy
- classroom mode toggle
- per-room access rules
- teacher override prompts
- audit summaries without invasive monitoring

---

# Safety Position

This project supports learning. It should not be used for covert surveillance.

A proper school deployment should be transparent to students and staff.
