from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .crud import add_slots, blacklist_player, charge_slot_after_game, link_player, set_comment, set_slots, unblacklist_player
from .db import get_session
from .models import Player, PlayerSlotLog
from .selection import select_next_player
from .twitch_proxy_client import streamer_proxy

app = FastAPI(title='Dota Lobby Dashboard', version='0.1.0')
templates = Jinja2Templates(directory='app/templates')


def authed(request: Request) -> bool:
    return request.cookies.get('web_auth') == settings.web_session_secret


def require_auth(request: Request) -> RedirectResponse | None:
    if not authed(request):
        return RedirectResponse('/login', status_code=303)
    return None


@app.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request, 'error': None})


@app.post('/login')
async def login(username: str = Form(...), password: str = Form(...)):
    if username != settings.web_admin_username or password != settings.web_admin_password:
        return templates.TemplateResponse('login.html', {'request': {}, 'error': 'Invalid login or password'}, status_code=401)
    response = RedirectResponse('/', status_code=303)
    response.set_cookie('web_auth', settings.web_session_secret, httponly=True, samesite='strict')
    return response


@app.get('/logout')
async def logout():
    response = RedirectResponse('/login', status_code=303)
    response.delete_cookie('web_auth')
    return response


@app.get('/', response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    redirect = require_auth(request)
    if redirect:
        return redirect
    total_players = await session.scalar(select(func.count(Player.id))) or 0
    active_players = await session.scalar(select(func.count(Player.id)).where(Player.slots_left > 0, Player.is_blacklisted.is_(False))) or 0
    blacklisted = await session.scalar(select(func.count(Player.id)).where(Player.is_blacklisted.is_(True))) or 0
    total_slots = await session.scalar(select(func.coalesce(func.sum(Player.slots_left), 0))) or 0
    result = await session.execute(select(Player).order_by(Player.slots_left.desc()).limit(8))
    players = result.scalars().all()
    return templates.TemplateResponse('dashboard.html', {
        'request': request,
        'total_players': total_players,
        'active_players': active_players,
        'blacklisted': blacklisted,
        'total_slots': total_slots,
        'players': players,
    })


@app.get('/players', response_class=HTMLResponse)
async def players_page(request: Request, q: str = '', session: AsyncSession = Depends(get_session)):
    redirect = require_auth(request)
    if redirect:
        return redirect
    stmt = select(Player).order_by(Player.slots_left.desc(), Player.updated_at.desc()).limit(200)
    if q:
        like = f'%{q}%'
        stmt = select(Player).where(
            (Player.dota_id.ilike(like)) | (Player.twitch_name.ilike(like)) | (Player.dota_name.ilike(like)) | (Player.steam_id.ilike(like))
        ).order_by(Player.slots_left.desc()).limit(200)
    result = await session.execute(stmt)
    return templates.TemplateResponse('players.html', {'request': request, 'players': result.scalars().all(), 'q': q})


@app.get('/player/{dota_id}', response_class=HTMLResponse)
async def player_page(request: Request, dota_id: str, session: AsyncSession = Depends(get_session)):
    redirect = require_auth(request)
    if redirect:
        return redirect
    player = (await session.execute(select(Player).where(Player.dota_id == dota_id))).scalar_one_or_none()
    logs = []
    if player:
        logs = (await session.execute(select(PlayerSlotLog).where(PlayerSlotLog.player_id == player.id).order_by(PlayerSlotLog.created_at.desc()).limit(25))).scalars().all()
    return templates.TemplateResponse('player.html', {'request': request, 'player': player, 'logs': logs})


@app.post('/players/add')
async def web_add_player(dota_id: str = Form(...), slots: int = Form(...), session: AsyncSession = Depends(get_session)):
    await add_slots(session, dota_id, slots, created_by='web')
    return RedirectResponse('/players', status_code=303)


@app.post('/player/{dota_id}/link')
async def web_link_player(dota_id: str, twitch_name: str = Form(''), steam_id: str = Form(''), dota_name: str = Form(''), session: AsyncSession = Depends(get_session)):
    await link_player(session, dota_id, twitch_name or None, steam_id or None, dota_name or None)
    return RedirectResponse(f'/player/{dota_id}', status_code=303)


@app.post('/player/{dota_id}/slots')
async def web_set_slots(dota_id: str, slots: int = Form(...), session: AsyncSession = Depends(get_session)):
    await set_slots(session, dota_id, slots, created_by='web')
    return RedirectResponse(f'/player/{dota_id}', status_code=303)


@app.post('/player/{dota_id}/charge')
async def web_charge(dota_id: str, session: AsyncSession = Depends(get_session)):
    await charge_slot_after_game(session, dota_id, created_by='web')
    return RedirectResponse(f'/player/{dota_id}', status_code=303)


@app.post('/player/{dota_id}/comment')
async def web_comment(dota_id: str, comment: str = Form(''), session: AsyncSession = Depends(get_session)):
    await set_comment(session, dota_id, comment or None)
    return RedirectResponse(f'/player/{dota_id}', status_code=303)


@app.post('/player/{dota_id}/blacklist')
async def web_blacklist(dota_id: str, reason: str = Form(''), session: AsyncSession = Depends(get_session)):
    await blacklist_player(session, dota_id, reason or 'web')
    return RedirectResponse(f'/player/{dota_id}', status_code=303)


@app.post('/player/{dota_id}/unblacklist')
async def web_unblacklist(dota_id: str, session: AsyncSession = Depends(get_session)):
    await unblacklist_player(session, dota_id)
    return RedirectResponse(f'/player/{dota_id}', status_code=303)


@app.get('/lobby', response_class=HTMLResponse)
async def lobby_page(request: Request):
    redirect = require_auth(request)
    if redirect:
        return redirect
    error = None
    lobby = None
    try:
        lobby = await streamer_proxy.get_lobby()
    except Exception as exc:
        error = str(exc)
    return templates.TemplateResponse('lobby.html', {'request': request, 'lobby': lobby, 'error': error})


@app.get('/queue', response_class=HTMLResponse)
async def queue_page(request: Request, session: AsyncSession = Depends(get_session)):
    redirect = require_auth(request)
    if redirect:
        return redirect
    error = None
    player = None
    try:
        chatters = await streamer_proxy.get_chatters()
        online_names = {c.get('user_login', '').lower() for c in chatters if c.get('user_login')}
        player = await select_next_player(session, online_names)
    except Exception as exc:
        error = str(exc)
    return templates.TemplateResponse('queue.html', {'request': request, 'player': player, 'error': error})


@app.post('/invite/{steam_id}')
async def web_invite(steam_id: str):
    await streamer_proxy.invite(steam_id)
    return RedirectResponse('/queue', status_code=303)
