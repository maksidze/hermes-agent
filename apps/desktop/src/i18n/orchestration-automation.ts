const en = {
  title: 'Automatic teamwork',
  description:
    'Write a normal request. The architect plans, workers implement, and checks decide whether to accept or escalate.',
  setup: 'Use recommended setup',
  missing: 'Create an enabled execution profile and a route first.',
  detection:
    'When enabled, every user message uses orchestration. When disabled, the chat model answers normally. Changes apply to the next message.',
  architect: 'Architect',
  architectHelp: 'Creates a plan and acceptance checks. Usually your strongest model.',
  workers: 'Worker route',
  workersHelp:
    'Profiles are tried from the requested level upward. A failed check can trigger a repair or a stronger model.',
  reviewer: 'Reviewer',
  reviewerHelp: 'Evaluates the result when test evidence is insufficient.',
  isolation: 'Keep attempts in a separate Git worktree',
  isolationHelp:
    'Saves checkpoints, patches and checks. Failed changes remain for the next model to inspect. Requires a local Git project with a commit; dependencies may need installing in the worktree. External effects cannot be rolled back.',
  apply: 'Apply the completed result to the project',
  applyHelp:
    'Only after all subtasks pass and the source is unchanged. Otherwise the worktree and patch remain for review.',
  preferred: 'Fixed worker (optional)',
  preferredHelp:
    'Use one particular model, including a small local model, regardless of its level. This disables worker escalation. Permission and policy refusals stop for review.',
  automatic: 'Choose through the route',
  advanced: 'Advanced settings',
  enabled: 'Enable orchestration'
}

const ru: typeof en = {
  title: 'Автоматическая работа команды',
  description:
    'Напиши обычный запрос. Архитектор составит план, исполнители внесут изменения, а проверка решит, принять результат или повысить уровень.',
  setup: 'Настроить автоматически',
  missing: 'Сначала создай включённый профиль исполнения и маршрут.',
  detection:
    'Когда включена, каждый пользовательский запрос проходит через оркестрацию. Когда выключена, отвечает модель чата. Изменение действует со следующего сообщения.',
  architect: 'Архитектор',
  architectHelp: 'Составляет план и критерии готовности. Обычно самая сильная модель.',
  workers: 'Маршрут исполнителей',
  workersHelp:
    'Модели выбираются от нужного уровня к более сильному. При провале проверки — исправление или передача следующей модели.',
  reviewer: 'Проверяющий',
  reviewerHelp: 'Оценивает результат, когда недостаточно подтверждения тестами.',
  isolation: 'Хранить попытки в отдельной рабочей копии Git',
  isolationHelp:
    'Сохраняет контрольные точки, изменения и проверки. Следующая модель видит неудачную попытку. Нужен локальный Git-проект с коммитом; зависимости могут потребовать установки в рабочей копии. Внешние действия не откатываются.',
  apply: 'Применять готовый результат к проекту',
  applyHelp:
    'После успешной проверки всех подзадач, если исходный проект не изменился. Иначе рабочая копия и patch останутся для проверки.',
  preferred: 'Фиксированный исполнитель (необязательно)',
  preferredHelp:
    'Любая конкретная модель, включая маленькую локальную, независимо от уровня. Повышение уровня исполнителя отключается. Отказ по правилам или правам доступа останавливает задачу для разбора.',
  automatic: 'Выбирать по маршруту',
  advanced: 'Дополнительные настройки',
  enabled: 'Включить оркестрацию'
}

export function automationCopy(locale: string) {
  return locale === 'ru' ? ru : en
}
