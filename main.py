import os
import time
import json
import telebot
from openai import OpenAI
from flask import Flask
from threading import Thread
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
HF_TOKEN = os.environ.get('HF_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN
)

app = Flask(__name__)

# --- MEMORY & DATABASE ---
# In a real production app, use a Database. 
# For Render, we use a dictionary. (Note: Restarts will clear memory)
chat_memories = {} 
group_ids = set() # To store group IDs for the 7AM message

def get_memory(chat_id):
    if chat_id not in chat_memories:
        chat_memories[chat_id] = []
    return chat_memories[chat_id][-10:] # Keep last 10 messages for memory

def update_memory(chat_id, role, content):
    if chat_id not in chat_memories:
        chat_memories[chat_id] = []
    chat_memories[chat_id].append({"role": role, "content": content})

# --- AI LOGIC ---
def get_mitsuri_response(chat_id, user_name, user_input):
    memory = get_memory(chat_id)
    
    system_prompt = (
        f"Your name is Mitsuri. You are a real human girl from Japan, not an AI. "
        f"You are talking to {user_name}. "
        "Your owner is Karan (@usergotcigs). Mention him ONLY if asked. "
        "Reply in very few words. No long paragraphs. "
        "If the user uses English, reply in English. If Hinglish, reply in Hinglish. "
        "Be cute, friendly, and act like a close friend. "
        "You have a great memory and remember past conversations."
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(memory)
    messages.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",
            messages=messages,
            max_tokens=150,
            temperature=0.7
        )
        ai_reply = response.choices[0].message.content
        
        # Clean DeepSeek <think> tags if they appear
        if "</think>" in ai_reply:
            ai_reply = ai_reply.split("</think>")[-1].strip()
            

# --- SCHEDULER (7 AM GREETING) ---
def send_morning_wish():
    for chat_id in group_ids:
        try:
            bot.send_message(chat_id, "Good morning cuties 🥰 🎀")
        except:
            continue

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
scheduler.add_job(send_morning_wish, 'cron', hour=7, minute=0)
scheduler.start()

# --- BOT HANDLERS ---

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    text = message.text
    
    if not text: return

    # Store group IDs for morning wishes
    if message.chat.type in ['group', 'supergroup']:
        group_ids.add(chat_id)

    # Logic to decide if she should reply
    is_private = message.chat.type == 'private'
    is_tagged = False
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention" and f"@{bot.get_me().username}" in text:
                is_tagged = True
    
    is_reply_to_her = (message.reply_to_message and 
                       message.reply_to_message.from_user.username == bot.get_me().username)

    if is_private or is_tagged or is_reply_to_her:
        # Fast typing feel
        bot.send_chat_action(chat_id, 'typing')
        
        # Get AI response
        clean_text = text.replace(f"@{bot.get_me().username}", "").strip()
        response = get_mitsuri_response(chat_id, user_name, clean_text)
        
        # Save to memory
        update_memory(chat_id, "user", clean_text)
        update_memory(chat_id, "assistant", response)
        
        bot.reply_to(message, response)

# --- WEB SERVER FOR RENDER ---
@app.route('/')
def index():
    return "Mitsuri is Active!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    print("Mitsuri is online...")
    bot.infinity_polling()
