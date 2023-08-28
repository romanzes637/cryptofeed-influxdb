'''
Copyright (C) 2017-2023 Bryant Moscon - bmoscon@gmail.com

Please see the LICENSE file for the terms and conditions
associated with this software.
'''
import argparse
from decimal import Decimal
import asyncio
import aiohttp
import os
from datetime import datetime
import logging
import yaml

from cryptofeed import exchanges as cryptofeed_exchanges
from cryptofeed.backends.influxdb import CandlesInflux


LOG = logging.getLogger('feedhandler')
    
    
class CandlesInfluxSkipSSL(CandlesInflux):
    """CandleFlux without SSL verification (for self-signed InlfuxDB)"""
    
    async def http_write(self, data, headers=None):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
            
        async with self.session.post(self.addr, data=data, headers=headers, ssl=False) as resp:
            if resp.status >= 400:
                error = await resp.text()
                LOG.error("POST to %s failed: %d - %s", self.addr, resp.status, error)
            resp.raise_for_status()

            
async def wait(callback):
    """Wait until writer of callback is done and stop worker"""
    await callback.queue.join()
    await callback.stop()   


def convert_datetime(dt):
    """Convert datetime to "%Y-%m-%d %H:%M:%S" format used by cryptofeed"""
    if isinstance(dt, str):  # ISO-8601
        dt = datetime.fromisoformat(dt)
    if isinstance(dt, datetime):
        dt = datetime.utcfromtimestamp(dt.timestamp())
        dt = dt.strftime("%Y-%m-%d %H:%M:%S")
    return dt
    
    
def main(exhange_kwargs, candles_kwargs, callback_kwargs=None):
    """Collect historical candles with cryptofeed and dump them to the InfluxDB
    
    See Also:
        * https://github.com/bmoscon/cryptofeed/blob/master/cryptofeed/backends/backend.py
        * https://stackoverflow.com/questions/52582685/using-asyncio-queue-for-producer-consumer-flow
    """
    # Initialize callback
    callback_kwargs = {} if callback_kwargs is None else callback_kwargs
    callback_kwargs.setdefault('addr', os.getenv('INFLUXDB_V2_URL', 'https://localhost:8086'))
    callback_kwargs.setdefault('org', os.getenv('INFLUXDB_V2_ORG', 'cryptofeed'))
    callback_kwargs.setdefault('bucket', os.getenv('INFLUXDB_V2_BUCKET', 'cryptofeed'))
    callback_kwargs.setdefault('token', os.getenv('INFLUXDB_V2_TOKEN', None))
    cb = CandlesInfluxSkipSSL(**callback_kwargs)
 
    # Initialize exchange
    exchange_class = exhange_kwargs.pop('class')
    exchanges_class = getattr(cryptofeed_exchanges, exchange_class)    
    exchange = exchanges_class(**exhange_kwargs)
    
    # Initialize candles method
    candles_method = candles_kwargs.pop('method')
    candles_method = getattr(exchange, candles_method)    
    
    # Convert datetimes
    for k in ['start', 'end']:
        if k in candles_kwargs:
            v = candles_kwargs[k]
            candles_kwargs[k] = convert_datetime(v)
    
    # Start loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start callback
    cb.start(loop=loop, multiprocess=False)
    
    # Collect candles
    symbols = exhange_kwargs.get('symbols', [])
    for s in symbols:
        candles_kwargs['symbol'] = s
        g = candles_method(**candles_kwargs)
        for candles in g:
            print(exchange.id, s, len(candles))
            for c in candles:
                loop.create_task(cb(c, c.timestamp))
             
    # Wait callback's end
    loop.create_task(wait(cb))
    
    # Stop loop
    loop.run_until_complete(cb.worker)

    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config')
    args = parser.parse_args()
    
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)
    main(**config)
