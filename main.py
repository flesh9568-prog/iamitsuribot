import os
import time
import threading
from flask import Flask
from telebot import TeleBot, types
from openai import OpenAI
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
HF_TOKEN = os.environ.get('HF_TOKEN')

bot = TeleBot(BOT_TOKEN)
app = Flask(__name__)

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN
)

# In-memory storage for chat history (Memory)
# Note: On Render free tier, this clears if the server restarts.
memories = {}

def get_mitsuri_response(chat_id, user_name, user_text):
    # Maintain memory (keep last 10 exchanges)
    if chat_id not in memories:
        memories[chat_id] = []
    
    # System Prompt to define personality
    system_prompt = (
        f"Your name is Mitsuri. You are a human girl from Japan, not an AI. "
        f"You are chatting with {user_name}. Your owner is Karan (@usergotcigs). "
        "Rules: 1. Reply in very few words (short and sweet). 2. Never use long paragraphs. "
        "3. Use Hinglish if the user speaks Hinglish, and English if they speak English. "
        "4. Be friendly, casual, and act like a close friend. 5. If asked about your owner, "
        "mention Karan (@usergotcigs). 6. If asked where you are from, say Japan. "
        "7. Remember past details of the conversation to act human."
    )

    messages = [{"role": "system", "content": system_prompt}]
    # Add history
    messages.extend(memories[chat_id][-10:])
    # Add current message
    messages.append({"role": "user", "content": user_text})

    try:
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",
            messages=messages,
            max_tokens=150
        )
        reply = response.choices[0].message.content
        
        # Clean up Thinking tags if DeepSeek provides them
        if "</thought>" in reply:
            reply = reply.split("</thought>")[-1].strip()
        
        # Save to memory
        memories[chat_id].append({"role": "user", "content": user_text})
        memories[chat_id].append({"role": "assistant", "content": reply})
        
        return reply
    except Exception as e:
        print(f"Error: {e}")
        return "Gomen... can you say that again? 🎀"

# --- TELEGRAM HANDLERS ---

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    text = message.text
    bot_username = bot.get_me().username

    # Group Logic: Reply if tagged, or if it's a private chat
    is_private = message.chat.type == 'private'
    is_tagged = (message.reply_to_message and message.reply_to_message.from_user.username == bot_username) or \
                (f"@{bot_username}" in text) or ("mitsuri" in text.lower())

    if is_private or is_tagged:
        # Show typing status for realism
        bot.send_chat_action(chat_id, 'typing')
        response = get_mitsuri_response(chat_id, user_name, text)
        bot.reply_to(message, response)

# --- SCHEDULED TASK ---

def send_good_morning():
    # Replace with specific Group IDs or use a database to store group IDs
    # For now, this will send to known memories that are groups
    for chat_id in memories.keys():
        try:
            bot.send_message(chat_id, "Good morning everyone 🎀")
        except:
            continue

scheduler = BackgroundScheduler()
# Set to 7:00 AM IST (Asia/Kolkata)
scheduler.add_job(send_good_morning, 'cron', hour=7, minute=0, timezone=timezone('Asia/Kolkata'))
scheduler.start()

# --- WEB SERVER FOR RENDER ---

@app.route('/')
def home():
    return "Mitsuri is Awake! 🎀"

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # Run Telegram bot in a separate thread
    threading.Thread(target=run_bot).start()
    # Run Flask server
    po
