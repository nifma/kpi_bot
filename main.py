import asyncio
import mysql.connector
import logging
import threading
import socketio
import time
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from config import *
from get_data import *

logging.basicConfig(level=logging.INFO)

con = mysql.connector.connect(**db_connection_config)
cursor = con.cursor(dictionary=True)

session = AiohttpSession(proxy=SOCKS5_PROXY) if SOCKS5_PROXY else AiohttpSession()
bot = Bot(
    token=BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    session=session
)
dp = Dispatcher(storage=MemoryStorage())

event_loop = None 

sio = socketio.Client(logger=True, engineio_logger=True)

@sio.on("*")
def my_message(event, data):
    cursor.execute("SELECT * FROM subscriptions WHERE team_id=%s", (data["team_id"],))
    subs = cursor.fetchall()

    if subs != []:
        team = subs[-1]["team"]
        league = get_league(data["league_id"])['name']

        if data["type"] == "kvartaly_add_answer":
            text = f"Кварталы. Задача №{data['question_num']}. {team}. {league}\n\n"

            if data['delta_correct'] > 0:
                text += "Получен верный ответ\n"
            elif data['delta_incorrect'] > 0:
                text += "Получен неверный ответ\n"
            elif data['delta_correct'] < 0:
                text += "Убран верный ответ\n"
            elif data['delta_incorrect'] < 0:
                text += "Убран неверный ответ\n"

            text += f"Балл за задачу: {data['score']}\n\nСчет: {data['total']}"

        elif data["type"] == "kvartaly_finish":
            if data["finished"]: 
                text = f"Квартал №{data['kvartal']} завершен. {team}. {league}\n\nСчет: {data['total']}"
            else:
                text = f"Квартал №{data['kvartal']} снова открыт. {team}. {league}\n\nСчет: {data['total']}"

        elif data["type"] == "kvartaly_set_penalty":
            text = f"Кварталы. Пенальти. {team}. {league}\n\nПенальти: {data['penalty']}\n\nСчет: {data['total']}"

        elif data["type"] == "fudzi_set_answer":
            text = f"Фудзи. Задача №{data['question_num']}. {team}. {league}\n\n"

            if data["status"] == "correct":
                text += "Получен верный ответ\n"
            elif data["status"] == "incorrect":
                text += "Получен неверный ответ\n"
            else:
                text += "Ответ за задачу был сброшен\n"
            
            text += f"Балл за задачу: {data['score']}\n\nСчет: {data['total']}"
        
        elif data["type"] == "fudzi_set_penalty":
            text = f"Фудзи. Пенальти. {team}. {league}\n\nПенальти: {data['penalty']}\n\nСчет: {data['total']}"


        for sub in subs:
            asyncio.run_coroutine_threadsafe(
                bot.send_message(sub["user_id"], text),
                event_loop
            )
            time.sleep(.05)

def run_socketio():
    sio.connect(SOCKET_IO_URL, transports=["websocket", "polling"])
    sio.wait()
    
@dp.callback_query(lambda c: c.data == "start")
async def procces_start(callback, state):
    await(start(callback.message, state))


@dp.callback_query(lambda c: c.data.startswith("events:"))
async def process_events(callback):
    message = callback.message
    data = callback.data

    shift = int(data.split(":")[1])
    cnt = 5
    all_events = get_events()
    events = all_events[shift:shift+cnt]

    keyboard = []
    for event in events:
        keyboard.append([
            InlineKeyboardButton(text=event['name'], callback_data=f"event:{event['id']}")
        ])

    pagination_row = []

    if shift > 0:
        pagination_row.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"events:{shift-cnt}")
        )

    if shift+cnt < len(all_events):
        pagination_row.append(
            InlineKeyboardButton(text="➡️", callback_data=f"events:{shift+cnt}")
        )

    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([
        InlineKeyboardButton(text="🏠 На главную", callback_data="start")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)

    if all_events != []:
        await message.edit_text("Выберите мероприятие, в котором участвует команда", reply_markup=keyboard)
    else:
        await message.edit_text("Мероприятий нет", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("event:"))
async def process_event(callback, state):
    message = callback.message
    data = callback.data

    event_id = int(data.split(":")[1])
    await state.update_data(event_id=event_id)

    callback = CallbackQuery(
        id=callback.id,
        from_user=callback.from_user,
        chat_instance=callback.chat_instance,
        data="locations:0",
        message=message
    )
    await process_locations(callback, state)


@dp.callback_query(lambda c: c.data.startswith("locations:"))
async def process_locations(callback, state):
    message = callback.message
    data = callback.data
    state_data = await state.get_data()

    shift = int(data.split(":")[1])
    cnt = 5
    all_locations = get_locations(state_data.get("event_id"))
    locations = all_locations[shift:shift+cnt]

    keyboard = []
    for location in locations:
        keyboard.append([
            InlineKeyboardButton(text=location['name'], callback_data=f"location:{location['id']}")
        ])

    pagination_row = []

    if shift > 0:
        pagination_row.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"locations:{shift-cnt}")
        )

    if shift+cnt < len(all_locations):
        pagination_row.append(
            InlineKeyboardButton(text="➡️", callback_data=f"locations:{shift+cnt}")
        )

    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="events:0")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)

    if all_locations != []: 
        await message.edit_text("Выберите место проведения мероприятия", reply_markup=keyboard)
    else:
        await message.edit_text("Место мероприятия еще не определено", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("location:"))
async def process_location(callback, state):
    message = callback.message
    data = callback.data

    location_id = int(data.split(":")[1])
    await state.update_data(location_id=location_id)

    callback = CallbackQuery(
        id=callback.id,
        from_user=callback.from_user,
        chat_instance=callback.chat_instance,
        data="leagues:0",
        message=message
    )
    await process_leagues(callback, state)


@dp.callback_query(lambda c: c.data.startswith("leagues:"))
async def process_leagues(callback, state):
    message = callback.message
    data = callback.data
    state_data = await state.get_data()

    shift = int(data.split(":")[1])
    cnt = 5
    all_leagues = get_leagues(state_data.get("location_id"))
    leagues = all_leagues[shift:shift+cnt]

    keyboard = []
    for league in leagues:
        keyboard.append([
            InlineKeyboardButton(text=league['name'], callback_data=f"league:{league['id']}")
        ])

    pagination_row = []

    if shift > 0:
        pagination_row.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"leagues:{shift-cnt}")
        )

    if shift+cnt < len(all_leagues):
        pagination_row.append(
            InlineKeyboardButton(text="➡️", callback_data=f"leagues:{shift+cnt}")
        )

    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="locations:0")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)

    if all_leagues != []: 
        await message.edit_text("Выберите лигу", reply_markup=keyboard)
    else:
        await message.edit_text("Лиг еще не определены", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("league:"))
async def process_league(callback, state):
    message = callback.message
    data = callback.data

    league_id = int(data.split(":")[1])
    await state.update_data(league_id=league_id)

    callback = CallbackQuery(
        id=callback.id,
        from_user=callback.from_user,
        chat_instance=callback.chat_instance,
        data="teams:0",
        message=message
    )
    await process_teams(callback, state)


@dp.callback_query(lambda c: c.data.startswith("teams:"))
async def process_teams(callback, state):
    message = callback.message
    data = callback.data
    user_id = message.chat.id
    state_data = await state.get_data()

    shift = int(data.split(":")[1])
    cnt = 5
    all_teams = get_teams(state_data.get("league_id"))
    all_teams = [team for team in all_teams if (team["status"] == "ACCEPTED") or (team["status"] == "ARRIVED")]
    teams = all_teams[shift:shift+cnt]

    cursor.execute("SELECT team_id FROM subscriptions WHERE user_id=%s", (user_id,))
    subs = cursor.fetchall()

    keyboard = []
    for team in teams:
        print(subs, {"team_id": team['id']}, {"team_id": team['id']} in subs)
        if {"team_id": team['id']} in subs:
            keyboard.append([
                InlineKeyboardButton(text=team['name'], callback_data=f"team:{team['id']}", style="success")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(text=team['name'], callback_data=f"team:{team['id']}")
            ])

    keyboard.append([
        InlineKeyboardButton(text="⬅️", callback_data=f"teams:{max(shift-cnt, 0)}"),
        InlineKeyboardButton(text=f"{shift//cnt+1}/{(len(all_teams)+cnt-1)//cnt}", callback_data=f"pages"),
        InlineKeyboardButton(text="➡️", callback_data=f"teams:{min(shift+cnt, (len(all_teams)+cnt-1)//cnt*cnt-cnt)}")
    ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="leagues:0")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)

    if all_teams != []: 
        await message.edit_text("Выберите команду, на которую хотите подписаться", reply_markup=keyboard)
    else:
        await message.edit_text("Команд еще не добавлены", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("team:"))
async def process_team(callback, state):
    message = callback.message
    data = callback.data
    state_data = await state.get_data()
    user_id = message.chat.id

    event_id = state_data.get("event_id")
    event = get_event(event_id)['name']

    location_id = state_data.get("location_id")
    location = get_location(location_id)['name']

    team_id = int(data.split(":")[1])
    team = get_team(team_id)

    league_id = state_data.get("league_id")
    league = team["league_name"]

    team = team["name"]
    
    
    cursor.execute("SELECT * FROM subscriptions WHERE user_id=%s AND team_id=%s", (user_id, team_id,))
    result = cursor.fetchone() 

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 На главную", callback_data="start")
        ]
    ])
    if result is None:
        cursor.execute("INSERT INTO subscriptions (user_id, event_id, event, location_id, location, league_id, league, team_id, team) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (user_id, event_id, event, location_id, location, league_id, league, team_id, team,))
        con.commit()

        await message.edit_text(text=f"Вы подписались на <b>{team}, {league}, {location}, {event}</b>", reply_markup=keyboard)
    else:
        await message.edit_text(text=f"Вы уже подписаны", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("subscriptions:"))
async def process_subscriptions(callback):
    message = callback.message
    data = callback.data
    user_id = message.chat.id

    shift = int(data.split(":")[1])
    cnt = 5
    
    cursor.execute("SELECT * FROM subscriptions WHERE user_id=%s", (user_id,))
    all_subs = cursor.fetchall()[::-1]
    subs = all_subs[shift:shift+cnt]

    keyboard = []
    for sub in subs:
        keyboard.append([
            InlineKeyboardButton(text=f"{sub['team']} • {sub['league']} • {sub['location']} • {sub['event']}", callback_data=f"subscribe:{sub['id']}")
        ])

    pagination_row = []

    if shift > 0:
        pagination_row.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"subscriptions:{shift-cnt}")
        )

    if shift+cnt < len(all_subs):
        pagination_row.append(
            InlineKeyboardButton(text="➡️", callback_data=f"subscriptions:{shift+cnt}")
        )

    if pagination_row:
        keyboard.append(pagination_row)


    if all_subs == []:
        keyboard.append([
            InlineKeyboardButton(text="➕ Подписаться на команду", callback_data="events:0")
        ])

    keyboard.append([
        InlineKeyboardButton(text="🏠 На главную", callback_data="start")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)

    if all_subs != []:
        await message.edit_text("Команды, на которые Вы подписаны", reply_markup=keyboard)
    else:
        await message.edit_text("У Вас нет подписок :(", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("subscribe:"))
async def process_subscribe(callback):
    message = callback.message
    data = callback.data
    
    sub_id = int(data.split(":")[1])

    cursor.execute("SELECT * FROM subscriptions WHERE id=%s", (sub_id,))
    sub = cursor.fetchone()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❌ Отписаться", callback_data=f"unsubscribe:{sub['id']}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="subscriptions:0")
        ]
    ])
    await message.edit_text(f"<b>{sub['team']} • {sub['league']}</b>\n\n<b>Мероприятие:</b> {sub['event']}\n<b>Место проведения:</b> {sub['location']}\n<b>Лига:</b> {sub['league']}\n<b>Команда:</b> {sub['team']}", reply_markup=keyboard)
    

@dp.callback_query(lambda c: c.data.startswith("unsubscribe:"))
async def process_unsubscribe(callback):
    message = callback.message
    data = callback.data
    
    sub_id = int(data.split(":")[1])

    cursor.execute("SELECT * FROM subscriptions WHERE id=%s", (sub_id,))
    sub = cursor.fetchone()

    cursor.execute("DELETE FROM subscriptions WHERE id=%s", (sub_id,))
    con.commit()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="subscriptions:0")
        ]
    ])
    await message.edit_text(f"Вы отписались от <b>{sub['team']}, {sub['league']}, {sub['location']}, {sub['event']}</b>", reply_markup=keyboard)
  

@dp.message(Command("start"))
async def start(message, state):
    await state.clear()

    user_id = message.chat.id

    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone() 

    if result is None:
        cursor.execute("INSERT INTO users (user_id) VALUES (%s)", (user_id,))
        con.commit()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔔 Мои подписки", callback_data="subscriptions:0")
        ],
        [
            InlineKeyboardButton(text="➕ Подписаться на команду", callback_data="events:0")
        ]
    ])
    await message.answer("Приветствуем Вас в боте <tg-emoji emoji-id='5370740459142409053'>👋</tg-emoji> Турнира математических игр kπца\n\nТут Вы можете подписаться на свою любимую команду и получать уведомления о ее результатах на играх", reply_markup=keyboard)


async def main():
    global event_loop 
    event_loop = asyncio.get_running_loop()

    thread = threading.Thread(target=run_socketio, daemon=True)
    thread.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
    finally:
        sio.disconnect()
        con.close()