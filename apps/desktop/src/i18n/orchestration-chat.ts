const en = {
  title: 'Orchestration',
  on: 'On',
  off: 'Off',
  selection: 'Orchestration team and profile',
  team: 'Worker team',
  architect: 'Architect profile',
  scope: 'From the next message. Applies to chats in this Hermes profile.'
}

const ru: typeof en = {
  title: 'Оркестрация',
  on: 'Вкл',
  off: 'Выкл',
  selection: 'Команда и профиль оркестрации',
  team: 'Команда исполнителей',
  architect: 'Профиль архитектора',
  scope: 'Со следующего сообщения. Для чатов текущего профиля Hermes.'
}

export const orchestrationChatCopy = (locale: string) => (locale === 'ru' ? ru : en)
