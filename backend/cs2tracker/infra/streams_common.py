"""Modelo neutro de un stream en vivo, compartido por twitch.py y kick.py."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LiveStream:
    platform: str  # "twitch" | "kick"
    channel: str  # display name
    login: str  # slug del canal, para armar la URL y el player embebido
    title: str
    viewers: int
    language: str  # "es" | "pt"
    thumbnail_url: str
