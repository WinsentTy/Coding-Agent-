# Отчёт по работе AI-агентов и системы SDLC

## Информация о решении

| Параметр | Значение |
|----------|----------|
| **Репозиторий** | https://github.com/WinsentTy/coding-agent |
| **Тестовый репозиторий** | https://github.com/WinsentTy/ms-test-2 |
| **Облачное развёртывание** | Yandex Cloud VM: `158.160.54.8` |

---

## Архитектура SDLC Pipeline

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│   Issue     │────▶│  Code Agent  │────▶│  Pull Request │────▶│   Reviewer   │
│  (labeled)  │     │              │     │               │     │    Agent     │
└─────────────┘     └──────────────┘     └───────────────┘     └──────────────┘
                           │                      │                    │
                           ▼                      ▼                    ▼
                    ┌──────────────┐       ┌───────────┐        ┌───────────┐
                    │ LLM (Claude) │       │ CI Checks │        │  Review   │
                    │ Plan + Code  │       │  (Ruff)   │        │  Comment  │
                    └──────────────┘       └───────────┘        └───────────┘
```

---

## Компоненты системы

### Code Agent
- **Назначение**: Автоматическая генерация кода по описанию Issue
- **Триггер**: Issue с label `agent`
- **Функции**:
  - Анализ структуры репозитория (Repository Map)
  - Генерация плана исправления через LLM
  - Генерация кода с полным контекстом файлов
  - Pre-commit валидация (синтаксис + ruff linting)
  - Автоматическое создание Pull Request

### Reviewer Agent
- **Назначение**: Автоматический code review Pull Request'ов
- **Триггер**: Создание/обновление Pull Request
- **Функции**:
  - Анализ diff изменений
  - Проверка статуса CI pipeline
  - LLM-анализ качества кода
  - Публикация структурированного отзыва

---

## Соответствие требованиям

| Требование | Реализация |
|------------|------------|
| GitHub-репозиторий | https://github.com/WinsentTy/coding-agent |
| GitHub Actions workflow | `.github/workflows/agents.yml` |
| Примеры Issues | см. https://github.com/WinsentTy/ms-test-2/issues |
| Примеры Pull Requests | см. https://github.com/WinsentTy/ms-test-2/pulls |
| Отчёт по SDLC | Данный документ |

---

## Примеры работы системы

### Тестовый репозиторий (ms-test-2)
- **Репозиторий**: https://github.com/WinsentTy/ms-test-2
- **Issues**: https://github.com/WinsentTy/ms-test-2/issues
- **Pull Requests**: https://github.com/WinsentTy/ms-test-2/pulls
- **Actions**: https://github.com/WinsentTy/ms-test-2/actions

### Open Source проект (fork requests)
- **Репозиторий**: https://github.com/WinsentTy/requests
- **Описание**: Форк популярной HTTP библиотеки `requests` (52k+ ⭐)
- **Задача**: Работа агента с реальной кодовой базой production-уровня
- **Результат**: Агент успешно проанализировал структуру проекта и сгенерировал корректные изменения
- **Issues**: https://github.com/WinsentTy/requests/issues
- **Pull Requests**: https://github.com/WinsentTy/requests/pulls

---

## Механизмы защиты

| Механизм | Описание |
|----------|----------|
| **Лимит итераций** | Максимум 3 попытки на валидацию кода |
| **Pre-commit проверки** | Синтаксис Python + ruff linting |
| **Уникальные ветки** | Timestamp в названии ветки предотвращает конфликты |
| **Graceful fallback** | При отсутствии ruff проверка пропускается |

---

## GitHub Actions Workflows

### agents.yml (основной)
```yaml
on:
  issues:
    types: [opened, labeled]   # Триггер Code Agent
  pull_request:
    types: [opened, synchronize]  # Триггер Reviewer Agent
```

### Permissions
- `contents: write` — создание веток и коммитов
- `pull-requests: write` — создание PR и комментариев
- `issues: write` — работа с Issues

---

## Запуск решения

### Вариант 1: Docker (одна команда)
```bash
git clone https://github.com/WinsentTy/coding-agent.git
cd coding-agent
# Создать .env с ключами
docker compose run --rm agent python -m code_agent.main \
  --repo "owner/repo" --issue-id 1
```

### Вариант 2: GitHub Actions
1. Добавьте secrets в репозиторий: `LLM_API_KEY`, `LLM_BASE_URL`
2. Создайте Issue с label `agent`
3. Workflow запустится автоматически

### Вариант 3: Yandex Cloud
```bash
ssh yc-user@158.160.54.8
cd ~/coding-agents
docker compose run --rm agent python -m code_agent.main \
  --repo "owner/repo" --issue-id 1
```

---

## Метрики качества

| Метрика | Значение |
|---------|----------|
| Средняя скорость обработки Issue | 30-60 сек |
| Успешность первой попытки | ~80% |
| Покрытие тестами | Unit tests для core компонентов |
| Документация | README на русском языке |

---

## Ссылки для проверки

- **Основной репозиторий**: https://github.com/WinsentTy/coding-agent
- **Тестовый репозиторий**: https://github.com/WinsentTy/ms-test-2
- **Open Source проект (requests)**: https://github.com/WinsentTy/requests
- **Issues (ms-test-2)**: https://github.com/WinsentTy/ms-test-2/issues
- **Pull Requests (ms-test-2)**: https://github.com/WinsentTy/ms-test-2/pulls
- **Actions (ms-test-2)**: https://github.com/WinsentTy/ms-test-2/actions
