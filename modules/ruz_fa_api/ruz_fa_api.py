from datetime import datetime
import requests


class RuzFaAPI:
    HOST = "https://ruz.fa.ru/"

    def __current_date(self) -> str:
        return datetime.now().strftime("%Y.%m.%d")

    def __request(self, sub_url: str) -> requests.Response:
        response = requests.get(self.HOST + sub_url)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Error, RUZ answered with code: {response.status_code}")

    def __find_group_in_response(self, group_name: str, response: requests.Response) -> dict:
        for group in response:
            if group["label"] == group_name:
                return group
        return None

    def get_group_by_name(self, group_name: str) -> dict:
        group_name = group_name.upper()
        response = self.__request(f"api/search?term={group_name}&type=group")
        group_info = self.__find_group_in_response(group_name, response)
        if group_info:
            return group_info
        else:
            return None

    def get_group_schedule_by_group_id(self, group_id: str, start_date: str, end_date: str = None) -> dict:
        if end_date is None:
            end_date = start_date
        response = self.__request(f"api/schedule/group/{group_id}?start={start_date}&finish={end_date}&lng=1")
        if response:
            schedule = []
            for lesson in response:
                lesson_dct = {}
                lesson_dct["auditorium"] = lesson["auditorium"].encode().decode()
                lesson_dct["beginLesson"] = lesson["beginLesson"]
                lesson_dct["endLesson"] = lesson["endLesson"]
                lesson_dct["discipline"] = lesson["discipline"].encode().decode()
                lesson_dct["kindOfWork"] = lesson["kindOfWork"].encode().decode()
                lesson_dct["lecturer"] = lesson["lecturer"].encode().decode()
                schedule.append(lesson_dct)

            return schedule # FIXME: Что-то не так с данными response, куча буков и цифор
        else:
            return None
