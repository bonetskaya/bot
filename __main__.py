import config
from copy import deepcopy
from random import shuffle
import telebot

NOTHING = 0
SEND_POEMS = 1
MAY_START_VOTING = 2
VOTING = 3


class GameLogicError(RuntimeError):
    pass


class Game:
    def __init__(self):
        self._players = {}
        self._admin = None
        self._status = NOTHING
        self._start_poem = None
        self._right_answer = None
        self._custom_answers = {}
        self._shuffled_answers = None
        self._right_score = {}
        self._sympathy_score = {}
        self._voted = set()

    def add_player(self, username: str, chat_id: int):
        if self._status == NOTHING:
            self._players[username] = chat_id
        else:
            raise GameLogicError("Дождись конца текущей игры!")

    def is_player(self, username):
        return username in self._players

    def remove_player(self, username):
        if username == self._admin:
            GameLogicError("Сначала перестань быть админом!")
        if self._status == NOTHING:
            if username in self._players:
                self._players.pop(username)
        else:
            raise GameLogicError("Дождись конца текущей игры!")

    def set_admin(self, username):
        if self._admin is None:
            self._admin = username
        else:
            raise GameLogicError(f"Админ уже есть, это {self._admin}")

    def is_admin(self, username):
        return self._admin == username

    def get_admin(self):
        return self._admin

    def get_admin_chat(self):
        return self._players[self._admin]

    def remove_admin(self):
        if self._status == NOTHING:
            self._admin = None
        elif self._status == VOTING:
            if len(self._voted) + 1 == len(self._players):
                self._admin = None
                self._status = NOTHING
                self._start_poem = None
                self._right_answer = None
                self._custom_answers = {}
                self._shuffled_answers = None
                self._voted = set()
                print(sorted(self._right_score.items(), key=lambda x: x[1]))
                print(sorted(self._sympathy_score.items(), key=lambda x: x[1]))
                print("____________________________________________")
            else:
                raise GameLogicError("Не все ещё проголосовали!")
        else:
            raise GameLogicError("Дождись конца текущей игры!")

    def reset_game(self):
        if self._voted:
            raise GameLogicError("Придётся доиграть игру.")
        self._status = NOTHING
        self._start_poem = None
        self._right_answer = None
        self._custom_answers = {}
        self._shuffled_answers = None

    def get_status(self):
        return self._status

    def get_players_without_admin(self):
        players_without_admin = deepcopy(self._players)
        if self._admin is not None:
            players_without_admin.pop(self._admin)
            return players_without_admin
        return players_without_admin

    def set_start_poem(self, text: str):
        self._status = SEND_POEMS
        self._start_poem = text.strip().lower()

    def set_right_answer(self, text: str):
        self._right_answer = text.strip().lower()

    def add_answer(self, username: str, text: str):
        self._custom_answers[username] = text.strip().lower()
        return len(self._custom_answers) + 1 == len(self._players)

    def get_answers(self):
        if self._status == NOTHING:
            raise GameLogicError("Игра не началась.")
        if self._start_poem is None:
            raise GameLogicError("Пока админ не отправил правильный ответ...")
        if len(self._custom_answers) + 1 != len(self._players):
            raise GameLogicError("Не все отправили свои ответы!")
        if self._shuffled_answers is None:
            self._shuffled_answers = [(user, "\n".join((self._start_poem, answer))) for user, answer in self._custom_answers.items()]
            print(self._shuffled_answers)
            self._shuffled_answers.append((None, "\n".join((self._start_poem, self._right_answer))))
            shuffle(self._shuffled_answers)
            if self._status == SEND_POEMS:
                self._status = MAY_START_VOTING
        return self._shuffled_answers

    def start_voting(self):
        if self._status == VOTING:
            raise GameLogicError("Голосование уже идёт")
        if self._status != MAY_START_VOTING:
            raise GameLogicError("Сейчас нельзя начать голосование.")
        if len(self._custom_answers) + 1 != len(self._players):
            raise GameLogicError("Пока не все отправили ответы.")
        self._status = VOTING

    def get_result(self):
        return f"Результат по правильным ответам:\n{sorted(self._right_score.items(), key=lambda x: x[1])}\n" \
               f"По симпатиям:\n{sorted(self._sympathy_score.items(), key=lambda x: x[1])}"

    def vote(self, username, right_number: int, sympathy_number: int):
        if self._status != VOTING:
            print(self._status)
            raise GameLogicError("Сейчас не фаза голосования.")
        if self._admin == username:
            raise GameLogicError("Админ не может голосовать.")
        if not (0 < right_number <= len(self._shuffled_answers) and 0 < sympathy_number <= len(self._shuffled_answers)):
            raise GameLogicError("Неправильный формат ввода.")
        if username in self._voted:
            raise GameLogicError("Ты уже голосовал(а)")
        right_number -= 1
        sympathy_number -= 1
        if self._shuffled_answers[sympathy_number][0] == username:
            raise GameLogicError("За себя голосовать нехорошо! -_-")
        self._right_score[username] = self._right_score.get(username, 0) + int(self._shuffled_answers[right_number][0] is None)
        sympathy_username = self._shuffled_answers[sympathy_number][0]
        self._sympathy_score[sympathy_username] = self._sympathy_score.get(sympathy_username, 0) + 1
        self._voted.add(username)
        self._sympathy_score[username] = self._sympathy_score.get(username, 0)
        return len(self._voted) + 1 == len(self._players)


bot = telebot.TeleBot(config.token)
game = Game()


def check(message):
    if not game.is_player(message.from_user.username):
        bot.send_message(message.chat.id, "Ты не участвуешь в игре. Чтобы участвовать в игре, отправь сообщение с командой /participate")
    return game.is_player(message.from_user.username)


def check_admin(message):
    if not game.is_admin(message.from_user.username):
        bot.send_message(message.chat.id, "Ты не админ")
    return game.is_admin(message.from_user.username)


@bot.message_handler(commands=["start"])
def start_message(message):
    bot.send_message(message.chat.id, """Добро пожаловать в завалинку!
Чтобы участвовать в игре, отправь сообщение с командой /participate
""")


@bot.message_handler(commands=["participate"])
def participate(message):
    try:
        game.add_player(message.from_user.username, message.chat.id)
        bot.send_message(message.chat.id, "Ура, ты участвуешь в игре! Можешь попробовать стать админом, отправив сообщение /admin")
    except GameLogicError as e:
        bot.send_message(message.chat.id, str(e))



@bot.message_handler(commands=["exit"])
def exit(message):
    try:
        game.remove_player(message.from_user.username)
        bot.send_message(message.chat.id, "Прощай.")
    except GameLogicError as e:
        bot.send_message(message.chat.id, str(e))


@bot.message_handler(commands=["admin"])
def admin(message):
    if not check(message):
        return
    try:
        game.set_admin(message.from_user.username)
        bot.send_message(message.chat.id, """Теперь ты админ 😎
Отправь две строчки стихотворения следующим сообщением или набери команду /not_admin, если ты больше не хочешь быть админом.
Осторожно! Следующее сообщение отправится всем участникам игры. Если что-то пойдёт не так, можно использовать команду /restart_session
""")
    except GameLogicError as e:
        bot.send_message(message.chat.id, str(e))


@bot.message_handler(commands=["not_admin"])
def not_admin(message):
    if not check_admin(message):
        return
    try:
        game.remove_admin()
        bot.send_message(message.chat.id, "Теперь ты не админ")
    except GameLogicError as e:
        bot.send_message(message.chat.id, str(e))


@bot.message_handler(commands=["restart_session"])
def restart_session(message):
    if not check_admin(message):
        return
    try:
        game.reset_game()
        bot.send_message(message.chat.id, "Ты перезапустил(а) игру. Введи первые две строчки стихотворения или введи /not_admin")
    except GameLogicError as e:
        bot.send_message(message.chat.id, str(e))


@bot.message_handler(commands=["admin_eto_who"])
def admin_eto_who(message):
    if not check(message):
        return
    if game.get_admin() is None:
        bot.send_message(message.chat.id, "А админа нет! Хочешь им стать? Нужно всего лишь написать /admin")
    else:
        bot.send_message(message.chat.id, f"Сейчас админ {message.from_user.username}.")


def get_answers():
    try:
        answers = game.get_answers()
        admin_message = "Вот, что прислали участники. Чтобы отправить стихотворения участникам и начать голосование, отправь сообщение с командой /start_voting\n\n"
        for answer in answers:
            username = answer[0] if answer[0] is not None else "Правильный ответ"
            admin_message += f"(({username}))\n{answer[1]}\n\n"
        bot.send_message(game.get_admin_chat(), admin_message)
    except GameLogicError as e:
        bot.send_message(game.get_admin_chat(), str(e))


@bot.message_handler(commands=["start_voting"])
def start_voting(message):
    if not check_admin(message):
        return
    try:
        game.start_voting()
        answers = game.get_answers()
        others_message = "Теперь ты можешь голосовать! Отправь сообщение с двумя числами: правильный по твоему мнению ответ и самое понравившееся продолжение.\n\n"
        for i, answer in enumerate(answers):
            others_message += f"{i + 1}) \n{answer[1]}\n\n"
        for chat_id in game.get_players_without_admin().values():
            bot.send_message(chat_id, others_message)
        bot.send_message(message.chat.id, "Все получили ответы и могут голосовать! Когда все проголосуют, получишь результат :)")
    except GameLogicError as e:
        bot.send_message(message.chat.id, str(e))


@bot.message_handler(content_types=["text"])
def poems(message):
    if not check(message):
        return
    if game.is_admin(message.from_user.username):
        if game.get_status() == NOTHING:
            try:
                game.set_start_poem(message.text)
                for chat_id in game.get_players_without_admin().values():
                    bot.send_message(chat_id, "Тебе надо продолжить это стихотворение. Следующим сообщением отправь продолжение.\n\n" + message.text)
                bot.send_message(message.chat.id, "Игроки получили твоё сообщение и уже придумывают ответы. Теперь напиши правильное продолжение!")
            except GameLogicError as e:
                bot.send_message(message.chat.id, str(e))
        elif game.get_status() == SEND_POEMS:
            try:
                game.set_right_answer(message.text)
                bot.send_message(message.chat.id, "Правильный ответ принят. Ждём, когда игроки придумают ответы!")
            except GameLogicError as e:
                bot.send_message(message.chat.id, str(e))
        else:
            bot.send_message(message.chat.id, "Сейчас нельзя присылать стихотворения.")
    else:
        if game.get_status() == SEND_POEMS:
            try:
                if game.add_answer(message.from_user.username, message.text):
                    get_answers()
                bot.send_message(message.chat.id, "Твой ответ принят!")
                return
            except GameLogicError as e:
                bot.send_message(message.chat.id, str(e))
        if game.get_status() == VOTING:
            try:
                right, sympathy = message.text.split()
                right_num, sympathy_num = int(right), int(sympathy)
            except:
                bot.send_message(message.chat.id, "Неправильный формат ввода. Введи два числа через пробел.")
                return
            try:
                if game.vote(message.from_user.username, right_num, sympathy_num):
                    bot.send_message(game.get_admin_chat(), game.get_result())
                    game.remove_admin()
                bot.send_message(message.chat.id, "Твой голос принят!")
            except GameLogicError as e:
                bot.send_message(message.chat.id, str(e))
        else:
            bot.send_message(message.chat.id, "Сейчас нельзя присылать стихотворения.")


if __name__ == '__main__':
    bot.infinity_polling()
