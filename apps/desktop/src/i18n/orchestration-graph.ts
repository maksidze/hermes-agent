const en = {
  help: 'Connect groups to define the workflow. Models within a group are tried in order. Double-click the canvas to add a group; drag between ports to connect it.',
  group: 'Model group',
  add: 'Add group',
  entry: 'Start here',
  name: 'Name',
  description: 'Purpose and strengths',
  models: 'Models · execution order',
  addModel: 'Add model',
  remove: 'Remove',
  undo: 'Undo',
  redo: 'Redo',
  select: 'Select a group to edit its models and purpose.',
  outcomes: { success: 'Verified', failure: 'Check failed', unavailable: 'Unavailable', uncertain: 'Evidence missing' },
  endings:
    'An unconnected Verified port completes the task. Other unconnected ports stop it. Loops share the run budget. Permission and external-state blocks always stop execution.',
  invalid: 'Connect every group from the start, choose models, and use at most one connection per output.',
  modelHelp: 'Describe useful tasks, limitations and local execution. This description is included in planning.',
  route: 'Workflow',
  addRoute: 'Add workflow'
}

type Copy = typeof en

const copies: Record<string, Copy> = {
  en,
  ru: {
    help: 'Соедините группы в нужном порядке. Модели внутри группы пробуются по очереди. Двойной щелчок добавляет группу; перетащите связь между портами.',
    group: 'Группа моделей',
    add: 'Добавить группу',
    entry: 'Начать здесь',
    name: 'Название',
    description: 'Назначение и сильные стороны',
    models: 'Модели · порядок выполнения',
    addModel: 'Добавить модель',
    remove: 'Удалить',
    undo: 'Отменить',
    redo: 'Повторить',
    select: 'Выберите группу, чтобы настроить модели и назначение.',
    outcomes: {
      success: 'Проверено',
      failure: 'Проверка не пройдена',
      unavailable: 'Недоступно',
      uncertain: 'Недостаточно данных'
    },
    endings:
      'Порт «Проверено» без связи завершает задачу. Остальные порты без связи останавливают её. Циклы используют общий бюджет запуска. Ограничения доступа и неопределённые внешние действия всегда останавливают выполнение.',
    invalid: 'Соедините все группы с начальной, выберите модели и оставьте не более одной связи на выход.',
    modelHelp: 'Укажите подходящие задачи, ограничения и локальное исполнение. Описание учитывается при планировании.',
    route: 'Сценарий',
    addRoute: 'Добавить сценарий'
  },
  de: {
    ...en,
    help: 'Gruppen verbinden, Modelle in Reihenfolge ausprobieren. Doppelklick fügt eine Gruppe hinzu; Anschlüsse zum Verbinden ziehen.',
    select: 'Gruppe auswählen, um Modelle und Zweck zu bearbeiten.',
    outcomes: {
      success: 'Geprüft',
      failure: 'Prüfung fehlgeschlagen',
      unavailable: 'Nicht verfügbar',
      uncertain: 'Nachweise fehlen'
    },
    endings:
      'Ein freier Geprüft-Ausgang beendet die Aufgabe erfolgreich; andere freie Ausgänge stoppen sie. Schleifen teilen das Budget. Berechtigungsprobleme und unklare externe Aktionen stoppen immer.',
    invalid:
      'Alle Gruppen mit dem Start verbinden, Modelle wählen und höchstens eine Verbindung pro Ausgang verwenden.',
    modelHelp:
      'Geeignete Aufgaben, Grenzen und lokale Ausführung beschreiben. Die Planung berücksichtigt diese Angaben.',
    group: 'Modellgruppe',
    add: 'Gruppe hinzufügen',
    entry: 'Hier starten',
    name: 'Name',
    description: 'Zweck und Stärken',
    models: 'Modelle · Reihenfolge',
    addModel: 'Modell hinzufügen',
    remove: 'Entfernen',
    undo: 'Rückgängig',
    redo: 'Wiederholen',
    route: 'Workflow',
    addRoute: 'Workflow hinzufügen'
  },
  fr: {
    ...en,
    help: 'Reliez les groupes ; les modèles sont essayés dans l’ordre. Double-cliquez pour ajouter un groupe, puis faites glisser entre les ports.',
    select: 'Sélectionnez un groupe pour modifier ses modèles et son usage.',
    outcomes: {
      success: 'Vérifié',
      failure: 'Échec du contrôle',
      unavailable: 'Indisponible',
      uncertain: 'Preuves manquantes'
    },
    endings:
      'Une sortie Vérifié libre termine la tâche ; les autres sorties libres l’arrêtent. Les boucles partagent le budget. Les problèmes d’accès et les effets externes incertains arrêtent toujours l’exécution.',
    invalid: 'Reliez tous les groupes au départ, choisissez des modèles et une seule connexion par sortie.',
    modelHelp:
      'Décrivez les tâches adaptées, les limites et l’exécution locale. La planification utilise cette description.',
    group: 'Groupe de modèles',
    add: 'Ajouter un groupe',
    entry: 'Commencer ici',
    name: 'Nom',
    description: 'Usage et points forts',
    models: 'Modèles · ordre',
    addModel: 'Ajouter un modèle',
    remove: 'Supprimer',
    undo: 'Annuler',
    redo: 'Rétablir',
    route: 'Workflow',
    addRoute: 'Ajouter un workflow'
  },
  es: {
    ...en,
    help: 'Conecta grupos; los modelos se prueban en orden. Haz doble clic para añadir un grupo y arrastra entre puertos para conectarlos.',
    select: 'Selecciona un grupo para editar sus modelos y propósito.',
    outcomes: {
      success: 'Verificado',
      failure: 'Comprobación fallida',
      unavailable: 'No disponible',
      uncertain: 'Faltan pruebas'
    },
    endings:
      'Una salida Verificado libre completa la tarea; las demás la detienen. Los ciclos comparten presupuesto. Los problemas de permisos y efectos externos inciertos siempre detienen la ejecución.',
    invalid: 'Conecta todos los grupos al inicio, elige modelos y utiliza una sola conexión por salida.',
    modelHelp: 'Describe tareas adecuadas, limitaciones y ejecución local. La planificación utiliza esta descripción.',
    group: 'Grupo de modelos',
    add: 'Añadir grupo',
    entry: 'Empezar aquí',
    name: 'Nombre',
    description: 'Uso y puntos fuertes',
    models: 'Modelos · orden',
    addModel: 'Añadir modelo',
    remove: 'Eliminar',
    undo: 'Deshacer',
    redo: 'Rehacer',
    route: 'Flujo',
    addRoute: 'Añadir flujo'
  },
  ja: {
    ...en,
    help: 'グループを接続して実行順を設定します。グループ内のモデルは順番に試されます。ダブルクリックで追加し、ポート間をドラッグして接続します。',
    select: 'グループを選択してモデルと用途を編集します。',
    outcomes: { success: '検証済み', failure: '検証失敗', unavailable: '利用不可', uncertain: '根拠不足' },
    endings:
      '未接続の「検証済み」出力はタスクを完了し、他の未接続出力は停止します。ループは共通予算を使います。権限の問題や不明な外部操作がある場合は常に停止します。',
    invalid: 'すべてのグループを開始点から接続し、モデルを選択してください。各出力の接続は1つまでです。',
    modelHelp: '適したタスク、制限、ローカル実行について記述します。計画時に参照されます。',
    group: 'モデルグループ',
    add: 'グループを追加',
    entry: 'ここから開始',
    name: '名前',
    description: '用途と得意分野',
    models: 'モデル・実行順',
    addModel: 'モデルを追加',
    remove: '削除',
    undo: '元に戻す',
    redo: 'やり直す',
    route: 'ワークフロー',
    addRoute: 'ワークフローを追加'
  },
  zh: {
    ...en,
    help: '连接组以定义流程，组内模型按顺序尝试。双击画布添加组，拖动端口以连接。',
    select: '选择组以编辑模型和用途。',
    outcomes: { success: '已验证', failure: '验证失败', unavailable: '不可用', uncertain: '证据不足' },
    endings:
      '未连接的“已验证”输出完成任务，其他未连接输出停止任务。循环共享运行预算。权限问题和不确定的外部操作始终停止执行。',
    invalid: '从起点连接所有组，选择模型，每个输出最多一个连接。',
    modelHelp: '描述适用任务、限制和本地执行。规划时会参考此描述。',
    group: '模型组',
    add: '添加组',
    entry: '从此开始',
    name: '名称',
    description: '用途和优势',
    models: '模型 · 执行顺序',
    addModel: '添加模型',
    remove: '删除',
    undo: '撤销',
    redo: '重做',
    route: '工作流',
    addRoute: '添加工作流'
  },
  'zh-Hant': {
    ...en,
    help: '連接群組以定義流程，群組內模型依序嘗試。按兩下畫布新增群組，拖曳連接埠以連接。',
    select: '選取群組以編輯模型與用途。',
    outcomes: { success: '已驗證', failure: '驗證失敗', unavailable: '無法使用', uncertain: '證據不足' },
    endings:
      '未連接的「已驗證」輸出完成任務，其他未連接輸出停止任務。迴圈共用執行預算。權限問題和不確定的外部操作一律停止執行。',
    invalid: '從起點連接所有群組，選擇模型，每個輸出最多一個連線。',
    modelHelp: '描述適用任務、限制和本機執行。規劃時會參考此描述。',
    group: '模型群組',
    add: '新增群組',
    entry: '從此開始',
    name: '名稱',
    description: '用途與優勢',
    models: '模型 · 執行順序',
    addModel: '新增模型',
    remove: '刪除',
    undo: '復原',
    redo: '重做',
    route: '工作流程',
    addRoute: '新增工作流程'
  },
  ar: {
    ...en,
    help: 'اربط المجموعات لتحديد سير العمل. تُجرّب النماذج بالترتيب. انقر مرتين لإضافة مجموعة واسحب بين المنافذ لربطها.',
    select: 'اختر مجموعة لتعديل نماذجها والغرض منها.',
    outcomes: { success: 'تم التحقق', failure: 'فشل التحقق', unavailable: 'غير متاح', uncertain: 'أدلة ناقصة' },
    endings:
      'مخرج تم التحقق غير المتصل يُكمل المهمة؛ المخارج الأخرى توقفها. الحلقات تشترك في الميزانية. مشكلات الصلاحيات والآثار الخارجية غير المؤكدة توقف التنفيذ دائمًا.',
    invalid: 'اربط جميع المجموعات بنقطة البداية واختر النماذج واستخدم اتصالًا واحدًا لكل مخرج.',
    modelHelp: 'صف المهام المناسبة والقيود والتنفيذ المحلي. يُستخدم الوصف عند التخطيط.',
    group: 'مجموعة نماذج',
    add: 'إضافة مجموعة',
    entry: 'ابدأ هنا',
    name: 'الاسم',
    description: 'الاستخدام ونقاط القوة',
    models: 'النماذج · ترتيب التنفيذ',
    addModel: 'إضافة نموذج',
    remove: 'حذف',
    undo: 'تراجع',
    redo: 'إعادة',
    route: 'سير العمل',
    addRoute: 'إضافة سير عمل'
  }
}

export function graphCopy(locale: string): Copy {
  return copies[locale] ?? en
}
