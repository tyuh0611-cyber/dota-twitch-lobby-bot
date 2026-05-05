from urllib.parse import quote

import httpx
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from .config import settings
from .crud import add_slots, blacklist_player, charge_slot_after_game, link_player, set_comment, set_slots, unblacklist_player
from .csrf import CSRF_COOKIE_NAME, csrf_guard, csrf_token_for_request
from .db import get_session
from .models import InviteQueue, MatchPlayer, Player, PlayerSlotLog
from .selection import ranked_queue_players
from .settings_service import get_all_settings, set_setting
from .twitch_proxy_client import streamer_proxy

app = FastAPI(title='Dota Lobby Dashboard', version='0.1.0')
app.mount('/static', StaticFiles(directory='app/static'), name='static')
templates = Jinja2Templates(directory='app/templates')


def with_notice(path: str, message: str, level: str = 'success') -> str:
    sep = '&' if '?' in path else '?'
    return f'{path}{sep}notice={quote(message)}&level={quote(level)}'


def authed(request: Request) -> bool:
    return request.cookies.get('web_auth') == settings.web_session_secret


def require_auth(request: Request) -> RedirectResponse | None:
    if not authed(request):
        return RedirectResponse('/login', status_code=303)
    return None


def render_template(template_name: str, context: dict, request: Request):
    csrf_token = csrf_token_for_request(request)
    response = templates.TemplateResponse(template_name, {**context, 'request': request, 'csrf_token': csrf_token})
    if request.cookies.get(CSRF_COOKIE_NAME) != csrf_token:
        response.set_cookie(CSRF_COOKIE_NAME, csrf_token, httponly=True, samesite='strict')
    return response


async def get_twitch_auth_redirect_url() -> str | None:
    proxy_url = settings.streamer_proxy_url.rstrip('/')
    headers = {'X-Api-Key': settings.streamer_proxy_api_key}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(f'{proxy_url}/twitch/auth-url', headers=headers)
        response.raise_for_status()
        data = response.json()
    if isinstance(data, dict):
        return data.get('auth_url') or data.get('url') or data.get('redirect_url')
    return None


async def control_center_context(request: Request, session: AsyncSession) -> dict:
    total_players = await session.scalar(select(func.count(Player.id))) or 0
    active_players = await session.scalar(select(func.count(Player.id)).where(Player.slots_left > 0, Player.is_blacklisted.is_(False))) or 0
    blacklisted = await session.scalar(select(func.count(Player.id)).where(Player.is_blacklisted.is_(True))) or 0
    total_slots = await session.scalar(select(func.coalesce(func.sum(Player.slots_left), 0))) or 0
    queue_settings = await get_all_settings(session)

    lobby = None
    lobby_error = None
    ranked = []
    queue_error = None
    chatters = []
    twitch_error = None
    twitch_status = {
        'connected': False,
        'chatters_count': 0,
        'require_online': queue_settings.get('require_twitch_online', 'false') == 'true',
        'error': None,
    }

    try:
        lobby = await streamer_proxy.get_lobby()
    except Exception as exc:
        lobby_error = str(exc)

    try:
        chatters = await streamer_proxy.get_chatters()
        online_names = {c.get('user_login', '').lower() for c in chatters if c.get('user_login')}
        twitch_status.update({
            'connected': True,
            'chatters_count': len(online_names),
            'error': None,
        })
        ranked, queue_settings = await ranked_queue_players(session, online_names)
        twitch_status['require_online'] = queue_settings.get('require_twitch_online', 'false') == 'true'
    except Exception as exc:
        twitch_error = str(exc)
        queue_error = str(exc)
        twitch_status.update({
            'connected': False,
            'chatters_count': 0,
            'error': twitch_error,
        })

    result = await session.execute(select(Player).order_by(Player.slots_left.desc(), Player.updated_at.desc()).limit(80))
    players = result.scalars().all()

    return {
        'request': request,
        'total_players': total_players,
        'active_players': active_players,
        'blacklisted': blacklisted,
        'total_slots': total_slots,
        'players': players,
        'ranked': ranked,
        'settings': queue_settings,
        'lobby': lobby,
        'lobby_error': lobby_error,
        'queue_error': queue_error,
        'twitch_status': twitch_status,
    }


@app.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse('login.html', {'request': request, 'error': None})


@app.post('/login')
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username != settings.web_admin_username or password != settings.web_admin_password:
        return templates.TemplateResponse('login.html', {'request': request, 'error': 'Invalid login or password'}, status_code=401)
    response = RedirectResponse(with_notice('/', 'Logged in'), status_code=303)
    response.set_cookie('web_auth', settings.web_session_secret, httponly=True, samesite='strict')
    return response


@app.get('/logout')
async def logout():
    response = RedirectResponse('/login', status_code=303)
    response.delete_cookie('web_auth')
    response.delete_cookie(CSRF_COOKIE_NAME)
    return response


@app.get('/twitch/connect')
async def twitch_connect(request: Request):
    redirect = require_auth(request)
    if redirect:
        return redirect
    try:
        auth_url = await get_twitch_auth_redirect_url()
    except Exception as exc:
        return RedirectResponse(with_notice('/', f'Twitch auth unavailable: {exc}', 'error'), status_code=303)
    if not auth_url:
        return RedirectResponse(with_notice('/', 'Twitch auth URL is empty', 'error'), status_code=303)
    return RedirectResponse(auth_url, status_code=303)


@app.get('/', response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    redirect = require_auth(request)
    if redirect:
        return redirect
    return render_template('dashboard.html', await control_center_context(request, session), request)


@app.get('/players', response_class=HTMLResponse)
async def players_page(request: Request, q: str = '', session: AsyncSession = Depends(get_session)):
    redirect = require_auth(request)
    if redirect:
        return redirect
    stmt = select(Player).order_by(Player.slots_left.desc(), Player.updated_at.desc()).limit(200)
    if q:
        like = f'%{q}%'
        stmt = select(Player).where((Player.dota_id.ilike(like)) | (Player.twitch_name.ilike(like)) | (Player.dota_name.ilike(like)) | (Player.steam_id.ilike(like))).order_by(Player.slots_left.desc()).limit(200)
    result = await session.execute(stmt)
    return render_template('players.html', {'players': result.scalars().all(), 'q': q}, request)


@app.get('/player/{dota_id}', response_class=HTMLResponse)
async def player_page(request: Request, dota_id: str, session: AsyncSession = Depends(get_session)):
    redirect = require_auth(request)
    if redirect:
        return redirect
    player = (await session.execute(select(Player).where(Player.dota_id == dota_id))).scalar_one_or_none()
    logs = []
    if player:
        logs = (await session.execute(select(PlayerSlotLog).where(PlayerSlotLog.player_id == player.id).order_by(PlayerSlotLog.created_at.desc()).limit(25))).scalars().all()
    return render_template('player.html', {'player': player, 'logs': logs}, request)


@app.post('/players/add', dependencies=[Depends(csrf_guard)])
async def web_add_player(dota_id: str = Form(...), slots: int = Form(...), return_to: str = Form('/'), session: AsyncSession = Depends(get_session)):
    await add_slots(session, dota_id, slots, created_by='web')
    return RedirectResponse(with_notice(return_to, f'Added {slots} slots to {dota_id}'), status_code=303)


@app.post('/player/{dota_id}/link', dependencies=[Depends(csrf_guard)])
async def web_link_player(dota_id: str, twitch_name: str = Form(''), steam_id: str = Form(''), dota_name: str = Form(''), session: AsyncSession = Depends(get_session)):
    await link_player(session, dota_id, twitch_name or None, steam_id or None, dota_name or None)
    return RedirectResponse(with_notice(f'/player/{dota_id}', 'Player links saved'), status_code=303)


@app.post('/player/{dota_id}/slots', dependencies=[Depends(csrf_guard)])
async def web_set_slots(dota_id: str, slots: int = Form(...), session: AsyncSession = Depends(get_session)):
    await set_slots(session, dota_id, slots, created_by='web')
    return RedirectResponse(with_notice(f'/player/{dota_id}', 'Slots updated'), status_code=303)


@app.post('/player/{dota_id}/field', dependencies=[Depends(csrf_guard)])
async def web_autosave_field(
    dota_id: str,
    field: str = Form(...),
    value: str = Form(''),
    session: AsyncSession = Depends(get_session),
):
    player = (await session.execute(select(Player).where(Player.dota_id == dota_id))).scalar_one_or_none()
    if not player:
        return JSONResponse({'ok': False, 'error': 'Player not found'}, status_code=404)

    value = value.strip()
    try:
        if field == 'slots_left':
            await set_slots(session, dota_id, max(0, int(value or '0')), created_by='web_autosave')
        elif field == 'comment':
            await set_comment(session, dota_id, value or None)
        elif field == 'twitch_name':
            await link_player(session, dota_id, value or None, player.steam_id, player.dota_name)
        elif field == 'steam_id':
            await link_player(session, dota_id, player.twitch_name, value or None, player.dota_name)
        elif field == 'dota_name':
            await link_player(session, dota_id, player.twitch_name, player.steam_id, value or None)
        else:
            return JSONResponse({'ok': False, 'error': 'Field is not editable'}, status_code=400)
    except ValueError:
        return JSONResponse({'ok': False, 'error': 'Invalid number'}, status_code=400)
    except IntegrityError:
        await session.rollback()
        return JSONResponse({'ok': False, 'error': 'Duplicate value'}, status_code=400)

    return JSONResponse({'ok': True, 'field': field, 'value': value})


@app.post('/player/{dota_id}/quick-edit', dependencies=[Depends(csrf_guard)])
async def web_quick_edit_player(
    dota_id: str,
    twitch_name: str = Form(''),
    steam_id: str = Form(''),
    dota_name: str = Form(''),
    slots_left: int = Form(...),
    comment: str = Form(''),
    return_to: str = Form('/'),
    session: AsyncSession = Depends(get_session),
):
    await link_player(session, dota_id, twitch_name or None, steam_id or None, dota_name or None)
    await set_slots(session, dota_id, slots_left, created_by='web_inline')
    await set_comment(session, dota_id, comment or None)
    return RedirectResponse(with_notice(return_to, f'Saved {dota_id}'), status_code=303)


@app.post('/player/{dota_id}/charge', dependencies=[Depends(csrf_guard)])
async def web_charge(dota_id: str, return_to: str = Form(None), session: AsyncSession = Depends(get_session)):
    await charge_slot_after_game(session, dota_id, created_by='web')
    return RedirectResponse(with_notice(return_to or f'/player/{dota_id}', f'Charged -1 slot from {dota_id}'), status_code=303)


@app.post('/player/{dota_id}/comment', dependencies=[Depends(csrf_guard)])
async def web_comment(dota_id: str, comment: str = Form(''), session: AsyncSession = Depends(get_session)):
    await set_comment(session, dota_id, comment or None)
    return RedirectResponse(with_notice(f'/player/{dota_id}', 'Comment saved'), status_code=303)


@app.post('/player/{dota_id}/blacklist', dependencies=[Depends(csrf_guard)])
async def web_blacklist(dota_id: str, reason: str = Form(''), return_to: str = Form(None), session: AsyncSession = Depends(get_session)):
    await blacklist_player(session, dota_id, reason or 'web')
    return RedirectResponse(with_notice(return_to or f'/player/{dota_id}', f'Blocked {dota_id}', 'warning'), status_code=303)


@app.post('/player/{dota_id}/unblacklist', dependencies=[Depends(csrf_guard)])
async def web_unblacklist(dota_id: str, session: AsyncSession = Depends(get_session)):
    await unblacklist_player(session, dota_id)
    return RedirectResponse(with_notice(f'/player/{dota_id}', 'Player unblocked'), status_code=303)


@app.post('/player/{dota_id}/delete', dependencies=[Depends(csrf_guard)])
async def web_delete_player(dota_id: str, return_to: str = Form('/'), session: AsyncSession = Depends(get_session)):
    player = (await session.execute(select(Player).where(Player.dota_id == dota_id))).scalar_one_or_none()
    if not player:
        return RedirectResponse(with_notice(return_to, f'Player {dota_id} not found', 'warning'), status_code=303)

    await session.execute(update(MatchPlayer).where(MatchPlayer.player_id == player.id).values(player_id=None))
    await session.execute(delete(InviteQueue).where(InviteQueue.player_id == player.id))
    await session.execute(delete(PlayerSlotLog).where(PlayerSlotLog.player_id == player.id))
    await session.delete(player)
    await session.commit()
    return RedirectResponse(with_notice(return_to, f'Deleted {dota_id} from database', 'warning'), status_code=303)


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
    return render_template('lobby.html', {'lobby': lobby, 'error': error}, request)


@app.get('/queue', response_class=HTMLResponse)
async def queue_page(request: Request, session: AsyncSession = Depends(get_session)):
    redirect = require_auth(request)
    if redirect:
        return redirect
    error = None
    ranked = []
    queue_settings = {}
    try:
        chatters = await streamer_proxy.get_chatters()
        online_names = {c.get('user_login', '').lower() for c in chatters if c.get('user_login')}
        ranked, queue_settings = await ranked_queue_players(session, online_names)
    except Exception as exc:
        error = str(exc)
    return render_template('queue.html', {'ranked': ranked, 'settings': queue_settings, 'error': error}, request)


@app.post('/invite/{steam_id}', dependencies=[Depends(csrf_guard)])
async def web_invite(steam_id: str, return_to: str = Form('/')):
    await streamer_proxy.invite(steam_id)
    return RedirectResponse(with_notice(return_to, f'Invite sent to {steam_id}'), status_code=303)


@app.post('/quick-invite', dependencies=[Depends(csrf_guard)])
async def web_quick_invite(limit: int = Form(1), return_to: str = Form('/'), session: AsyncSession = Depends(get_session)):
    chatters = await streamer_proxy.get_chatters()
    online_names = {c.get('user_login', '').lower() for c in chatters if c.get('user_login')}
    ranked, _ = await ranked_queue_players(session, online_names)
    sent = 0
    for item in ranked[:max(1, min(limit, 10))]:
        player = item['player']
        if player.steam_id:
            await streamer_proxy.invite(player.steam_id)
            sent += 1
    return RedirectResponse(with_notice(return_to, f'Quick invite sent: {sent}'), status_code=303)


@app.get('/settings', response_class=HTMLResponse)
async def settings_page(request: Request, session: AsyncSession = Depends(get_session)):
    redirect = require_auth(request)
    if redirect:
        return redirect
    current = await get_all_settings(session)
    return render_template('settings.html', {'settings': current}, request)


@app.post('/settings', dependencies=[Depends(csrf_guard)])
async def settings_save(require_twitch_online: str = Form(...), special_first_twitch_names: str = Form(''), queue_strategy: str = Form(...), invite_timeout_seconds: int = Form(...), return_to: str = Form('/'), session: AsyncSession = Depends(get_session)):
    allowed_strategies = {'oldest_played', 'most_slots', 'recent_slot', 'recent_played', 'most_active'}
    if queue_strategy not in allowed_strategies:
        queue_strategy = 'oldest_played'
    invite_timeout_seconds = min(max(invite_timeout_seconds, 5), 600)
    await set_setting(session, 'require_twitch_online', 'true' if require_twitch_online == 'true' else 'false')
    await set_setting(session, 'special_first_twitch_names', special_first_twitch_names.strip())
    await set_setting(session, 'queue_strategy', queue_strategy)
    await set_setting(session, 'invite_timeout_seconds', str(invite_timeout_seconds))
    return RedirectResponse(with_notice(return_to, 'Settings saved'), status_code=303)
