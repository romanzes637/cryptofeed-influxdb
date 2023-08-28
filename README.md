# Cryptofeed with InfluxDB backend

## Database
1. Go to docker directory
```sh
cd docker
```
2. Generate self-signed certificate for InfluxDB
```sh
sudo openssl req -x509 -nodes -newkey rsa:2048 -keyout influxdb-selfsigned.key -out influxdb-selfsigned.crt -days 365
```
3. Copy and modify "dotenv" files from examples
```sh
cp influxdb/.env.example influxdb/.env
cp influxdb/.env.secret.example influxdb/.env.secret
```
4. Run database
```sh
docker compose --profile database up -d
```
> Check InfluxDB UI at http://YOUR_HOST:8086

## Collector(s)
1. Copy and modify "dotenv" files from examples
```sh
cp collector/.env.example collector/.env
cp collector/.env.secret.example collector/.env.secret
```
2. Run collector
```sh
docker compose --profile collector up
```
3. Change collector config file in `docker-compose.yaml`
```yaml
historical-candles-collector:
  ...
  command: ["conf/collect_historical_candles/binance.yaml"]
```
4. Modify collector config in `conf/collect_historical_candles` directory
```sh
cd ../conf/collect_historical_candles
cat binance.yaml
```
```yaml
exhange_kwargs:
    class: Binance
    symbols: [BTC-USDT, ETH-USDT]
    config: 
        log: {filename: demo.log, level: DEBUG, disabled: False}
candles_kwargs:
    method: candles_sync 
    interval: 1h
    start: "2023-08-01T00:00:00"
    # end: "2023-08-25T02:00:00"
    end: ~
    retry_count: 1
    retry_delay: 60
```
> For more informaton about *_kwargs, see cryptofeed [docs](https://github.com/bmoscon/cryptofeed/tree/master/docs)