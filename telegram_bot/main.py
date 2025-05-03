import os
import telebot, logging
from dotenv import load_dotenv
from helpers import get_agent_response

load_dotenv()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "Hello my friend, how are you doing?")

@bot.message_handler(commands=['ask-anything'])
def sign_handler(message):
    text = '''
    I am a smart assistant. Atleast that is what I like to think.\n**How can I help you today?**
    '''
    sent_msg = bot.send_message(message.chat.id, text, parse_mode="Markdown")
    bot.register_next_step_handler(sent_msg, call_agent)

def call_agent(message):
    query = message.text
    agent_output = get_agent_response(query)
    bot.send_message(message.chat.id, "I have something for you! Your output - ")
    bot.send_message(message.chat.id, agent_output["response"], parse_mode="Markdown")

@bot.message_handler(func=lambda msg: True)
def echo_all(message):
    bot.reply_to(message, message.text)

def main():
    logger.info("Starting SSE server at 8080...")
    bot.infinity_polling(
        logger_level=20
    )

if __name__ == '__main__':
    main()