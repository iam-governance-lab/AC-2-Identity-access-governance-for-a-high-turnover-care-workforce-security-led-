"""Deployment entrypoint. Use run.py for the no-dependency local demonstration."""
import config
import database

def main():
    config.validate_config()
    from waitress import serve
    from wsgi import application
    database.init_db()
    import queue_worker
    stop=queue_worker.start()
    print(f'Sunhaven {config.RELEASE_VERSION} listening on {config.HOST}:{config.PORT}', flush=True)
    try:
        serve(application, host=config.HOST, port=config.PORT, threads=4,
          max_request_body_size=65536, channel_timeout=60,
          expose_tracebacks=False)
    finally:
        if stop:stop.set()

if __name__ == '__main__':
    main()
