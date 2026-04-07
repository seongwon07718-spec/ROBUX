Exception in ASGI application
Traceback (most recent call last):
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\uvicorn\protocols\http\h11_impl.py", line 410, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        self.scope, self.receive, self.send
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\fastapi\applications.py", line 1160, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\starlette\applications.py", line 107, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\starlette\middleware\errors.py", line 186, in __call__
    raise exc
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\starlette\middleware\errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\starlette\middleware\exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\fastapi\middleware\asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\starlette\routing.py", line 716, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\starlette\routing.py", line 736, in app
    await route.handle(scope, receive, send)
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\starlette\routing.py", line 290, in handle
    await self.app(scope, receive, send)
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\fastapi\routing.py", line 130, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\fastapi\routing.py", line 116, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\fastapi\routing.py", line 670, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\fastapi\routing.py", line 324, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\user\Desktop\auto 로벅스 자판기\main.py", line 164, in get_purchase_logs
    cur.execute("""
    ~~~~~~~~~~~^^^^
        SELECT order_id, user_id, amount, robux, created_at, roblox_name, roblox_id, gamepass_name
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        FROM orders WHERE status = 'completed'
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        ORDER BY created_at DESC LIMIT ? OFFSET ?
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    """, (limit, offset))
    ^^^^^^^^^^^^^^^^^^^^^
sqlite3.OperationalError: no such column: roblox_name
