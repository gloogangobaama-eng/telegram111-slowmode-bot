{\rtf1\ansi\ansicpg1251\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import os\
import json\
import asyncio\
import logging\
from datetime import datetime, timedelta, timezone\
\
from flask import Flask, request\
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup\
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters\
\
logging.basicConfig(\
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",\
    level=logging.INFO\
)\
logger = logging.getLogger(__name__)\
\
BOT_TOKEN = os.getenv("BOT_TOKEN")\
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))\
BASE_URL = os.getenv("BASE_URL")\
PORT = int(os.getenv("PORT", "8080"))\
\
if not BOT_TOKEN:\
    raise RuntimeError("\uc0\u1053 \u1077 \u1090  BOT_TOKEN")\
if not ADMIN_ID:\
    raise RuntimeError("\uc0\u1053 \u1077 \u1090  ADMIN_ID")\
if not BASE_URL:\
    raise RuntimeError("\uc0\u1053 \u1077 \u1090  BASE_URL")\
\
CONFIG_FILE = "config.json"\
MOSCOW_OFFSET = timedelta(hours=3)\
\
def load_config():\
    if os.path.exists(CONFIG_FILE):\
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:\
            config = json.load(f)\
    else:\
        config = \{\}\
\
    config.setdefault("enabled", True)\
    config.setdefault("topics", \{\})\
    config.setdefault("whitelist", [])\
    config.setdefault("autodelete_seconds", 180)\
    config.setdefault("warning", \{\
        "text": "\uc0\u1042 \u1099  \u1091 \u1078 \u1077  \u1086 \u1090 \u1087 \u1088 \u1072 \u1074 \u1083 \u1103 \u1083 \u1080  \u1089 \u1086 \u1086 \u1073 \u1097 \u1077 \u1085 \u1080 \u1077  \u1074  \{next_time_old\}, \u1087 \u1086 \u1078 \u1072 \u1083 \u1091 \u1081 \u1089 \u1090 \u1072 , \u1087 \u1086 \u1076 \u1086 \u1078 \u1076 \u1080 \u1090 \u1077  \{delay_hours\} \u1095 \u1072 \u1089 \u1072 (\u1086 \u1074 ), \u1089 \u1083 \u1077 \u1076 \u1091 \u1102 \u1097 \u1077 \u1077  \u1089 \u1086 \u1086 \u1073 \u1097 \u1077 \u1085 \u1080 \u1077  \u1076 \u1086 \u1089 \u1090 \u1091 \u1087 \u1085 \u1086  \u1074  \{next_time\}.",\
        "buttons": [\{"text": "\uc0\u55357 \u56546  \u1056 \u1077 \u1082 \u1083 \u1072 \u1084 \u1072 ", "url": "https://t.me/reklama_opt_chat"\}]\
    \})\
    return config\
\
def save_config(config):\
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:\
        json.dump(config, f, indent=2, ensure_ascii=False)\
\
config = load_config()\
last_message_time = \{\}\
media_group_processed = set()\
media_group_to_delete = set()\
\
def is_admin(user_id):\
    return user_id == ADMIN_ID\
\
def is_whitelisted(user):\
    uid = str(user.id)\
    uname = f"@\{user.username\}" if user.username else None\
    for item in config["whitelist"]:\
        if item == uid or (uname and item == uname):\
            return True\
    return False\
\
def get_thread_key(message):\
    return "main" if message.message_thread_id is None else str(message.message_thread_id)\
\
def format_warning_text(username, delay_hours, old_time, next_time):\
    text = config["warning"]["text"]\
    text = text.replace("\{username\}", username)\
    text = text.replace("\{delay_hours\}", str(delay_hours))\
    text = text.replace("\{next_time_old\}", old_time)\
    text = text.replace("\{next_time\}", next_time)\
    return text\
\
def get_keyboard():\
    buttons = config["warning"].get("buttons", [])\
    if not buttons:\
        return None\
    keyboard = []\
    for btn in buttons:\
        keyboard.append([InlineKeyboardButton(btn["text"], url=btn["url"])])\
    return InlineKeyboardMarkup(keyboard)\
\
async def delete_after(bot, chat_id, message_id, seconds):\
    await asyncio.sleep(seconds)\
    try:\
        await bot.delete_message(chat_id=chat_id, message_id=message_id)\
    except Exception:\
        pass\
\
async def cleanup_group(group_id):\
    await asyncio.sleep(10)\
    media_group_to_delete.discard(group_id)\
\
async def cleanup_processed(group_id):\
    await asyncio.sleep(10)\
    media_group_processed.discard(group_id)\
\
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    await update.message.reply_text(\
        "\uc0\u55358 \u56598  \u1041 \u1086 \u1090  \u1091 \u1087 \u1088 \u1072 \u1074 \u1083 \u1077 \u1085 \u1080 \u1103  \u1084 \u1077 \u1076 \u1083 \u1077 \u1085 \u1085 \u1099 \u1084  \u1088 \u1077 \u1078 \u1080 \u1084 \u1086 \u1084 \\n\\n"\
        "\uc0\u1050 \u1086 \u1084 \u1072 \u1085 \u1076 \u1099  \u1076 \u1083 \u1103  \u1090 \u1077 \u1084 :\\n"\
        "/add_topic <id> <\uc0\u1095 \u1072 \u1089 \u1099 > \'96 \u1076 \u1086 \u1073 \u1072 \u1074 \u1080 \u1090 \u1100  \u1090 \u1077 \u1084 \u1091  (main \'96 \u1075 \u1083 \u1072 \u1074 \u1085 \u1072 \u1103 )\\n"\
        "/set_topic_slowmode <id> <\uc0\u1095 \u1072 \u1089 \u1099 > \'96 \u1080 \u1079 \u1084 \u1077 \u1085 \u1080 \u1090 \u1100  \u1079 \u1072 \u1076 \u1077 \u1088 \u1078 \u1082 \u1091 \\n"\
        "/remove_topic <id> \'96 \uc0\u1091 \u1076 \u1072 \u1083 \u1080 \u1090 \u1100  \u1090 \u1077 \u1084 \u1091 \\n"\
        "/list_topics \'96 \uc0\u1087 \u1086 \u1082 \u1072 \u1079 \u1072 \u1090 \u1100  \u1090 \u1077 \u1084 \u1099 \\n"\
        "/enable \'96 \uc0\u1074 \u1082 \u1083 \u1102 \u1095 \u1080 \u1090 \u1100  \u1082 \u1086 \u1085 \u1090 \u1088 \u1086 \u1083 \u1100 \\n"\
        "/disable \'96 \uc0\u1086 \u1090 \u1082 \u1083 \u1102 \u1095 \u1080 \u1090 \u1100 \\n"\
        "/status \'96 \uc0\u1089 \u1090 \u1072 \u1090 \u1091 \u1089 \\n\\n"\
        "\uc0\u1041 \u1077 \u1083 \u1099 \u1081  \u1089 \u1087 \u1080 \u1089 \u1086 \u1082 :\\n"\
        "/whitelist_add <@username \uc0\u1080 \u1083 \u1080  ID> \'96 \u1076 \u1086 \u1073 \u1072 \u1074 \u1080 \u1090 \u1100 \\n"\
        "/whitelist_remove <@username \uc0\u1080 \u1083 \u1080  ID> \'96 \u1091 \u1076 \u1072 \u1083 \u1080 \u1090 \u1100 \\n"\
        "/whitelist_list \'96 \uc0\u1087 \u1086 \u1082 \u1072 \u1079 \u1072 \u1090 \u1100 \\n\\n"\
        "\uc0\u1055 \u1088 \u1077 \u1076 \u1091 \u1087 \u1088 \u1077 \u1078 \u1076 \u1077 \u1085 \u1080 \u1077 :\\n"\
        "/set_warning_text <\uc0\u1090 \u1077 \u1082 \u1089 \u1090 > \'96 \u1080 \u1079 \u1084 \u1077 \u1085 \u1080 \u1090 \u1100  \u1090 \u1077 \u1082 \u1089 \u1090 \\n"\
        "/import_warning_text \'96 \uc0\u1086 \u1090 \u1074 \u1077 \u1090 \u1100 \u1090 \u1077  \u1085 \u1072  \u1089 \u1086 \u1086 \u1073 \u1097 \u1077 \u1085 \u1080 \u1077  \u1089  \u1092 \u1086 \u1088 \u1084 \u1072 \u1090 \u1080 \u1088 \u1086 \u1074 \u1072 \u1085 \u1080 \u1077 \u1084 \\n"\
        "/add_warning_button <\uc0\u1090 \u1077 \u1082 \u1089 \u1090 > <url> \'96 \u1076 \u1086 \u1073 \u1072 \u1074 \u1080 \u1090 \u1100  \u1082 \u1085 \u1086 \u1087 \u1082 \u1091 \\n"\
        "/remove_warning_button <\uc0\u1080 \u1085 \u1076 \u1077 \u1082 \u1089 > \'96 \u1091 \u1076 \u1072 \u1083 \u1080 \u1090 \u1100 \\n"\
        "/list_warning_buttons \'96 \uc0\u1087 \u1086 \u1082 \u1072 \u1079 \u1072 \u1090 \u1100 \\n"\
        "/preview \'96 \uc0\u1087 \u1086 \u1082 \u1072 \u1079 \u1072 \u1090 \u1100  \u1087 \u1088 \u1080 \u1084 \u1077 \u1088 \\n"\
        "/reset_memory \'96 \uc0\u1089 \u1073 \u1088 \u1086 \u1089 \u1080 \u1090 \u1100  \u1087 \u1072 \u1084 \u1103 \u1090 \u1100  \u1086  \u1074 \u1088 \u1077 \u1084 \u1077 \u1085 \u1080 \\n"\
        "/set_autodelete <\uc0\u1089 \u1077 \u1082 > \'96 \u1072 \u1074 \u1090 \u1086 \u1091 \u1076 \u1072 \u1083 \u1077 \u1085 \u1080 \u1077  (0 \'96 \u1074 \u1099 \u1082 \u1083 )\\n"\
        "/reset_config \'96 \uc0\u1089 \u1073 \u1088 \u1086 \u1089 \u1080 \u1090 \u1100  \u1074 \u1089 \u1077  \u1085 \u1072 \u1089 \u1090 \u1088 \u1086 \u1081 \u1082 \u1080 "\
    )\
\
async def set_autodelete(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    try:\
        sec = int(context.args[0])\
        if sec < 0:\
            raise ValueError\
        config["autodelete_seconds"] = sec\
        save_config(config)\
        await update.message.reply_text(f"\uc0\u9989  \u1040 \u1074 \u1090 \u1086 \u1091 \u1076 \u1072 \u1083 \u1077 \u1085 \u1080 \u1077 : \{'\u1086 \u1090 \u1082 \u1083 \u1102 \u1095 \u1077 \u1085 \u1086 ' if sec == 0 else f'\{sec\} \u1089 \u1077 \u1082 '\}")\
    except Exception:\
        await update.message.reply_text("\uc0\u1048 \u1089 \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1085 \u1080 \u1077 : /set_autodelete <\u1089 \u1077 \u1082 >")\
\
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    state = "\uc0\u1042 \u1050 \u1051 " if config["enabled"] else "\u1042 \u1067 \u1050 \u1051 "\
    await update.message.reply_text(\
        f"\uc0\u1056 \u1077 \u1078 \u1080 \u1084 : \{state\}\\n"\
        f"\uc0\u1058 \u1077 \u1084 : \{len(config['topics'])\}\\n"\
        f"\uc0\u1041 \u1077 \u1083 \u1099 \u1081  \u1089 \u1087 \u1080 \u1089 \u1086 \u1082 : \{len(config['whitelist'])\}\\n"\
        f"\uc0\u1040 \u1074 \u1090 \u1086 \u1091 \u1076 \u1072 \u1083 \u1077 \u1085 \u1080 \u1077 : \{config['autodelete_seconds']\} \u1089 \u1077 \u1082 "\
    )\
\
async def add_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    try:\
        topic_id = context.args[0]\
        hours = float(context.args[1])\
        if hours < 0:\
            raise ValueError\
        config["topics"][topic_id] = hours\
        save_config(config)\
        await update.message.reply_text(\
            f"\uc0\u9989  \u1058 \u1077 \u1084 \u1072  \{topic_id\} \u1076 \u1086 \u1073 \u1072 \u1074 \u1083 \u1077 \u1085 \u1072 . \u1056 \u1077 \u1078 \u1080 \u1084 : \{'\u1073 \u1077 \u1079  \u1086 \u1075 \u1088 \u1072 \u1085 \u1080 \u1095 \u1077 \u1085 \u1080 \u1081 ' if hours == 0 else f'\{hours\} \u1095 \u1072 \u1089 (\u1086 \u1074 )'\}"\
        )\
    except Exception:\
        await update.message.reply_text("\uc0\u1048 \u1089 \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1085 \u1080 \u1077 : /add_topic <id> <\u1095 \u1072 \u1089 \u1099 >")\
\
async def set_topic_slowmode(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    try:\
        topic_id = context.args[0]\
        hours = float(context.args[1])\
        if hours < 0:\
            raise ValueError\
        if topic_id not in config["topics"]:\
            return await update.message.reply_text("\uc0\u1058 \u1077 \u1084 \u1072  \u1085 \u1077  \u1085 \u1072 \u1081 \u1076 \u1077 \u1085 \u1072 ")\
        config["topics"][topic_id] = hours\
        save_config(config)\
        await update.message.reply_text(f"\uc0\u9201  \u1058 \u1077 \u1084 \u1072  \{topic_id\} \'96 \{hours\} \u1095 \u1072 \u1089 (\u1086 \u1074 )")\
    except Exception:\
        await update.message.reply_text("\uc0\u1048 \u1089 \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1085 \u1080 \u1077 : /set_topic_slowmode <id> <\u1095 \u1072 \u1089 \u1099 >")\
\
async def remove_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    try:\
        topic_id = context.args[0]\
        if topic_id in config["topics"]:\
            del config["topics"][topic_id]\
            save_config(config)\
            await update.message.reply_text(f"\uc0\u10060  \u1058 \u1077 \u1084 \u1072  \{topic_id\} \u1091 \u1076 \u1072 \u1083 \u1077 \u1085 \u1072 ")\
        else:\
            await update.message.reply_text("\uc0\u1058 \u1077 \u1084 \u1072  \u1085 \u1077  \u1085 \u1072 \u1081 \u1076 \u1077 \u1085 \u1072 ")\
    except Exception:\
        await update.message.reply_text("\uc0\u1048 \u1089 \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1085 \u1080 \u1077 : /remove_topic <id>")\
\
async def list_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    if not config["topics"]:\
        return await update.message.reply_text("\uc0\u1057 \u1087 \u1080 \u1089 \u1086 \u1082  \u1090 \u1077 \u1084  \u1087 \u1091 \u1089 \u1090 .")\
    text = "\uc0\u55357 \u56523  \u1058 \u1077 \u1084 \u1099 :\\n"\
    for topic_id, hours in config["topics"].items():\
        name = "\uc0\u1075 \u1083 \u1072 \u1074 \u1085 \u1072 \u1103 " if topic_id == "main" else f"ID \{topic_id\}"\
        text += f"\'95 \{name\}: \{hours\} \uc0\u1095 \u1072 \u1089 (\u1086 \u1074 )\\n"\
    await update.message.reply_text(text)\
\
async def enable(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    config["enabled"] = True\
    save_config(config)\
    await update.message.reply_text("\uc0\u9989  \u1042 \u1082 \u1083 \u1102 \u1095 \u1105 \u1085 ")\
\
async def disable(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    config["enabled"] = False\
    save_config(config)\
    await update.message.reply_text("\uc0\u10060  \u1042 \u1099 \u1082 \u1083 \u1102 \u1095 \u1077 \u1085 ")\
\
async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    text = format_warning_text("@example", 4, "10:00:00", "14:00:00")\
    await update.message.reply_text(\
        text=text,\
        reply_markup=get_keyboard(),\
        parse_mode="HTML",\
        disable_web_page_preview=True\
    )\
\
async def reset_memory(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    last_message_time.clear()\
    await update.message.reply_text("\uc0\u9989  \u1055 \u1072 \u1084 \u1103 \u1090 \u1100  \u1089 \u1073 \u1088 \u1086 \u1096 \u1077 \u1085 \u1072 ")\
\
async def reset_config(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    global config\
    config = \{\
        "enabled": True,\
        "topics": \{\},\
        "whitelist": [],\
        "autodelete_seconds": 180,\
        "warning": \{\
            "text": "\uc0\u1042 \u1099  \u1091 \u1078 \u1077  \u1086 \u1090 \u1087 \u1088 \u1072 \u1074 \u1083 \u1103 \u1083 \u1080  \u1089 \u1086 \u1086 \u1073 \u1097 \u1077 \u1085 \u1080 \u1077  \u1074  \{next_time_old\}, \u1087 \u1086 \u1078 \u1072 \u1083 \u1091 \u1081 \u1089 \u1090 \u1072 , \u1087 \u1086 \u1076 \u1086 \u1078 \u1076 \u1080 \u1090 \u1077  \{delay_hours\} \u1095 \u1072 \u1089 \u1072 (\u1086 \u1074 ), \u1089 \u1083 \u1077 \u1076 \u1091 \u1102 \u1097 \u1077 \u1077  \u1089 \u1086 \u1086 \u1073 \u1097 \u1077 \u1085 \u1080 \u1077  \u1076 \u1086 \u1089 \u1090 \u1091 \u1087 \u1085 \u1086  \u1074  \{next_time\}.",\
            "buttons": [\{"text": "\uc0\u55357 \u56546  \u1056 \u1077 \u1082 \u1083 \u1072 \u1084 \u1072 ", "url": "https://t.me/reklama_opt_chat"\}]\
        \}\
    \}\
    save_config(config)\
    await update.message.reply_text("\uc0\u9989  \u1042 \u1089 \u1077  \u1085 \u1072 \u1089 \u1090 \u1088 \u1086 \u1081 \u1082 \u1080  \u1089 \u1073 \u1088 \u1086 \u1096 \u1077 \u1085 \u1099 ")\
\
async def set_warning_text(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    new_text = " ".join(context.args)\
    if not new_text:\
        return await update.message.reply_text("\uc0\u1059 \u1082 \u1072 \u1078 \u1080 \u1090 \u1077  \u1090 \u1077 \u1082 \u1089 \u1090 ")\
    config["warning"]["text"] = new_text\
    save_config(config)\
    await update.message.reply_text("\uc0\u9989  \u1058 \u1077 \u1082 \u1089 \u1090  \u1086 \u1073 \u1085 \u1086 \u1074 \u1083 \u1105 \u1085 ")\
\
async def import_warning_text(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    if not update.message.reply_to_message:\
        return await update.message.reply_text("\uc0\u1054 \u1090 \u1074 \u1077 \u1090 \u1100 \u1090 \u1077  \u1085 \u1072  \u1089 \u1086 \u1086 \u1073 \u1097 \u1077 \u1085 \u1080 \u1077  \u1089  \u1092 \u1086 \u1088 \u1084 \u1072 \u1090 \u1080 \u1088 \u1086 \u1074 \u1072 \u1085 \u1080 \u1077 \u1084 ")\
    reply = update.message.reply_to_message\
    if reply.text:\
        config["warning"]["text"] = reply.text_html\
        save_config(config)\
        await update.message.reply_text("\uc0\u9989  \u1058 \u1077 \u1082 \u1089 \u1090  \u1080 \u1084 \u1087 \u1086 \u1088 \u1090 \u1080 \u1088 \u1086 \u1074 \u1072 \u1085 ")\
    else:\
        await update.message.reply_text("\uc0\u10060  \u1053 \u1077  \u1091 \u1076 \u1072 \u1083 \u1086 \u1089 \u1100  \u1080 \u1079 \u1074 \u1083 \u1077 \u1095 \u1100  \u1090 \u1077 \u1082 \u1089 \u1090 ")\
\
async def add_warning_button(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    try:\
        text = context.args[0]\
        url = context.args[1]\
        config["warning"]["buttons"].append(\{"text": text, "url": url\})\
        save_config(config)\
        await update.message.reply_text(f"\uc0\u9989  \u1050 \u1085 \u1086 \u1087 \u1082 \u1072  \{text\} \u1076 \u1086 \u1073 \u1072 \u1074 \u1083 \u1077 \u1085 \u1072 ")\
    except Exception:\
        await update.message.reply_text("\uc0\u1048 \u1089 \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1085 \u1080 \u1077 : /add_warning_button <\u1090 \u1077 \u1082 \u1089 \u1090 > <url>")\
\
async def remove_warning_button(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    try:\
        index = int(context.args[0])\
        if 0 <= index < len(config["warning"]["buttons"]):\
            removed = config["warning"]["buttons"].pop(index)\
            save_config(config)\
            await update.message.reply_text(f"\uc0\u10060  \u1050 \u1085 \u1086 \u1087 \u1082 \u1072  \{removed['text']\} \u1091 \u1076 \u1072 \u1083 \u1077 \u1085 \u1072 ")\
        else:\
            await update.message.reply_text("\uc0\u1053 \u1077 \u1074 \u1077 \u1088 \u1085 \u1099 \u1081  \u1080 \u1085 \u1076 \u1077 \u1082 \u1089 ")\
    except Exception:\
        await update.message.reply_text("\uc0\u1048 \u1089 \u1087 \u1086 \u1083 \u1100 \u1079 \u1086 \u1074 \u1072 \u1085 \u1080 \u1077 : /remove_warning_button <\u1080 \u1085 \u1076 \u1077 \u1082 \u1089 >")\
\
async def list_warning_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    if not config["warning"]["buttons"]:\
        return await update.message.reply_text("\uc0\u1050 \u1085 \u1086 \u1087 \u1086 \u1082  \u1085 \u1077 \u1090 ")\
    text = "\uc0\u55357 \u56523  \u1050 \u1085 \u1086 \u1087 \u1082 \u1080 :\\n"\
    for i, btn in enumerate(config["warning"]["buttons"]):\
        text += f"\{i\}. \{btn['text']\} \uc0\u8594  \{btn['url']\}\\n"\
    await update.message.reply_text(text)\
\
async def whitelist_add(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    if not context.args:\
        return await update.message.reply_text("\uc0\u1059 \u1082 \u1072 \u1078 \u1080 \u1090 \u1077  @username \u1080 \u1083 \u1080  ID")\
    item = context.args[0]\
    if item in config["whitelist"]:\
        return await update.message.reply_text("\uc0\u1059 \u1078 \u1077  \u1077 \u1089 \u1090 \u1100 ")\
    config["whitelist"].append(item)\
    save_config(config)\
    await update.message.reply_text(f"\uc0\u9989  \{item\} \u1076 \u1086 \u1073 \u1072 \u1074 \u1083 \u1077 \u1085 ")\
\
async def whitelist_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    if not context.args:\
        return await update.message.reply_text("\uc0\u1059 \u1082 \u1072 \u1078 \u1080 \u1090 \u1077  @username \u1080 \u1083 \u1080  ID")\
    item = context.args[0]\
    if item not in config["whitelist"]:\
        return await update.message.reply_text("\uc0\u1053 \u1077  \u1085 \u1072 \u1081 \u1076 \u1077 \u1085 ")\
    config["whitelist"].remove(item)\
    save_config(config)\
    await update.message.reply_text(f"\uc0\u10060  \{item\} \u1091 \u1076 \u1072 \u1083 \u1105 \u1085 ")\
\
async def whitelist_list(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    if not is_admin(update.effective_user.id):\
        return await update.message.reply_text("\uc0\u1053 \u1077 \u1090  \u1087 \u1088 \u1072 \u1074 .")\
    if not config["whitelist"]:\
        return await update.message.reply_text("\uc0\u1041 \u1077 \u1083 \u1099 \u1081  \u1089 \u1087 \u1080 \u1089 \u1086 \u1082  \u1087 \u1091 \u1089 \u1090 ")\
    await update.message.reply_text("\uc0\u55357 \u56523  \u1041 \u1077 \u1083 \u1099 \u1081  \u1089 \u1087 \u1080 \u1089 \u1086 \u1082 :\\n" + "\\n".join(config["whitelist"]))\
\
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):\
    message = update.message\
    if not message:\
        return\
    if message.chat.type not in ["group", "supergroup"]:\
        return\
    if not config["enabled"]:\
        return\
    if is_whitelisted(message.from_user):\
        return\
\
    thread_key = get_thread_key(message)\
    if thread_key not in config["topics"]:\
        return\
\
    delay_h = config["topics"][thread_key]\
    if delay_h == 0:\
        return\
\
    user_id = message.from_user.id\
    key = (user_id, thread_key)\
    now = datetime.now(timezone.utc)\
    last = last_message_time.get(key)\
    delay_sec = delay_h * 3600\
\
    media_group_id = message.media_group_id\
    if media_group_id:\
        if media_group_id in media_group_to_delete:\
            try:\
                await message.delete()\
            except Exception:\
                pass\
            return\
        if media_group_id in media_group_processed:\
            return\
\
    if last and (now - last).total_seconds() < delay_sec:\
        try:\
            await message.delete()\
        except Exception:\
            pass\
\
        if media_group_id:\
            media_group_to_delete.add(media_group_id)\
            asyncio.create_task(cleanup_group(media_group_id))\
\
        next_utc = last + timedelta(seconds=delay_sec)\
        msk = timezone(MOSCOW_OFFSET)\
        next_str = next_utc.astimezone(msk).strftime("%H:%M:%S")\
        old_str = last.astimezone(msk).strftime("%H:%M:%S")\
\
        username = f"@\{message.from_user.username\}" if message.from_user.username else message.from_user.first_name\
        text = format_warning_text(username, delay_h, old_str, next_str)\
\
        try:\
            sent = await context.bot.send_message(\
                chat_id=message.chat_id,\
                text=text,\
                message_thread_id=message.message_thread_id,\
                reply_markup=get_keyboard(),\
                parse_mode="HTML",\
                disable_web_page_preview=True\
            )\
            if config["autodelete_seconds"] > 0:\
                asyncio.create_task(delete_after(context.bot, sent.chat_id, sent.message_id, config["autodelete_seconds"]))\
        except Exception as e:\
            logger.exception("\uc0\u1054 \u1096 \u1080 \u1073 \u1082 \u1072  \u1086 \u1090 \u1087 \u1088 \u1072 \u1074 \u1082 \u1080  \u1087 \u1088 \u1077 \u1076 \u1091 \u1087 \u1088 \u1077 \u1078 \u1076 \u1077 \u1085 \u1080 \u1103 : %s", e)\
        return\
\
    last_message_time[key] = now\
\
    if media_group_id:\
        media_group_processed.add(media_group_id)\
        asyncio.create_task(cleanup_processed(media_group_id))\
\
telegram_app = Application.builder().token(BOT_TOKEN).build()\
\
for cmd, func in [\
    ("start", start),\
    ("set_autodelete", set_autodelete),\
    ("status", status),\
    ("add_topic", add_topic),\
    ("set_topic_slowmode", set_topic_slowmode),\
    ("remove_topic", remove_topic),\
    ("list_topics", list_topics),\
    ("enable", enable),\
    ("disable", disable),\
    ("preview", preview),\
    ("reset_memory", reset_memory),\
    ("reset_config", reset_config),\
    ("set_warning_text", set_warning_text),\
    ("import_warning_text", import_warning_text),\
    ("add_warning_button", add_warning_button),\
    ("remove_warning_button", remove_warning_button),\
    ("list_warning_buttons", list_warning_buttons),\
    ("whitelist_add", whitelist_add),\
    ("whitelist_remove", whitelist_remove),\
    ("whitelist_list", whitelist_list),\
]:\
    telegram_app.add_handler(CommandHandler(cmd, func))\
\
telegram_app.add_handler(MessageHandler(filters.ALL, handle_message))\
\
flask_app = Flask(__name__)\
\
loop = asyncio.new_event_loop()\
asyncio.set_event_loop(loop)\
\
async def telegram_bootstrap():\
    await telegram_app.initialize()\
    await telegram_app.start()\
    await telegram_app.bot.delete_webhook(drop_pending_updates=True)\
    await telegram_app.bot.set_webhook(f"\{BASE_URL\}/webhook")\
    logger.info("Webhook \uc0\u1091 \u1089 \u1090 \u1072 \u1085 \u1086 \u1074 \u1083 \u1077 \u1085 : %s/webhook", BASE_URL)\
\
loop.run_until_complete(telegram_bootstrap())\
\
@flask_app.route("/", methods=["GET"])\
@flask_app.route("/health", methods=["GET"])\
def health():\
    return "OK", 200\
\
@flask_app.route("/webhook", methods=["POST"])\
def webhook():\
    try:\
        data = request.get_json(force=True)\
        update = Update.de_json(data, telegram_app.bot)\
        asyncio.run_coroutine_threadsafe(telegram_app.update_queue.put(update), loop)\
        return "OK", 200\
    except Exception as e:\
        logger.exception("\uc0\u1054 \u1096 \u1080 \u1073 \u1082 \u1072  webhook: %s", e)\
        return "ERROR", 500\
\
if __name__ == "__main__":\
    flask_app.run(host="0.0.0.0", port=PORT)}