# Contributing to Mantrix Axis AI

Thank you for your interest in contributing to Mantrix Axis AI! This document provides guidelines and standards for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)
- [Common Tasks](#common-tasks)

---

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- Git
- Redis server
- Docker (optional, for services)
- Google Cloud Project with BigQuery
- Anthropic API key
- OpenAI API key

### Initial Setup

1. **Fork the repository** on GitHub

2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mantrix-axis-ai.git
   cd mantrix-axis-ai
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/mantrix-axis-ai.git
   ```

4. **Set up environment**:
   ```bash
   # Backend
   cp backend/.env.example backend/.env
   # Edit backend/.env with your API keys

   # Frontend
   cp frontend/.env.example frontend/.env
   # Edit frontend/.env with your keys
   ```

5. **Install dependencies**:
   ```bash
   # Backend
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Frontend
   cd frontend
   npm install
   ```

6. **Start development environment**:
   ```bash
   ./start_dev.sh
   ```

---

## Development Workflow

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Critical production fixes

### Creating a Feature

1. **Sync with upstream**:
   ```bash
   git checkout main
   git pull upstream main
   ```

2. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make changes** following code standards

4. **Test thoroughly**:
   ```bash
   # Backend tests
   cd backend
   python test_*.py

   # Frontend linting
   cd frontend
   npm run lint
   ```

5. **Commit changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create Pull Request** on GitHub

### Keeping Your Fork Updated

```bash
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
```

---

## Code Standards

### Python Backend

#### Style Guide

- Follow **PEP 8** style guide
- Use **Black** for formatting (line length: 100)
- Use **type hints** for all function signatures
- Write **docstrings** for all public functions/classes (Google style)

#### Example:

```python
from typing import List, Optional
import structlog

logger = structlog.get_logger()


def generate_sql(
    question: str,
    dataset: str,
    conversation_id: Optional[str] = None
) -> dict[str, Any]:
    """Generate SQL query from natural language question.

    Args:
        question: Natural language query
        dataset: BigQuery dataset name
        conversation_id: Optional conversation context ID

    Returns:
        Dictionary containing generated SQL and metadata

    Raises:
        ValueError: If question is empty or invalid
        LLMError: If LLM API call fails
    """
    if not question.strip():
        raise ValueError("Question cannot be empty")

    logger.info("Generating SQL", question=question, dataset=dataset)
    # Implementation
    return {"sql": sql_query, "metadata": {...}}
```

#### Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: `_leading_underscore`
- **Files/modules**: `snake_case.py`

#### Import Organization

```python
# Standard library imports
import os
from typing import List, Dict

# Third-party imports
import structlog
from fastapi import FastAPI

# Local application imports
from src.core.sql_generator import SQLGenerator
from src.config import settings
```

### JavaScript/React Frontend

#### Style Guide

- Follow **Airbnb JavaScript Style Guide**
- Use **Prettier** for formatting
- Use **ESLint** for linting
- Prefer **functional components** with hooks
- Use **PropTypes** or TypeScript for type checking

#### Example:

```jsx
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Box, Typography, Button } from '@mui/material';
import { apiService } from '../services/api';

/**
 * QueryInterface - Main component for executing NLP queries
 */
const QueryInterface = ({ conversationId, onResultsUpdate }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiService.executeQuery(query, { conversationId });
      onResultsUpdate(response.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      {/* Component JSX */}
    </Box>
  );
};

QueryInterface.propTypes = {
  conversationId: PropTypes.string,
  onResultsUpdate: PropTypes.func.isRequired,
};

QueryInterface.defaultProps = {
  conversationId: null,
};

export default QueryInterface;
```

#### Naming Conventions

- **Components**: `PascalCase` (e.g., `QueryInterface.jsx`)
- **Functions/variables**: `camelCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Files**: `PascalCase.jsx` for components, `camelCase.js` for utilities
- **CSS classes**: `kebab-case`

### General Principles

1. **DRY**: Don't Repeat Yourself - Extract common logic
2. **SOLID**: Follow SOLID principles for object-oriented code
3. **Single Responsibility**: One function/class should do one thing well
4. **Error Handling**: Always handle errors gracefully
5. **Logging**: Use structured logging, not print statements
6. **Security**: Never commit secrets, sanitize inputs, validate data

---

## Testing Requirements

### Backend Testing

#### Unit Tests

- Test individual functions/methods in isolation
- Mock external dependencies (databases, APIs)
- Aim for **70%+ code coverage**

```python
import pytest
from src.core.sql_generator import SQLGenerator

def test_generate_sql_with_valid_question():
    """Test SQL generation with valid input"""
    generator = SQLGenerator()
    result = generator.generate("Show me top customers", "test_dataset")

    assert "SELECT" in result["sql"].upper()
    assert result["metadata"]["question"] == "Show me top customers"
```

#### Integration Tests

- Test API endpoints end-to-end
- Use test database/fixtures
- Test authentication and authorization

```python
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_query_endpoint():
    """Test /api/v1/query endpoint"""
    response = client.post(
        "/api/v1/query",
        json={"question": "Show top customers"},
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    assert "sql" in response.json()["data"]
```

### Frontend Testing

#### Component Tests

```jsx
import { render, screen, fireEvent } from '@testing-library/react';
import QueryInterface from './QueryInterface';

test('submits query when button clicked', async () => {
  const mockOnResults = jest.fn();
  render(<QueryInterface onResultsUpdate={mockOnResults} />);

  const input = screen.getByRole('textbox');
  const button = screen.getByRole('button', { name: /submit/i });

  fireEvent.change(input, { target: { value: 'Show customers' } });
  fireEvent.click(button);

  expect(mockOnResults).toHaveBeenCalled();
});
```

### Test File Naming

- Backend: `test_*.py` or `*_test.py`
- Frontend: `*.test.js` or `*.test.jsx`

### Running Tests

```bash
# Backend
cd backend
pytest                     # Run all tests
pytest -v                  # Verbose output
pytest --cov=src          # With coverage
pytest test_specific.py   # Run specific file

# Frontend
cd frontend
npm test                  # Run all tests
npm test -- --coverage   # With coverage
```

---

## Commit Guidelines

### Commit Message Format

Use **Conventional Commits** format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Build process, dependencies, tooling
- `ci`: CI/CD changes

#### Examples

```bash
# Feature
git commit -m "feat(sql-generator): add support for JOIN queries"

# Bug fix
git commit -m "fix(cache): resolve Redis connection timeout issue"

# Documentation
git commit -m "docs(readme): add deployment section"

# With body
git commit -m "feat(agents): implement multi-agent orchestration

Add CrewAI-based agent system for complex analytical workflows.
Agents can collaborate on multi-step financial analysis tasks.

Closes #123"
```

### Commit Best Practices

- Keep commits **atomic** (one logical change per commit)
- Write **descriptive messages** (explain why, not just what)
- Reference issues: `Fixes #123`, `Closes #456`, `Refs #789`
- Limit subject line to 50 characters
- Wrap body at 72 characters
- Use imperative mood ("add" not "added")

---

## Pull Request Process

### Before Submitting PR

1. ✅ Code follows style guidelines
2. ✅ Tests pass locally
3. ✅ New tests added for new features
4. ✅ Documentation updated (README, docstrings, comments)
5. ✅ No merge conflicts with main branch
6. ✅ Commit messages follow conventions
7. ✅ No secrets or sensitive data committed

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe testing performed:
- [ ] Unit tests added/updated
- [ ] Integration tests passed
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally

## Screenshots (if applicable)

## Related Issues
Fixes #issue_number
```

### Review Process

1. **Automated checks** must pass:
   - Linting (Black, ESLint)
   - Tests (pytest, Jest)
   - Type checking (mypy)

2. **Code review** by maintainer:
   - Logic correctness
   - Code quality
   - Test coverage
   - Documentation

3. **Address feedback**:
   - Make requested changes
   - Push updates to same branch
   - Re-request review

4. **Merge**: Squash and merge or rebase

---

## Project Structure

### Backend Structure

```
backend/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings management
│   ├── api/                 # API route handlers
│   │   ├── routes.py        # Main endpoints
│   │   ├── models.py        # Pydantic request/response models
│   │   └── ...
│   ├── core/                # Core business logic
│   │   ├── sql_generator.py
│   │   ├── llm_client.py
│   │   ├── cache_manager.py
│   │   └── knowledge_graph/
│   ├── agents/              # Multi-agent system
│   ├── db/                  # Database clients
│   └── utils/               # Utilities
├── tests/                   # Test files
├── requirements.txt         # Python dependencies
└── .env.example             # Environment template
```

### Frontend Structure

```
frontend/
├── src/
│   ├── main.jsx             # React entry point
│   ├── App.jsx              # Main app component
│   ├── components/          # React components
│   ├── pages/               # Page components
│   ├── services/            # API client, services
│   ├── themes/              # MUI themes
│   └── utils/               # Utilities
├── package.json
├── vite.config.js
└── .env.example
```

---

## Common Tasks

### Adding a New API Endpoint

1. **Define Pydantic model** in `backend/src/api/models.py`:
   ```python
   class QueryRequest(BaseModel):
       question: str
       dataset: Optional[str] = None
   ```

2. **Create route handler** in appropriate file:
   ```python
   @router.post("/your-endpoint")
   async def your_endpoint(request: QueryRequest):
       # Implementation
       return {"data": result}
   ```

3. **Add router** to `main.py` if new file:
   ```python
   from src.api.your_routes import router as your_router
   app.include_router(your_router, prefix="/api/v1")
   ```

4. **Add frontend service** in `frontend/src/services/api.js`:
   ```javascript
   yourEndpoint: (data) => api.post('/api/v1/your-endpoint', data)
   ```

5. **Write tests** for endpoint

6. **Update documentation**

### Adding a New React Component

1. **Create component file** `frontend/src/components/YourComponent.jsx`:
   ```jsx
   import React from 'react';
   import PropTypes from 'prop-types';

   const YourComponent = ({ prop1, prop2 }) => {
     return <div>{/* JSX */}</div>;
   };

   YourComponent.propTypes = {
     prop1: PropTypes.string.isRequired,
     prop2: PropTypes.number,
   };

   export default YourComponent;
   ```

2. **Add tests** `YourComponent.test.jsx`

3. **Import and use** in parent component

### Adding a Database Migration (Future)

```bash
# Once Alembic is set up (Phase 7)
cd backend
alembic revision -m "description of change"
# Edit generated file in alembic/versions/
alembic upgrade head
```

### Running Code Quality Checks

```bash
# Backend
cd backend
black .                    # Format code
flake8 .                   # Lint code
mypy src/                  # Type check

# Frontend
cd frontend
npm run lint              # ESLint
npm run format            # Prettier
```

---

## Questions or Issues?

- Check existing [GitHub Issues](link-to-issues)
- Review [CLAUDE.md](CLAUDE.md) for architecture details
- Read [README.md](README.md) for setup help
- Create new issue with detailed description

---

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow
- Follow the project's best interests

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (ISC License).

---

Thank you for contributing to Mantrix Axis AI! 🚀
