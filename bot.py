import nextcord
import os
import json
from nextcord.ext import commands, tasks
from nextcord.ext import tasks
from nextcord import Interaction, SlashOption
import asyncio
import datetime
from flask import Flask
from threading import Thread
import re
import gspread
import traceback
from oauth2client.service_account import ServiceAccountCredentials
import aiohttp
import requests
from nextcord.ui import View, Select, button
import time
import psutil
from ping3 import ping
import functools

intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_IDS = []
    
# ────────────────────────────────────────────────
# ✅ 디도스 공격 방지
active_commands = {}

def prevent_overlap(func):
    """유저별 중복 실행을 막는 데코레이터"""
    @functools.wraps(func)
    async def wrapper(interaction: nextcord.Interaction, *args, **kwargs):
        user = interaction.user

        if active_commands.get(user.id, False):
            await interaction.response.send_message(
                "📡 이전 명령어가 아직 처리 중입니다",
                ephemeral=True
            )
            return

        active_commands[user.id] = True
        try:
            return await func(interaction, *args, **kwargs)
        finally:
            active_commands.pop(user.id, None)

    return wrapper
 
# ────────────────────────────────────────────────
# ✅ 오류 메시지 전송
@bot.event
async def on_application_command_error(interaction: nextcord.Interaction, error: Exception):
    # 전체 스택 추적
    full_traceback = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    # 짧은 오류 메시지 (한 줄)
    short_error = "".join(traceback.format_exception_only(type(error), error)).strip()

    # 기본 오류 Embed (공개 메시지)
    embed = nextcord.Embed(
        title="❌ 오류 발생",
        description="명령어 사용 중 오류가 발생했습니다.",
        color=0xFF0000,
        timestamp=datetime.datetime.now(datetime.UTC)
    )
    embed.add_field(name="오류 코드", value=f"```{short_error}```", inline=False)
    embed.set_footer(text=f"요청자: {interaction.user}", icon_url=interaction.user.display_avatar.url)

    # 버튼 View 정의
    class ErrorView(View):
        def __init__(self):
            super().__init__(timeout=120)

        @button(label="세부사항 보기", style=nextcord.ButtonStyle.danger)
        async def details_button(self, button, i: nextcord.Interaction):
            # 버튼 누른 사람에게만 세부사항 출력
            await i.response.send_message(f"```py\n{full_traceback[:1900]}```", ephemeral=True)

    # ⚡ 메시지 공개로 전송 (ephemeral=False)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=ErrorView(), ephemeral=False)
        else:
            await interaction.response.send_message(embed=embed, view=ErrorView(), ephemeral=False)
    except Exception as e:
        print(f"⚠️ 오류 임베드 전송 실패: {e}")
# ────────────────────────────────────────────────
# ✅ 봇 시작 시간 기록
bot_start_time = time.time()

# ────────────────────────────────────────────────
# ✅ 유틸 함수들
def create_bar(value, max_value=100, length=20):
    """흰색 progress bar 생성"""
    filled_length = int(length * min(value, max_value) / max_value)
    empty_length = length - filled_length
    bar = "█" * filled_length + "░" * empty_length
    return bar

def format_uptime(seconds):
    """초 단위를 '일시간분초' 형태로 변환"""
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, sec = divmod(remainder, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}일")
    if hours > 0:
        parts.append(f"{hours}시간")
    if minutes > 0:
        parts.append(f"{minutes}분")
    parts.append(f"{sec}초")
    return " ".join(parts)

# ────────────────────────────────────────────────
# ✅ /핑 명령어
@bot.slash_command(name="핑", description="봇의 상태를 확인합니다.")
@prevent_overlap
async def 핑(
    interaction: nextcord.Interaction,
    모드: str = nextcord.SlashOption(
        name="모드",
        description="표시할 정보 수준을 선택하세요",
        required=False,
        choices={"일반": "basic", "고급": "advanced"}
    )
):
    if 모드 is None:
        모드 = "basic"

    # ────────────────────────────────────────────────
    # 기본 정보
    latency = round(bot.latency * 1000)
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    ram_used = mem.used / (1024**3)
    ram_total = mem.total / (1024**3)
    ram_percent = mem.percent
    uptime_sec = time.time() - bot_start_time
    uptime_str = format_uptime(uptime_sec)

    # 상태 판정
    def status_check(v, limits):
        if v <= limits[0]:
            return "🟢 좋음"
        elif v <= limits[1]:
            return "🟡 보통"
        else:
            return "🔴 나쁨"

    cpu_status = status_check(cpu, (70, 90))
    ram_status = status_check(ram_percent, (70, 90))
    latency_status = status_check(latency, (150, 300))

    # Embed 컬러는 가장 심각한 상태 기준
    color_map = {"🟢 좋음": 0x00FFAA, "🟡 보통": 0xFFD700, "🔴 나쁨": 0xFF4C4C}
    max_status = max([cpu_status, ram_status, latency_status],
                     key=lambda s: ["🟢 좋음","🟡 보통","🔴 나쁨"].index(s))
    embed_color = color_map[max_status]

    # Progress bar 생성
    cpu_bar = create_bar(cpu)
    ram_bar = create_bar(ram_percent)
    latency_bar = create_bar(min(latency, 500), max_value=500)

    # ────────────────────────────────────────────────
    # Embed 기본 구조
    embed = nextcord.Embed(
        title="🏓 퐁!",
        color=embed_color,
        timestamp=datetime.datetime.now(datetime.UTC)
    )

    # 일반 모드 정보
    embed.add_field(name=f"⏱️ 핑 {latency_status}", value=f"{latency}ms\n`{latency_bar}`", inline=False)
    embed.add_field(name=f"🖥️ CPU 사용량 {cpu_status}", value=f"{cpu}%\n`{cpu_bar}`", inline=False)
    embed.add_field(name=f"💾 RAM 사용량 {ram_status}", value=f"{ram_used:.2f}GB / {ram_total:.2f}GB ({ram_percent}%)\n`{ram_bar}`", inline=False)
    embed.add_field(name="⏳ 서버 가동 시간", value=uptime_str, inline=False)

    # 고급 모드 정보
    if 모드 == "advanced":
        embed.add_field(name="\u200b", value="**─── 🛠️ 고급 정보 ───**", inline=False)

        guilds = len(bot.guilds)
        users = sum(g.member_count for g in bot.guilds)
        shards = bot.shard_count or 1

        # 네트워크 속도 측정
        net_before = psutil.net_io_counters()
        await asyncio.sleep(1)
        net_after = psutil.net_io_counters()
        upload_speed = (net_after.bytes_sent - net_before.bytes_sent) * 8 / (1024**2)  # Mbps
        download_speed = (net_after.bytes_recv - net_before.bytes_recv) * 8 / (1024**2)  # Mbps

        # 네트워크 인터페이스별 상태
        interfaces = psutil.net_if_stats()
        net_io_pernic = psutil.net_io_counters(pernic=True)
        iface_status_list = []
        max_speed_reference = 100
        for name, stats in interfaces.items():
            sent = net_io_pernic[name].bytes_sent / (1024**2)
            recv = net_io_pernic[name].bytes_recv / (1024**2)
            speed_mbps = stats.speed if stats.speed > 0 else max_speed_reference
            bar_length = int((speed_mbps / max_speed_reference) * 20)
            bar_length = min(bar_length, 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            status_emoji = "🟢" if stats.isup else "🔴"
            iface_status_list.append(
                f"{name} {status_emoji} `{bar}` ↑{sent:.1f}MB ↓{recv:.1f}MB ({speed_mbps}Mbps)"
            )
        iface_status_str = "\n".join(iface_status_list)

        embed.add_field(name="⬆️ 업로드 속도", value=f"{upload_speed:.2f} Mbps", inline=True)
        embed.add_field(name="⬇️ 다운로드 속도", value=f"{download_speed:.2f} Mbps", inline=True)
        embed.add_field(name="🌍 길드 수", value=str(guilds), inline=True)
        embed.add_field(name="👥 사용자 수", value=str(users), inline=True)
        embed.add_field(name="🧩 샤드", value=str(shards), inline=True)
        embed.add_field(name="💻 네트워크 인터페이스 상태", value=iface_status_str, inline=False)

    await interaction.response.send_message(embed=embed)

# ────────────────────────────────────────────────
# ✅ /타임아웃 명령어어
@bot.slash_command(name="타임아웃", description="굴라그로 보내기", guild_ids=GUILD_IDS)
async def timeout(
    interaction: Interaction,
    user: nextcord.Member = SlashOption(description="제재할 유저"),
    days: int = SlashOption(description="일", required=False, default=0),
    hours: int = SlashOption(description="시", required=False, default=0),
    minutes: int = SlashOption(description="분", required=False, default=0),
    seconds: int = SlashOption(description="초", required=False, default=0),
    reason: str = SlashOption(description="사유", required=False, default="사유 없음"),
):
    total_seconds = days*86400 + hours*3600 + minutes*60 + seconds

    if total_seconds <= 0:
        await interaction.response.send_message("❌ 타임아웃 시간은 1초 이상이어야 합니다.", ephemeral=True)
        return

    try:
        await user.timeout(
            timeout=nextcord.utils.utcnow() + timedelta(seconds=total_seconds),
            reason=reason
        )
        # 보기 좋은 시간 문자열 만들기
        duration_text = []
        if days: duration_text.append(f"{days}일")
        if hours: duration_text.append(f"{hours}시간")
        if minutes: duration_text.append(f"{minutes}분")
        if seconds: duration_text.append(f"{seconds}초")
        duration_str = " ".join(duration_text)

        embed = nextcord.Embed(
            title="🚨 제재 알림",
            description=f"{user.mention} 에게 **굴라그 {duration_str}** 이 적용되었습니다.\n**사유:** {reason}\n\n규칙을 잘 지킵시다.",
            color=nextcord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ 오류 발생: {e}", ephemeral=True)

# ────────────────────────────────────────────────
# ✅ /추방 명령어
@bot.slash_command(name="추방", description="나가리 시키기", guild_ids=GUILD_IDS)
async def kick(
    interaction: Interaction,
    user: nextcord.Member = SlashOption(description="나가리할 유저"),
    reason: str = SlashOption(description="사유", required=False, default="사유 없음"),
):
    try:
        await user.kick(reason=reason)
        embed = nextcord.Embed(
            title="🚨 제재 알림",
            description=f"{user.mention} 이(가) 나가리되었습니다.\n**사유:** {reason}\n\n규칙을 잘 지킵시다.",
            color=nextcord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ 오류 발생: {e}", ephemeral=True)

# ────────────────────────────────────────────────
# ✅ /차단 명령어
@bot.slash_command(name="차단", description="숙청 시키기", guild_ids=GUILD_IDS)
async def ban(
    interaction: Interaction,
    user: nextcord.Member = SlashOption(description="숙청할 유저"),
    reason: str = SlashOption(description="사유", required=False, default="사유 없음"),
):
    try:
        await user.ban(reason=reason)
        embed = nextcord.Embed(
            title="🚨 제재 알림",
            description=f"{user.mention} 이(가) 숙청되었습니다.\n**사유:** {reason}\n\n규칙을 잘 지킵시다.",
            color=nextcord.Color.dark_red(),
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ 오류 발생: {e}", ephemeral=True)

# ────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"🤖 봇 로그인됨: {bot.user}")
    
    # 슬래시 명령어 동기화
    await bot.sync_application_commands()
    print("📡 슬래시 명령어 동기화 완료")

# ────────────────────────────────────────────────
# ✅ Render/Replit 등의 환경에서 꺼지지 않도록 웹 서버 유지
app = Flask('')

@app.route('/')
def home():
    return "✅ 봇이 온라인으로 전환되었습니다. 이제 이 창을 닫아도 됩니다."

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run_web).start()

keep_alive()

# ────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ 환경변수 DISCORD_TOKEN 이 설정되지 않았습니다.")
else:
    bot.run(TOKEN)
