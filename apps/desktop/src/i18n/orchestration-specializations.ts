const en = {
  intro:
    'Choose specialists by task type, independently of Fast / Balanced / Deep. The architect can select a category; an executor can request a transfer with a reason. A refusal alone does not trigger a transfer.',
  templates: 'Add four category templates',
  custom: 'Add custom specialization',
  description: 'When to use this category',
  route: 'Execution route',
  planner: 'Architect',
  verifier: 'Reviewer',
  inherit: 'Use general setting',
  localDefault: 'Last enabled profile in this route',
  local: 'Require local model endpoints',
  localHint:
    'Requires loopback endpoints for the orchestrated architect, workers, reviewer and auxiliary model calls. Cloud profiles will be blocked. For confidential input, use a fully local Hermes profile too: main model and all auxiliary services. Select @local_private before sending the task; a later transfer cannot undo prior cloud disclosure.',
  workspace: 'Isolated Git worktree and attempt checkpoints',
  workspaceHint:
    'Applies when starting a new category task. Transfers within an existing run keep its workspace. Turn off for prose tasks that do not need a Git project.',
  prefix: 'Start a task directly with',
  emptyRoute: 'Create an execution route first.',
  setup:
    'Templates start disabled. Assign suitable profiles through a route, select the reviewer if needed, enable the category and save. No model is downloaded or assumed to be unrestricted.',
  automatic:
    'When orchestration is on, every user message is planned and can select a category. Use @category to choose it explicitly before planning.',
  reverse: 'Decompilation and reverse engineering: analyze binaries, formats, protocols and program behavior.',
  roleplay: 'Fictional roleplay: character voices, scenes and dialogue with continuity.',
  sensitive:
    'Analysis and discussion of sensitive topics, with context and clear distinctions between facts and opinions.',
  private: 'Tasks whose content must remain on this computer; use local model endpoints only.'
}

const ru: typeof en = {
  intro:
    'Специализация выбирается по типу задачи независимо от Fast / Balanced / Deep. Архитектор может назначить категорию, а исполнитель — запросить передачу с объяснением причины. Сам по себе отказ не вызывает переключение.',
  templates: 'Добавить четыре шаблона категорий',
  custom: 'Добавить свою специализацию',
  description: 'Когда выбирать эту категорию',
  route: 'Маршрут исполнения',
  planner: 'Архитектор',
  verifier: 'Проверяющий',
  inherit: 'Из общих настроек',
  localDefault: 'Последний включённый профиль маршрута',
  local: 'Только локальные подключения к моделям',
  localHint:
    'Архитектор, исполнители, проверяющий и вспомогательные вызовы моделей внутри оркестрации требуют loopback-адресов. Облачные профили будут заблокированы. Для конфиденциального ввода нужен также полностью локальный профиль Hermes: основная модель и все вспомогательные сервисы. Выберите @local_private до отправки задачи: позднее переключение не отменяет прежнюю передачу текста в облако.',
  workspace: 'Отдельная рабочая копия Git и контрольные точки попыток',
  workspaceHint:
    'Применяется при запуске новой задачи категории. Передача внутри текущего запуска сохраняет его рабочую копию. Отключите для текстовых задач, которым не нужен Git-проект.',
  prefix: 'Прямой запуск задачи:',
  emptyRoute: 'Сначала создайте маршрут исполнения.',
  setup:
    'Шаблоны изначально выключены. Назначьте подходящие профили через маршрут, при необходимости выберите проверяющего, включите категорию и сохраните. Модели не скачиваются и не считаются автоматически «без цензуры».',
  automatic:
    'Когда оркестрация включена, каждый запрос проходит планирование с выбором категории. Префикс @категория выбирает её явно до планирования.',
  reverse: 'Декомпиляция и реверс-инжиниринг: анализ бинарных файлов, форматов, протоколов и поведения программ.',
  roleplay: 'Ролевые диалоги: художественные сцены, характеры персонажей и последовательное развитие диалога.',
  sensitive: 'Анализ и обсуждение чувствительных тем с учётом контекста и разделением фактов и мнений.',
  private: 'Задачи, содержание которых должно оставаться на этом компьютере; только локальные подключения к моделям.'
}

export const specializationCopy = (locale: string) => (locale === 'ru' ? ru : en)
