# Contributing to FinChat

Thank you for your interest in contributing to **FinChat**! This guide outlines the development workflow, project architecture, coding standards, and repository conventions to help you get started.

---

## 📋 Table of Contents
- [Project Architecture](#-project-architecture)
- [Development Setup](#-development-setup)
- [Git Contribution Workflow](#-git-contribution-workflow)
- [Coding Standards](#-coding-standards)
- [Submitting Pull Requests](#-submitting-pull-requests)

---

## 🏗️ Project Architecture

FinChat is organized into isolated modules for easy updates and scale:

```text
finchat/
│
├── api_routes/        # FastAPI endpoint definitions (chat, documents, settings)
├── app/               # Frontend source code (HTML, JS, CSS assets)
├── core/              # Global initialization and startup scripts
├── data/              # Stores processed PDFs and raw data
├── ingestion/         # PDF parser, text chunking, and metadata extractor
├── services/          # Core business logic (chat formatting, doc indexer)
├── vector_store/      # FAISS vector store configurations and indexes
├── requirements.txt   # Core project dependencies
└── run.sh             # Startup script
```

---

## 💻 Development Setup

### Prerequisite Tools
- **Python 3.10+**
- **Git**
- **llama.cpp** or **Ollama** running locally

### Local Installation

1. **Fork the Repository**: Fork [kanishk57/finchat](https://github.com/kanishk57/finchat) on GitHub.
2. **Clone Your Fork**:
   ```bash
   git clone https://github.com/kanishk57/finchat.git
   cd finchat
   ```
3. **Configure Remotes**: Add the original repository as `upstream` to stay synchronized:
   ```bash
   git remote add upstream https://github.com/armaan-choudhary/finchat.git
   ```
4. **Create a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
5. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
6. **Launch the Local Development Server**:
   ```bash
   ./run.sh
   ```

---

## 🔀 Git Contribution Workflow

To keep the project clean and history navigable, please follow this workflow:

### 1. Sync Your Branch
Before starting any new feature, pull the latest commits from the original repository:
```bash
git checkout main
git pull upstream main
```

### 2. Create a Feature Branch
Use descriptive branch names with prefixes:
- `feature/` for new features (e.g., `feature/add-bm25-tuning`)
- `bugfix/` for bug fixes (e.g., `bugfix/fix-pdf-highlighting`)
- `docs/` for documentation updates (e.g., `docs/update-contributing-guide`)

```bash
git checkout -b feature/your-feature-name
```

### 3. Make and Commit Changes
Follow clear commit message formats:
* `feat:` for new features
* `fix:` for bug fixes
* `docs:` for documentation updates
* `refactor:` for code refactoring with no behavior changes

Example:
```bash
git commit -m "feat: integrate cross-encoder threshold settings in UI"
```

### 4. Push to Your Fork
```bash
git push origin feature/your-feature-name
```

---

## 🎨 Coding Standards

To maintain clean and legible code, we follow these standards:

### Python Back-End
- Follow **PEP 8** guidelines.
- Use explicit type hinting where possible.
- Wrap complex retrieval logic inside the `services/` layer rather than endpoints.
- Document classes and functions using docstrings.

### Front-End (JavaScript & CSS)
- Maintain Vanilla JS structure; minimize external libraries.
- Use Tailwind utility classes for responsive design.
- Keep state local or handle gracefully in session storage.

---

## 🚀 Submitting Pull Requests

1. Navigate to the original [armaan-choudhary/finchat](https://github.com/armaan-choudhary/finchat) repository on GitHub.
2. Click **Pull Requests** → **New Pull Request**.
3. Choose your fork and branch as the source, and `armaan-choudhary/finchat` `main` as the destination.
4. Provide a clear description of your changes, what issues it addresses, and how it was tested.
5. Submit for review!
