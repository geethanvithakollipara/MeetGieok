# MeetGieok

<p align="center">
  <strong>Remember. Prepare. Connect.</strong>
</p>

> A memory-powered AI meeting preparation agent that remembers your conversations, commitments, follow-ups, and preferences — and uses them to prepare you better for every future meeting.

---

## 🧠 Overview

**MeetGieok** is an AI-powered **Meeting Prep Agent** built around persistent agent memory.

Instead of preparing for every meeting from scratch, MeetGieok remembers what happened in previous meetings with each contact — including:

- 📝 Topics discussed
- 🤝 Decisions and commitments
- ⏳ Missed follow-ups
- 🎯 Unresolved issues
- 💬 Communication preferences
- 📌 Important context from previous interactions

Before the next meeting, MeetGieok recalls relevant history and generates a **personalized meeting preparation brief**.

The more you use MeetGieok, the more context it can use to prepare you for future meetings.

---

## 💡 The Problem

Meeting preparation often means searching through old notes, emails, documents, and messages to remember:

- What did we discuss last time?
- What did I promise?
- What are they waiting for?
- What was left unresolved?
- What should I ask this time?
- Did I miss any follow-up?

A generic AI assistant can generate questions and talking points, but without persistent memory, it does not have the history of the relationship.

**MeetGieok solves this by making memory central to the meeting-preparation workflow.**

---

## 🎯 Our Solution

MeetGieok follows a continuous learning cycle:

```text
Previous Meeting
      ↓
Capture Context
      ↓
Store in Hindsight Memory
      ↓
Recall Relevant History
      ↓
Generate Personalized Preparation
      ↓
Next Meeting
      ↓
Capture New Outcomes
      ↓
Update Memory
      ↺
```

This creates a progressive learning experience:

```text
Interaction 1
     ↓
Generic preparation

Interaction 5
     ↓
More personalized preparation

Interaction 20
     ↓
Deeply contextual preparation
```

---

## ✨ Key Features

### 👤 Contact Memory

MeetGieok maintains a persistent history for each person you interact with.

It can remember:

- Name
- Role
- Company
- Previous meetings
- Communication preferences
- Important context

### 🧠 Persistent Memory with Hindsight

**Hindsight** provides the persistent memory layer for the agent.

MeetGieok retains relevant information from previous interactions and recalls it when preparing for future meetings.

Memory is not just an additional feature — it is a core part of the application.

### 📋 Personalized Meeting Brief

Before a meeting, MeetGieok can generate a preparation brief containing:

- Previous discussion points
- Open items
- Missed commitments
- Important decisions
- Suggested questions
- Recommended talking points
- Relevant historical context

### 🔄 Continuous Learning

After each meeting, new information can be retained.

Future meeting preparation can then use the accumulated history to become increasingly personalized.

### 🔍 Memory Transparency

MeetGieok can surface relevant remembered context behind its recommendations, helping the user understand **why a particular question or talking point was suggested**.

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │      MeetGieok      │
                    │    React Frontend   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Backend / API    │
                    │   Business Logic    │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
       ┌──────────────────┐       ┌──────────────────┐
       │ Hindsight Memory │       │ Structured Data  │
       │                  │       │                  │
       │ Retain           │       │ Contacts         │
       │ Recall           │       │ Meetings         │
       │ Context          │       │ Metadata         │
       └────────┬─────────┘       └──────────────────┘
                │
                ▼
       ┌──────────────────┐
       │     AI / LLM     │
       │    Reasoning     │
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │ Personalized     │
       │ Meeting Brief    │
       └──────────────────┘
```

---

## 🔄 Core Workflow

### 1. Select a Contact

The user selects the person they are meeting.

### 2. Add Meeting Context

The user provides information such as:

- Meeting topic
- Agenda
- Meeting date
- Current objectives

### 3. Recall Memory

MeetGieok retrieves relevant information from previous interactions using Hindsight.

### 4. Generate Preparation

The AI combines the current meeting context with remembered history.

### 5. Conduct the Meeting

The user enters the meeting with relevant context and preparation.

### 6. Retain New Information

After the meeting, outcomes, decisions, commitments, and unresolved items can be added to memory.

### 7. Improve Future Preparation

The next meeting preparation uses the accumulated history.

---

## 🧪 Example

### First Interaction

**Contact:** Sarah — Product Manager

**Meeting:** Product roadmap discussion

MeetGieok has no previous history with Sarah.

It may generate general preparation such as:

```text
Suggested Questions:

• What are the key priorities for the next quarter?
• What are the major product challenges?
• What outcomes are expected from this meeting?
```

### After Several Meetings

MeetGieok has accumulated context such as:

```text
• Sarah prioritizes customer feedback.
• Previous discussion focused on onboarding.
• You promised to share analytics data.
• The analytics data was not shared.
• Pricing concerns were left unresolved.
```

### Next Meeting

MeetGieok can produce a more contextual preparation:

```text
⚠️ Follow-up

You previously committed to sharing onboarding analytics.

🎯 Priority Discussion

Continue the unresolved pricing discussion.

💬 Suggested Question

Ask whether the latest customer-feedback findings
changed the onboarding priorities.

📌 Relationship Context

Previous discussions emphasized customer feedback
when evaluating roadmap decisions.
```

This demonstrates the difference between **generic preparation** and **memory-informed preparation**.

---

## 🧠 Why Hindsight Matters

Hindsight is central to MeetGieok.

Without persistent memory:

```text
Meeting
   ↓
AI
   ↓
Generic Suggestions
```

With persistent memory:

```text
Past Meetings
      ↓
Hindsight Memory
      ↓
Relevant Context
      ↓
AI Reasoning
      ↓
Personalized Preparation
```

As interaction history grows, the agent can use more relevant context when preparing for future meetings.

---

## 🛠️ Technology Stack

### Frontend

- React
- Vite
- TypeScript
- HTML5
- CSS

### Backend

- Python
- Flask
- REST APIs

### AI & Memory

- Hindsight — persistent agent memory
- Large Language Model for meeting preparation

### Data

- Structured database for contacts and meeting metadata
- Hindsight for agent memory and contextual recall

### Development Tools

- Visual Studio Code
- Git
- GitHub
- Postman

---

## 📁 Project Structure

```text
MeetGieok/
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── backend/
│   ├── app/
│   ├── routes/
│   ├── services/
│   ├── models/
│   ├── config/
│   ├── requirements.txt
│   └── ...
│
├── README.md
└── .gitignore
```

> The final project structure may evolve during implementation.

---

## 🎯 Core Design Principles

### Memory First

Memory is a core part of the workflow rather than a secondary feature.

### One Clear Workflow

MeetGieok focuses on one primary task:

> **Prepare me for my next meeting with this person.**

### Personalization Over Generic Answers

The goal is not simply to generate meeting questions. The goal is to generate preparation using the user's actual relationship history.

### Explainable Context

Relevant recommendations should be connected to remembered information wherever possible.

### Progressive Learning

The system should demonstrate a visible difference between:

```text
First Interaction
       ↓
Repeated Interactions
       ↓
Accumulated Relationship Context
       ↓
Better Personalized Preparation
```

---

## 🧪 Testing

Important scenarios to validate:

- Create a new contact
- Create a first meeting
- Generate initial preparation
- Retain meeting outcomes
- Create a second meeting
- Recall relevant previous information
- Generate personalized preparation
- Verify memories remain associated with the correct contact
- Verify new meetings improve future preparation
- Verify unrelated contact information is not incorrectly recalled

---

## 🚀 Getting Started

### Prerequisites

Make sure the following are installed:

- Node.js
- Python 3.x
- Git
- A Hindsight-compatible environment/API
- Required LLM/API credentials

### Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/MeetGieok.git
cd MeetGieok
```

### Start the Backend

```bash
cd backend
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
python app.py
```

### Start the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open the local development URL displayed by Vite.

> The exact setup commands may be updated as the implementation is finalized.

---

## 🔐 Environment Variables

Create a `.env` file for local development.

Example:

```env
HINDSIGHT_API_KEY=your_hindsight_api_key
LLM_API_KEY=your_llm_api_key
```

**Never commit API keys or secrets to GitHub.**

Add `.env` to `.gitignore`:

```gitignore
.env
.venv/
node_modules/
__pycache__/
```

---

## 📊 Expected Behavior

MeetGieok should demonstrate a clear change in behavior as memory accumulates.

### Without Memory

```text
User:
Prepare me for my meeting with Sarah.

AI:
Here are some general questions you could ask...
```

### With Memory

```text
User:
Prepare me for my next meeting with Sarah.

AI:
You previously discussed onboarding with Sarah.
You also committed to sharing analytics, which was
not recorded as completed.

Suggested priorities:
1. Follow up on the analytics commitment.
2. Continue the unresolved pricing discussion.
3. Ask whether onboarding priorities have changed.
```

The second response demonstrates the value of persistent memory.

---

## 🔮 Future Scope

Potential future extensions include:

- 📅 Calendar integration
- 📧 Email integration
- 🎙️ Automatic meeting-note extraction
- 🗣️ Voice/transcript-based memory
- ⏰ Follow-up reminders
- 📈 Meeting outcome analytics
- 🤝 Relationship insights
- 🧠 Multi-agent meeting workflows
- 🏢 Organization/team-level memory

---

## 🌟 Project Vision

MeetGieok is designed around a simple idea:

> **An AI assistant should become more useful as it remembers relevant experience.**

Rather than treating every meeting as an isolated event, MeetGieok builds continuity across interactions.

### Remember.

Relevant information from previous meetings.

### Prepare.

Personalized context for the next conversation.

### Connect.

Better continuity across professional relationships.

---

## 👥 Team

**MeetGieok** is being developed as a collaborative project focused on demonstrating a practical application of persistent AI memory.

---

## 📚 References

- [Hindsight GitHub](https://github.com/vectorize-io/hindsight)
- [Hindsight Documentation](https://hindsight.vectorize.io/)
- [Vectorize — What is Agent Memory?](https://vectorize.io/what-is-agent-memory)

---

## 📄 License

This project is intended for educational, demonstration, and development purposes.

---

**MeetGieok**

*Remember. Prepare. Connect.*
