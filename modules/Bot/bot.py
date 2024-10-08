from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, ConversationHandler, CommandHandler, MessageHandler, ContextTypes, filters, PicklePersistence, BaseHandler
from datetime import datetime, timedelta
from ..ruz_fa_api.ruz_fa_api import RuzFaAPI


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
                GROUP: [MessageHandler(filters.Regex("^[а-яА-Я]+\d{2}-\d$"), self.save_group)],
                DATE: [MessageHandler(filters.Regex("^(Сегодня|Завтра|Послезавтра|\d{2}.\d{2}.\d{4})$"), self.save_date),
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
        if delta_days:
            return (datetime.now() + timedelta(days=delta_days)).strftime("%Y.%m.%d")
        if date:
            date_lst = date.split(".")
            return f"{datetime.now().year}.{date_lst[1]}.{date_lst[0]}"

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Привет! Я неофициальный бот для просмотра расписания ruz.fa.ru.")
        return await self.choose_group(update, context)

    async def choose_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Выберите группу:")
        return GROUP

    async def save_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        group = update.message.text
        user_data = context.user_data
        group_id = None

        data_lst = self.ruz_fa_api.get_group(group)
        for group_json in data_lst:
            if group_json["label"] == group:
                group_id = group_json["id"]
                break
        
        if group_id:
            user_data["group_id"] = group_id
            user_data["group"] = group
            return await self.choose_date(update, context)

        await update.message.reply_text("Группа не найдена")
        return await self.choose_group(update, context)

    async def choose_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_keyboard = [["Сегодня", "Завтра"],
                        ["Послезавтра", "Вернуться к выбору группы"]]
        reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Выберите дату из списка или введите вручную в формате dd.mm:", reply_markup=reply_markup)
        return DATE

    async def save_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE): # FIXME: Не выдаёт расписание на 09.10 по группе ТРПО23-3 (или может вообще по всем группам), возможно дело в дате, а может и в самих группах
        date = update.message.text
        user_data = context.user_data

        if date == "Сегодня":
            date_to_save = self.__get_date()
        elif date == "Завтра":
            date_to_save = self.__get_date(delta_days=1)
        elif date == "Послезавтра":
            date_to_save = self.__get_date(delta_days=2)
        else:
            date_to_save = self.__get_date(date=date)
        user_data["date"] = date_to_save
        return await self.show_schedule(update, context)

    async def show_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data = context.user_data
        group_id = user_data["group_id"]
        date = user_data["date"]
        schedule = self.ruz_fa_api.get_group_schedule_by_group_id(group_id, date)
        if schedule:
            await update.message.reply_text(schedule) # TODO: Разобраться с выводом расписания
        else:
            await update.message.reply_text(f"Расписание на эту дату не найдено")
        
        reply_keyboard = [["Показать расписание на другой день", "Вернуться к выбору группы"]]
        reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Что дальше?", reply_markup=reply_markup)
        return DATE
