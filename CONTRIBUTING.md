# Contributing to NCKH - Trọ CTU

First off, thank you for considering contributing to this project! It's people like you that make this tool great.

## Getting Started

1. **Clone the repository** locally.
2. **Setup Environment**:
   - Run `cp .env.example .env`.
3. **Run the Project with Docker**:
   - Run `docker compose up --build`.
   - Database migrations and sample data (Seed Data) will be loaded automatically on first boot.
   - Access Backend at `http://localhost:8000/docs`
   - Access Frontend at `http://localhost:3000`

4. **Reset Database & Seed Data (Optional)**:
   - Windows: Run `.\infra\db\reset_and_seed.ps1`
   - Linux/Mac: Run `./infra/db/reset_and_seed.sh`
   - Test accounts (Password: `123456`):
     - Admin: `admin@ctu.edu.vn`
     - Sinh viên K47: `nguyenvana@ctu.edu.vn` (MSSV: `B2101234`)
     - Sinh viên K48: `tranthib@ctu.edu.vn` (MSSV: `B2205678`)
     - Chủ trọ: `chutro.xuanhuong@gmail.com`


## Branching Strategy

- `main` is our main production branch.
- For new features or bugs, create a new branch from `main` using the convention:
  - `feature/<feature-name>` for features
  - `bugfix/<bug-name>` for bug fixes
  - `hotfix/<hotfix-name>` for urgent fixes

## Commit Messages

We use standard commit messages:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting, missing semi colons, etc
- `refactor:` for refactoring code
- `test:` for adding missing tests
- `chore:` for updating build tasks, package manager configs, etc

## Pull Requests

1. Ensure your code follows the `.editorconfig` standards.
2. Ensure you have tested your code locally using pytest and frontend linting.
3. Create a Pull Request against the `main` branch.
4. Fill out the Pull Request template completely.
5. Request a review from at least one other team member.
