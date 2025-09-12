import os
import time
import asyncio
import datetime
import traceback
import functools
from threading import Thread
from flask import Flask
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
from nextcord.ui import View, button
from datetime import timedelta
import psutil

# ────────────────────────────────────────────────
# ✅ 인텐트 설정
intents = nextcord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_IDS = []

# ────────────────────────────────────────────────
# ✅ 실험단계 허용 유저 ID
ALLOWED_USERS = {1203155506856726581}  # 원하는 유저 ID로 교체

def user_only():
    async def predicate(interaction: Interaction):
        if interaction.user.id not in ALLOWED_USERS:
            await interaction.response.send_message(
                "❌ 오류 발생 : you are not ALLOWED_USERS",
                ephemeral=True
            )
            return False
        return True
    return commands.check(predicate)

# ────────────────────────────────────────────────
# ✅ /타임아웃 명령어
@bot.slash_command(
    name="타임아웃",
    description="유저를 타임아웃합니다.",
    default_member_permissions=nextcord.Permissions(moderate_members=True),  # 권한 요구
    dm_permission=False,
    guild_ids=GUILD_IDS
)
@user_only()
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
        duration_text = []
        if days: duration_text.append(f"{days}일")
        if hours: duration_text.append(f"{hours}시간")
        if minutes: duration_text.append(f"{minutes}분")
        if seconds: duration_text.append(f"{seconds}초")
        duration_str = " ".join(duration_text)

        embed = nextcord.Embed(
            title="🚨 제재 알림",
            description=f"{user.mention} 에게 **타임아웃 {duration_str}** 이 적용되었습니다.\n"
                        f"**사유:** {reason}\n\n규칙을 잘 지킵시다.",
            color=nextcord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ 오류 발생: {e}", ephemeral=True)

# ────────────────────────────────────────────────
# ✅ /추방 명령어
@bot.slash_command(
    name="추방",
    description="유저를 서버에서 추방합니다.",
    default_member_permissions=nextcord.Permissions(kick_members=True),  # 권한 요구
    dm_permission=False,
    guild_ids=GUILD_IDS
)
@user_only()
async def kick(
    interaction: Interaction,
    user: nextcord.Member = SlashOption(description="추방할 유저"),
    reason: str = SlashOption(description="사유", required=False, default="사유 없음"),
):
    try:
        await user.kick(reason=reason)
        embed = nextcord.Embed(
            title="🚨 제재 알림",
            description=f"{user.mention} 이(가) 추방되었습니다.\n"
                        f"**사유:** {reason}\n\n규칙을 잘 지킵시다.",
            color=nextcord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ 오류 발생: {e}", ephemeral=True)

# ────────────────────────────────────────────────
# ✅ /차단 명령어
@bot.slash_command(
    name="차단",
    description="유저를 서버에서 차단합니다.",
    default_member_permissions=nextcord.Permissions(ban_members=True),  # 권한 요구
    dm_permission=False,
    guild_ids=GUILD_IDS
)
@user_only()
async def ban(
    interaction: Interaction,
    user: nextcord.Member = SlashOption(description="차단할 유저"),
    reason: str = SlashOption(description="사유", required=False, default="사유 없음"),
):
    try:
        await user.ban(reason=reason)
        embed = nextcord.Embed(
            title="🚨 제재 알림",
            description=f"{user.mention} 이(가) 차단되었습니다.\n"
                        f"**사유:** {reason}\n\n규칙을 잘 지킵시다.",
            color=nextcord.Color.dark_red(),
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ 오류 발생: {e}", ephemeral=True)

# ────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"🤖 봇 로그인됨: {bot.user}")
    await bot.sync_application_commands()
    print("📡 슬래시 명령어 동기화 완료")

# ────────────────────────────────────────────────
# ✅ Render 등의 환경에서 꺼지지 않도록 웹서버 유지
app = Flask('')

@app.route('/')
def home():
    return "✅ 봇이 온라인 상태입니다."

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
