from secrets import compare_digest, token_urlsafe

from fastapi import HTTPException, Request

CSRF_COOKIE_NAME = 'csrf_token'


def csrf_token_for_request(request: Request) -> str:
    return request.cookies.get(CSRF_COOKIE_NAME) or token_urlsafe(32)


async def csrf_guard(request: Request) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    form = await request.form()
    submitted_token = form.get('csrf_token')
    if not cookie_token or not submitted_token or not compare_digest(cookie_token, str(submitted_token)):
        raise HTTPException(status_code=403, detail='Invalid CSRF token')
