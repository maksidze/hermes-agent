import type { Translations } from './types'

const en = {
  title: 'Orchestration',
  general: 'General',
  profiles: 'Profiles',
  routes: 'Routes',
  specializations: 'Specializations',
  escalation: 'Escalation',
  verification: 'Verification',
  limits: 'Limits',
  diagnostics: 'Diagnostics',
  addProfile: 'Add execution profile',
  addRoute: 'Add route',
  test: 'Test profile',
  profileId: 'Profile ID',
  routeId: 'Route ID',
  level: 'Level',
  reasoning: 'Reasoning effort',
  parallel: 'Maximum parallel tasks',
  priority: 'Priority',
  tools: 'Tools',
  vision: 'Vision',
  structured: 'Structured output',
  inUse: 'This profile is used by a route or verifier. Remove those references first.',
  invalid:
    'Complete every profile and route. Routes must reference existing profiles from lighter to more powerful models.',
  nextSession: 'Changes apply to the next user message. An active orchestration run keeps its current settings.',
  emptyEvents: 'No orchestration events in this backend process yet.',
  saveFirst: 'Save changes before testing a profile.',
  refresh: 'Refresh'
}

type OrchestrationCopy = typeof en

const translations: Record<string, Partial<OrchestrationCopy>> = {
  ru: {
    title: 'Оркестрация моделей',
    general: 'Основные',
    profiles: 'Профили',
    routes: 'Маршруты',
    specializations: 'Специализации',
    escalation: 'Эскалация',
    verification: 'Проверка',
    limits: 'Лимиты',
    diagnostics: 'Диагностика',
    addProfile: 'Добавить профиль исполнения',
    addRoute: 'Добавить маршрут',
    test: 'Проверить профиль',
    profileId: 'ID профиля',
    routeId: 'ID маршрута',
    level: 'Уровень',
    reasoning: 'Уровень рассуждения',
    parallel: 'Максимум параллельных задач',
    priority: 'Приоритет',
    tools: 'Инструменты',
    vision: 'Изображения',
    structured: 'Структурированный ответ',
    inUse: 'Профиль используется в маршруте или для проверки. Сначала удалите эти ссылки.',
    invalid:
      'Заполните профили и маршруты. В маршрутах располагайте существующие профили от лёгких моделей к более мощным.',
    nextSession: 'Изменения действуют со следующего сообщения. Уже запущенная оркестрация сохраняет текущие настройки.',
    emptyEvents: 'В этом процессе backend ещё нет событий оркестрации.',
    saveFirst: 'Сохраните изменения перед проверкой профиля.',
    refresh: 'Обновить'
  },
  de: {
    title: 'Orchestrierung',
    general: 'Allgemein',
    profiles: 'Profile',
    routes: 'Routen',
    escalation: 'Eskalation',
    verification: 'Prüfung',
    limits: 'Grenzen',
    diagnostics: 'Diagnose'
  },
  fr: {
    title: 'Orchestration',
    general: 'Général',
    profiles: 'Profils',
    routes: 'Routage',
    escalation: 'Escalade',
    verification: 'Vérification',
    limits: 'Limites',
    diagnostics: 'Diagnostic'
  },
  es: {
    title: 'Orquestación',
    general: 'General',
    profiles: 'Perfiles',
    routes: 'Rutas',
    escalation: 'Escalado',
    verification: 'Verificación',
    limits: 'Límites',
    diagnostics: 'Diagnóstico'
  },
  ja: {
    title: 'モデルオーケストレーション',
    general: '一般',
    profiles: 'プロファイル',
    routes: 'ルート',
    escalation: 'エスカレーション',
    verification: '検証',
    limits: '制限',
    diagnostics: '診断'
  },
  zh: {
    title: '模型编排',
    general: '常规',
    profiles: '执行配置',
    routes: '路由',
    escalation: '升级',
    verification: '验证',
    limits: '限制',
    diagnostics: '诊断'
  },
  'zh-hant': {
    title: '模型編排',
    general: '一般',
    profiles: '執行設定',
    routes: '路由',
    escalation: '升級',
    verification: '驗證',
    limits: '限制',
    diagnostics: '診斷'
  },
  ar: {
    title: 'تنسيق النماذج',
    general: 'عام',
    profiles: 'ملفات التنفيذ',
    routes: 'المسارات',
    escalation: 'التصعيد',
    verification: 'التحقق',
    limits: 'الحدود',
    diagnostics: 'التشخيص'
  }
}

export function orchestrationCopy(locale: string): OrchestrationCopy {
  return { ...en, ...translations[locale] }
}

const fieldLabels: Record<string, [string, string]> = {
  enabled: ['Enable orchestration', 'Включить оркестрацию'],
  mode: ['Mode', 'Режим'],
  'automation.mode': ['Automatic start', 'Автоматический запуск'],
  'automation.planner_profile': ['Architect profile', 'Профиль архитектора'],
  'automation.max_tasks': ['Maximum plan steps', 'Максимум подзадач в плане'],
  'workspace.enabled': ['Isolated worktree and checkpoints', 'Отдельная рабочая копия и контрольные точки'],
  'workspace.apply_on_success': ['Apply verified result', 'Применять проверенный результат'],
  'routing.preferred_profile': ['Fixed worker profile', 'Фиксированный профиль исполнителя'],
  'routing.strategy': ['Routing strategy', 'Стратегия маршрутизации'],
  'routing.default_route': ['Default route', 'Маршрут по умолчанию'],
  'routing.default_level': ['Default level', 'Уровень по умолчанию'],
  'routing.allow_direct_deep': ['Allow direct Deep routing', 'Разрешить сразу выбирать Deep'],
  'routing.max_specialist_switches': ['Maximum specialist transfers', 'Максимум передач между специализациями'],
  'escalation.enabled': ['Automatic escalation', 'Автоматическое повышение уровня'],
  'escalation.same_profile_repairs': ['Repairs on the same profile', 'Попытки исправления на том же профиле'],
  'escalation.max_escalations': ['Maximum escalations', 'Максимум повышений уровня'],
  'escalation.triggers.verification_failed': ['On verification failure', 'При провале проверки'],
  'escalation.triggers.schema_failed': ['On invalid structured output', 'При неверном формате ответа'],
  'escalation.triggers.repetition_detected': ['On repetition or loop', 'При повторениях или зацикливании'],
  'escalation.triggers.explicit_request': ['On executor request', 'По запросу исполнителя'],
  'verification.deterministic': ['Deterministic verification', 'Проверка по формальным критериям'],
  'verification.semantic': ['Semantic verification', 'Проверка моделью'],
  'verification.verifier_profile': ['Verifier profile', 'Профиль проверяющего'],
  'verification.uncertain_action': ['When verification is uncertain', 'При неопределённом результате проверки'],
  'verification.main_agent_stop_gate': [
    'Check main-agent failures before finishing',
    'Проверять неудачи основного агента перед завершением'
  ],
  'budget.max_attempts': ['Maximum attempts', 'Максимум попыток'],
  'budget.max_escalations': ['Escalation budget', 'Лимит повышений уровня'],
  'budget.max_model_calls': ['Maximum model calls', 'Максимум вызовов моделей'],
  'budget.max_calls_per_attempt': ['Model calls per attempt', 'Вызовов модели на одну попытку'],
  'budget.max_parallel_tasks': ['Maximum tasks per batch', 'Максимум задач в пакете'],
  'budget.timeout_seconds': ['Task timeout (seconds)', 'Время на задачу (секунды)'],
  'availability.cache_seconds': ['Availability cache (seconds)', 'Кэш доступности (секунды)'],
  'availability.failure_cooldown_seconds': ['Failure cooldown (seconds)', 'Пауза после недоступности (секунды)'],
  'privacy.cloud_allowed': ['Allow cloud models', 'Разрешить облачные модели'],
  'logging.decisions': ['Log routing decisions', 'Записывать решения маршрутизации'],
  'logging.attempts': ['Log execution attempts', 'Записывать попытки исполнения'],
  'logging.verification': ['Log verification', 'Записывать результаты проверок']
}

export function withOrchestration(t: Translations, locale: string): Translations {
  const copy = orchestrationCopy(locale)

  const pages = [
    'general',
    'profiles',
    'routes',
    'specializations',
    'escalation',
    'verification',
    'limits',
    'diagnostics'
  ] as const

  return {
    ...t,
    settings: {
      ...t.settings,
      fieldLabels: {
        ...t.settings.fieldLabels,
        ...Object.fromEntries(
          Object.entries(fieldLabels).map(([key, labels]) => [`orchestration.${key}`, labels[locale === 'ru' ? 1 : 0]])
        )
      },
      sections: { ...t.settings.sections, orchestration: copy.title },
      subpages: {
        ...t.settings.subpages,
        ...Object.fromEntries(pages.map(page => [`orchestration_${page}`, copy[page]]))
      }
    }
  }
}
