from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ConversationHandler, CommandHandler, MessageHandler, ContextTypes, filters, PicklePersistence, BaseHandler
from datetime import datetime, timedelta
from ..ruz_fa_api.ruz_fa_api import RuzFaAPI
import re


GROUP, DATE = range(2)

class Bot:
    def __init__(self, bot_token: str, persistence_file_path: str, ruz_fa_api: RuzFaAPI):
        self.bot_token = bot_token
        self.persistence_file_path = persistence_file_path
        self.ruz_fa_api = ruz_fa_api

    async def run(self):
        persistence = PicklePersistence(self.persistence_file_path)
        application = ApplicationBuilder().token(self.bot_token).persistence(persistence).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                GROUP: [MessageHandler(filters.TEXT, self.save_group)],
                DATE: [MessageHandler(filters.Regex("^(Сегодня|Завтра|Послезавтра|\d{2}.\d{2})$"), self.save_date),
                        MessageHandler(filters.Regex("^Показать расписание на другой день$"), self.choose_date)],
            },
            fallbacks=[MessageHandler(filters.Regex("^Вернуться к выбору группы$"), self.choose_group)],
            name="ruz_fa_schedule",
            persistent=True,
            allow_reentry=True,
        )

        application.add_handler(conv_handler)

        await application.initialize()
        await application.start()
        await application.updater.start_polling()

    def __get_date(self, delta_days: int = 0, date: str = None):
        if date:
            date_lst = date.split(".")
            return f"{datetime.now().year}.{date_lst[1]}.{date_lst[0]}"
        return (datetime.now() + timedelta(days=delta_days)).strftime("%Y.%m.%d")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Привет! Я неофициальный бот для просмотра расписания ruz.fa.ru.")
        return await self.choose_group(update, context)

    async def choose_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Введите название группы:")
        return GROUP

    async def save_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        group_name = update.message.text
        if not re.match(r"^[а-яА-Я]+\d{2}-\d$", group_name):
            await update.message.reply_text("Некорректное название группы")
            return await self.choose_group(update, context)
        user_data = context.user_data
        group_id = None

        data_lst = self.ruz_fa_api.get_group_by_name(group_name)
        if data_lst:
            group_id = data_lst["id"]
            user_data["group_id"] = group_id
            user_data["group_name"] = group_name
            return await self.choose_date(update, context)
        else:
            await update.message.reply_text("Группа не найдена")
            return await self.choose_group(update, context)

    async def choose_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_keyboard = [["Сегодня", "Завтра"],
                        ["Послезавтра", "Вернуться к выбору группы"]]
        reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Выберите дату из списка или введите вручную в формате dd.mm:", reply_markup=reply_markup)
        return DATE

    def __convert_word_to_delta_days(self, word: str) -> int:
        words_dct = {"Сегодня": 0, "Завтра": 1, "Послезавтра": 2}
        if word in words_dct.keys():
            return words_dct[word]
        return None

    async def save_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE): # FIXME: Не выдаёт расписание на 09.10 по группе ТРПО23-3 (или может вообще по всем группам), возможно дело в дате, а может и в самих группах
        date = update.message.text
        user_data = context.user_data

        delta_days = self.__convert_word_to_delta_days(date)
        if delta_days is not None:
            date_to_save = self.__get_date(delta_days=delta_days)
        else:
            date_to_save = self.__get_date(date=date)
        user_data["date"] = date_to_save
        return await self.show_schedule(update, context)

    def __convert_schedule_dict_to_str(self, schedule_dict: dict) -> str:
        schedule_str = ""
        for lesson in schedule_dict:
            schedule_str += f"{lesson['auditorium']}\n{lesson['beginLesson']} - {lesson['endLesson']}\n{lesson['kindOfWork']}\n{lesson['discipline']}\n{lesson['lecturer']}\n{'-'*10}\n"
        return schedule_str

    async def show_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        group_id = user_data["group_id"]
        date = user_data["date"]
        schedule = self.ruz_fa_api.get_group_schedule_by_group_id(group_id, date)
        if schedule:
            schedule_str = self.__convert_schedule_dict_to_str(schedule)
            await update.message.reply_text(schedule_str) # TODO: Разобраться с выводом расписания
        else:
            await update.message.reply_text(f"Расписание на эту дату не найдено")
        
        reply_keyboard = [["Показать расписание на другой день", "Вернуться к выбору группы"]]
        reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return DATE
