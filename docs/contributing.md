# Contributing

`torrra` is an open-source project, and we warmly welcome contributions from the community! Whether you're reporting a bug, suggesting a new feature, or submitting code, your efforts help make `torrra` better for everyone.

This guide will help you get started with contributing to the project.

## How to Contribute

### 1. Reporting Bugs

If you find a bug, please help us by reporting it. A good bug report is crucial for us to understand and fix the issue quickly.

Before opening a new issue, please check the [existing issues](https://github.com/stabldev/torrra/issues) to see if the bug has already been reported.

When reporting a bug, please include:

- **Clear Description:** A concise explanation of the problem.
- **Steps to Reproduce:** Detailed steps that allow others to reliably reproduce the bug.
  1.  `Command or action 1`
  2.  `Command or action 2`
  3.  `...`
- **Expected Behavior:** What you expected `torrra` to do.
- **Actual Behavior:** What `torrra` actually did.
- **Environment:** Your operating system, Python version, `torrra` version, and how you installed `torrra` (e.g., `pipx`, Docker, standalone binary).
- **Screenshots/GIFs:** If applicable, a screenshot or GIF (like the one in the main README) can be very helpful.

You can open a bug report here: [Open a new issue](https://github.com/stabldev/torrra/issues/new?template=bug_report.yml).

### 2. Suggesting Features

We're always looking for ideas to improve `torrra`! If you have a feature in mind, please open an issue to suggest it.

Before suggesting a new feature, please check the [existing issues](https://github.com/stabldev/torrra/issues) and the [Roadmap](roadmap) to see if it's already being discussed or planned.

When suggesting a feature, please include:

- **Clear Description:** Explain the feature in detail.
- **Problem Solved:** What problem does this feature solve, or what new functionality does it add?
- **Use Case:** How would a user typically use this feature?
- **Potential Benefits:** Why do you think this feature would be valuable?

You can open a feature request here: [Open a new issue](https://github.com/stabldev/torrra/issues/new?template=feature_request.yml).

### 3. Submitting Pull Requests (Code Contributions)

Code contributions are highly appreciated! If you want to fix a bug, implement a new feature, or improve existing code, please follow these steps:

1.  **Fork the Repository:** Click the "Fork" button on the [GitHub repository page](https://github.com/stabldev/torrra).
2.  **Clone Your Fork:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/torrra.git
    cd torrra
    ```
3.  **Set Up Development Environment:** `torrra` uses `uv` for dependency management, which is fast and efficient.
    ```bash
    uv sync # This installs all dependencies and sets up the project
    ```
    You can then run `torrra` from your development setup:
    ```bash
    uv run torrra
    ```
4.  **Create a New Branch:** Always work on a new branch for your changes.
    ```bash
    git checkout -b feature/your-feature-name # for new features
    # or
    git checkout -b bugfix/issue-number # for bug fixes
    ```
5.  **Make Your Changes:** Implement your bug fix or feature.
    - Adhere to [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines.
    - Write clear, concise, and well-commented code.
    - Add or update tests as appropriate to cover your changes.
6.  **Commit Your Changes:** Write clear and descriptive commit messages.
    ```bash
    git add .
    git commit -m "feat: Add new awesome feature"
    # or
    git commit -m "fix: Resolve issue #123 with download manager"
    ```
7.  **Push to Your Fork:**
    ```bash
    git push origin feature/your-feature-name
    ```
8.  **Open a Pull Request (PR):**
    - Go to your forked repository on GitHub.
    - Click the "Compare & pull request" button.
    - Provide a clear title and description for your PR.
    - Reference any related issues (e.g., "Closes #123" or "Fixes #456").
    - Be prepared to discuss your changes and make any requested revisions.

## Code Style and Guidelines

- **Python PEP 8:** Please follow the official Python style guide.
- **Type Hinting:** Use type hints where appropriate for better code clarity and maintainability.
- **Docstrings:** Add clear docstrings to functions, classes, and modules.
- **Testing:** New features and bug fixes should ideally be accompanied by tests.

## License

By contributing to `torrra`, you agree that your contributions will be licensed under the project's **MIT License**.
