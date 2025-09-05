import nextcord
import os
import json
from nextcord.ext import commands, tasks
from nextcord.ext import tasks
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
intents.members = True
bot = commands.Bot(intents=intents)

GUILD_IDS = []  # 테스트할 서버 ID 넣으면 빠른 등록 가능

@bot.event
async def on_ready():
    print(f"✅ 로그인됨: {bot.user}")

# ------------------ 타임아웃 ------------------
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

# ------------------ 추방 ------------------
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

# ------------------ 차단 ------------------
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

# ------------------ 실행 ------------------
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ 환경변수 DISCORD_TOKEN 이 설정되지 않았습니다.")
else:
    bot.run(TOKEN)
