import asyncio
import io
import json
import os
import random
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import discord
import qrcode
from discord import app_commands
from discord.ext import commands, tasks

# =========================
# CONFIGURAÇÃO BASE
# =========================
# Segurança: defina o token em variável de ambiente DISCORD_BOT_TOKEN
TOKEN = os.getenv("TOKEN") or os.getenv("DISCORD_BOT_TOKEN", "")

GUILD_ID = 1358235999783620771
CATEGORY_TICKETS_ID = 1399236036965568573
CANAL_PAINEL_ID = 1398490374103629996
CANAL_LOGS_ID = 1492745296843641003
CARGO_CLIENTE_ID = 1399977908105252984
CARGO_ADMIN_ID = 1367990975133122581

ARQUIVO_JSON = Path("twx_store_data_v5.json")
COR_PADRAO = 0x7C3AED
COR_SUCESSO = 0x22C55E
COR_ALERTA = 0xF59E0B
COR_ERRO = 0xEF4444
COR_INFO = 0x3B82F6

DEFAULT_BANNER_ONLINE = "https://uploadimagem.com//uploads/img_69dd3eb3300ef.png"
DEFAULT_LOGO = ""
NOME_PADRAO_LOJA = "TWX STORE"
MOEDA_PADRAO = "R$"
MERCHANT_NAME = "JULIO CESAR DO NASCIMENTO FILHO"
MERCHANT_CITY = "ARACAJU"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
ACTIVE_GIVEAWAYS: dict[str, "GiveawayView"] = {}
TRANSCRIPTS_DIR = Path("transcripts")


# =========================
# UTILITÁRIOS
# =========================
def default_data() -> dict:
    return {
        "painel": {
            "titulo": NOME_PADRAO_LOJA,
            "status": "online",
            "mensagem_offline": "Loja offline no momento. Volte mais tarde.",
            "cor": COR_PADRAO,
            "banner_online_url": DEFAULT_BANNER_ONLINE,
            "banner_offline_url": "",
            "thumbnail_url": DEFAULT_LOGO,
            "mostrar_calc_no_painel": True,
            "mostrar_resumo_estoque": True,
            "mensagem_boas_vindas": "Escolha uma categoria abaixo para abrir seu atendimento.",
        },
        "pix": {
            "tipo": "aleatoria",
            "chave": "86c32427-7746-4507-ba21-31f8a1139411",
            "beneficiario": MERCHANT_NAME,
            "cidade": MERCHANT_CITY,
            "descricao": "Pagamento Pix",
            "mostrar_chave_no_painel": False,
        },
        "loja": {
            "nome": NOME_PADRAO_LOJA,
            "moeda": MOEDA_PADRAO,
        },
        "stats": {
            "sales_count": 0,
            "sales_total": 0.0
        },
        "usuarios": {},
        "blacklist": {},
        "ticket_states": {},
        "vip": {
            "enabled": True,
            "role_id": 0,
            "discount_percent": 5,
            "auto_role_after_sales": 3,
            "auto_role_after_spent": 100.0
        },
        "payment": {
            "default_deadline_minutes": 20,
            "message_pending": "Pagamento pendente. Envie o comprovante ou aguarde a conferência da equipe.",
            "message_approved": "Pagamento aprovado com sucesso.",
            "message_expired": "O prazo para pagamento expirou e o ticket foi encerrado.",
            "message_denied": "Pagamento não aprovado.",
            "tax_percent": 0.0,
            "pix_discount_percent": 0.0
        },
        "service_tickets": {
            "support": {"nome": "SUPORTE", "emoji": "🛠️", "descricao": "Suporte geral e dúvidas."},
            "refund": {"nome": "REEMBOLSO", "emoji": "💸", "descricao": "Solicitação de reembolso."},
            "partnership": {"nome": "PARCERIA", "emoji": "🤝", "descricao": "Parcerias e propostas."},
            "calc": {"nome": "CÁLCULO", "emoji": "🧮", "descricao": "Orçamento personalizado."}
        },
        "categorias": {
            "contas": {
                "nome": "CONTAS",
                "emoji": "👤",
                "descricao": "Contas prontas para compra.",
                "banner_url": "",
                "cor": 0x22C55E,
                "produtos": [
                    {
                        "nome": "RAÇA MÍSTICA ALEATÓRIA + ITENS",
                        "preco": "R$ 12,90",
                        "descricao": "Conta com raça mística aleatória + itens.",
                        "estoque_arquivo": "contas_stock.txt",
                        "stock_quantity": 0,
                    },
                    {
                        "nome": "LEVEL MAX + ITENS",
                        "preco": "R$ 7,90",
                        "descricao": "Conta level max + itens.",
                        "estoque_arquivo": "contas_stock.txt",
                        "stock_quantity": 0,
                    },
                    {
                        "nome": "CONTA PREMIUM SAILOR",
                        "preco": "R$ 19,90",
                        "descricao": "Conta premium Sailor.",
                        "estoque_arquivo": "contas_stock.txt",
                        "stock_quantity": 0,
                    },
                ],
            },
            "itens": {
                "nome": "ITENS",
                "emoji": "🎁",
                "descricao": "Itens raros disponíveis.",
                "banner_url": "",
                "cor": 0x3B82F6,
                "produtos": [
                    {
                        "nome": "KIT DE ITENS RAROS",
                        "preco": "R$ 5,50",
                        "descricao": "Kit com itens raros.",
                        "estoque_arquivo": "itens_stock.txt",
                        "stock_quantity": 0,
                    },
                    {
                        "nome": "CAIXA DE AURA",
                        "preco": "R$ 1,20",
                        "descricao": "Caixa contendo aura aleatória.",
                        "estoque_arquivo": "itens_stock.txt",
                        "stock_quantity": 0,
                    },
                ],
            },
            "reroll_raca": {
                "nome": "REROLL RAÇA",
                "emoji": "🧬",
                "descricao": "Pacotes de reroll de raça.",
                "banner_url": "",
                "cor": 0xF59E0B,
                "produtos": [
                    {
                        "nome": "1k reroll raça",
                        "preco": "R$ 1,00",
                        "descricao": "Pacote 1k reroll raça.",
                        "estoque_arquivo": "reroll_stock.txt",
                        "stock_quantity": 0,
                    },
                    {
                        "nome": "5k reroll raça",
                        "preco": "R$ 4,50",
                        "descricao": "Pacote 5k reroll raça.",
                        "estoque_arquivo": "reroll_stock.txt",
                        "stock_quantity": 0,
                    },
                    {
                        "nome": "10k reroll raça",
                        "preco": "R$ 9,50",
                        "descricao": "Pacote 10k reroll raça.",
                        "estoque_arquivo": "reroll_stock.txt",
                        "stock_quantity": 0,
                    },
                ],
            },
            "cla_reroll": {
                "nome": "CLÃ REROLL",
                "emoji": "🌀",
                "descricao": "Pacotes de reroll de clã.",
                "banner_url": "",
                "cor": 0x8B5CF6,
                "produtos": [
                    {
                        "nome": "1k reroll clã",
                        "preco": "R$ 1,20",
                        "descricao": "Pacote 1k reroll de clã.",
                        "estoque_arquivo": "cla_reroll_stock.txt",
                        "stock_quantity": 0,
                    },
                    {
                        "nome": "5k reroll clã",
                        "preco": "R$ 5,50",
                        "descricao": "Pacote 5k reroll de clã.",
                        "estoque_arquivo": "cla_reroll_stock.txt",
                        "stock_quantity": 0,
                    },
                ],
            },
            "sets": {
                "nome": "SETS",
                "emoji": "🧥",
                "descricao": "Sets e kits especiais.",
                "banner_url": "",
                "cor": 0xEC4899,
                "produtos": [
                    {
                        "nome": "SET INICIANTE",
                        "preco": "R$ 3,50",
                        "descricao": "Kit básico para iniciar.",
                        "estoque_arquivo": "sets_stock.txt",
                        "stock_quantity": 0,
                    },
                    {
                        "nome": "SET PREMIUM",
                        "preco": "R$ 9,90",
                        "descricao": "Kit premium com itens melhores.",
                        "estoque_arquivo": "sets_stock.txt",
                        "stock_quantity": 0,
                    },
                ],
            },
        },
    }




def deep_merge_missing(target: dict, source: dict) -> bool:
    changed = False
    for key, value in source.items():
        if key not in target:
            target[key] = value
            changed = True
        elif isinstance(value, dict) and isinstance(target.get(key), dict):
            if deep_merge_missing(target[key], value):
                changed = True
    return changed


def save_data(data: dict) -> None:
    ARQUIVO_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")



def load_data() -> dict:
    if not ARQUIVO_JSON.exists():
        data = default_data()
        save_data(data)
        return data

    try:
        data = json.loads(ARQUIVO_JSON.read_text(encoding="utf-8"))
    except Exception:
        data = default_data()
        save_data(data)
        return data

    base = default_data()
    changed = deep_merge_missing(data, base)

    if "categorias" in base:
        for category_id, category_data in base["categorias"].items():
            if category_id not in data["categorias"]:
                data["categorias"][category_id] = category_data
                changed = True

    for category_id, category in data.get("categorias", {}).items():
        if "produtos" not in category:
            category["produtos"] = []
            changed = True
            continue
        for product in category["produtos"]:
            if "stock_quantity" not in product:
                product["stock_quantity"] = 0
                changed = True
            if "estoque_arquivo" not in product:
                product["estoque_arquivo"] = f"{category_id}_stock.txt"
                changed = True

    if changed:
        save_data(data)
    return data



def get_user_data(user_id: int) -> dict:
    data = load_data()
    users = data.setdefault("usuarios", {})
    key = str(user_id)
    if key not in users:
        users[key] = {
            "gasto_total": 0.0,
            "compras": 0,
            "produtos": {},
            "tickets": 0,
            "ultimo_produto": "",
            "ultima_compra": "",
        }
        save_data(data)
    return users[key]


def register_user_ticket(user_id: int) -> None:
    data = load_data()
    users = data.setdefault("usuarios", {})
    key = str(user_id)
    if key not in users:
        users[key] = {
            "gasto_total": 0.0,
            "compras": 0,
            "produtos": {},
            "tickets": 0,
            "ultimo_produto": "",
            "ultima_compra": "",
        }
    users[key]["tickets"] = int(users[key].get("tickets", 0) or 0) + 1
    save_data(data)


def register_sale(user_id: int, product_name: str, price_text: str) -> None:
    data = load_data()
    amount = money_to_float(price_text)
    stats = data.setdefault("stats", {"sales_count": 0, "sales_total": 0.0})
    stats["sales_count"] = int(stats.get("sales_count", 0) or 0) + 1
    stats["sales_total"] = round(float(stats.get("sales_total", 0.0) or 0.0) + amount, 2)

    users = data.setdefault("usuarios", {})
    key = str(user_id)
    if key not in users:
        users[key] = {
            "gasto_total": 0.0,
            "compras": 0,
            "produtos": {},
            "tickets": 0,
            "ultimo_produto": "",
            "ultima_compra": "",
        }
    user = users[key]
    user["gasto_total"] = round(float(user.get("gasto_total", 0.0) or 0.0) + amount, 2)
    user["compras"] = int(user.get("compras", 0) or 0) + 1
    produtos = user.setdefault("produtos", {})
    produtos[product_name] = int(produtos.get(product_name, 0) or 0) + 1
    user["ultimo_produto"] = product_name
    user["ultima_compra"] = datetime.utcnow().isoformat()
    save_data(data)


def top_buyers(limit: int = 10) -> list[tuple[int, dict]]:
    data = load_data()
    users = data.get("usuarios", {})
    ranked = []
    for uid, info in users.items():
        try:
            ranked.append((int(uid), info))
        except Exception:
            continue
    ranked.sort(key=lambda item: (float(item[1].get("gasto_total", 0.0) or 0.0), int(item[1].get("compras", 0) or 0)), reverse=True)
    return ranked[:limit]


def blacklist_add_user(user_id: int, reason: str, staff_id: int) -> None:
    data = load_data()
    bl = data.setdefault("blacklist", {})
    bl[str(user_id)] = {
        "reason": reason.strip()[:300] or "Sem motivo informado.",
        "staff_id": int(staff_id),
        "created_at": datetime.utcnow().isoformat(),
    }
    save_data(data)


def blacklist_remove_user(user_id: int) -> bool:
    data = load_data()
    bl = data.setdefault("blacklist", {})
    if str(user_id) in bl:
        del bl[str(user_id)]
        save_data(data)
        return True
    return False


def get_blacklist_entry(user_id: int) -> Optional[dict]:
    data = load_data()
    return data.get("blacklist", {}).get(str(user_id))


def is_blacklisted(user_id: int) -> bool:
    return get_blacklist_entry(user_id) is not None




def get_ticket_state(channel_id: int) -> dict:
    data = load_data()
    states = data.setdefault("ticket_states", {})
    return states.get(str(channel_id), {})


def set_ticket_state(channel_id: int, updates: dict) -> dict:
    data = load_data()
    states = data.setdefault("ticket_states", {})
    state = states.setdefault(str(channel_id), {})
    state.update(updates)
    save_data(data)
    return state


def delete_ticket_state(channel_id: int) -> None:
    data = load_data()
    states = data.setdefault("ticket_states", {})
    if str(channel_id) in states:
        del states[str(channel_id)]
        save_data(data)


def iso_now() -> str:
    return datetime.utcnow().isoformat()


def parse_iso(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def get_ticket_elapsed_text(state: dict) -> str:
    created_at = parse_iso(state.get("created_at"))
    if not created_at:
        return "Não disponível"
    delta = datetime.utcnow() - created_at
    total_seconds = max(0, int(delta.total_seconds()))
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours}h {minutes}m {seconds}s"


def member_is_vip(member: Optional[discord.Member]) -> bool:
    if not isinstance(member, discord.Member):
        return False
    data = load_data()
    vip = data.get("vip", {})
    role_id = int(vip.get("role_id", 0) or 0)
    return bool(role_id and any(r.id == role_id for r in member.roles))


def get_price_components(price_text: str, member: Optional[discord.Member], extra_percent: float | None = None, pix_discount_percent: float | None = None) -> dict:
    data = load_data()
    payment = data.get("payment", {})
    vip = data.get("vip", {})
    base = money_to_float(price_text)
    extra = float(extra_percent if extra_percent is not None else payment.get("tax_percent", 0.0) or 0.0)
    pix_discount = float(pix_discount_percent if pix_discount_percent is not None else payment.get("pix_discount_percent", 0.0) or 0.0)
    vip_discount = float(vip.get("discount_percent", 0.0) or 0.0) if member_is_vip(member) and vip.get("enabled", True) else 0.0
    after_extra = base * (1 + extra / 100.0)
    after_vip = after_extra * (1 - vip_discount / 100.0)
    final = after_vip * (1 - pix_discount / 100.0)
    return {
        "base": base,
        "extra_percent": extra,
        "vip_discount_percent": vip_discount,
        "pix_discount_percent": pix_discount,
        "final": max(0.0, round(final, 2))
    }


def try_promote_vip(guild: Optional[discord.Guild], member: Optional[discord.Member]) -> bool:
    if guild is None or member is None:
        return False
    data = load_data()
    vip = data.get("vip", {})
    if not vip.get("enabled", True):
        return False
    role_id = int(vip.get("role_id", 0) or 0)
    if not role_id:
        return False
    role = guild.get_role(role_id)
    if role is None or role in member.roles:
        return False
    info = get_user_data(member.id)
    enough_sales = int(info.get("compras", 0) or 0) >= int(vip.get("auto_role_after_sales", 999999) or 999999)
    enough_spent = float(info.get("gasto_total", 0.0) or 0.0) >= float(vip.get("auto_role_after_spent", 999999999) or 999999999)
    if not (enough_sales or enough_spent):
        return False
    try:
        coro = member.add_roles(role, reason="VIP automático por compras")
    except Exception:
        return False
    return coro

async def create_ticket_transcript(channel: discord.TextChannel) -> Path:
    TRANSCRIPTS_DIR.mkdir(exist_ok=True)
    filename = f"{slugify(channel.name)}-{channel.id}.txt"
    output = TRANSCRIPTS_DIR / filename
    lines = []
    async for message in channel.history(limit=None, oldest_first=True):
        created = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author = f"{message.author} ({message.author.id})"
        content = message.content or ""
        if message.embeds:
            content += " [EMBED]"
        if message.attachments:
            names = ", ".join(att.filename for att in message.attachments)
            content += f" [ARQUIVOS: {names}]"
        lines.append(f"[{created}] {author}: {content}".rstrip())
    output.write_text("\n".join(lines) or "Sem mensagens.", encoding="utf-8")
    return output


def is_admin(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    role = member.guild.get_role(CARGO_ADMIN_ID)
    return role in member.roles if role else False



def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s_-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:90] or "item"



def get_color(value) -> discord.Color:
    try:
        if isinstance(value, int):
            return discord.Color(value)
        if isinstance(value, str):
            return discord.Color(int(value.replace("#", ""), 16))
    except Exception:
        pass
    return discord.Color(COR_PADRAO)



def money_to_float(price: str) -> float:
    data = load_data()
    moeda = data["loja"].get("moeda", MOEDA_PADRAO)
    clean = price.replace(moeda, "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(clean)
    except Exception:
        return 0.0



def format_money(value: float) -> str:
    data = load_data()
    moeda = data["loja"].get("moeda", MOEDA_PADRAO)
    return f"{moeda} {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")



def stock_count(filename: str) -> int:
    path = Path(filename)
    if not path.exists():
        return 0
    return len([x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()])



def add_stock(filename: str, lines_to_add: list[str]) -> int:
    path = Path(filename)
    current = []
    if path.exists():
        current = [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    current.extend([x.strip() for x in lines_to_add if x.strip()])
    path.write_text("\n".join(current), encoding="utf-8")
    return len(lines_to_add)



def pop_stock(filename: str) -> Optional[str]:
    path = Path(filename)
    if not path.exists():
        return None
    lines = [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    if not lines:
        return None
    first = lines.pop(0)
    path.write_text("\n".join(lines), encoding="utf-8")
    return first


def product_display_stock(product: dict) -> int:
    linhas = stock_count(product.get("estoque_arquivo", ""))
    quantidade = int(product.get("stock_quantity", 0) or 0)
    return max(0, linhas + quantidade)


def set_product_stock_quantity(product_name: str, quantidade: int) -> tuple[bool, str, int]:
    data = load_data()
    for category in data["categorias"].values():
        for product in category["produtos"]:
            if product["nome"].casefold() == product_name.casefold():
                product["stock_quantity"] = max(0, int(quantidade))
                save_data(data)
                return True, product["nome"], product_display_stock(product)
    return False, "", 0


def add_product_stock_quantity(product_name: str, quantidade: int) -> tuple[bool, str, int]:
    data = load_data()
    for category in data["categorias"].values():
        for product in category["produtos"]:
            if product["nome"].casefold() == product_name.casefold():
                atual = int(product.get("stock_quantity", 0) or 0)
                product["stock_quantity"] = max(0, atual + int(quantidade))
                save_data(data)
                return True, product["nome"], product_display_stock(product)
    return False, "", 0


def remove_product_stock_quantity(product_name: str, quantidade: int) -> tuple[bool, str, int]:
    data = load_data()
    for category in data["categorias"].values():
        for product in category["produtos"]:
            if product["nome"].casefold() == product_name.casefold():
                atual = int(product.get("stock_quantity", 0) or 0)
                product["stock_quantity"] = max(0, atual - int(quantidade))
                save_data(data)
                return True, product["nome"], product_display_stock(product)
    return False, "", 0


def find_product(product_name: str):
    data = load_data()
    for category_id, category in data["categorias"].items():
        for product in category["produtos"]:
            if product["nome"].casefold() == product_name.casefold():
                return category_id, category, product
    return None, None, None



def parse_buyer_id(channel: discord.TextChannel) -> Optional[int]:
    topic = channel.topic or ""
    match = re.search(r"comprador:(\d+)", topic)
    return int(match.group(1)) if match else None



def parse_product_name(channel: discord.TextChannel) -> Optional[str]:
    topic = channel.topic or ""
    match = re.search(r"produto:([^|]+)", topic)
    return match.group(1).strip() if match else None


def parse_ticket_type(channel: discord.TextChannel) -> str:
    topic = channel.topic or ""
    match = re.search(r"tipo:([^|]+)", topic)
    return match.group(1).strip().lower() if match else "compra"


def is_custom_ticket_product(channel: discord.TextChannel) -> bool:
    state = get_ticket_state(channel.id)
    return bool(state.get("custom_product", False))



def base_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    data = load_data()
    embed = discord.Embed(title=title, description=description, color=color)
    thumb = data["painel"].get("thumbnail_url", "")
    if thumb:
        embed.set_thumbnail(url=thumb)
    embed.set_footer(text=data["loja"].get("nome", NOME_PADRAO_LOJA))
    return embed


# =========================
# PIX / QR CODE
# =========================
def crc16(payload: str) -> str:
    polynomial = 0x1021
    result = 0xFFFF
    for char in payload:
        result ^= ord(char) << 8
        for _ in range(8):
            if result & 0x8000:
                result = (result << 1) ^ polynomial
            else:
                result <<= 1
            result &= 0xFFFF
    return f"{result:04X}"



def emv(field_id: str, value: str) -> str:
    value = str(value)
    return f"{field_id}{len(value):02d}{value}"



def only_ascii(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ASCII", "ignore").decode("ASCII")
    return text.upper().strip()


def pix_safe_beneficiary_name(name: str) -> str:
    sanitized = only_ascii(name)
    if len(sanitized) <= 25:
        return sanitized
    parts = [p for p in sanitized.split() if p]
    for candidate in (
        " ".join(parts[:2]),
        f"{parts[0]} {parts[-1]}" if len(parts) >= 2 else sanitized,
        sanitized[:25],
    ):
        candidate = candidate.strip()
        if candidate and len(candidate) <= 25:
            return candidate
    return sanitized[:25].strip()


def pix_safe_city(city: str) -> str:
    return only_ascii(city)[:15].strip() or "ARACAJU"


def pix_safe_txid(txid: str | None) -> str:
    value = re.sub(r"[^A-Za-z0-9]", "", only_ascii(txid or ""))[:25]
    return value or "***"



def build_pix_payload(key: str, amount: Optional[float] = None, txid: str = "***") -> str:
    data = load_data()

    key = (key or "").strip()
    beneficiary = pix_safe_beneficiary_name(data["pix"].get("beneficiario") or MERCHANT_NAME)
    city = pix_safe_city(data["pix"].get("cidade") or MERCHANT_CITY)
    txid = pix_safe_txid(txid)

    gui = emv("00", "BR.GOV.BCB.PIX")
    key_field = emv("01", key)
    merchant_account = emv("26", gui + key_field)

    payload = ""
    payload += emv("00", "01")
    payload += emv("01", "11")
    payload += merchant_account
    payload += emv("52", "0000")
    payload += emv("53", "986")
    if amount is not None and amount > 0:
        payload += emv("54", f"{amount:.2f}")
    payload += emv("58", "BR")
    payload += emv("59", beneficiary)
    payload += emv("60", city)
    payload += emv("62", emv("05", txid))
    payload_with_crc = payload + "6304"
    payload_with_crc += crc16(payload_with_crc)
    return payload_with_crc



def build_qr_file(payload: str) -> discord.File:
    qr = qrcode.QRCode(version=None, box_size=10, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(buffer, filename="pix_qrcode.png")



def build_pix_embed(product_name: Optional[str] = None, amount_text: Optional[str] = None, member: Optional[discord.Member] = None, extra_percent: Optional[float] = None, pix_discount_percent: Optional[float] = None) -> tuple[discord.Embed, discord.File, str]:
    data = load_data()
    key = data["pix"].get("chave", "")
    final_text = amount_text
    if amount_text:
        comp = get_price_components(amount_text, member, extra_percent=extra_percent, pix_discount_percent=pix_discount_percent)
        final_text = format_money(comp["final"])
    amount = money_to_float(final_text) if final_text else None
    payload = build_pix_payload(key, amount=amount, txid="***")
    qr_file = build_qr_file(payload)

    desc = [
        "Escaneie o QR Code ou use os botões para copiar a chave e o Pix copia e cola.",
        f"**Tipo:** {data['pix'].get('tipo', 'aleatoria').title()}",
        f"**Chave:** `{key}`",
    ]
    if product_name:
        desc.append(f"**Produto:** {product_name}")
    if amount_text:
        desc.append(f"**Valor base:** {amount_text}")
    if final_text and final_text != amount_text:
        desc.append(f"**Valor final no Pix:** {final_text}")
    elif final_text:
        desc.append(f"**Valor:** {final_text}")

    desc.append("\nOs dados internos do recebedor continuam no QR para o Pix funcionar, mas não ficam expostos na mensagem.")

    embed = base_embed("💳 Pagamento via Pix", "\n".join(desc), discord.Color.gold())
    embed.set_image(url="attachment://pix_qrcode.png")
    return embed, qr_file, payload



# =========================
# LOG / ENTREGA
# =========================
async def send_log(guild: discord.Guild, title: str, buyer=None, product_name: str = "", price: str = "", ticket_channel=None, extra: str = ""):
    channel = guild.get_channel(CANAL_LOGS_ID)
    if not isinstance(channel, discord.TextChannel):
        return

    embed = discord.Embed(title=title, color=discord.Color.blurple())
    if buyer:
        embed.add_field(name="👤 Cliente", value=buyer.mention, inline=False)
    if product_name:
        embed.add_field(name="📦 Produto", value=product_name, inline=False)
    if price:
        embed.add_field(name="💰 Valor", value=price, inline=False)
    if ticket_channel:
        embed.add_field(name="🎫 Ticket", value=ticket_channel.mention, inline=False)
    if extra:
        embed.add_field(name="📌 Extra", value=extra[:1024], inline=False)
    await channel.send(embed=embed)


async def deliver_product(guild: discord.Guild, buyer: Optional[discord.Member], channel: Optional[discord.TextChannel], product_name: str, manual_content: Optional[str] = None):
    _, _, product = find_product(product_name)

    if channel:
        state = get_ticket_state(channel.id)
        if state.get("delivered"):
            return False, "Esse ticket já teve entrega registrada. Anti-entrega duplicada ativo."
    else:
        state = {}

    if product:
        content = manual_content.strip() if manual_content else pop_stock(product["estoque_arquivo"])
        if not content:
            return False, "Sem estoque automático. Use /entrega_manual ou o botão de entrega manual."
        price_text = state.get("amount_text") or product.get("preco", "")
    else:
        if not manual_content:
            return False, "Esse produto não existe na loja. Defina um produto livre no ticket e faça a entrega manual."
        content = manual_content.strip()
        price_text = state.get("amount_text", "")

    embed = base_embed(
        f"📦 Entrega — {product_name}",
        f"**Seu item foi liberado com sucesso.**\n\n```\n{content}\n```",
        discord.Color(COR_SUCESSO),
    )

    dm_ok = False
    if buyer:
        try:
            await buyer.send(embed=embed)
            dm_ok = True
        except discord.Forbidden:
            dm_ok = False

    if channel:
        set_ticket_state(channel.id, {"delivered": True, "delivered_at": iso_now(), "delivery_mode": "manual" if manual_content else "automatic"})
        await channel.send(embed=embed)
        if buyer:
            await channel.send(f"✅ Entrega registrada para {buyer.mention}.")

    await send_log(
        guild,
        title="📬 Entrega realizada",
        buyer=buyer,
        product_name=product_name,
        price=price_text,
        ticket_channel=channel,
        extra=f"DM enviada: {'sim' if dm_ok else 'não'} | Modo: {'manual' if manual_content else 'automático'} | Anti-duplicada: ativo",
    )
    return True, "Entrega concluída com sucesso."


# =========================
# VIEWS
# =========================

class TicketCloseModal(discord.ui.Modal, title="Fechar ticket"):
    motivo = discord.ui.TextInput(label="Motivo do fechamento", required=False, max_length=200, placeholder="Ex: pedido concluído, cancelado, sem resposta...")

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Use dentro de um ticket.", ephemeral=True)
            return
        await interaction.response.send_message("Fechando ticket...", ephemeral=True)
        await close_ticket_flow(interaction.channel, interaction.user if isinstance(interaction.user, discord.Member) else None, str(self.motivo or "").strip())


class ManualDeliveryModal(discord.ui.Modal, title="Entrega manual"):
    conteudo = discord.ui.TextInput(label="Conteúdo da entrega", style=discord.TextStyle.paragraph, required=True, max_length=2000, placeholder="Login, senha, código, instruções...")

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Use em um ticket.", ephemeral=True)
            return
        buyer_id = parse_buyer_id(interaction.channel)
        buyer = interaction.guild.get_member(buyer_id) if interaction.guild and buyer_id else None
        product_name = parse_product_name(interaction.channel)
        if not product_name:
            await interaction.response.send_message("Não achei o produto do ticket.", ephemeral=True)
            return
        ok, msg = await deliver_product(interaction.guild, buyer, interaction.channel, product_name, manual_content=str(self.conteudo))
        await interaction.response.send_message(msg, ephemeral=True)


async def close_ticket_flow(channel: discord.TextChannel, closer: Optional[discord.Member], reason: str = ""):
    state = get_ticket_state(channel.id)
    transcript_path = await create_ticket_transcript(channel)
    guild = channel.guild
    buyer_id = parse_buyer_id(channel)
    buyer = guild.get_member(buyer_id) if buyer_id else None
    elapsed = get_ticket_elapsed_text(state)
    if reason:
        set_ticket_state(channel.id, {"close_reason": reason})
    log_channel = guild.get_channel(CANAL_LOGS_ID)
    if isinstance(log_channel, discord.TextChannel):
        file = discord.File(transcript_path, filename=transcript_path.name)
        embed = base_embed(
            "🧾 Transcript de ticket",
            f"**Canal:** {channel.name}\n**Tipo:** {state.get('ticket_type', parse_ticket_type(channel)).upper()}\n**Tempo total:** {elapsed}\n**Motivo:** {reason or 'Não informado'}\n**Fechado por:** {closer.mention if closer else 'Sistema'}",
            discord.Color(COR_INFO),
        )
        await log_channel.send(embed=embed, file=file)
    await send_log(guild, "🔒 Ticket fechado", buyer=buyer, product_name=parse_product_name(channel) or "", ticket_channel=channel, extra=f"Tempo: {elapsed} | Motivo: {reason or 'Não informado'}")
    delete_ticket_state(channel.id)
    await asyncio.sleep(1)
    await channel.delete()


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fechar", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="twx_close_ticket_v7")
    async def close_ticket(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Esse botão só funciona em ticket.", ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
            await interaction.response.send_message("Só a equipe pode fechar ticket.", ephemeral=True)
            return
        await interaction.response.send_modal(TicketCloseModal())


class PixActionsView(discord.ui.View):
    def __init__(self, product_name: str, amount_text: Optional[str], payload: str, key: str):
        super().__init__(timeout=600)
        self.product_name = product_name
        self.amount_text = amount_text
        self.payload = payload
        self.key = key

    @discord.ui.button(label="Copiar chave", style=discord.ButtonStyle.secondary, emoji="🔑")
    async def copy_key(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_message(f"**Chave Pix:**\n```{self.key}```", ephemeral=True)

    @discord.ui.button(label="Copiar Pix", style=discord.ButtonStyle.secondary, emoji="📋")
    async def copy_payload(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.send_message(f"**Pix Copia e Cola:**\n```{self.payload}```", ephemeral=True)

    @discord.ui.button(label="Marcar pendente", style=discord.ButtonStyle.primary, emoji="⏳")
    async def mark_pending(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Use em ticket.", ephemeral=True)
            return
        state = set_ticket_state(interaction.channel.id, {"payment_status": "pending"})
        await interaction.response.send_message(embed=base_embed("⏳ Pagamento pendente", load_data()["payment"].get("message_pending", "Pagamento pendente."), discord.Color(COR_ALERTA)))
        buyer_id = parse_buyer_id(interaction.channel)
        buyer = interaction.guild.get_member(buyer_id) if interaction.guild and buyer_id else None
        await send_log(interaction.guild, "⏳ Pagamento pendente", buyer=buyer, product_name=self.product_name, price=state.get("amount_text", self.amount_text or ""), ticket_channel=interaction.channel)


class TicketActionView(discord.ui.View):
    def __init__(self, buyer_id: int, product_name: str):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id
        self.product_name = product_name

    @discord.ui.button(label="Enviar Pix", style=discord.ButtonStyle.secondary, emoji="💳", custom_id="twx_send_pix_v7")
    async def send_pix(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Use em ticket.", ephemeral=True)
            return
        state = get_ticket_state(interaction.channel.id)
        amount_text = state.get("amount_text")
        if not amount_text:
            _, _, product = find_product(self.product_name)
            amount_text = product.get("preco") if product else None
        buyer = interaction.guild.get_member(self.buyer_id) if interaction.guild else None
        embed, qr_file, payload = build_pix_embed(self.product_name, amount_text, buyer, extra_percent=state.get("extra_percent"), pix_discount_percent=state.get("pix_discount_percent"))
        key = load_data()["pix"].get("chave", "")
        set_ticket_state(interaction.channel.id, {"payment_status": "pending"})
        await interaction.response.send_message(embed=embed, file=qr_file, view=PixActionsView(self.product_name, amount_text, payload, key))

    @discord.ui.button(label="Confirmar Pagamento", style=discord.ButtonStyle.success, emoji="✅", custom_id="twx_confirm_payment_v7")
    async def confirm_payment(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
            await interaction.response.send_message("Só a equipe pode confirmar pagamento.", ephemeral=True)
            return
        guild = interaction.guild
        if guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Erro ao validar o ticket.", ephemeral=True)
            return

        state = get_ticket_state(interaction.channel.id)
        deadline = parse_iso(state.get("payment_deadline"))
        if deadline and datetime.utcnow() > deadline:
            await interaction.response.send_message("Esse pagamento já expirou. Use /ticket_valor para reabrir um novo prazo.", ephemeral=True)
            return

        _, _, product = find_product(self.product_name)
        buyer = guild.get_member(self.buyer_id)

        client_role = guild.get_role(CARGO_CLIENTE_ID)
        if buyer and client_role:
            try:
                await buyer.add_roles(client_role, reason="Compra confirmada")
            except discord.Forbidden:
                pass

        amount_text = state.get("amount_text") or (product.get("preco") if product else "")
        set_ticket_state(interaction.channel.id, {"payment_status": "approved", "approved_by": interaction.user.id, "approved_at": iso_now()})
        await interaction.response.send_message(embed=base_embed(
            "✅ Pagamento confirmado",
            load_data()["payment"].get("message_approved", "Pagamento aprovado com sucesso."),
            discord.Color(COR_SUCESSO),
        ))

        if buyer:
            register_sale(buyer.id, self.product_name, amount_text)
            promo = try_promote_vip(guild, buyer)
            if promo:
                await promo
        await send_log(guild, "🛒 Compra confirmada", buyer, self.product_name, amount_text, interaction.channel, extra=f"Aprovado por: {interaction.user.mention}")
        ok, msg = await deliver_product(guild, buyer, interaction.channel, self.product_name)
        if not ok:
            await interaction.channel.send(f"⚠️ {msg}")

    @discord.ui.button(label="Entrega manual", style=discord.ButtonStyle.primary, emoji="📦", custom_id="twx_manual_delivery_v7")
    async def manual_delivery(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
            await interaction.response.send_message("Só a equipe pode usar isso.", ephemeral=True)
            return
        await interaction.response.send_modal(ManualDeliveryModal())


class ProductSelect(discord.ui.Select):
    def __init__(self, category_id: str):
        self.category_id = category_id
        data = load_data()
        category = data["categorias"][category_id]

        options = []
        for product in category["produtos"][:25]:
            estoque = stock_count(product["estoque_arquivo"])
            stock_text = f"Estoque {estoque}" if estoque > 0 else "Sob consulta"
            options.append(
                discord.SelectOption(
                    label=product["nome"][:100],
                    description=f"{product['preco']} • {stock_text}"[:100],
                    emoji=category["emoji"],
                    value=product["nome"],
                )
            )

        disabled = False
        if not options:
            options = [discord.SelectOption(label="Categoria sem produtos ainda", description="Adicione produtos nessa categoria primeiro", value="__empty__")]
            disabled = True

        super().__init__(
            placeholder="Selecione um produto para abrir ticket...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"twx_select_{category_id}_v8",
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(self.view, CategoryView):
            await interaction.response.send_message("Erro interno.", ephemeral=True)
            return
        if self.values[0] == "__empty__":
            await interaction.response.send_message("Essa categoria ainda não tem produtos cadastrados.", ephemeral=True)
            return
        await self.view.create_ticket(interaction, self.category_id, self.values[0])


class CategoryView(discord.ui.View):
    def __init__(self, category_id: str):
        super().__init__(timeout=None)
        self.category_id = category_id
        self.add_item(ProductSelect(category_id))

    async def create_ticket(self, interaction: discord.Interaction, category_id: str, product_name: str):
        guild = interaction.guild
        user = interaction.user

        if guild is None or not isinstance(user, discord.Member):
            await interaction.response.send_message("Erro ao criar ticket.", ephemeral=True)
            return

        data = load_data()
        if is_blacklisted(user.id):
            entry = get_blacklist_entry(user.id) or {}
            await interaction.response.send_message(f"Você não pode abrir compra agora. Motivo: {entry.get('reason', 'Bloqueado.')}", ephemeral=True)
            return
        if data["painel"].get("status") != "online":
            await interaction.response.send_message("A loja está offline agora.", ephemeral=True)
            return

        ticket_category = guild.get_channel(CATEGORY_TICKETS_ID)
        if not isinstance(ticket_category, discord.CategoryChannel):
            await interaction.response.send_message("Categoria de tickets não encontrada.", ephemeral=True)
            return

        for channel in ticket_category.text_channels:
            if channel.topic and f"comprador:{user.id}" in channel.topic:
                await interaction.response.send_message(f"Você já tem um ticket aberto: {channel.mention}", ephemeral=True)
                return

        _, category, product = find_product(product_name)
        if not category or not product:
            await interaction.response.send_message("Produto não encontrado.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True)
        admin_role = guild.get_role(CARGO_ADMIN_ID)
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel_name = f"ticket-{slugify(product_name)}-{slugify(user.name)}"[:90]
        ticket = await guild.create_text_channel(
            name=channel_name,
            category=ticket_category,
            overwrites=overwrites,
            topic=f"comprador:{user.id} | tipo:compra | produto:{product_name}",
        )

        estoque = product_display_stock(product)
        stock_line = f"{estoque} unidade(s)" if estoque > 0 else "sob consulta"
        embed = base_embed(
            f"{category['emoji']} {product['nome']}",
            (
                f"**Descrição:** {product['descricao']}\n"
                f"**Preço:** {product['preco']}\n"
                f"**Estoque:** {stock_line}\n\n"
                "Use o botão **Enviar Pix** para receber o QR Code do pagamento."
            ),
            get_color(category.get("cor")),
        )
        if category.get("banner_url"):
            embed.set_image(url=category["banner_url"])

        price_info = get_price_components(product["preco"], user)
        deadline = datetime.utcnow() + timedelta(minutes=int(data.get("payment", {}).get("default_deadline_minutes", 20) or 20))
        set_ticket_state(ticket.id, {
            "ticket_type": "compra",
            "created_at": iso_now(),
            "priority": "normal",
            "assigned_staff_id": 0,
            "payment_status": "pending",
            "payment_deadline": deadline.isoformat(),
            "amount_text": format_money(price_info["final"]),
            "base_amount_text": product["preco"],
            "extra_percent": data.get("payment", {}).get("tax_percent", 0.0),
            "pix_discount_percent": data.get("payment", {}).get("pix_discount_percent", 0.0),
            "delivered": False,
        })
        register_user_ticket(user.id)

        await ticket.send(content=user.mention, embed=embed, view=TicketActionView(user.id, product["nome"]))
        await ticket.send(view=CloseTicketView())

        await send_log(guild, "🧾 Ticket criado", user, product["nome"], format_money(price_info["final"]), ticket, extra=f"Prazo Pix até: {deadline.strftime('%H:%M')}")
        await interaction.response.send_message(f"Ticket criado com sucesso: {ticket.mention}", ephemeral=True)




class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        data = load_data()
        options = []
        for ticket_id, info in data.get("service_tickets", {}).items():
            options.append(
                discord.SelectOption(
                    label=info.get("nome", ticket_id).title()[:100],
                    description=info.get("descricao", "Abrir atendimento.")[:100],
                    emoji=info.get("emoji", "🎫"),
                    value=ticket_id,
                )
            )
        super().__init__(
            placeholder="Selecione o tipo de ticket...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="twx_service_ticket_select_v7",
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(self.view, TicketHubView):
            await interaction.response.send_message("Erro interno.", ephemeral=True)
            return
        await self.view.create_service_ticket(interaction, self.values[0])


class TicketHubView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

    async def create_service_ticket(self, interaction: discord.Interaction, ticket_type: str):
        guild = interaction.guild
        user = interaction.user
        if guild is None or not isinstance(user, discord.Member):
            await interaction.response.send_message("Erro ao criar ticket.", ephemeral=True)
            return
        if is_blacklisted(user.id):
            entry = get_blacklist_entry(user.id) or {}
            await interaction.response.send_message(f"Você não pode abrir ticket agora. Motivo: {entry.get('reason', 'Bloqueado.')}", ephemeral=True)
            return

        ticket_category = guild.get_channel(CATEGORY_TICKETS_ID)
        if not isinstance(ticket_category, discord.CategoryChannel):
            await interaction.response.send_message("Categoria de tickets não encontrada.", ephemeral=True)
            return

        for channel in ticket_category.text_channels:
            if channel.topic and f"comprador:{user.id}" in channel.topic and f"tipo:{ticket_type}" in channel.topic:
                await interaction.response.send_message(f"Você já possui um ticket desse tipo: {channel.mention}", ephemeral=True)
                return

        info = load_data().get("service_tickets", {}).get(ticket_type, {})
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True)
        admin_role = guild.get_role(CARGO_ADMIN_ID)
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        ticket = await guild.create_text_channel(
            name=f"ticket-{ticket_type}-{slugify(user.name)}"[:90],
            category=ticket_category,
            overwrites=overwrites,
            topic=f"comprador:{user.id} | tipo:{ticket_type} | produto:{info.get('nome', ticket_type)}",
        )

        deadline = datetime.utcnow() + timedelta(minutes=int(load_data().get("payment", {}).get("default_deadline_minutes", 20) or 20))
        set_ticket_state(ticket.id, {
            "ticket_type": ticket_type,
            "created_at": iso_now(),
            "priority": "normal",
            "assigned_staff_id": 0,
            "payment_status": "none",
            "payment_deadline": deadline.isoformat(),
            "amount_text": "",
            "extra_percent": load_data().get("payment", {}).get("tax_percent", 0.0),
            "pix_discount_percent": load_data().get("payment", {}).get("pix_discount_percent", 0.0),
            "delivered": False,
        })
        register_user_ticket(user.id)

        desc = info.get("descricao", "Atendimento aberto.") + "\\n\\n"
        desc += "**Tipo:** " + info.get("nome", ticket_type)
        desc += "\\n**Prioridade:** normal"
        if ticket_type == "calc":
            desc += "\\n\\nEnvie o item e a quantidade. Depois a equipe pode usar `/ticket_valor` para gerar o valor Pix."
        elif ticket_type == "refund":
            desc += "\\n\\nExplique o motivo do reembolso e envie provas, se necessário."
        elif ticket_type == "partnership":
            desc += "\\n\\nEnvie sua proposta de parceria com detalhes."
        else:
            desc += "\\n\\nExplique seu pedido para a equipe."

        await ticket.send(content=user.mention, embed=base_embed(f"{info.get('emoji','🎫')} {info.get('nome', ticket_type)}", desc, discord.Color(COR_INFO)))
        await ticket.send(view=CloseTicketView())
        await send_log(guild, "🎫 Ticket de serviço criado", user, info.get("nome", ticket_type), "", ticket, extra=f"Tipo: {ticket_type}")
        await interaction.response.send_message(f"Ticket criado: {ticket.mention}", ephemeral=True)

class CalcTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir ticket de cálculo", style=discord.ButtonStyle.primary, emoji="🧮", custom_id="twx_calc_ticket_v5")
    async def open_calc_ticket(self, interaction: discord.Interaction, _: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        if guild is None or not isinstance(user, discord.Member):
            await interaction.response.send_message("Erro ao criar ticket.", ephemeral=True)
            return

        ticket_category = guild.get_channel(CATEGORY_TICKETS_ID)
        if not isinstance(ticket_category, discord.CategoryChannel):
            await interaction.response.send_message("Categoria de tickets não encontrada.", ephemeral=True)
            return

        for channel in ticket_category.text_channels:
            if channel.topic and f"comprador:{user.id}" in channel.topic and "produto:CÁLCULO PERSONALIZADO" in channel.topic:
                await interaction.response.send_message(f"Você já possui um ticket de cálculo: {channel.mention}", ephemeral=True)
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if guild.me:
            overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True)
        admin_role = guild.get_role(CARGO_ADMIN_ID)
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        ticket = await guild.create_text_channel(
            name=f"ticket-calc-{slugify(user.name)}"[:90],
            category=ticket_category,
            overwrites=overwrites,
            topic=f"comprador:{user.id} | tipo:calc | produto:CÁLCULO PERSONALIZADO",
        )

        embed = base_embed(
            "🧮 Cálculo personalizado",
            "Envie aqui o item, quantidade e detalhes para a equipe calcular o valor.",
            discord.Color(COR_ALERTA),
        )
        deadline = datetime.utcnow() + timedelta(minutes=int(load_data().get("payment", {}).get("default_deadline_minutes", 20) or 20))
        set_ticket_state(ticket.id, {
            "ticket_type": "calc",
            "created_at": iso_now(),
            "priority": "normal",
            "assigned_staff_id": 0,
            "payment_status": "none",
            "payment_deadline": deadline.isoformat(),
            "amount_text": "",
            "extra_percent": load_data().get("payment", {}).get("tax_percent", 0.0),
            "pix_discount_percent": load_data().get("payment", {}).get("pix_discount_percent", 0.0),
            "delivered": False,
        })
        register_user_ticket(user.id)
        await ticket.send(content=user.mention, embed=embed)
        await ticket.send(view=CloseTicketView())
        await send_log(guild, "📐 Ticket de cálculo criado", user, "CÁLCULO PERSONALIZADO", "A definir", ticket)
        await interaction.response.send_message(f"Ticket criado: {ticket.mention}", ephemeral=True)


class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id: str, prize: str, winner_count: int = 1, required_role_id: Optional[int] = None):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        self.prize = prize
        self.winner_count = max(1, int(winner_count))
        self.required_role_id = required_role_id
        self.participants: set[int] = set()
        self.message: Optional[discord.Message] = None
        self.ended = False

    def winners_text(self, guild: Optional[discord.Guild], winner_ids: list[int]) -> str:
        mentions = []
        for uid in winner_ids:
            member = guild.get_member(uid) if guild else None
            mentions.append(member.mention if member else f"<@{uid}>")
        return ", ".join(mentions) if mentions else "Sem vencedores"

    async def finish(self, channel: discord.TextChannel):
        if self.ended:
            return []
        self.ended = True
        winner_ids = random.sample(list(self.participants), k=min(self.winner_count, len(self.participants))) if self.participants else []
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass
        if winner_ids:
            desc = f"**Prêmio:** {self.prize}\n**Vencedores:** {self.winners_text(channel.guild, winner_ids)}\n**Participantes:** {len(self.participants)}"
            await channel.send(embed=base_embed("🏆 Sorteio encerrado", desc, discord.Color(COR_SUCESSO)))
        else:
            await channel.send(embed=base_embed("⚠️ Sorteio encerrado", f"Nenhum participante entrou no sorteio de **{self.prize}**.", discord.Color(COR_ALERTA)))
        return winner_ids

    @discord.ui.button(label="Participar", style=discord.ButtonStyle.success, emoji="🎉")
    async def participate(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.ended:
            await interaction.response.send_message("Esse sorteio já foi encerrado.", ephemeral=True)
            return
        if is_blacklisted(interaction.user.id):
            await interaction.response.send_message("Você não pode participar deste sorteio.", ephemeral=True)
            return
        if self.required_role_id and isinstance(interaction.user, discord.Member):
            if not any(role.id == self.required_role_id for role in interaction.user.roles):
                await interaction.response.send_message("Você não tem o cargo necessário para participar.", ephemeral=True)
                return
        if interaction.user.id in self.participants:
            await interaction.response.send_message("Você já está participando.", ephemeral=True)
            return
        self.participants.add(interaction.user.id)
        await interaction.response.send_message("Você entrou no sorteio com sucesso.", ephemeral=True)


# =========================
# PAINEL
# =========================
async def send_panel(guild: discord.Guild, clear_channel: bool = False):
    data = load_data()
    panel = data["painel"]
    panel_channel = guild.get_channel(CANAL_PAINEL_ID)
    if not isinstance(panel_channel, discord.TextChannel):
        raise ValueError("Canal do painel não encontrado.")

    if clear_channel:
        try:
            await panel_channel.purge(limit=100)
        except discord.Forbidden:
            pass

    if panel.get("status") == "offline":
        offline_embed = base_embed(
            "🔴 LOJA OFFLINE",
            f"**{panel['titulo']}**\n{panel.get('mensagem_offline', 'Loja offline.')}",
            discord.Color(COR_ERRO),
        )
        if panel.get("banner_offline_url"):
            offline_embed.set_image(url=panel["banner_offline_url"])
        elif panel.get("banner_online_url"):
            offline_embed.set_image(url=panel["banner_online_url"])
        await panel_channel.send(embed=offline_embed)
        return

    resumo = []
    if panel.get("mostrar_resumo_estoque", True):
        total_produtos = 0
        total_stock = 0
        for category in data["categorias"].values():
            total_produtos += len(category["produtos"])
            for p in category["produtos"]:
                total_stock += product_display_stock(p)
        resumo.append(f"**Categorias:** {len(data['categorias'])}")
        resumo.append(f"**Produtos:** {total_produtos}")
        resumo.append(f"**Estoque total:** {total_stock}")

    top_desc = [f"**{panel['titulo']}**", panel.get("mensagem_boas_vindas", "")] + resumo
    top_embed = base_embed("🟢 LOJA ONLINE", "\n".join([x for x in top_desc if x]), get_color(panel.get("cor")))
    if panel.get("banner_online_url"):
        top_embed.set_image(url=panel["banner_online_url"])
    await panel_channel.send(embed=top_embed)

    for category_id, category in data["categorias"].items():
        estoque_total = sum(product_display_stock(p) for p in category["produtos"])
        category_embed = base_embed(
            f"{category['emoji']} {category['nome']}",
            f"{category['descricao']}\n\n**Produtos:** {len(category['produtos'])}\n**Estoque da categoria:** {estoque_total}",
            get_color(category.get("cor")),
        )
        if category.get("banner_url"):
            category_embed.set_image(url=category["banner_url"])
        await panel_channel.send(embed=category_embed, view=CategoryView(category_id))

    service_embed = base_embed(
        "🎫 Central de tickets",
        "Abra por menu: suporte, cálculo, reembolso ou parceria.\nA equipe pode assumir, priorizar, avaliar e fechar com transcript.",
        discord.Color(COR_INFO),
    )
    await panel_channel.send(embed=service_embed, view=TicketHubView())

    if panel.get("mostrar_calc_no_painel", True):
        calc_embed = base_embed(
            "🎟️ Cálculo rápido",
            "Se quiser ir direto para orçamento personalizado, use o botão abaixo.",
            discord.Color(COR_ALERTA),
        )
        await panel_channel.send(embed=calc_embed, view=CalcTicketView())




@tasks.loop(minutes=1)
async def payment_expiry_loop():
    await bot.wait_until_ready()
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return
    category = guild.get_channel(CATEGORY_TICKETS_ID)
    if not isinstance(category, discord.CategoryChannel):
        return
    data = load_data()
    expired_message = data.get("payment", {}).get("message_expired", "Pagamento expirado.")
    for channel in list(category.text_channels):
        state = get_ticket_state(channel.id)
        if not state:
            continue
        if state.get("payment_status") == "approved":
            continue
        deadline = parse_iso(state.get("payment_deadline"))
        if not deadline or datetime.utcnow() <= deadline:
            continue
        if state.get("expired_notified"):
            continue
        set_ticket_state(channel.id, {"payment_status": "expired", "expired_notified": True})
        try:
            await channel.send(embed=base_embed("⌛ Pagamento expirado", expired_message, discord.Color(COR_ERRO)))
        except Exception:
            continue


# =========================
# EVENTOS
# =========================
@bot.event
async def on_ready():
    data = load_data()
    for category_id in data["categorias"].keys():
        bot.add_view(CategoryView(category_id))
    bot.add_view(CalcTicketView())
    bot.add_view(TicketHubView())
    bot.add_view(CloseTicketView())
    bot.add_view(TicketActionView(0, "dummy"))

    try:
        if not payment_expiry_loop.is_running():
            payment_expiry_loop.start()
        synced = await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Bot online como {bot.user}")
        print(f"{len(synced)} comando(s) sincronizado(s).")
    except Exception as exc:
        print(f"Erro ao sincronizar comandos: {exc}")


# =========================
# COMANDOS - PAINEL / CONFIG
# =========================
@tree.command(name="painel", description="Envia ou atualiza o painel da loja", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(titulo="Título do painel", status="online ou offline", limpar_canal="Apagar mensagens antigas do canal")
async def painel(interaction: discord.Interaction, titulo: Optional[str] = None, status: Optional[str] = None, limpar_canal: bool = False):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    if titulo:
        data["painel"]["titulo"] = titulo
    if status:
        data["painel"]["status"] = status.strip().lower()
    save_data(data)
    await interaction.response.defer(ephemeral=True)
    await send_panel(interaction.guild, clear_channel=limpar_canal)
    await interaction.followup.send("Painel atualizado com sucesso.", ephemeral=True)


@tree.command(name="set_banner_online", description="Define o banner principal da loja online", guild=discord.Object(id=GUILD_ID))
async def set_banner_online(interaction: discord.Interaction, url: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    data["painel"]["banner_online_url"] = url
    save_data(data)
    await interaction.response.send_message("Banner online atualizado.", ephemeral=True)


@tree.command(name="set_logo", description="Define a logo pequena da loja", guild=discord.Object(id=GUILD_ID))
async def set_logo(interaction: discord.Interaction, url: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    data["painel"]["thumbnail_url"] = url
    save_data(data)
    await interaction.response.send_message("Logo atualizada.", ephemeral=True)


@tree.command(name="config_pix", description="Troca a chave Pix e dados do QR Code", guild=discord.Object(id=GUILD_ID))
async def config_pix(interaction: discord.Interaction, chave: str, tipo: str = "aleatoria", beneficiario: Optional[str] = None, cidade: Optional[str] = None):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    data["pix"]["chave"] = chave.strip()
    data["pix"]["tipo"] = tipo.strip().lower()
    if beneficiario:
        data["pix"]["beneficiario"] = beneficiario
    if cidade:
        data["pix"]["cidade"] = cidade
    save_data(data)
    await interaction.response.send_message("Configuração Pix atualizada.", ephemeral=True)


@tree.command(name="loja_on", description="Coloca a loja online", guild=discord.Object(id=GUILD_ID))
async def loja_on(interaction: discord.Interaction, limpar_canal: bool = True):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    data["painel"]["status"] = "online"
    save_data(data)
    await interaction.response.defer(ephemeral=True)
    await send_panel(interaction.guild, clear_channel=limpar_canal)
    await interaction.followup.send("Loja colocada como online.", ephemeral=True)


@tree.command(name="loja_off", description="Coloca a loja offline", guild=discord.Object(id=GUILD_ID))
async def loja_off(interaction: discord.Interaction, mensagem: str = "Loja offline no momento.", limpar_canal: bool = True):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    data["painel"]["status"] = "offline"
    data["painel"]["mensagem_offline"] = mensagem
    save_data(data)
    await interaction.response.defer(ephemeral=True)
    await send_panel(interaction.guild, clear_channel=limpar_canal)
    await interaction.followup.send("Loja colocada como offline.", ephemeral=True)


# =========================
# COMANDOS - CATEGORIAS / PRODUTOS / ESTOQUE
# =========================
@tree.command(name="categoria_add", description="Cria uma nova categoria", guild=discord.Object(id=GUILD_ID))
async def categoria_add(interaction: discord.Interaction, categoria_id: str, nome: str, emoji: str, descricao: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    categoria_id = slugify(categoria_id).replace("-", "_")
    if categoria_id in data["categorias"]:
        await interaction.response.send_message("Essa categoria já existe.", ephemeral=True)
        return
    data["categorias"][categoria_id] = {
        "nome": nome,
        "emoji": emoji,
        "descricao": descricao,
        "banner_url": "",
        "cor": COR_PADRAO,
        "produtos": [],
    }
    save_data(data)
    await interaction.response.send_message(f"Categoria `{categoria_id}` criada.", ephemeral=True)


@tree.command(name="categoria_banner", description="Define o banner de uma categoria", guild=discord.Object(id=GUILD_ID))
async def categoria_banner(interaction: discord.Interaction, categoria_id: str, url: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    if categoria_id not in data["categorias"]:
        await interaction.response.send_message("Categoria não encontrada.", ephemeral=True)
        return
    data["categorias"][categoria_id]["banner_url"] = url
    save_data(data)
    await interaction.response.send_message("Banner da categoria atualizado.", ephemeral=True)


@tree.command(name="produto_add", description="Adiciona produto em uma categoria", guild=discord.Object(id=GUILD_ID))
async def produto_add(interaction: discord.Interaction, categoria_id: str, nome: str, preco: str, descricao: str, estoque_arquivo: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    if categoria_id not in data["categorias"]:
        await interaction.response.send_message("Categoria não encontrada.", ephemeral=True)
        return
    data["categorias"][categoria_id]["produtos"].append({
        "nome": nome,
        "preco": preco,
        "descricao": descricao,
        "estoque_arquivo": estoque_arquivo,
        "stock_quantity": 0,
    })
    save_data(data)
    await interaction.response.send_message(f"Produto `{nome}` adicionado.", ephemeral=True)


@tree.command(name="produto_editar", description="Edita um produto", guild=discord.Object(id=GUILD_ID))
async def produto_editar(interaction: discord.Interaction, nome_atual: str, novo_nome: Optional[str] = None, novo_preco: Optional[str] = None, nova_descricao: Optional[str] = None, novo_estoque_arquivo: Optional[str] = None, novo_stock: Optional[int] = None):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    for category in data["categorias"].values():
        for product in category["produtos"]:
            if product["nome"].casefold() == nome_atual.casefold():
                if novo_nome:
                    product["nome"] = novo_nome
                if novo_preco:
                    product["preco"] = novo_preco
                if nova_descricao:
                    product["descricao"] = nova_descricao
                if novo_estoque_arquivo:
                    product["estoque_arquivo"] = novo_estoque_arquivo
                if novo_stock is not None:
                    product["stock_quantity"] = max(0, int(novo_stock))
                save_data(data)
                await interaction.response.send_message("Produto atualizado.", ephemeral=True)
                return
    await interaction.response.send_message("Produto não encontrado.", ephemeral=True)


@tree.command(name="produto_remover", description="Remove produto", guild=discord.Object(id=GUILD_ID))
async def produto_remover(interaction: discord.Interaction, categoria_id: str, nome: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    if categoria_id not in data["categorias"]:
        await interaction.response.send_message("Categoria não encontrada.", ephemeral=True)
        return
    before = len(data["categorias"][categoria_id]["produtos"])
    data["categorias"][categoria_id]["produtos"] = [p for p in data["categorias"][categoria_id]["produtos"] if p["nome"].casefold() != nome.casefold()]
    save_data(data)
    if before == len(data["categorias"][categoria_id]["produtos"]):
        await interaction.response.send_message("Produto não encontrado.", ephemeral=True)
        return
    await interaction.response.send_message("Produto removido.", ephemeral=True)




@tree.command(name="estoque_set", description="Define o estoque manual do produto", guild=discord.Object(id=GUILD_ID))
async def estoque_set_cmd(interaction: discord.Interaction, produto: str, quantidade: app_commands.Range[int, 0, 999999] = 0):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    ok, nome, total = set_product_stock_quantity(produto, quantidade)
    if not ok:
        await interaction.response.send_message("Produto não encontrado.", ephemeral=True)
        return
    await interaction.response.send_message(
        f"Estoque manual de `{nome}` definido para **{quantidade}**. Total visível agora: **{total}**.",
        ephemeral=True,
    )


@tree.command(name="estoque_add_qtd", description="Adiciona quantidade ao estoque manual", guild=discord.Object(id=GUILD_ID))
async def estoque_add_qtd_cmd(interaction: discord.Interaction, produto: str, quantidade: app_commands.Range[int, 1, 999999]):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    ok, nome, total = add_product_stock_quantity(produto, quantidade)
    if not ok:
        await interaction.response.send_message("Produto não encontrado.", ephemeral=True)
        return
    await interaction.response.send_message(
        f"Adicionado **{quantidade}** ao estoque manual de `{nome}`. Total visível agora: **{total}**.",
        ephemeral=True,
    )


@tree.command(name="estoque_rem_qtd", description="Remove quantidade do estoque manual", guild=discord.Object(id=GUILD_ID))
async def estoque_rem_qtd_cmd(interaction: discord.Interaction, produto: str, quantidade: app_commands.Range[int, 1, 999999]):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    ok, nome, total = remove_product_stock_quantity(produto, quantidade)
    if not ok:
        await interaction.response.send_message("Produto não encontrado.", ephemeral=True)
        return
    await interaction.response.send_message(
        f"Removido **{quantidade}** do estoque manual de `{nome}`. Total visível agora: **{total}**.",
        ephemeral=True,
    )

@tree.command(name="estoque_add", description="Adiciona linhas ao estoque", guild=discord.Object(id=GUILD_ID))
async def estoque_add_cmd(interaction: discord.Interaction, produto: str, conteudo: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    _, _, product = find_product(produto)
    if not product:
        await interaction.response.send_message("Produto não encontrado.", ephemeral=True)
        return
    lines = [line for line in conteudo.split("|") if line.strip()]
    qtd = add_stock(product["estoque_arquivo"], lines)
    await interaction.response.send_message(f"{qtd} item(ns) adicionados ao estoque.", ephemeral=True)


@tree.command(name="estoque_ver", description="Mostra o estoque do produto", guild=discord.Object(id=GUILD_ID))
async def estoque_ver(interaction: discord.Interaction, produto: str):
    _, _, product = find_product(produto)
    if not product:
        await interaction.response.send_message("Produto não encontrado.", ephemeral=True)
        return
    linhas = stock_count(product.get("estoque_arquivo", ""))
    manual = int(product.get("stock_quantity", 0) or 0)
    total = product_display_stock(product)
    texto = (
        f"**Produto:** `{product['nome']}`\n"
        f"**Estoque por linhas:** **{linhas}**\n"
        f"**Estoque manual:** **{manual}**\n"
        f"**Total visível:** **{total}**"
    )
    await interaction.response.send_message(embed=base_embed("📦 Estoque do produto", texto, discord.Color(COR_INFO)), ephemeral=True)


@tree.command(name="produtos", description="Lista produtos da loja", guild=discord.Object(id=GUILD_ID))
async def produtos(interaction: discord.Interaction):
    data = load_data()
    parts = []
    for category in data["categorias"].values():
        lines = [f"**{category['emoji']} {category['nome']}**"]
        if not category["produtos"]:
            lines.append("Sem produtos.")
        else:
            for product in category["produtos"][:20]:
                lines.append(f"• {product['nome']} — {product['preco']} — estoque {product_display_stock(product)}")
        parts.append("\n".join(lines))
    await interaction.response.send_message(embed=base_embed("📦 Produtos cadastrados", "\n\n".join(parts)[:4000], discord.Color(COR_INFO)), ephemeral=True)


# =========================
# COMANDOS - TICKETS / PIX / ENTREGA
# =========================
@tree.command(name="pix", description="Envia o Pix com QR Code", guild=discord.Object(id=GUILD_ID))
async def pix(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=not isinstance(interaction.channel, discord.TextChannel))

        product_name = None
        amount_text = None
        member = interaction.user if isinstance(interaction.user, discord.Member) else None

        if isinstance(interaction.channel, discord.TextChannel):
            product_name = parse_product_name(interaction.channel)
            _, _, product = find_product(product_name or "")
            if product:
                state = get_ticket_state(interaction.channel.id)
                custom_value = state.get("custom_value")
                amount_text = custom_value or product.get("preco")
            else:
                state = get_ticket_state(interaction.channel.id)
                amount_text = state.get("custom_value")

        embed, qr_file, payload = build_pix_embed(product_name, amount_text, member=member)

        data = load_data()
        key = data["pix"].get("chave", "")
        view = PixActionsView(product_name or "compra", amount_text, payload, key)

        await interaction.followup.send(
            embed=embed,
            file=qr_file,
            view=view,
            ephemeral=not isinstance(interaction.channel, discord.TextChannel),
        )
    except Exception as e:
        print(f"Erro no /pix: {e}")
        try:
            await interaction.followup.send(f"❌ Erro ao gerar Pix: `{e}`", ephemeral=True)
        except Exception:
            pass


@tree.command(name="entrega_manual", description="Envia a entrega manualmente", guild=discord.Object(id=GUILD_ID))
async def entrega_manual(interaction: discord.Interaction, mensagem: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use dentro do ticket.", ephemeral=True)
        return
    buyer_id = parse_buyer_id(interaction.channel)
    product_name = parse_product_name(interaction.channel)
    buyer = interaction.guild.get_member(buyer_id) if interaction.guild and buyer_id else None
    if not product_name:
        await interaction.response.send_message("Produto do ticket não encontrado.", ephemeral=True)
        return
    ok, msg = await deliver_product(interaction.guild, buyer, interaction.channel, product_name, manual_content=mensagem)
    await interaction.response.send_message(msg, ephemeral=True)


@tree.command(name="entrega_auto", description="Tenta a entrega automática novamente", guild=discord.Object(id=GUILD_ID))
async def entrega_auto(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use dentro do ticket.", ephemeral=True)
        return
    buyer_id = parse_buyer_id(interaction.channel)
    product_name = parse_product_name(interaction.channel)
    buyer = interaction.guild.get_member(buyer_id) if interaction.guild and buyer_id else None
    if not product_name:
        await interaction.response.send_message("Produto do ticket não encontrado.", ephemeral=True)
        return
    ok, msg = await deliver_product(interaction.guild, buyer, interaction.channel, product_name)
    await interaction.response.send_message(msg, ephemeral=True)


@tree.command(name="ticket_renomear", description="Renomeia o ticket", guild=discord.Object(id=GUILD_ID))
async def ticket_renomear(interaction: discord.Interaction, novo_nome: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use em um ticket.", ephemeral=True)
        return
    await interaction.channel.edit(name=slugify(novo_nome))
    await interaction.response.send_message("Ticket renomeado.", ephemeral=True)


@tree.command(name="ticket_produto", description="Troca o produto vinculado ao ticket", guild=discord.Object(id=GUILD_ID))
async def ticket_produto(interaction: discord.Interaction, produto: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use em um ticket.", ephemeral=True)
        return
    buyer_id = parse_buyer_id(interaction.channel)
    _, category, product = find_product(produto)
    if not category or not product:
        await interaction.response.send_message("Produto não encontrado.", ephemeral=True)
        return
    await interaction.channel.edit(topic=f"comprador:{buyer_id} | produto:{product['nome']}")
    embed = base_embed(
        f"{category['emoji']} Produto atualizado",
        f"**Produto:** {product['nome']}\n**Preço:** {product['preco']}\n**Descrição:** {product['descricao']}",
        get_color(category.get("cor")),
    )
    await interaction.channel.send(embed=embed, view=TicketActionView(buyer_id or 0, product["nome"]))
    await interaction.response.send_message("Produto do ticket atualizado.", ephemeral=True)


@tree.command(name="ticket_produto_livre", description="Define um produto manual em ticket de cálculo ou compra", guild=discord.Object(id=GUILD_ID))
async def ticket_produto_livre(interaction: discord.Interaction, nome: str, valor: Optional[str] = None, descricao: Optional[str] = None, prazo_minutos: Optional[int] = None):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use em um ticket.", ephemeral=True)
        return

    buyer_id = parse_buyer_id(interaction.channel)
    ticket_type = parse_ticket_type(interaction.channel)
    novo_topico = f"comprador:{buyer_id} | tipo:{ticket_type} | produto:{nome}"
    await interaction.channel.edit(topic=novo_topico)

    payload = {"custom_product": True, "custom_product_name": nome}
    desc_lines = [f"**Produto manual:** {nome}"]
    if descricao:
        payload["custom_product_description"] = descricao
        desc_lines.append(f"**Descrição:** {descricao}")
    if valor:
        payload["amount_text"] = valor
        payload["base_amount_text"] = valor
        minutos = max(1, int(prazo_minutos or load_data().get("payment", {}).get("default_deadline_minutes", 20) or 20))
        deadline = datetime.utcnow() + timedelta(minutes=minutos)
        payload["payment_deadline"] = deadline.isoformat()
        payload["payment_status"] = "pending"
        desc_lines.append(f"**Valor:** {valor}")
        desc_lines.append(f"**Prazo para pagar:** até {deadline.strftime('%H:%M UTC')}")

    set_ticket_state(interaction.channel.id, payload)
    embed = base_embed("📦 Produto manual vinculado", "\n".join(desc_lines), discord.Color(COR_INFO))
    await interaction.channel.send(embed=embed, view=TicketActionView(buyer_id or 0, nome))
    await interaction.response.send_message("Produto manual configurado no ticket.", ephemeral=True)


@tree.command(name="ticket_calc", description="Envia o painel de ticket de cálculo", guild=discord.Object(id=GUILD_ID))
async def ticket_calc(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    embed = base_embed(
        "🧮 Cálculo personalizado",
        "Abra um ticket para pedir orçamento de itens que não estão na loja.",
        discord.Color(COR_ALERTA),
    )
    await interaction.response.send_message(embed=embed, view=CalcTicketView())


# =========================
# COMANDOS - EXTRAS
# =========================
@tree.command(name="sorteio", description="Cria um sorteio avançado", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(premio="Nome do prêmio", tempo="Número de tempo", unidade="minutos, horas ou dias", quantidade_vencedores="Quantos vencedores", cargo_obrigatorio="Cargo obrigatório para participar")
@app_commands.choices(unidade=[
    app_commands.Choice(name="minutos", value="minutos"),
    app_commands.Choice(name="horas", value="horas"),
    app_commands.Choice(name="dias", value="dias"),
])
async def sorteio(
    interaction: discord.Interaction,
    premio: str,
    tempo: app_commands.Range[int, 1, 999],
    unidade: app_commands.Choice[str],
    quantidade_vencedores: app_commands.Range[int, 1, 20] = 1,
    cargo_obrigatorio: Optional[discord.Role] = None,
):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Só a equipe pode usar este comando.", ephemeral=True)
        return

    multiplier = {"minutos": 60, "horas": 3600, "dias": 86400}[unidade.value]
    seconds = tempo * multiplier
    giveaway_id = f"gw-{interaction.guild_id}-{interaction.channel_id}-{int(datetime.utcnow().timestamp())}"
    view = GiveawayView(giveaway_id, premio, quantidade_vencedores, cargo_obrigatorio.id if cargo_obrigatorio else None)
    ACTIVE_GIVEAWAYS[giveaway_id] = view

    role_text = cargo_obrigatorio.mention if cargo_obrigatorio else "Livre para todos"
    desc = (
        f"**Prêmio:** {premio}\n"
        f"**Duração:** {tempo} {unidade.value}\n"
        f"**Vencedores:** {quantidade_vencedores}\n"
        f"**Cargo obrigatório:** {role_text}\n\n"
        "Clique no botão abaixo para participar."
    )
    embed = base_embed("🎉 Sorteio", desc, discord.Color.purple())
    await interaction.response.send_message("Sorteio criado com sucesso.", ephemeral=True)
    if interaction.channel:
        message = await interaction.channel.send(embed=embed, view=view)
        view.message = message

        async def finalize_giveaway():
            await asyncio.sleep(seconds)
            await view.finish(interaction.channel)

        asyncio.create_task(finalize_giveaway())


@tree.command(name="reroll", description="Refaz o sorteio de uma mensagem ativa", guild=discord.Object(id=GUILD_ID))
async def reroll(interaction: discord.Interaction, mensagem_id: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Só a equipe pode usar este comando.", ephemeral=True)
        return
    for view in ACTIVE_GIVEAWAYS.values():
        if view.message and str(view.message.id) == str(mensagem_id):
            if not view.participants:
                await interaction.response.send_message("Esse sorteio não teve participantes.", ephemeral=True)
                return
            winner_ids = random.sample(list(view.participants), k=min(view.winner_count, len(view.participants)))
            text = view.winners_text(interaction.guild, winner_ids)
            await interaction.response.send_message(embed=base_embed("🔄 Reroll realizado", f"**Prêmio:** {view.prize}\n**Novos vencedores:** {text}", discord.Color(COR_SUCESSO)))
            return
    await interaction.response.send_message("Não achei um sorteio ativo com essa mensagem.", ephemeral=True)


@tree.command(name="cupom", description="Calcula valor com desconto", guild=discord.Object(id=GUILD_ID))
async def cupom(interaction: discord.Interaction, valor: str, desconto_percentual: app_commands.Range[int, 1, 100]):
    base = money_to_float(valor)
    final = base * (1 - desconto_percentual / 100)
    await interaction.response.send_message(
        f"Valor original: **{format_money(base)}**\nDesconto: **{desconto_percentual}%**\nValor final: **{format_money(final)}**"
    )


@tree.command(name="calc_robux", description="Calcula valor por quantidade de robux", guild=discord.Object(id=GUILD_ID))
async def calc_robux(interaction: discord.Interaction, quantidade: int, preco_por_mil: str):
    mil = money_to_float(preco_por_mil)
    total = (quantidade / 1000) * mil
    await interaction.response.send_message(f"**{quantidade} robux** = **{format_money(total)}**")


@tree.command(name="anuncio", description="Envia um anúncio estilizado", guild=discord.Object(id=GUILD_ID))
async def anuncio(interaction: discord.Interaction, titulo: str, mensagem: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    await interaction.response.send_message(embed=base_embed(f"📢 {titulo}", mensagem, discord.Color(COR_INFO)))


@tree.command(name="cliente", description="Marca um membro como cliente", guild=discord.Object(id=GUILD_ID))
async def cliente(interaction: discord.Interaction, membro: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    cargo = interaction.guild.get_role(CARGO_CLIENTE_ID) if interaction.guild else None
    if not cargo:
        await interaction.response.send_message("Cargo cliente não encontrado.", ephemeral=True)
        return
    await membro.add_roles(cargo, reason="Compra confirmada")
    await interaction.response.send_message(f"{membro.mention} recebeu o cargo de cliente.", ephemeral=True)


@tree.command(name="perfil", description="Mostra o perfil de compras", guild=discord.Object(id=GUILD_ID))
async def perfil(interaction: discord.Interaction, membro: Optional[discord.Member] = None):
    target = membro or interaction.user
    info = get_user_data(target.id)
    produtos = info.get("produtos", {})
    top_produtos = sorted(produtos.items(), key=lambda x: x[1], reverse=True)[:5]
    produtos_text = "\n".join([f"• {name} — {qty}x" for name, qty in top_produtos]) or "Sem compras registradas."
    desc = (
        f"**Compras:** {info.get('compras', 0)}\n"
        f"**Gasto total:** {format_money(float(info.get('gasto_total', 0.0) or 0.0))}\n"
        f"**Tickets abertos/criados:** {info.get('tickets', 0)}\n"
        f"**Último produto:** {info.get('ultimo_produto', 'Nenhum')}\n\n"
        f"**Produtos:**\n{produtos_text}"
    )
    await interaction.response.send_message(embed=base_embed(f"👤 Perfil de {target.display_name}", desc, discord.Color(COR_INFO)), ephemeral=True)


@tree.command(name="ranking", description="Mostra o ranking dos compradores", guild=discord.Object(id=GUILD_ID))
async def ranking(interaction: discord.Interaction):
    ranked = top_buyers(10)
    if not ranked:
        await interaction.response.send_message("Ainda não há compras registradas.", ephemeral=True)
        return
    lines = []
    for pos, (uid, info) in enumerate(ranked, start=1):
        member = interaction.guild.get_member(uid) if interaction.guild else None
        name = member.display_name if member else f"Usuário {uid}"
        lines.append(f"**{pos}.** {name} — {format_money(float(info.get('gasto_total', 0.0) or 0.0))} • {info.get('compras', 0)} compra(s)")
    await interaction.response.send_message(embed=base_embed("🏆 Ranking de compradores", "\n".join(lines), discord.Color.gold()))


@tree.command(name="vendas", description="Mostra estatísticas de vendas", guild=discord.Object(id=GUILD_ID))
async def vendas(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    stats = data.get("stats", {})
    total_produtos = sum(len(cat.get("produtos", [])) for cat in data.get("categorias", {}).values())
    total_stock = sum(product_display_stock(prod) for cat in data.get("categorias", {}).values() for prod in cat.get("produtos", []))
    desc = (
        f"**Vendas registradas:** {stats.get('sales_count', 0)}\n"
        f"**Faturamento registrado:** {format_money(float(stats.get('sales_total', 0.0) or 0.0))}\n"
        f"**Produtos cadastrados:** {total_produtos}\n"
        f"**Estoque visível:** {total_stock}\n"
        f"**Usuários salvos:** {len(data.get('usuarios', {}))}"
    )
    await interaction.response.send_message(embed=base_embed("📊 Estatísticas da loja", desc, discord.Color(COR_INFO)), ephemeral=True)


@tree.command(name="blacklist_add", description="Adiciona usuário à blacklist", guild=discord.Object(id=GUILD_ID))
async def blacklist_add(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Tentativa inválida ou bloqueio manual"):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    blacklist_add_user(membro.id, motivo, interaction.user.id)
    await interaction.response.send_message(f"{membro.mention} foi adicionado à blacklist.", ephemeral=True)


@tree.command(name="blacklist_remove", description="Remove usuário da blacklist", guild=discord.Object(id=GUILD_ID))
async def blacklist_remove(interaction: discord.Interaction, membro: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if blacklist_remove_user(membro.id):
        await interaction.response.send_message(f"{membro.mention} foi removido da blacklist.", ephemeral=True)
    else:
        await interaction.response.send_message("Esse usuário não estava na blacklist.", ephemeral=True)


@tree.command(name="blacklist_list", description="Lista usuários bloqueados", guild=discord.Object(id=GUILD_ID))
async def blacklist_list(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    entries = data.get("blacklist", {})
    if not entries:
        await interaction.response.send_message("A blacklist está vazia.", ephemeral=True)
        return
    lines = []
    for uid, info in list(entries.items())[:20]:
        member = interaction.guild.get_member(int(uid)) if interaction.guild else None
        name = member.display_name if member else uid
        lines.append(f"• {name} — {info.get('reason', 'Sem motivo')} ")
    await interaction.response.send_message(embed=base_embed("🚫 Blacklist", "\n".join(lines), discord.Color(COR_ERRO)), ephemeral=True)


@tree.command(name="ticket_assumir", description="Marca que você assumiu o ticket", guild=discord.Object(id=GUILD_ID))
async def ticket_assumir(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use dentro de um ticket.", ephemeral=True)
        return
    set_ticket_state(interaction.channel.id, {"assigned_staff_id": interaction.user.id})
    await interaction.channel.send(embed=base_embed("🧑‍💼 Ticket assumido", f"{interaction.user.mention} assumiu este atendimento.", discord.Color(COR_INFO)))
    await interaction.response.send_message("Ticket assumido com sucesso.", ephemeral=True)


@tree.command(name="ticket_transcript", description="Gera transcript manual do ticket", guild=discord.Object(id=GUILD_ID))
async def ticket_transcript(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use dentro de um ticket.", ephemeral=True)
        return
    path = await create_ticket_transcript(interaction.channel)
    await interaction.response.send_message(file=discord.File(path, filename=path.name), ephemeral=True)



@tree.command(name="ticket_sair", description="Sai do ticket assumido", guild=discord.Object(id=GUILD_ID))
async def ticket_sair(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use dentro de um ticket.", ephemeral=True)
        return
    set_ticket_state(interaction.channel.id, {"assigned_staff_id": 0})
    await interaction.channel.send(embed=base_embed("↩️ Staff saiu do ticket", f"{interaction.user.mention} saiu do atendimento.", discord.Color(COR_ALERTA)))
    await interaction.response.send_message("Você saiu do ticket.", ephemeral=True)


@tree.command(name="ticket_prioridade", description="Define a prioridade do ticket", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(nivel="baixa, normal, alta ou urgente")
async def ticket_prioridade(interaction: discord.Interaction, nivel: str):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use em um ticket.", ephemeral=True)
        return
    nivel = nivel.lower().strip()
    if nivel not in {"baixa", "normal", "alta", "urgente"}:
        await interaction.response.send_message("Use: baixa, normal, alta ou urgente.", ephemeral=True)
        return
    set_ticket_state(interaction.channel.id, {"priority": nivel})
    try:
        await interaction.channel.edit(name=f"{nivel[:1]}-{interaction.channel.name}"[:90] if not interaction.channel.name.startswith(tuple("bnau")) else interaction.channel.name)
    except Exception:
        pass
    await interaction.response.send_message(embed=base_embed("🚦 Prioridade atualizada", f"Nova prioridade: **{nivel}**", discord.Color(COR_ALERTA)))


@tree.command(name="ticket_valor", description="Define valor personalizado do ticket", guild=discord.Object(id=GUILD_ID))
async def ticket_valor(interaction: discord.Interaction, valor: str, taxa_extra_percentual: Optional[float] = None, desconto_pix_percentual: Optional[float] = None, prazo_minutos: Optional[int] = None):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use em um ticket.", ephemeral=True)
        return
    buyer_id = parse_buyer_id(interaction.channel)
    buyer = interaction.guild.get_member(buyer_id) if interaction.guild and buyer_id else None
    comps = get_price_components(valor, buyer, extra_percent=taxa_extra_percentual, pix_discount_percent=desconto_pix_percentual)
    deadline = datetime.utcnow() + timedelta(minutes=max(1, int(prazo_minutos or load_data().get("payment", {}).get("default_deadline_minutes", 20) or 20)))
    set_ticket_state(interaction.channel.id, {
        "amount_text": format_money(comps["final"]),
        "base_amount_text": valor,
        "extra_percent": comps["extra_percent"],
        "pix_discount_percent": comps["pix_discount_percent"],
        "payment_deadline": deadline.isoformat(),
        "payment_status": "pending",
    })
    desc = (
        f"**Valor base:** {valor}\n"
        f"**Taxa extra:** {comps['extra_percent']}%\n"
        f"**Desconto VIP:** {comps['vip_discount_percent']}%\n"
        f"**Desconto Pix:** {comps['pix_discount_percent']}%\n"
        f"**Valor final:** {format_money(comps['final'])}\n"
        f"**Prazo:** até {deadline.strftime('%H:%M UTC')}"
    )
    await interaction.response.send_message(embed=base_embed("💰 Valor do ticket atualizado", desc, discord.Color(COR_SUCESSO)))


@tree.command(name="ticket_fechar", description="Fecha o ticket com motivo", guild=discord.Object(id=GUILD_ID))
async def ticket_fechar(interaction: discord.Interaction, motivo: Optional[str] = None):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use dentro de um ticket.", ephemeral=True)
        return
    await interaction.response.send_message("Fechando ticket...", ephemeral=True)
    await close_ticket_flow(interaction.channel, interaction.user, motivo or "")


@tree.command(name="avaliar_atendimento", description="Avalia o atendimento do ticket", guild=discord.Object(id=GUILD_ID))
async def avaliar_atendimento(interaction: discord.Interaction, nota: app_commands.Range[int, 1, 5], comentario: Optional[str] = None):
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("Use dentro de um ticket.", ephemeral=True)
        return
    buyer_id = parse_buyer_id(interaction.channel)
    if interaction.user.id != buyer_id and not (isinstance(interaction.user, discord.Member) and is_admin(interaction.user)):
        await interaction.response.send_message("Só o cliente do ticket pode avaliar.", ephemeral=True)
        return
    set_ticket_state(interaction.channel.id, {"rating": nota, "rating_comment": comentario or ""})
    await interaction.response.send_message(embed=base_embed("⭐ Avaliação registrada", f"Nota: **{nota}/5**\nComentário: {comentario or 'Sem comentário'}", discord.Color(COR_SUCESSO)))
    buyer = interaction.guild.get_member(buyer_id) if interaction.guild and buyer_id else None
    await send_log(interaction.guild, "⭐ Atendimento avaliado", buyer=buyer, product_name=parse_product_name(interaction.channel) or "", ticket_channel=interaction.channel, extra=f"Nota: {nota}/5 | Comentário: {comentario or 'Sem comentário'}")


@tree.command(name="vip_config", description="Configura o sistema VIP", guild=discord.Object(id=GUILD_ID))
async def vip_config(interaction: discord.Interaction, cargo_vip: Optional[discord.Role] = None, desconto_percentual: Optional[float] = None, compras_minimas: Optional[int] = None, gasto_minimo: Optional[float] = None):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    vip = data.setdefault("vip", {})
    if cargo_vip is not None:
        vip["role_id"] = cargo_vip.id
    if desconto_percentual is not None:
        vip["discount_percent"] = max(0.0, float(desconto_percentual))
    if compras_minimas is not None:
        vip["auto_role_after_sales"] = max(0, int(compras_minimas))
    if gasto_minimo is not None:
        vip["auto_role_after_spent"] = max(0.0, float(gasto_minimo))
    save_data(data)
    await interaction.response.send_message("Configuração VIP atualizada.", ephemeral=True)


@tree.command(name="vip_add", description="Dá o cargo VIP para um membro", guild=discord.Object(id=GUILD_ID))
async def vip_add(interaction: discord.Interaction, membro: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    role = interaction.guild.get_role(int(data.get("vip", {}).get("role_id", 0) or 0)) if interaction.guild else None
    if role is None:
        await interaction.response.send_message("Cargo VIP não configurado.", ephemeral=True)
        return
    await membro.add_roles(role, reason="VIP manual")
    await interaction.response.send_message(f"{membro.mention} agora é VIP.", ephemeral=True)


@tree.command(name="vip_remove", description="Remove o cargo VIP de um membro", guild=discord.Object(id=GUILD_ID))
async def vip_remove(interaction: discord.Interaction, membro: discord.Member):
    if not isinstance(interaction.user, discord.Member) or not is_admin(interaction.user):
        await interaction.response.send_message("Sem permissão.", ephemeral=True)
        return
    data = load_data()
    role = interaction.guild.get_role(int(data.get("vip", {}).get("role_id", 0) or 0)) if interaction.guild else None
    if role is None:
        await interaction.response.send_message("Cargo VIP não configurado.", ephemeral=True)
        return
    await membro.remove_roles(role, reason="VIP removido")
    await interaction.response.send_message(f"VIP removido de {membro.mention}.", ephemeral=True)

@tree.command(name="comandos_loja", description="Mostra os comandos do bot", guild=discord.Object(id=GUILD_ID))
async def comandos_loja(interaction: discord.Interaction):
    texto = (
        "**Loja e visual**\n"
        "/painel, /loja_on, /loja_off, /set_banner_online, /set_logo, /config_pix\n\n"
        "**Produtos e estoque**\n"
        "/categoria_add, /categoria_banner, /produto_add, /produto_editar, /produto_remover, /produtos, /estoque_set, /estoque_add_qtd, /estoque_rem_qtd, /estoque_add, /estoque_ver\n\n"
        "**Pagamentos e entrega**\n"
        "/pix, /ticket_valor, /entrega_manual, /entrega_auto, /cupom, /calc_robux\n\n"
        "**Tickets**\n"
        "/ticket_calc, /ticket_produto, /ticket_renomear, /ticket_assumir, /ticket_sair, /ticket_prioridade, /ticket_transcript, /ticket_fechar, /avaliar_atendimento\n\n"
        "**Sorteio e gestão**\n"
        "/sorteio, /reroll, /perfil, /ranking, /vendas, /cliente, /anuncio, /blacklist_add, /blacklist_remove, /blacklist_list, /vip_config, /vip_add, /vip_remove"
    )
    await interaction.response.send_message(embed=base_embed("📚 Comandos da loja", texto, discord.Color.dark_gold()), ephemeral=True)





@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"Erro de comando: {error}")
    try:
        if interaction.response.is_done():
            await interaction.followup.send(f"❌ Erro: `{error}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Erro: `{error}`", ephemeral=True)
    except Exception:
        pass


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("Defina a variável de ambiente TOKEN antes de iniciar o bot.")
    bot.run(TOKEN)
