from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from tqdm import tqdm
from PIL import Image
from io import BytesIO
from pixivpy3 import *
import sys, os
import json
import mgd
import auth
import requests
import time
import asyncio
import threading
import logging

# Big Image
def compress_image(image_data, max_size_mb=5, max_resolution=4096):
    with Image.open(BytesIO(image_data)) as img:
        img_size_mb = len(image_data) / (1024 * 1024)
        if img_size_mb <= max_size_mb:
            return image_data

        img = img.convert("RGB")
        width, height = img.size

        if width > max_resolution or height > max_resolution:
            ratio = min(max_resolution / width, max_resolution / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            img = img.resize((new_width, new_height), Image.LANCZOS)

        output_buffer = BytesIO()
        img.save(output_buffer, format="WEBP", quality=85)

        compressed_data = output_buffer.getvalue()
        return compressed_data

# Config
try:
    configFile = open("./config.json", 'r', encoding="UTF-8").read()
    config = json.loads(configFile)
except:
    print("Error: Couldn't open config.")
    sys.exit(1)

def saveConfig():
    open("./config.json", 'w', encoding="UTF-8").write(json.dumps(config))

# Pixiv
api = AppPixivAPI()
api.auth(refresh_token=config["refresh_token"])
api.set_accept_language(config["lang"])

# MongoDB
db_client = mgd.MongoDB(config["mongo_uri"], config["database_name"])
db_client.connect()

# Save Image
def save_image(img: str, id: int, index: int):
    r = requests.get(img, headers={
        "Referer": "https://www.pixiv.net/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    })
    filepath = os.path.join(config['img_path'], f'{id}_{index}.{img.split("/")[-1].split(".")[-1]}')
    open(filepath, "wb").write(compress_image(r.content))

    return filepath

async def update_follow(bot, run):
    try:
        auth.refresh(config['refresh_token'])
        
        data = api.illust_follow()

        for i in tqdm(data["illusts"]):
            if len(db_client.read_data("illust", {"id": i.id})) == 0:
                taglist = []
                for tag in i.tags:
                    if tag.translated_name: tagname = tag.translated_name
                    else: tagname = tag.name
                    taglist.append(tagname.replace(" ", "\_").replace("R-18", "R18"))

                text = f'ID: [{i.id}](https://pixiv.net/i/{i.id})\nTitle: {i.title}\nUser: [{i.user.name}](https://pixiv.net/users/{i.user.id}) (#{i.user.name})\nTags: #{" #".join(taglist)}'

                if i.page_count == 1:
                    file = save_image(i.meta_single_page.original_image_url, i.id, 0)
                    try: await bot.send_photo(chat_id=config["channel_id"], photo=open(file, "rb").read(), parse_mode="Markdown", caption=text, connect_timeout=60000)
                    except Exception as e:
                        print(f"Error: {e}")
                else:
                    filelist = []
                    for j in range(0, len(i.meta_pages)):
                        filelist.append(save_image(i.meta_pages[j].image_urls.original, i.id, j))
                    try:  await bot.send_media_group(chat_id=config["channel_id"], media=[InputMediaPhoto(open(image, 'rb')) for image in filelist], connect_timeout=60000, read_timeout=60000, write_timeout=60000)
                    except Exception as e:
                        print(f"Error: {e}")
                    try: await bot.send_message(chat_id=config["channel_id"], text=text, parse_mode="Markdown", connect_timeout=60000)
                    except Exception as e:
                        print(f"Error: {e}")

                db_client.write_data("illust", {"id": i.id, "title": i.title, "user": i.user, "tags": taglist, "count": i.page_count})
            await asyncio.sleep(2)
    except Exception as e:
        await bot.send_message(chat_id=config["admin"][0], text="Error: update follow, {}".format(e))
        print(f"Error: {e}")

    await asyncio.sleep(1800)

    os.execl(sys.executable, sys.executable, *sys.argv)

async def up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in config["admin"]:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Create update task.")
        os.execl(sys.executable, sys.executable, *sys.argv)

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == config["admin"][0]:
        if update.message.reply_to_message and update.message.reply_to_message.from_user:
            if update.message.reply_to_message.from_user.id in config["admin"]:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Existing admin.")
            else:
                config["admin"].append(update.message.reply_to_message.from_user.id)
                saveConfig()
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Add Admin {update.message.reply_to_message.from_user.id}")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Must reply to a message.")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == config["admin"][0]:
        if update.message.reply_to_message and update.message.reply_to_message.from_user:
            if update.message.reply_to_message.from_user.id in config["admin"]:
                config["admin"] = list(filter(lambda x: x != update.message.reply_to_message.from_user.id, config["admin"]))
                saveConfig()
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Remove Admin {update.message.reply_to_message.from_user.id}")
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Non-existent admin.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Must reply to a message.")

async def add_follow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in config["admin"]:
        command = update.message.text.split(" ")
        if len(command) == 2:
            try:
                api.user_follow_add(int(command[1]))
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Add Follow: "+command[1])
            except:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="/add_follow <pixiv_user_id>")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="/add_follow <pixiv_user_id>")

async def delete_follow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in config["admin"]:
        command = update.message.text.split(" ")
        if len(command) == 2:
            try:
                api.user_follow_delete(int(command[1]))
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Delete Follow: "+command[1])
            except:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="/delete_follow <pixiv_user_id>")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="/delete_follow <pixiv_user_id>")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="/up - Create update task\n/add_admin - Add a admin (Reply message)\n/remove_admin - Remove a admin (Reply message)\n/add_follow <pixiv_user_id> - Add follow\n/delete_follow <pixiv_user_id> - Delete follow")

if __name__ == '__main__':
    def update_follow_threading(bot, run):
        asyncio.run(update_follow(bot, run))

    application = ApplicationBuilder().token(config['bot_token']).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('up', up))
    application.add_handler(CommandHandler('add_admin', add_admin))
    application.add_handler(CommandHandler('remove_admin', remove_admin))
    application.add_handler(CommandHandler('add_follow', add_follow))
    application.add_handler(CommandHandler('delete_follow', delete_follow))

    # Start threads as daemon threads
    threading.Thread(target=update_follow_threading, args=(application.bot, True,), daemon=True).start()

    print("Starting bot...")
    application.run_polling()