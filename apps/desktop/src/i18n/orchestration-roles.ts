const en = {
  adaptive: 'Architect chooses the starting group',
  adaptiveHelp: 'Routine tasks start economically; complex tasks can go straight to a suitable group.',
  adaptivePlan: 'Plan → selected group',
  planning: 'Planning',
  planner: 'Architect model',
  plan: 'Plan → first worker',
  review: 'Result verification',
  reviewer: 'Reviewer model',
  mode: 'Model review',
  auto: 'Automatic selection',
  missing: 'Not selected',
  help: 'Shared roles for all workflows. Category settings can override them. Planning runs before workers; verification runs after each attempt.',
  checks:
    'Hermes checks recorded test results, output format and execution errors. The reviewer receives the goal and evidence; it does not run tools.',
  modes: {
    off: 'Disabled',
    risk_based: 'When automatic checks are inconclusive',
    always: 'After automatic checks, unless they fail'
  } as Record<string, string>
}

const ru: typeof en = {
  adaptive: 'Архитектор выбирает начальную группу',
  adaptiveHelp: 'Простые задачи начинают с экономичной модели; сложные могут сразу перейти к подходящей группе.',
  adaptivePlan: 'План → выбранная группа',
  planning: 'Планирование',
  planner: 'Модель-архитектор',
  plan: 'План → первый исполнитель',
  review: 'Проверка результата',
  reviewer: 'Модель-проверяющий',
  mode: 'Проверка моделью',
  auto: 'Автоматический выбор',
  missing: 'Не выбрана',
  help: 'Общие роли для всех сценариев. Категории могут переопределять их. Планирование выполняется до исполнителей, проверка — после каждой попытки.',
  checks:
    'Hermes проверяет записанные результаты тестов, формат ответа и ошибки выполнения. Модель-проверяющий получает задачу и доказательства; сама инструменты не запускает.',
  modes: {
    off: 'Выключена',
    risk_based: 'Когда автоматических проверок недостаточно',
    always: 'После автоматических проверок, если они не выявили ошибку'
  }
}

const translations: Record<string, typeof en> = {
  en, ru,
  de: {
    planning: 'Planung', planner: 'Architekturmodell', plan: 'Plan → erster Bearbeiter', review: 'Ergebnisprüfung', reviewer: 'Prüfmodell', mode: 'Modellprüfung', auto: 'Automatische Auswahl', missing: 'Nicht ausgewählt',
    adaptive: 'Architekt wählt die Startgruppe', adaptiveHelp: 'Einfache Aufgaben starten sparsam; komplexe können direkt eine passende Gruppe nutzen.', adaptivePlan: 'Plan → gewählte Gruppe',
    help: 'Gemeinsame Rollen für alle Abläufe; Kategorien können sie überschreiben. Planung erfolgt zuerst, Prüfung nach jedem Versuch.',
    checks: 'Hermes prüft protokollierte Tests, Ausgabeformat und Fehler. Das Prüfmodell erhält Aufgabe und Nachweise und führt keine Werkzeuge aus.',
    modes: { off: 'Aus', risk_based: 'Bei unklaren automatischen Prüfungen', always: 'Nach automatischen Prüfungen ohne Fehler' }
  },
  fr: {
    planning: 'Planification', planner: 'Modèle architecte', plan: 'Plan → premier exécutant', review: 'Vérification du résultat', reviewer: 'Modèle vérificateur', mode: 'Vérification par modèle', auto: 'Sélection automatique', missing: 'Non sélectionné',
    adaptive: 'L’architecte choisit le groupe initial', adaptiveHelp: 'Les tâches simples commencent économiquement ; les tâches complexes peuvent utiliser directement un groupe adapté.', adaptivePlan: 'Plan → groupe choisi',
    help: 'Rôles communs aux workflows, modifiables par catégorie. La planification précède l’exécution ; la vérification suit chaque tentative.',
    checks: 'Hermes contrôle les tests enregistrés, le format et les erreurs. Le vérificateur reçoit la tâche et les preuves, sans exécuter d’outils.',
    modes: { off: 'Désactivée', risk_based: 'Si les contrôles automatiques ne suffisent pas', always: 'Après les contrôles automatiques sans erreur' }
  },
  es: {
    planning: 'Planificación', planner: 'Modelo arquitecto', plan: 'Plan → primer ejecutor', review: 'Verificación del resultado', reviewer: 'Modelo revisor', mode: 'Revisión por modelo', auto: 'Selección automática', missing: 'Sin seleccionar',
    adaptive: 'El arquitecto elige el grupo inicial', adaptiveHelp: 'Las tareas sencillas empiezan con un modelo económico; las complejas pueden ir directamente a un grupo adecuado.', adaptivePlan: 'Plan → grupo elegido',
    help: 'Roles compartidos por todos los flujos; las categorías pueden sustituirlos. La planificación va primero y la revisión sigue a cada intento.',
    checks: 'Hermes comprueba pruebas registradas, formato y errores. El revisor recibe la tarea y las evidencias; no ejecuta herramientas.',
    modes: { off: 'Desactivada', risk_based: 'Cuando las comprobaciones automáticas no bastan', always: 'Tras comprobaciones automáticas sin fallos' }
  },
  ja: {
    planning: '計画', planner: '設計モデル', plan: '計画 → 最初の実行役', review: '結果の検証', reviewer: '検証モデル', mode: 'モデルによる検証', auto: '自動選択', missing: '未選択',
    adaptive: '設計モデルが開始グループを選択', adaptiveHelp: '簡単なタスクは低コストで開始し、複雑なタスクは適したグループで直接開始できます。', adaptivePlan: '計画 → 選択したグループ',
    help: '全ワークフロー共通の役割です。カテゴリで上書きできます。計画が先に実行され、各試行後に検証されます。',
    checks: 'Hermesは記録されたテスト、出力形式、実行エラーを確認します。検証モデルはタスクと根拠を受け取り、ツールを実行しません。',
    modes: { off: '無効', risk_based: '自動検証だけでは判断できない場合', always: '自動検証で失敗しなかった場合は毎回' }
  },
  zh: {
    planning: '规划', planner: '架构模型', plan: '计划 → 首个执行者', review: '结果验证', reviewer: '验证模型', mode: '模型验证', auto: '自动选择', missing: '未选择',
    adaptive: '架构模型选择起始组', adaptiveHelp: '简单任务从经济模型开始，复杂任务可直接交给合适的组。', adaptivePlan: '计划 → 所选组',
    help: '所有流程共享角色，分类设置可覆盖。先规划，再执行；每次尝试后验证。',
    checks: 'Hermes检查记录的测试、输出格式和执行错误。验证模型接收任务和证据，不执行工具。',
    modes: { off: '关闭', risk_based: '自动检查不足以判断时', always: '自动检查未发现错误后每次验证' }
  },
  'zh-hant': {
    planning: '規劃', planner: '架構模型', plan: '計畫 → 首個執行者', review: '結果驗證', reviewer: '驗證模型', mode: '模型驗證', auto: '自動選擇', missing: '未選擇',
    adaptive: '架構模型選擇起始群組', adaptiveHelp: '簡單任務從經濟模型開始，複雜任務可直接交給適合的群組。', adaptivePlan: '計畫 → 所選群組',
    help: '所有流程共用角色，分類設定可覆寫。先規劃再執行，每次嘗試後驗證。',
    checks: 'Hermes檢查記錄的測試、輸出格式和執行錯誤。驗證模型接收任務與證據，不執行工具。',
    modes: { off: '關閉', risk_based: '自動檢查不足以判斷時', always: '自動檢查未發現錯誤後每次驗證' }
  },
  ar: {
    planning: 'التخطيط', planner: 'نموذج التخطيط', plan: 'الخطة ← المنفذ الأول', review: 'التحقق من النتيجة', reviewer: 'نموذج المراجعة', mode: 'مراجعة النموذج', auto: 'اختيار تلقائي', missing: 'لم يُحدد',
    adaptive: 'المخطط يختار مجموعة البداية', adaptiveHelp: 'تبدأ المهام البسيطة بنموذج اقتصادي؛ يمكن توجيه المهام المعقدة مباشرة إلى مجموعة مناسبة.', adaptivePlan: 'الخطة ← المجموعة المختارة',
    help: 'أدوار مشتركة بين المسارات، ويمكن للفئات تجاوزها. يسبق التخطيط التنفيذ وتلي المراجعة كل محاولة.',
    checks: 'يفحص Hermes الاختبارات المسجلة وتنسيق المخرجات والأخطاء. يتلقى المراجع المهمة والأدلة ولا ينفذ أدوات.',
    modes: { off: 'معطلة', risk_based: 'عندما لا تكفي الفحوص التلقائية', always: 'بعد الفحوص التلقائية ما لم تفشل' }
  }
}

const choiceHelp: Record<string, string> = {
  en: 'Select a model and add a group, then drag from the planning output to its input. The architect chooses only connected groups. Delete a planning connection to exclude a group.',
  ru: 'Выберите модель и добавьте группу, затем протяните связь от выхода планирования к её входу. Архитектор выбирает только подключённые группы. Удаление связи исключает группу из прямого выбора.',
  de: 'Modell wählen, Gruppe hinzufügen und den Planungsausgang mit ihrem Eingang verbinden. Der Architekt wählt nur verbundene Gruppen.',
  fr: 'Choisissez un modèle, ajoutez un groupe et reliez la sortie du planificateur à son entrée. L’architecte choisit uniquement les groupes reliés.',
  es: 'Seleccione un modelo, añada un grupo y conecte la salida del planificador a su entrada. El arquitecto solo elige grupos conectados.',
  ja: 'モデルを選んでグループを追加し、計画の出力から入力へ接続してください。接続されたグループだけが選択対象です。',
  zh: '选择模型并添加组，然后将规划输出连接到组的输入。架构模型只选择已连接的组。',
  'zh-hant': '選擇模型並新增群組，再將規劃輸出連接到群組輸入。架構模型僅選擇已連接的群組。',
  ar: 'اختر نموذجاً وأضف مجموعة ثم صِل مخرج المخطط بمدخلها. يختار المخطط المجموعات المتصلة فقط.'
}

export const roleCopy = (locale: string) => {
  const copy = translations[locale] ?? en

  return { ...copy, adaptiveHelp: `${copy.adaptiveHelp} ${choiceHelp[locale] ?? choiceHelp.en}` }
}
