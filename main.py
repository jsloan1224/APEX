import argparse
import asyncio
import json
import os
import sys

import yaml

from core.database import DatabaseManager
from core.ibkr_client import IBKRClient, IBKRConnectionError
from core.logger import configure_logging, get_logger
from agents.risk_manager import KillSwitch
from agents.market_data_agent import MarketDataAgent
from core.bar_buffer import BufferManager

VALID_INSTRUMENTS = {'ES', 'NQ', 'YM'}


def load_config(profile: str, market_override: str | None) -> dict:
    with open('config.yaml', 'r') as f:
        raw = yaml.safe_load(f)

    if profile not in raw['profiles']:
        sys.exit(f'Unknown profile: {profile}')

    cfg = dict(raw)
    profile_data = raw['profiles'][profile]
    cfg.update(profile_data)

    if market_override:
        cfg['traded_instrument'] = market_override.upper()

    return cfg


def validate_config(cfg: dict):
    ti = cfg.get('traded_instrument', '')
    if ti not in VALID_INSTRUMENTS:
        sys.exit(f'Invalid traded_instrument: {ti!r}. Must be one of {VALID_INSTRUMENTS}.')

    ctx = cfg.get('context_instruments', [])
    if ti in ctx:
        sys.exit(
            f'Configuration error: traded_instrument "{ti}" must NOT appear in '
            f'context_instruments {ctx}.'
        )


def print_summary(cfg: dict, profile: str):
    ti = cfg['traded_instrument']
    params = cfg.get('instrument_params', {}).get(ti, {})
    print()
    print('=' * 60)
    print(f'  APEX — Profile: {profile}')
    print(f'  *** TRADED INSTRUMENT: {ti} ***')
    print(f'  Context instruments : {cfg.get("context_instruments")}')
    print(f'  bias_timeframes     : {cfg.get("bias_timeframes")}')
    print(f'  fvg_detection_tfs   : {cfg.get("fvg_detection_timeframes")}')
    print(f'  smt_check_tfs       : {cfg.get("smt_check_timeframes")}')
    print(f'  instrument_params   : {params}')
    print(f'  Mode                : {cfg.get("mode")}')
    print('=' * 60)
    print()


def prompt_interactive(cfg: dict) -> dict:
    print('Interactive mode — press Enter to accept defaults.')
    for key in ('traded_instrument', 'mode'):
        val = input(f'  {key} [{cfg.get(key)}]: ').strip()
        if val:
            cfg[key] = val
    return cfg


async def run(args: argparse.Namespace):
    cfg = load_config(args.profile, args.market)

    configure_logging(cfg)
    logger = get_logger('apex.main')

    if args.interactive:
        cfg = prompt_interactive(cfg)

    validate_config(cfg)
    print_summary(cfg, args.profile)

    db_path = cfg.get('database', {}).get('path', 'data/apex.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = DatabaseManager(db_path)
    await db.init()

    ks = KillSwitch(cfg)

    ibkr = IBKRClient(cfg)
    if not args.dry_run:
        try:
            await ibkr.connect(dry_run=False)
            await db.log_event('IBKR_CONNECT', f'Connected to port {ibkr._port}')
        except IBKRConnectionError as exc:
            logger.error('IBKR connection failed: %s', exc)
            await db.log_event('IBKR_DISCONNECT', str(exc))

    mda = None
    if not args.dry_run:
        buffer_manager = BufferManager(
            instruments=[cfg['traded_instrument']] + cfg['context_instruments'],
            timeframes=cfg['fvg_detection_timeframes'],
            max_size=cfg['market_data']['bar_buffer_size'],
        )
        mda = MarketDataAgent(cfg, ibkr, db, buffer_manager)
        await mda.start()

    ti = cfg['traded_instrument']
    startup_detail = json.dumps({
        'profile': args.profile,
        'traded_instrument': ti,
        'mode': cfg.get('mode'),
    })
    await db.log_event('STARTUP', startup_detail)
    logger.info('STARTUP: %s', startup_detail)

    print(f'APEX SYSTEM READY — TRADING {ti}')

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await db.log_event('SHUTDOWN', 'KeyboardInterrupt')
        logger.info('SHUTDOWN')
        if mda is not None:
            await mda.stop()
        await db.close()
        if ibkr.is_connected():
            await ibkr.disconnect()


def main():
    parser = argparse.ArgumentParser(description='APEX Autonomous Futures Trading System')
    parser.add_argument('--profile', default='paper_default',
                        choices=['paper_default', 'conservative', 'aggressive'],
                        help='Config profile to use')
    parser.add_argument('--market', choices=['ES', 'NQ', 'YM'],
                        help='Override traded_instrument from profile')
    parser.add_argument('--dry-run', action='store_true',
                        help='Skip IBKR connection')
    parser.add_argument('--interactive', action='store_true',
                        help='Prompt for each parameter')
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == '__main__':
    main()
