import argparse
import config
import database

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Delete and recreate only the development demo database')
    parser.add_argument('--confirm-reset',action='store_true')
    args=parser.parse_args()
    if config.ENVIRONMENT != 'development' or config.AUTH_MODE != 'local' or not config.SEED_DEMO:
        parser.error('Reset is disabled outside local development demo mode')
    if not args.confirm_reset:
        parser.error('Stop the app, back up the database, then pass --confirm-reset to replace demo data')
    database.init_db(reset=True)
    print('Demo database reset: 42 fictional workers and 30 fictional residents.')
