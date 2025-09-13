from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, 
    ConversationHandler
)
import config
from database import kb
import re
import uuid

# Состояния для ConversationHandler
(
    SELECTING_ACTION, SELECTING_TOPIC, SELECTING_SUBTOPIC, 
    TYPING_TITLE, TYPING_CONTENT, UPLOADING_IMAGE, UPLOADING_FILE, 
    TYPING_CAPTION, EDITING_MATERIAL, DELETING_MATERIAL, 
    ADDING_TOPIC, ADDING_SUBTOPIC, INTELLIGENT_SYSTEM, SHOWING_INSTRUCTIONS
) = range(14)

# Получаем список тем из базы знаний
topics = kb.get_topics()
# База знаний для интеллектуальной системы
INTELLIGENT_KNOWLEDGE_BASE = {
    "документ_подписание": {
        "keywords": ["документ", "подписание", "подписать", "подписан", "подписывать", "не приходит", "не поступает"],
        "questions": [
            "У вас не приходит документ на подписание?",
            "Не приходит МОЛу?",
            "Есть ли в справочнике сотрудники дубли?"
        ],
        "answers": {
            "да": {
                "0": "Проверьте настройки маршрутизации документов в системе.",
                "1": "Проверьте настройки прав МОЛа и его учетную запись в системе.",
                "2": "Удалите дубликаты сотрудников и перенастройте адресацию."
            },
            "нет": {
                "0": "Опишите проблему более подробно, возможно, дело не в подписании документов.",
                "1": "Тогда проблема может быть в настройках конкретного пользователя. Проверьте его учетную запись и права доступа.",
                "2": "Тогда проблема может быть в настройках маршрутизации. Проверьте правила маршрутизации документов в системе."
            }
        },
        # Добавляем информацию о связанном подразделе
        "related_subtopic": {
            "topic": "ОЦО ЦБ",
            "subtopic": "не_поступила_задача_на_подписание_молу",
            "condition": "all_yes"  # Показывать инструкцию только если на все вопросы ответили "да"
        }
    }
}

# Создаем клавиатуру для основного меню
def create_main_keyboard():
    keyboard = [[topic] for topic in topics]
    keyboard.append(["Поиск", "Управление материалами","Интеллектуальная система"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Создаем клавиатуру для подразделов
def create_subtopic_keyboard(topic):
    subtopics = kb.get_subtopics(topic)
    # Исключаем служебный файл _description из списка подразделов
    subtopics = [subtopic for subtopic in subtopics if subtopic != '_description']
    keyboard = [[subtopic] for subtopic in subtopics]
    keyboard.append(["Назад к разделам"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Клавиатура для управления материалами
manage_keyboard = [
    ["Добавить текст", "Добавить изображение", "Загрузить файл"],
    ["Добавить раздел", "Добавить подраздел", "Редактировать материал"],
    ["Удалить материал", "Назад к разделам"]
]
manage_markup = ReplyKeyboardMarkup(manage_keyboard, resize_keyboard=True)
# Клавиатура только с отменой для интеллектуального режима
cancel_only_keyboard = [["Отмена"]]
cancel_only_markup = ReplyKeyboardMarkup(cancel_only_keyboard, resize_keyboard=True)
# Клавиатура для ответов да/нет
yes_no_keyboard = [["Да", "Нет"], ["Отмена"]]
yes_no_markup = ReplyKeyboardMarkup(yes_no_keyboard, resize_keyboard=True)
# Глобальная переменная для хранения текущей клавиатуры
current_markup = create_main_keyboard()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    global current_markup
    
    welcome_text = """
Привет! Я - база знаний для системного аналитика в 1С.

Выбери раздел из меню ниже, напиши "Поиск [запрос]" для поиска информации или "Управление материалами" для редактирования базы знаний.
    """
    current_markup = create_main_keyboard()
    await update.message.reply_text(welcome_text, reply_markup=current_markup)
    return SELECTING_ACTION

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений в основном состоянии"""
    global current_markup
    
    text = update.message.text
    
    # Проверяем команды управления материалами
    if text == "Добавить текст":
        await update.message.reply_text("Выбери раздел для нового материала:", reply_markup=current_markup)
        context.user_data['action'] = 'add_text'
        return SELECTING_TOPIC
    
    elif text == "Добавить изображение":
        await update.message.reply_text("Выбери раздел для нового изображения:", reply_markup=current_markup)
        context.user_data['action'] = 'add_image'
        return SELECTING_TOPIC
    
    elif text == "Загрузить файл":
        await update.message.reply_text("Выбери раздел для загрузки файла:", reply_markup=current_markup)
        context.user_data['action'] = 'upload_file'
        return SELECTING_TOPIC
    
    elif text == "Добавить раздел":
        await update.message.reply_text("Введите название нового раздела:")
        context.user_data['action'] = 'add_topic'
        return ADDING_TOPIC
    
    elif text == "Добавить подраздел":
        await update.message.reply_text("Выбери раздел для добавления подраздела:", reply_markup=current_markup)
        context.user_data['action'] = 'add_subtopic'
        return SELECTING_TOPIC
    
    elif text == "Редактировать материал":
        await update.message.reply_text("Выбери раздел для редактирования:", reply_markup=current_markup)
        context.user_data['action'] = 'edit'
        return SELECTING_TOPIC
    
    elif text == "Удалить материал":
        await update.message.reply_text("Выбери раздел для удаления материала:", reply_markup=current_markup)
        context.user_data['action'] = 'delete'
        return SELECTING_TOPIC
    
    elif text == "Поиск":
        await update.message.reply_text("Напиши 'Поиск [запрос]' для поиска информации. Например: 'Поиск Waterfall'")
        return SELECTING_ACTION
    
    elif text == "Управление материалами":
        await update.message.reply_text("Выбери действие:", reply_markup=manage_markup)
        return SELECTING_ACTION
    elif text == "Интеллектуальная система":
        # Сбрасываем состояние интеллектуальной системы при входе
        if 'intelligent_state' in context.user_data:
            del context.user_data['intelligent_state']
        await update.message.reply_text(
            "Опишите вашу проблему, и я постараюсь помочь. Например: 'Не приходит документ на подписание'",
            reply_markup=cancel_only_markup  # Используем клавиатуру только с отменой
        )
        return INTELLIGENT_SYSTEM
    elif text == "Назад к разделам":
        current_markup = create_main_keyboard()
        # Очищаем информацию о текущем разделе из контекста
        if 'current_topic' in context.user_data:
            del context.user_data['current_topic']
        await update.message.reply_text("Выбери раздел:", reply_markup=current_markup)
        return SELECTING_ACTION
    
    elif text.lower().startswith("поиск "):
        query = text[6:]
        if query:
            result = kb.search(query)
            await update.message.reply_text(result[:4000])
        else:
            await update.message.reply_text("Напиши запрос для поиска после команды 'Поиск'")
        return SELECTING_ACTION
    
    # Проверяем, является ли сообщение одним из разделов
    elif text in topics:
        # Показываем описание раздела и его подразделы
        description = kb.get_topic_description(text)
        subtopics = kb.get_subtopics(text)
        # Исключаем служебный файл _description из списка подразделов
        subtopics = [subtopic for subtopic in subtopics if subtopic != '_description']
        
        if subtopics:
            # Сохраняем текущий раздел и показываем подразделы
            context.user_data['current_topic'] = text
            current_markup = create_subtopic_keyboard(text)
            
            response = f"{description}\n\nПодразделы раздела '{text}':\n"
            for subtopic in subtopics:
                response += f"• {subtopic}\n"
            response += "\nВыбери подраздел:"
            
            await update.message.reply_text(response, reply_markup=current_markup)
            return SELECTING_SUBTOPIC
        else:
            # В разделе нет подразделов
            response = f"{description}\n\nВ разделе '{text}' пока нет подразделов. Добавь подраздел через меню 'Управление материалами'."
            await update.message.reply_text(response)
            return SELECTING_ACTION
    
    # Если команда не распознана
    await update.message.reply_text("Не понимаю команду. Выбери раздел из меню или используй 'Поиск'.")
    return SELECTING_ACTION
async def show_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для показа инструкций из подраздела"""
    global current_markup
    
    user_input = update.message.text
    
    if user_input == "Отмена":
        current_markup = create_main_keyboard()
        await update.message.reply_text("Действие отменено.", reply_markup=current_markup)
        
        # Очищаем информацию об инструкции
        if 'instructions_topic' in context.user_data:
            del context.user_data['instructions_topic']
        if 'instructions_subtopic' in context.user_data:
            del context.user_data['instructions_subtopic']
            
        return SELECTING_ACTION
    
    if user_input == "Показать инструкцию":
        # Получаем информацию о подразделе
        topic = context.user_data.get('instructions_topic')
        subtopic = context.user_data.get('instructions_subtopic')
        
        if topic and subtopic:
            # Показываем содержимое подраздела
            content = kb.get_content(topic, subtopic)
            
            # Отправляем текст
            await update.message.reply_text(content["text"])
            
            # Отправляем изображения, если они есть
            for image_info in content["images"]:
                try:
                    with open(image_info["path"], 'rb') as photo:
                        caption = f"{image_info['caption']}\n\nID: {image_info['id']}"
                        await update.message.reply_photo(photo=photo, caption=caption)
                except FileNotFoundError:
                    await update.message.reply_text(f"Изображение не найдено: {image_info['path']}")
            
            # Отправляем файлы, если они есть
            for file_info in content["files"]:
                try:
                    with open(file_info["path"], 'rb') as file:
                        caption = f"{file_info['caption']}\n\nID: {file_info['id']}"
                        await update.message.reply_document(document=file, caption=caption)
                except FileNotFoundError:
                    await update.message.reply_text(f"Файл не найден: {file_info['path']}")
            
            # Очищаем информацию об инструкции
            del context.user_data['instructions_topic']
            del context.user_data['instructions_subtopic']
            
            # Возвращаемся к основному меню
            current_markup = create_main_keyboard()
            await update.message.reply_text("Чем еще могу помочь?", reply_markup=current_markup)
            
            return SELECTING_ACTION
        else:
            await update.message.reply_text("Информация об инструкции не найдена.")
            return SHOWING_INSTRUCTIONS
    
    await update.message.reply_text("Пожалуйста, выберите действие из предложенных вариантов.")
    return SHOWING_INSTRUCTIONS

async def handle_intelligent_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик интеллектуальной системы"""
    global current_markup
    
    user_input = update.message.text.lower()
    
    if user_input == "отмена":
        current_markup = create_main_keyboard()
        await update.message.reply_text("Диалог прерван.", reply_markup=current_markup)
        return SELECTING_ACTION
    
    # Инициализация или получение текущего состояния диалога
    if 'intelligent_state' not in context.user_data:
        context.user_data['intelligent_state'] = {
            'current_topic': None,
            'current_question': 0,
            'answers': {}
        }
    
    state = context.user_data['intelligent_state']
    
    # Определяем тему по ключевым словам
    if not state['current_topic']:
        matched_topics = []
        for topic, data in INTELLIGENT_KNOWLEDGE_BASE.items():
            for keyword in data['keywords']:
                if re.search(rf'\b{keyword}\b', user_input):
                    matched_topics.append(topic)
                    break
        
        if matched_topics:
            state['current_topic'] = matched_topics[0]
            state['current_question'] = 0
            question = INTELLIGENT_KNOWLEDGE_BASE[state['current_topic']]['questions'][0]
            await update.message.reply_text(question, reply_markup=yes_no_markup)
            return INTELLIGENT_SYSTEM
        else:
            current_markup = create_main_keyboard()
            await update.message.reply_text(
                "Не могу определить тему вашего вопроса. Попробуйте использовать другие слова или обратитесь к разделам базы знаний.",
                reply_markup=current_markup
            )
            return SELECTING_ACTION
    
    # Обработка ответов да/нет
    if user_input in ["да", "нет"]:
        topic_data = INTELLIGENT_KNOWLEDGE_BASE[state['current_topic']]
        current_q = state['current_question']
        
        # Сохраняем ответ
        state['answers'][current_q] = user_input
        
        # Проверяем, есть ли следующий вопрос
        if current_q + 1 < len(topic_data['questions']):
            state['current_question'] += 1
            next_question = topic_data['questions'][current_q + 1]
            await update.message.reply_text(next_question, reply_markup=yes_no_markup)
            return INTELLIGENT_SYSTEM
        else:
            # Формируем итоговый ответ на основе всех ответов
            final_answer = ""
            for i, answer in state['answers'].items():
                answer_text = topic_data['answers'][answer].get(str(i), "")
                if answer_text:
                    final_answer += f"{answer_text}\n\n"
            
            # Проверяем, нужно ли показывать инструкцию из подраздела
            if 'related_subtopic' in topic_data:
                condition = topic_data['related_subtopic'].get('condition')
                topic_name = topic_data['related_subtopic']['topic']
                subtopic_name = topic_data['related_subtopic']['subtopic']
                
                # Проверяем условие для показа инструкции
                show_instructions = False
                if condition == "all_yes":
                    show_instructions = all(answer == "да" for answer in state['answers'].values())
                
                if show_instructions:
                    # Сохраняем информацию о подразделе для показа
                    context.user_data['instructions_topic'] = topic_name
                    context.user_data['instructions_subtopic'] = subtopic_name
                    
                    # Добавляем предложение посмотреть инструкцию
                    final_answer += f"\nРекомендую ознакомиться с инструкцией по настройке: '{subtopic_name}'"
            
            # Устанавливаем клавиатуру с предложением посмотреть инструкцию
            if 'instructions_topic' in context.user_data:
                instructions_keyboard = [["Показать инструкцию"], ["Отмена"]]
                instructions_markup = ReplyKeyboardMarkup(instructions_keyboard, resize_keyboard=True)
                await update.message.reply_text(final_answer, reply_markup=instructions_markup)
            else:
                current_markup = create_main_keyboard()
                await update.message.reply_text(final_answer, reply_markup=current_markup)
            
            # Сбрасываем состояние интеллектуальной системы
            del context.user_data['intelligent_state']
            
            # Переходим в состояние показа инструкции или возвращаемся к выбору действия
            if 'instructions_topic' in context.user_data:
                return SHOWING_INSTRUCTIONS
            else:
                return SELECTING_ACTION
    else:
        await update.message.reply_text("Пожалуйста, ответьте 'Да' или 'Нет'.", reply_markup=yes_no_markup)
        return INTELLIGENT_SYSTEM

    
async def handle_subtopic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора подраздела"""
    global current_markup
    
    text = update.message.text.strip()  # Убираем лишние пробелы
    
    # Проверяем, не хочет ли пользователь вернуться к разделам
    if text == "Назад к разделам":
        current_markup = create_main_keyboard()
        # Очищаем информацию о текущем разделе из контекста
        if 'current_topic' in context.user_data:
            del context.user_data['current_topic']
        await update.message.reply_text("Выбери раздел:", reply_markup=current_markup)
        return SELECTING_ACTION
    
    # Проверяем, есть ли текущий раздел в контексте
    if 'current_topic' not in context.user_data:
        current_markup = create_main_keyboard()
        await update.message.reply_text("Сессия устарела. Выбери раздел заново:", reply_markup=current_markup)
        return SELECTING_ACTION
    
    current_topic = context.user_data['current_topic']
    subtopics = kb.get_subtopics(current_topic)
    # Исключаем служебный файл _description из списка подразделов
    subtopics = [subtopic for subtopic in subtopics if subtopic != '_description']
    
    # Нормализуем текст для сравнения (приводим к нижнему регистру и заменяем пробелы на подчеркивания)
    normalized_text = text.lower().replace(' ', '_')
    
    # Ищем подраздел с учетом нормализации
    matching_subtopic = None
    for subtopic in subtopics:
        normalized_subtopic = subtopic.lower().replace(' ', '_')
        if normalized_subtopic == normalized_text:
            matching_subtopic = subtopic
            break
    
    # Проверяем, является ли сообщение одним из подразделов
    if matching_subtopic:
        # Показываем содержимое подраздела
        content = kb.get_content(current_topic, matching_subtopic)
        
        # Отправляем текст
        await update.message.reply_text(content["text"])
        
        # Отправляем изображения, если они есть
        for image_info in content["images"]:
            try:
                with open(image_info["path"], 'rb') as photo:
                    caption = f"{image_info['caption']}\n\nID: {image_info['id']}"
                    await update.message.reply_photo(photo=photo, caption=caption)
            except FileNotFoundError:
                await update.message.reply_text(f"Изображение не найдено: {image_info['path']}")
        
        # Отправляем файлы, если они есть
        for file_info in content["files"]:
            try:
                with open(file_info["path"], 'rb') as file:
                    caption = f"{file_info['caption']}\n\nID: {file_info['id']}"
                    await update.message.reply_document(document=file, caption=caption)
            except FileNotFoundError:
                await update.message.reply_text(f"Файл не найден: {file_info['path']}")
        
        return SELECTING_ACTION
    else:
        # Если это не подраздел, показываем подразделы снова
        description = kb.get_topic_description(current_topic)
        
        response = f"{description}\n\nПодразделы раздела '{current_topic}':\n"
        for subtopic in subtopics:
            response += f"• {subtopic}\n"
        response += "\nВыбери подраздел:"
        
        await update.message.reply_text(response, reply_markup=current_markup)
        return SELECTING_SUBTOPIC

async def select_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора раздела для управления материалами"""
    text = update.message.text
    action = context.user_data.get('action')
    
    if text not in topics:
        await update.message.reply_text("Пожалуйста, выбери раздел из предложенных вариантов.")
        return SELECTING_TOPIC
    
    context.user_data['topic'] = text
    
    if action == 'add_text':
        # Переходим к выбору подраздела
        subtopics = kb.get_subtopics(text)
        # Исключаем служебный файл _description из списка подразделов
        subtopics = [subtopic for subtopic in subtopics if subtopic != '_description']
        if not subtopics:
            await update.message.reply_text("В этом разделе нет подразделов. Сначала добавь подраздел.")
            return SELECTING_ACTION
        
        global current_markup
        current_markup = create_subtopic_keyboard(text)
        await update.message.reply_text("Выбери подраздел для добавления текста:", reply_markup=current_markup)
        context.user_data['current_topic'] = text
        return SELECTING_SUBTOPIC
    
    elif action == 'add_image':
        # Переходим к выбору подраздела
        subtopics = kb.get_subtopics(text)
        subtopics = [subtopic for subtopic in subtopics if subtopic != '_description']
        if not subtopics:
            await update.message.reply_text("В этом разделе нет подразделов. Сначала добавь подраздел.")
            return SELECTING_ACTION
        
        current_markup = create_subtopic_keyboard(text)
        await update.message.reply_text("Выбери подраздел для добавления изображения:", reply_markup=current_markup)
        context.user_data['current_topic'] = text
        return SELECTING_SUBTOPIC
    
    elif action == 'upload_file':
        # Переходим к выбору подраздела
        subtopics = kb.get_subtopics(text)
        subtopics = [subtopic for subtopic in subtopics if subtopic != '_description']
        if not subtopics:
            await update.message.reply_text("В этого раздела нет подразделов. Сначала добавь подраздел.")
            return SELECTING_ACTION
        
        current_markup = create_subtopic_keyboard(text)
        await update.message.reply_text("Выбери подраздел для загрузки файла:", reply_markup=current_markup)
        context.user_data['current_topic'] = text
        return SELECTING_SUBTOPIC
    
    elif action == 'add_subtopic':
        await update.message.reply_text("Введите название нового подраздела:")
        return ADDING_SUBTOPIC
    
    elif action == 'edit':
        # Переходим к выбору подраздела
        subtopics = kb.get_subtopics(text)
        subtopics = [subtopic for subtopic in subtopics if subtopic != '_description']
        if not subtopics:
            await update.message.reply_text("В этом разделе нет подразделов. Сначала добавь подраздел.")
            return SELECTING_ACTION
        
        current_markup = create_subtopic_keyboard(text)
        await update.message.reply_text("Выбери подраздел для редактирования:", reply_markup=current_markup)
        context.user_data['current_topic'] = text
        return SELECTING_SUBTOPIC
    
    elif action == 'delete':
        # Переходим к выбору подраздела
        subtopics = kb.get_subtopics(text)
        subtopics = [subtopic for subtopic in subtopics if subtopic != '_description']
        if not subtopics:
            await update.message.reply_text("В этом разделе нет подразделов. Сначала добавь подраздел.")
            return SELECTING_ACTION
        
        current_markup = create_subtopic_keyboard(text)
        await update.message.reply_text("Выбери подраздел для удаления материала:", reply_markup=current_markup)
        context.user_data['current_topic'] = text
        return SELECTING_SUBTOPIC
    
    return SELECTING_ACTION

async def select_subtopic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора подраздела для действий с материалами"""
    text = update.message.text.strip()  # Убираем лишние пробелы
    action = context.user_data.get('action')
    topic = context.user_data.get('topic')
    
    # Получаем подразделы для текущего раздела
    subtopics = kb.get_subtopics(topic) if topic else []
    # Исключаем служебный файл _description из списка подразделов
    subtopics = [subtopic for subtopic in subtopics if subtopic != '_description']
    
    # Нормализуем текст для сравнения
    normalized_text = text.lower().replace(' ', '_')
    
    # Ищем подраздел с учетом нормализации
    matching_subtopic = None
    for subtopic in subtopics:
        normalized_subtopic = subtopic.lower().replace(' ', '_')
        if normalized_subtopic == normalized_text:
            matching_subtopic = subtopic
            break
    
    # Проверяем, является ли текст подразделом
    if not matching_subtopic:
        await update.message.reply_text("Пожалуйста, выбери подраздел из предложенных вариантов.")
        return SELECTING_SUBTOPIC
    
    context.user_data['subtopic'] = matching_subtopic
    
    if action == 'add_text':
        await update.message.reply_text("Введи заголовок материала:")
        return TYPING_TITLE
    
    elif action == 'add_image':
        await update.message.reply_text("Загрузи изображение:")
        return UPLOADING_IMAGE
    
    elif action == 'upload_file':
        await update.message.reply_text("Загрузи файл:")
        return UPLOADING_FILE
    
    elif action == 'edit':
        # Формируем ключ подраздела
        topic_key = f"{topic}/{matching_subtopic}"
        materials = kb.get_images_for_topic(topic_key) + kb.get_files_for_topic(topic_key)
        
        if not materials:
            await update.message.reply_text("В этом подразделе нет материалов для редактирования.")
            return SELECTING_ACTION
        
        materials_list = "\n".join([f"ID: {m['id']} - {m['caption']}" for m in materials])
        await update.message.reply_text(f"Материалы в подразделе '{matching_subtopic}':\n\n{materials_list}\n\nВведи ID материала для редактирования:")
        return EDITING_MATERIAL
    
    elif action == 'delete':
        # Формируем ключ подраздела
        topic_key = f"{topic}/{matching_subtopic}"
        materials = kb.get_images_for_topic(topic_key) + kb.get_files_for_topic(topic_key)
        
        if not materials:
            await update.message.reply_text("В этом подразделе нет материалов для удаления.")
            return SELECTING_ACTION
        
        materials_list = "\n".join([f"ID: {m['id']} - {m['caption']}" for m in materials])
        await update.message.reply_text(f"Материалы в подразделе '{matching_subtopic}':\n\n{materials_list}\n\nВведи ID материала для удаления:")
        return DELETING_MATERIAL
    
    return SELECTING_ACTION

async def add_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление нового раздела"""
    global topics, current_markup
    
    topic_name = update.message.text
    
    # Проверяем, не существует ли уже такой раздел
    if topic_name in topics:
        await update.message.reply_text("Раздел с таким названием уже существует. Введите другое название:")
        return ADDING_TOPIC
    
    # Добавляем новый раздел
    success = kb.add_topic(topic_name)
    
    if success:
        # Обновляем список тем
        topics = kb.get_topics()
        current_markup = create_main_keyboard()
        
        await update.message.reply_text(f"Раздел '{topic_name}' успешно добавлен!", reply_markup=current_markup)
    else:
        await update.message.reply_text("Ошибка при добавлении раздела. Попробуйте еще раз.")
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return SELECTING_ACTION

async def add_subtopic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление нового подраздела"""
    global current_markup
    
    subtopic_name = update.message.text
    topic = context.user_data['topic']
    
    # Проверяем, не существует ли уже такой подраздел
    existing_subtopics = kb.get_subtopics(topic)
    existing_subtopics = [subtopic for subtopic in existing_subtopics if subtopic != '_description']
    
    # Нормализуем для сравнения
    normalized_new_subtopic = subtopic_name.lower().replace(' ', '_')
    for existing_subtopic in existing_subtopics:
        normalized_existing = existing_subtopic.lower().replace(' ', '_')
        if normalized_existing == normalized_new_subtopic:
            await update.message.reply_text("Подраздел с таким названием уже существует в этом разделе. Введите другое название:")
            return ADDING_SUBTOPIC
    
    # Добавляем новый подраздел
    success = kb.add_subtopic(topic, subtopic_name)
    
    if success:
        await update.message.reply_text(f"Подраздел '{subtopic_name}' успешно добавлен в раздел '{topic}'!", reply_markup=current_markup)
    else:
        await update.message.reply_text("Ошибка при добавлении подраздела. Попробуйте еще раз.")
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return SELECTING_ACTION

async def create_text_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание текстового материала"""
    if 'title' not in context.user_data:
        context.user_data['title'] = update.message.text
        await update.message.reply_text("Теперь введи содержание материала:")
        return TYPING_CONTENT
    else:
        content = update.message.text
        title = context.user_data['title']
        topic = context.user_data['topic']
        subtopic = context.user_data['subtopic']
        
        # Формируем ключ подраздела
        topic_key = f"{topic}/{subtopic}"
        
        # Создаем текстовый файл
        full_text = f"{title}\n\n{content}"
        filename = f"{topic_key.replace('/', '_')}_{uuid.uuid4().hex[:8]}.txt"
        file_path = kb.create_text_file(full_text, filename)
        
        # Добавляем материал в базу знаний
        material_id = kb.add_material(topic_key, file_path, title, "file")
        
        # Отправляем подтверждение
        await update.message.reply_text(f"Материал '{title}' успешно добавлен в подраздел '{subtopic}' раздела '{topic}'! ID: {material_id}")
        
        # Показываем созданный файл
        with open(file_path, 'rb') as file:
            await update.message.reply_document(document=file, caption=title)
        
        # Очищаем данные пользователя
        context.user_data.clear()
        
        return SELECTING_ACTION

async def upload_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки изображения"""
    if update.message.photo:
        # Получаем самое большое изображение
        photo = update.message.photo[-1]
        file = await photo.get_file()
        file_data = await file.download_as_bytearray()
        
        # Определяем раздел и подраздел
        topic = context.user_data.get('topic')
        subtopic = context.user_data.get('subtopic')
        
        # Формируем ключ подраздела
        topic_key = f"{topic}/{subtopic}"
        
        # Сохраняем изображение
        filename = f"{topic_key.replace('/', '_')}_{uuid.uuid4().hex[:8]}.jpg"
        image_path = kb.save_uploaded_file(file_data, filename, "image")
        
        context.user_data['file_path'] = image_path
        await update.message.reply_text("Изображение загружено! Теперь введи подпись:")
        return TYPING_CAPTION
    
    await update.message.reply_text("Пожалуйста, загрузи изображение.")
    return UPLOADING_IMAGE

async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки файла"""
    if update.message.document:
        # Получаем файл
        document = update.message.document
        file = await document.get_file()
        file_data = await file.download_as_bytearray()
        
        # Определяем раздел и подраздел
        topic = context.user_data.get('topic')
        subtopic = context.user_data.get('subtopic')
        
        # Формируем ключ подраздела
        topic_key = f"{topic}/{subtopic}"
        
        # Сохраняем файл
        filename = document.file_name or f"{topic_key.replace('/', '_')}_{uuid.uuid4().hex[:8]}"
        file_path = kb.save_uploaded_file(file_data, filename, "file")
        
        context.user_data['file_path'] = file_path
        context.user_data['file_type'] = "file"
        await update.message.reply_text("Файл загружен! Теперь введи описание:")
        return TYPING_CAPTION
    
    await update.message.reply_text("Пожалуйста, загрузи файл.")
    return UPLOADING_FILE

async def add_file_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление подписи к файлу или изображению"""
    caption = update.message.text
    
    # Определяем раздел и подраздел
    topic = context.user_data.get('topic')
    subtopic = context.user_data.get('subtopic')
    
    # Формируем ключ подраздела
    topic_key = f"{topic}/{subtopic}"
    
    file_path = context.user_data['file_path']
    file_type = context.user_data.get('file_type', 'image')
    
    # Добавляем материал в базу знаний
    material_id = kb.add_material(topic_key, file_path, caption, file_type)
    
    # Отправляем подтверждение
    await update.message.reply_text(f"Файл успешно добавлен в подраздел '{subtopic}' раздела '{topic}'! ID: {material_id}")
    
    # Показываем добавленный файл
    if file_type == "image":
        with open(file_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption=caption)
    else:
        with open(file_path, 'rb') as file:
            await update.message.reply_document(document=file, caption=caption)
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return SELECTING_ACTION

async def edit_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование материала"""
    material_id = update.message.text
    
    # Определяем раздел и подраздел
    topic = context.user_data.get('topic')
    subtopic = context.user_data.get('subtopic')
    
    # Формируем ключ подраздела
    topic_key = f"{topic}/{subtopic}"
    
    # Ищем материал среди изображений и файлов
    material = kb.get_material(topic_key, material_id, "image") or kb.get_material(topic_key, material_id, "file")
    
    if not material:
        await update.message.reply_text("Материал с таким ID не найден. Попробуй еще раз:")
        return EDITING_MATERIAL
    
    context.user_data['material_id'] = material_id
    context.user_data['material_type'] = "image" if "type" not in material or material["type"] == "image" else "file"
    context.user_data['topic_key'] = topic_key
    
    # Показываем текущий материал
    if context.user_data['material_type'] == "image":
        with open(material['path'], 'rb') as photo:
            await update.message.reply_photo(
                photo=photo, 
                caption=f"Текущий материал: {material['caption']}\n\nВведи новое описание или отправь новое изображение:"
            )
    else:
        with open(material['path'], 'rb') as file:
            await update.message.reply_document(
                document=file, 
                caption=f"Текущий материал: {material['caption']}\n\nВведи новое описание или отправь новый файл:"
            )
    
    return TYPING_CAPTION

async def update_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновление материала"""
    material_id = context.user_data['material_id']
    topic_key = context.user_data['topic_key']
    material_type = context.user_data['material_type']
    
    if update.message.photo and material_type == "image":
        # Пользователь отправил новое изображение
        photo = update.message.photo[-1]
        file = await photo.get_file()
        file_data = await file.download_as_bytearray()
        
        # Сохраняем новое изображение
        filename = f"{topic_key.replace('/', '_')}_{uuid.uuid4().hex[:8]}.jpg"
        new_file_path = kb.save_uploaded_file(file_data, filename, "image")
        
        # Обновляем материал
        success = kb.update_material(
            topic_key, 
            material_id, 
            new_file_path=new_file_path,
            material_type=material_type
        )
        
        if success:
            await update.message.reply_text("Изображение материала успешно обновлено!")
        else:
            await update.message.reply_text("Ошибка при обновлении изображения.")
    
    elif update.message.document and material_type == "file":
        # Пользователь отправил новый файл
        document = update.message.document
        file = await document.get_file()
        file_data = await file.download_as_bytearray()
        
        # Сохраняем новый файл
        filename = document.file_name or f"{topic_key.replace('/', '_')}_{uuid.uuid4().hex[:8]}"
        new_file_path = kb.save_uploaded_file(file_data, filename, "file")
        
        # Обновляем материал
        success = kb.update_material(
            topic_key, 
            material_id, 
            new_file_path=new_file_path,
            material_type=material_type
        )
        
        if success:
            await update.message.reply_text("Файл материала успешно обновлен!")
        else:
            await update.message.reply_text("Ошибка при обновлении файла.")
    
    else:
        # Пользователь ввел новое описание
        new_caption = update.message.text
        
        # Обновляем материал
        success = kb.update_material(
            topic_key, 
            material_id, 
            new_caption=new_caption,
            material_type=material_type
        )
        
        if success:
            await update.message.reply_text("Описание материала успешно обновлено!")
        else:
            await update.message.reply_text("Ошибка при обновлении описания.")
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return SELECTING_ACTION

async def delete_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление материала"""
    material_id = update.message.text
    
    # Определяем раздел и подраздел
    topic = context.user_data.get('topic')
    subtopic = context.user_data.get('subtopic')
    
    # Формируем ключ подраздела
    topic_key = f"{topic}/{subtopic}"
    
    # Пытаемся удалить материал как изображение
    success = kb.delete_material(topic_key, material_id, "image")
    
    # Если не нашли как изображение, пробуем как файл
    if not success:
        success = kb.delete_material(topic_key, material_id, "file")
    
    if success:
        await update.message.reply_text(f"Материал успешно удален из подраздела '{subtopic}'!")
    else:
        await update.message.reply_text("Материал с таким ID не найден. Попробуй еще раз:")
        return DELETING_MATERIAL
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return SELECTING_ACTION

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущей операции"""
    global current_markup
    
    current_markup = create_main_keyboard()
    await update.message.reply_text("Операция отменена.", reply_markup=current_markup)
    context.user_data.clear()
    return SELECTING_ACTION

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
Я могу:
- Показать информацию по разделам и подразделам
- Выполнить поиск по материалам
- Добавлять новые разделы и подразделы
- Добавлять новые материалы (текст, изображения и файлы) в подразделы
- Редактировать и удалять материалы

Для управления материалами нажми "Управление материалами"
    """
    await update.message.reply_text(help_text)
    return SELECTING_ACTION

def main():
    """Основная функция запуска бота"""
    application = Application.builder().token(config.TOKEN).build()
    
    # Создаем обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_ACTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
                CommandHandler('help', help_command)
            ],
            SELECTING_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_topic),
                CommandHandler('cancel', cancel)
            ],
            SELECTING_SUBTOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_subtopic_selection),
                CommandHandler('cancel', cancel)
            ],
            ADDING_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_topic),
                CommandHandler('cancel', cancel)
            ],
            ADDING_SUBTOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_subtopic),
                CommandHandler('cancel', cancel)
            ],
            TYPING_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_text_material),
                CommandHandler('cancel', cancel)
            ],
            TYPING_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_text_material),
                CommandHandler('cancel', cancel)
            ],
            UPLOADING_IMAGE: [
                MessageHandler(filters.PHOTO, upload_image),
                CommandHandler('cancel', cancel)
            ],
            UPLOADING_FILE: [
                MessageHandler(filters.Document.ALL, upload_file),
                CommandHandler('cancel', cancel)
            ],
            TYPING_CAPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_file_caption),
                MessageHandler(filters.PHOTO, update_material),
                MessageHandler(filters.Document.ALL, update_material),
                CommandHandler('cancel', cancel)
            ],
            EDITING_MATERIAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_material),
                CommandHandler('cancel', cancel)
            ],
            DELETING_MATERIAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_material),
                CommandHandler('cancel', cancel)
            ],
            SHOWING_INSTRUCTIONS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, show_instructions),
            CommandHandler('cancel', cancel)
            ],
            INTELLIGENT_SYSTEM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_intelligent_system),
                CommandHandler('cancel', cancel)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()