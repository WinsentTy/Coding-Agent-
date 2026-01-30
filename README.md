# Coding Agents

Система автономных AI-агентов для автоматизации процесса разработки программного обеспечения.

## 🎯 Ключевые компоненты

- **Code Agent** — автоматически анализирует Issue, генерирует исправления кода, коммитит и создаёт Pull Request
- **Reviewer Agent** — проверяет Pull Request, анализирует CI pipeline, проводит code review и публикует структурированный отзыв
- **Feedback Loop** — автоматическая итерация исправлений с защитой от бесконечных циклов

## ✨ Особенности

| Функция | Описание |
|---------|----------|
| **Repository Map** | Автоматическое построение карты репозитория с AST-анализом Python файлов |
| **Pre-commit валидация** | Проверка синтаксиса и linting (ruff) перед коммитом |
| **Защита от циклов** | Лимит в 3 попытки для каждого этапа |
| **CI Jobs проверка** | Интеграция с GitHub Checks API для проверки статуса pipeline |
| **Structured Reviews** | Вывод в формате JSON для машинной обработки |

## 🚀 Быстрый старт (одна команда)

```bash
# Клонируйте репозиторий
git clone https://github.com/WinsentTy/coding-agent.git
cd coding-agent

# Создайте файл .env с вашими ключами
# GITHUB_TOKEN, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

# Запустите агент для обработки Issue
docker-compose run --rm agent python -m code_agent.main \
  --issue-id 1 \
  --repo "owner/repo"
```

## 📦 Установка

### Вариант 1: Docker (рекомендуется)

```bash
# Сборка образа
docker-compose build

# Запуск Code Agent
docker-compose run --rm agent python -m code_agent.main \
  --issue-id <ISSUE_NUMBER> \
  --repo "owner/repo"

# Запуск Reviewer Agent
docker-compose run --rm agent python -m reviewer_agent.main
```

### Вариант 2: Локальная установка

```bash
# Установка зависимостей через Poetry
pip install poetry
poetry install

# Запуск Code Agent
poetry run python -m code_agent.main --issue-id 1 --repo "owner/repo"

# Запуск Reviewer Agent
poetry run python -m reviewer_agent.main
```

## 🔄 CI/CD Pipeline

### Автоматический запуск через GitHub Actions

Добавьте workflow файл `.github/workflows/agents.yml` в ваш репозиторий:

```yaml
name: AI Code Agents

on:
  issues:
    types: [opened, labeled]
  pull_request:
    types: [opened, synchronize]

jobs:
  code-agent:
    if: contains(github.event.issue.labels.*.name, 'agent')
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - run: pip install poetry
      
      - run: |
          git clone https://github.com/WinsentTy/coding-agent.git /tmp/agents
          cd /tmp/agents && poetry install --no-interaction
      
      - run: |
          git config --global user.name "AI Agent"
          git config --global user.email "agent@example.com"
      
      - env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          LLM_BASE_URL: ${{ secrets.LLM_BASE_URL }}
        working-directory: /tmp/agents
        run: |
          poetry run python -m code_agent.main \
            --repo "${{ github.repository }}" \
            --issue-id ${{ github.event.issue.number }}
```

### Триггеры

| Событие | Агент | Условие |
|---------|-------|---------|
| Issue создан/labeled | Code Agent | Label `agent` |
| PR создан/обновлён | Reviewer Agent | Автоматически |

## 🧪 Тестирование

```bash
# Запуск всех тестов
poetry run pytest tests/ -v

# Запуск с покрытием
poetry run pytest tests/ -v --cov=src
```

## 📁 Структура проекта

```
coding-agent/
├── src/
│   ├── code_agent/          # Агент генерации кода
│   │   ├── cli.py           # CLI интерфейс
│   │   ├── main.py          # Entry point
│   │   └── service.py       # Бизнес-логика
│   ├── reviewer_agent/      # Агент code review
│   │   ├── cli.py           # CLI интерфейс
│   │   ├── main.py          # Entry point
│   │   └── service.py       # Логика ревью
│   └── shared/              # Общие компоненты
│       ├── llm.py           # LLM клиент
│       ├── diff_manager.py  # Работа с diff
│       └── utils.py         # Утилиты
├── tests/                   # Unit и integration тесты
├── Dockerfile               # Multi-stage Docker сборка
├── docker-compose.yml       # Конфигурация контейнеров
└── pyproject.toml           # Poetry конфигурация
```

## 🛡️ Защита от бесконечных циклов

- **Лимит итераций**: максимум 3 попытки на валидацию кода
- **История фидбеков**: хранение последних 3 комментариев
- **Уникальные ветки**: timestamp в названии ветки предотвращает конфликты
