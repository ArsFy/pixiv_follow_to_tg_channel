from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from pixivpy3 import *
import sys, os
import json
import mgd
import requests
import time
import asyncio

try:
    configFile = open("./config.json", 'r', encoding="UTF-8").read()
    config = json.loads(configFile)
except:
    print("Error: Couldn't open config.")
    sys.exit(1)

# Pixiv
api = AppPixivAPI()
api.auth(refresh_token=config["refresh_token"])
api.set_accept_language("zh-TW")

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
    open(filepath, "wb").write(r.content)

    return filepath


async def update_follow(bot):
    while True:
        data = api.illust_follow()

        for i in data["illusts"]:
            if len(db_client.read_data("illust", {"id": i.id})) == 0:

                taglist = []
                for tag in i.tags:
                    if tag.translated_name:
                        taglist.append(tag.translated_name.replace(" ", "_"))
                    else:
                        taglist.append(tag.name.replace(" ", "_"))

                if i.page_count == 1:
                    file = save_image(i.meta_single_page.original_image_url, i.id, 0)
                    try: await bot.send_photo(chat_id=config["channel_id"], photo=open(file, "rb").read(), parse_mode="Markdown", caption=f'ID: [{i.id}](https://pixiv.net/i/{i.id})\nTitle: {i.title}\nUser: [{i.user.name}](https://pixiv.net/users/{i.user.id})\nTags: #{" #".join(taglist)}')
                    except: pass
                else:
                    filelist = []
                    for j in range(0, len(i.meta_pages)):
                        filelist.append(save_image(i.meta_pages[j].image_urls.original, i.id, j))

                    try: await bot.send_media_group(chat_id=config["channel_id"], media=[InputMediaPhoto(open(image, 'rb')) for image in filelist])
                    except: pass
                    try: await bot.send_message(chat_id=config["channel_id"], text=f'ID: [{i.id}](https://pixiv.net/i/{i.id})\nTitle: {i.title}\nUser: [{i.user.name}](https://pixiv.net/users/{i.user.id})\nTags: #{" #".join(taglist)}', parse_mode="Markdown")
                    except: pass

                db_client.write_data("illust", {"id": i.id, "title": i.title, "user": i.user, "tags": taglist, "count": i.page_count})

                time.sleep(2)

        time.sleep(1800)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=config["channel_id"], text="Test")

if __name__ == '__main__':
    application = ApplicationBuilder().token(config['bot_token']).build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    asyncio.run(update_follow(application.bot))

    application.run_polling()