# Contributing to Video Encoder GUI

First off, thanks for thinking about contributing! We're excited to have you here. Whether you're a seasoned developer or just getting started, there's a place for you in this project.

## Code of Conduct

Please note that this project is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you're expected to uphold it. We're committed to making this a welcoming, harassment-free space for everyone.

## What Can You Contribute?

- **Bug reports and fixes** — Found a crash? Encoding quirk? Let us know or send a fix
- **New features** — Got an idea to make encoding smoother or add capability? We're listening
- **Documentation** — Spotted unclear docs? Help us clarify it for the next person
- **UI/UX improvements** — Ideas to make the interface more intuitive?
- **Cross-platform testing** — Test on Windows, macOS, or Linux and report issues
- **Translations** — Help make the app accessible in other languages
- **Code review** — Review PRs and give thoughtful feedback

All contributions are valued, regardless of size.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- git
- A code editor (VS Code, PyCharm, vim, whatever you like)

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub and clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ffmpeg_encode.git
   cd ffmpeg_encode
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   ```
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify the setup** by running the app:
   ```bash
   python src/main.py
   ```
   The GUI should launch without errors. If something's missing (FFmpeg, HandBrake, etc.), the app will help you install it.

## How to Contribute

### Reporting Bugs

Found something broken? Create an issue with:
- What you were trying to do
- What happened (include error messages if available)
- What you expected to happen
- Your OS and Python version
- Steps to reproduce

Check existing issues first to avoid duplicates. If a similar issue exists, add your details there.

### Suggesting Features

Have an idea? Open an issue to discuss it before diving into code. This helps us align on scope and approach. Sometimes a feature needs design discussion before implementation.

### Code Contributions

#### Making Changes

1. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```
   Use `feature/`, `fix/`, `docs/`, or `test/` prefixes to make the purpose clear.

2. **Make focused changes**. Each commit should do one thing well:
   - Keep commits atomic — one feature per commit when possible
   - Write clear commit messages (imperative mood: "Add subtitle detection" not "Added subtitle detection")
   - Reference related issues in your commit if applicable

3. **Test your changes** locally:
   - Verify the GUI launches and your changes work as expected
   - For new features, add unit tests if possible (see below)
   - Test on multiple platforms if you can (at least mention which OS you tested on)

4. **Push to your fork** and create a pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

#### Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) conventions
- Use meaningful variable and function names
- Keep functions focused and reasonably sized
- Add comments only where logic isn't obvious
- Follow the existing code patterns in the module you're modifying

The project uses:
- `src/gui/` — PyQt6 interface code
- `src/core/` — Encoding logic, preset parsing, track analysis
- `src/utils/` — Helper functions and utilities
- `src/storage/` — Data models and persistence

#### Testing

Unit tests help ensure reliability. If you're adding a feature:
- Check if there are existing tests in the repository
- Add tests for your new functionality if possible
- Keep tests focused and fast
- Run tests locally before pushing

To run tests (if configured):
```bash
pytest  # or your project's test command
```

### Documentation

Documentation lives in:
- **README.md** — Main overview and quick start
- **USAGE.md** — Detailed usage guide
- **wiki/** — In-depth guides (Installation, Troubleshooting, Building)

To improve docs:
1. Edit the relevant file or create a new one in `wiki/`
2. Check your formatting (markdown syntax)
3. Test links if you added any
4. Submit a PR with your changes

## Pull Request Process

1. **Keep PRs focused** — One feature or fix per PR. Avoid mixing refactoring with new features.

2. **Write a clear title and description**:
   - Title: Short, descriptive (e.g., "Add SRT subtitle support to subtitle policy")
   - Description: Explain *why* this change is needed and *what* it does
   - Reference related issues: "Fixes #42" or "Relates to #38"

3. **Be open to feedback**. Code review is a learning opportunity, not criticism. We'll discuss tradeoffs, suggest improvements, and iterate together.

4. **Ensure tests pass**. We use GitHub Actions to run checks automatically. All tests must pass before merge.

5. **Keep commits clean**. If feedback requires changes, feel free to add new commits or squash them — whatever keeps the history clear.

6. **Be patient**. We review PRs thoughtfully. If it's been a week with no response, feel free to ping us.

## Development Workflow Overview

### File Organization
- `src/main.py` — Application entry point
- `src/gui/main_window.py` — Main window and tab management
- `src/gui/tabs/` — Individual tab implementations
- `src/core/encoder.py` — FFmpeg/HandBrake encoding orchestration
- `src/core/preset_parser.py` — HandBrake preset handling
- `src/core/track_analyzer.py` — Audio/subtitle track detection
- `src/storage/` — Settings persistence, stats storage
- `tests/` — Unit tests (if present)

### Running the App
```bash
python src/main.py
```

### Building Executables
The project uses PyInstaller with GitHub Actions for automated builds. For manual builds:
```bash
pip install pyinstaller
pyinstaller build.spec
```
The executable will be in `dist/ffmpeg_encode/`.

## Questions?

- **Questions about contributing?** Open an issue or discussion
- **Want to chat?** Email the maintainer: ryahn@ffmpeg-encode.com
- **Check the wiki** — You might find answers in [Installation](wiki/Installation.md), [Usage Guide](wiki/Usage-Guide.md), or [Troubleshooting](wiki/Troubleshooting.md)

## License

By contributing to this project, you agree that your contributions will be licensed under the [MIT License](LICENSE). This means your work can be used, modified, and distributed freely by anyone.

---

Thanks for making video encoding better! 🎬
