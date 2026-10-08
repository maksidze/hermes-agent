const en = {
  profilesHelp:
    'One profile connects one model. Expand a row to edit it; connection and capability options are under Advanced.',
  strength: 'Model capability',
  strengthHelp:
    'Classify the model relative to your other models. Hermes uses this to choose a starting worker. This does not change its reasoning effort.',
  strengths: { fast: 'Light', balanced: 'Medium', deep: 'Powerful' } as Record<string, string>,
  advanced: 'Advanced settings',
  disabled: 'Disabled',
  selectModel: 'Select a model',
  routeHelp:
    'Arrange workers from lighter to more powerful, top to bottom. If a worker cannot complete the task, Hermes can try the next one.',
  startHelp:
    'Simple tasks start at the top. The architect can start a difficult task at a stronger model. Planning and review models are selected in General.',
  firstStep: 'Start here · light model',
  nextStep: 'If needed · stronger model',
  addStep: 'Add fallback model',
  orderError: 'Move lighter models above stronger ones, or correct their capability in Profiles.'
}

type Copy = typeof en

const copies: Record<string, Copy> = {
  en,
  ru: {
    profilesHelp:
      'Один профиль — подключение одной модели. Раскройте строку для редактирования; редкие параметры находятся в дополнительных настройках.',
    strength: 'Мощность модели',
    strengthHelp:
      'Оцените модель относительно остальных. По этому классу Hermes выбирает начального исполнителя. Это не глубина размышления модели.',
    strengths: { fast: 'Лёгкая', balanced: 'Средняя', deep: 'Мощная' },
    advanced: 'Дополнительные настройки',
    disabled: 'Выключена',
    selectModel: 'Выберите модель',
    routeHelp:
      'Расположите исполнителей сверху вниз: от лёгкой модели к более мощной. Если исполнитель не справится, Hermes сможет перейти к следующему.',
    startHelp:
      'Простые задачи начинаются сверху. Для сложной задачи архитектор может сразу выбрать модель мощнее. Архитектор и проверяющий выбираются во вкладке «Основные».',
    firstStep: 'Начало · лёгкая модель',
    nextStep: 'При неудаче · модель мощнее',
    addStep: 'Добавить следующую модель',
    orderError: 'Поднимите лёгкие модели выше мощных или исправьте их класс мощности во вкладке «Профили».'
  },
  de: {
    profilesHelp:
      'Ein Profil verbindet ein Modell. Zeile zum Bearbeiten öffnen; weitere Optionen stehen unter Erweitert.',
    strength: 'Modellleistung',
    strengthHelp:
      'Ordnen Sie das Modell relativ zu den anderen ein. Hermes wählt damit den ersten Ausführer. Dies ändert nicht die Denktiefe.',
    strengths: { fast: 'Leicht', balanced: 'Mittel', deep: 'Leistungsstark' },
    advanced: 'Erweiterte Einstellungen',
    disabled: 'Deaktiviert',
    selectModel: 'Modell auswählen',
    routeHelp:
      'Ordnen Sie Ausführer von oben nach unten nach steigender Leistung. Scheitert ein Ausführer, kann Hermes den nächsten versuchen.',
    startHelp:
      'Einfache Aufgaben beginnen oben. Der Architekt kann schwierige Aufgaben einem stärkeren Modell zuweisen. Planer und Prüfer werden unter Allgemein gewählt.',
    firstStep: 'Start · leichtes Modell',
    nextStep: 'Bei Bedarf · stärkeres Modell',
    addStep: 'Ersatzmodell hinzufügen',
    orderError: 'Leichte Modelle nach oben verschieben oder ihre Leistung unter Profile korrigieren.'
  },
  fr: {
    profilesHelp:
      'Un profil connecte un modèle. Dépliez une ligne pour la modifier ; les autres options sont dans les paramètres avancés.',
    strength: 'Capacité du modèle',
    strengthHelp:
      'Classez ce modèle par rapport aux autres. Hermes choisit ainsi le premier exécutant. Cela ne change pas son effort de raisonnement.',
    strengths: { fast: 'Léger', balanced: 'Moyen', deep: 'Puissant' },
    advanced: 'Paramètres avancés',
    disabled: 'Désactivé',
    selectModel: 'Choisir un modèle',
    routeHelp:
      'Classez les exécutants du plus léger au plus puissant, de haut en bas. En cas d’échec, Hermes peut essayer le suivant.',
    startHelp:
      'Les tâches simples commencent en haut. L’architecte peut choisir un modèle plus puissant pour une tâche complexe. Architecte et vérificateur se choisissent dans Général.',
    firstStep: 'Départ · modèle léger',
    nextStep: 'Si nécessaire · modèle plus puissant',
    addStep: 'Ajouter un modèle de secours',
    orderError: 'Placez les modèles légers en haut ou corrigez leur capacité dans Profils.'
  },
  es: {
    profilesHelp:
      'Cada perfil conecta un modelo. Despliega una fila para editarla; las demás opciones están en ajustes avanzados.',
    strength: 'Capacidad del modelo',
    strengthHelp:
      'Clasifica el modelo respecto a los demás. Hermes lo usa para elegir al primer ejecutor. No cambia su esfuerzo de razonamiento.',
    strengths: { fast: 'Ligero', balanced: 'Medio', deep: 'Potente' },
    advanced: 'Ajustes avanzados',
    disabled: 'Desactivado',
    selectModel: 'Elegir modelo',
    routeHelp:
      'Ordena los ejecutores de más ligero a más potente, de arriba abajo. Si uno no completa la tarea, Hermes puede probar el siguiente.',
    startHelp:
      'Las tareas sencillas empiezan arriba. El arquitecto puede elegir un modelo más potente para tareas difíciles. Arquitecto y revisor se eligen en General.',
    firstStep: 'Inicio · modelo ligero',
    nextStep: 'Si hace falta · modelo más potente',
    addStep: 'Añadir modelo de respaldo',
    orderError: 'Mueve los modelos ligeros arriba o corrige su capacidad en Perfiles.'
  },
  ja: {
    profilesHelp:
      'プロファイルごとに1つのモデルを接続します。行を開いて編集できます。その他の項目は詳細設定にあります。',
    strength: 'モデルの能力',
    strengthHelp:
      '他のモデルと比較して分類します。Hermes は最初の実行モデルを選ぶ際に参照します。推論の深さは変わりません。',
    strengths: { fast: '軽量', balanced: '中程度', deep: '高性能' },
    advanced: '詳細設定',
    disabled: '無効',
    selectModel: 'モデルを選択',
    routeHelp: '上から下へ軽量から高性能の順に並べます。実行モデルが完了できなければ、Hermes は次を試せます。',
    startHelp:
      '簡単なタスクは先頭から始めます。難しいタスクは設計モデルが高性能モデルから開始できます。設計・検証モデルは一般で選択します。',
    firstStep: '開始 · 軽量モデル',
    nextStep: '必要に応じて · より高性能なモデル',
    addStep: '次のモデルを追加',
    orderError: '軽量モデルを上に移動するか、プロファイルで能力を修正してください。'
  },
  zh: {
    profilesHelp: '每个配置连接一个模型。展开行即可编辑，其他选项位于高级设置中。',
    strength: '模型能力',
    strengthHelp: '相对其他模型进行分类。Hermes 据此选择初始执行模型，不会改变推理强度。',
    strengths: { fast: '轻量', balanced: '中等', deep: '强大' },
    advanced: '高级设置',
    disabled: '已禁用',
    selectModel: '选择模型',
    routeHelp: '从上到下按由轻到强排列执行模型。如果无法完成任务，Hermes 可以尝试下一个。',
    startHelp: '简单任务从顶部开始。复杂任务可由架构师直接选择更强的模型。规划和审核模型在常规中选择。',
    firstStep: '起点 · 轻量模型',
    nextStep: '需要时 · 更强的模型',
    addStep: '添加后备模型',
    orderError: '将轻量模型移到上方，或在执行配置中修正其能力分类。'
  },
  'zh-hant': {
    profilesHelp: '每個設定連接一個模型。展開列即可編輯，其他選項位於進階設定中。',
    strength: '模型能力',
    strengthHelp: '相對其他模型進行分類。Hermes 據此選擇初始執行模型，不會改變推理強度。',
    strengths: { fast: '輕量', balanced: '中等', deep: '強大' },
    advanced: '進階設定',
    disabled: '已停用',
    selectModel: '選擇模型',
    routeHelp: '由上到下按由輕到強排列執行模型。若無法完成任務，Hermes 可以嘗試下一個。',
    startHelp: '簡單任務從頂部開始。複雜任務可由架構師直接選擇更強的模型。規劃和審核模型在一般中選擇。',
    firstStep: '起點 · 輕量模型',
    nextStep: '需要時 · 更強的模型',
    addStep: '新增後備模型',
    orderError: '將輕量模型移到上方，或在執行設定中修正其能力分類。'
  },
  ar: {
    profilesHelp: 'يربط كل ملف نموذجًا واحدًا. وسّع الصف للتعديل؛ توجد الخيارات الأخرى في الإعدادات المتقدمة.',
    strength: 'قدرة النموذج',
    strengthHelp:
      'صنّف النموذج مقارنة بالنماذج الأخرى. يستخدم Hermes ذلك لاختيار المنفذ الأول. لا يغيّر هذا عمق التفكير.',
    strengths: { fast: 'خفيف', balanced: 'متوسط', deep: 'قوي' },
    advanced: 'إعدادات متقدمة',
    disabled: 'معطّل',
    selectModel: 'اختر نموذجًا',
    routeHelp:
      'رتّب المنفذين من الأخف إلى الأقوى من الأعلى إلى الأسفل. إذا تعذّر إكمال المهمة، يمكن لـ Hermes تجربة التالي.',
    startHelp:
      'تبدأ المهام البسيطة من الأعلى. يمكن للمهندس اختيار نموذج أقوى للمهام الصعبة. اختر نماذج التخطيط والمراجعة في الإعدادات العامة.',
    firstStep: 'البداية · نموذج خفيف',
    nextStep: 'عند الحاجة · نموذج أقوى',
    addStep: 'إضافة نموذج احتياطي',
    orderError: 'انقل النماذج الخفيفة إلى الأعلى أو صحّح قدرتها في ملفات التنفيذ.'
  }
}

export function orchestrationLayoutCopy(locale: string): Copy {
  return copies[locale] ?? en
}
