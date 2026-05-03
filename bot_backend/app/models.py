from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class Player(Base):
    __tablename__ = 'players'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    twitch_name: Mapped[str | None] = mapped_column(String(100), index=True)
    twitch_user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    dota_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    steam_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    dota_name: Mapped[str | None] = mapped_column(String(128))
    slots_total: Mapped[int] = mapped_column(Integer, default=0)
    slots_left: Mapped[int] = mapped_column(Integer, default=0, index=True)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    last_played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_slot_added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comment: Mapped[str | None] = mapped_column(Text)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    blacklist_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    slot_logs: Mapped[list['PlayerSlotLog']] = relationship(back_populates='player')


class PlayerSlotLog(Base):
    __tablename__ = 'player_slots_log'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id'), index=True)
    change_amount: Mapped[int] = mapped_column(Integer)
    old_slots_left: Mapped[int] = mapped_column(Integer)
    new_slots_left: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    player: Mapped[Player] = relationship(back_populates='slot_logs')


class Match(Base):
    __tablename__ = 'matches'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    lobby_id: Mapped[str | None] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MatchPlayer(Base):
    __tablename__ = 'match_players'
    __table_args__ = (UniqueConstraint('match_id', 'dota_id', name='uq_match_player_dota'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey('matches.id'), index=True)
    player_id: Mapped[int | None] = mapped_column(ForeignKey('players.id'), index=True)
    dota_id: Mapped[str | None] = mapped_column(String(64), index=True)
    steam_id: Mapped[str | None] = mapped_column(String(64), index=True)
    dota_name: Mapped[str | None] = mapped_column(String(128))
    twitch_name: Mapped[str | None] = mapped_column(String(100))
    slots_before: Mapped[int | None] = mapped_column(Integer)
    slots_after: Mapped[int | None] = mapped_column(Integer)
    slot_was_charged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BotSetting(Base):
    __tablename__ = 'bot_settings'

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class InviteQueue(Base):
    __tablename__ = 'invite_queue'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id'), index=True)
    status: Mapped[str] = mapped_column(String(40), default='pending', index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
