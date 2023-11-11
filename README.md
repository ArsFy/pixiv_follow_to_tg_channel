# PFPTG

![](https://img.shields.io/badge/license-MIT-blue)
![](https://img.shields.io/badge/Python-3.X-blue)
![](https://img.shields.io/badge/PRs-welcome-green)

Make pixiv follow push to telegram channel

### Edit Config

Rename `config.example.json` to `config.json`

> To get refresh_token, see [@ZipFile Pixiv OAuth Flow](https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362)

```js
{
    "refresh_token": "",
    "mongo_uri": "mongodb+srv://user:pass@127.0.0.1",
    "database_name": "name",
    "bot_token": "",      // @BotFather
    "channel_id": -1,     // Push to telegram channel id
    "img_path": "./img",  // Image path
    "admin": [],          // Telegram admin user id
    "lang": "en"          // Pixiv Tag ID
}
```

### Run

```
pip install -r requirements.txt
python3 main.py
```