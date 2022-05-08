import logging
import hashlib
import time
import db
import yamusic
import os
import requests
import config

from aiogram import Bot, Dispatcher, executor
from aiogram.types import InlineQuery,Message, ChosenInlineResult, InlineQueryResultAudio
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import InputMediaAudio, InputFile

TOKEN = config.TG_TOKEN
PLACEHOLDER_ID = "CQACAgIAAxkDAAMoYnZzJ7PczmtOm4SDgKk2t_eX2fcAAm4YAALgD7FLuEdigBDY9wMkBA"

if not os.path.exists("temp"):
    os.mkdir("temp")

logging.basicConfig(level=logging.DEBUG)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

result_ids = {} # Хеш массив Result_ID => Track_Id

# для тестов
@dp.message_handler(commands="upload_placeholder")
async def upload_placeholder(message: Message):
    with open('tagmp3_crank-2.mp3', 'rb') as audio:

        result = await message.reply_audio(audio)
        await message.reply(result.audio.file_id)


@dp.inline_handler()
async def inline_search_audio(inline_query: InlineQuery):
    items = []

    query = inline_query.query or "Виктор Цой" # если юзер ничего не ввел то цой

    result = yamusic.search(query=query)
    if len(result): # если результат не пустой
        for track in result:
            markup = InlineKeyboardMarkup(row_width=1) # обязательно нужна кнопка без нее редачить нельзя будет
            markup.add(InlineKeyboardButton("Загружаем...", callback_data=track['id']))

            result_id: str = hashlib.md5(str(track['id']).encode()).hexdigest()

            result_ids[result_id] = track['id'] # временно сохраняем ресалт айди чтобы потом знать что редачить

            item = InlineQueryResultAudio(
                id=result_id,
                audio_url="https://cs12.spac.me/f/022155028048118178004245225041194015065048227225162088184137/1651935767/90406904/0/912c9cca2ba0f5da4d0df7cb4f7483ea/placeholder-spcs.me.mp3#asdasd",
                title=f"{track['caption']}",
                performer=f"{track['artist']}",
                reply_markup=markup
            )
            items.append(item)

    await bot.answer_inline_query(inline_query.id, results=items, cache_time=5)


@dp.chosen_inline_handler(lambda chosen_inline_result: True) #срабатывает когла юзер выбрал что-то
async def chosen_track(chosen_inline_result: ChosenInlineResult):
    result_id = chosen_inline_result.result_id

    if result_id in result_ids: # проверяем что ресалт айди ранее был сохранен (оттуда надо взять id трека в я музыке)
        track_id = result_ids[result_id] 
        data = db.get(track_id) # Пытаемся достать из базы
        if not data: # если нету то загружаем в группу и получаем ид трека
            data = yamusic.get_track_data(track_id)
            
            with open(f"temp/{track_id}.mp3", 'wb') as f:
                r = requests.get(data['link']).content
                f.write(r)


            result = await bot.send_audio("-662250152", audio=InputFile(f"temp/{track_id}.mp3"), title=data['title'], performer=data['artists'], thumb=data['cover_url'])

            tg_file_id = result.audio.file_id
            db.save(track_id, tg_file_id)

            os.remove(f"temp/{track_id}.mp3")
            await bot.edit_message_media(
                media=InputMediaAudio(tg_file_id, title=data['title'], performer=data['artists'], thumb=data['cover_url']), inline_message_id=chosen_inline_result.inline_message_id
            )
        else: # если есть то берем ид трека из базы
            tg_file_id = data.tg_file_id

            await bot.edit_message_media(
                media=InputMediaAudio(tg_file_id), inline_message_id=chosen_inline_result.inline_message_id
            )

    else: # если нет то ну его нафиг кидаем хрень какую-то
        await bot.edit_message_media(media=InputMediaAudio("https://s114iva.storage.yandex.net/get-mp3/b828b82ff580f393c9fc191803d36da3/0005de6e687b0781/rmusic/U2FsdGVkX18fPBQBJahpAV02vIBhod8AFr1b_YNnKueVOq5KWRMv-iyXzwf3kP5svIpv25TMNMX87eR4HarJUyQxbnf6LAaMqrKF5FFbz2I/69181938730959e89f22c42c309531ee66afc2d099613ee92ecb43cd099672aa/38927"), inline_message_id=chosen_inline_result.inline_message_id)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)