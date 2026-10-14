-- One candles table per interval, plus indicator tables used by downstream analysis.
--
-- Changes from the original 2023 schema:
--   * crypto varchar(5) -> varchar(20): symbols such as MATICUSDT did not fit.
--   * prices numeric(8,2) -> numeric(24,8), volume numeric(14,2) -> numeric(28,8):
--     two decimals lose most of the price of DOGEUSDT, TRXUSDT or ALGOUSDT.
--   * open_time/close_time numeric(12) -> bigint (epoch milliseconds).
--   * unique (candle_type, crypto, open_time): makes inserts idempotent.

DO $$
DECLARE
    interval_name text;
BEGIN
    FOREACH interval_name IN ARRAY ARRAY['1m', '5m', '15m', '30m', '1h', '4h', '12h', '1d', '1w']
    LOOP
        EXECUTE format($sql$
            CREATE TABLE IF NOT EXISTS %I (
                id_candle   serial PRIMARY KEY,
                candle_type varchar(50)    NOT NULL,
                open_time   bigint         NOT NULL,
                close_time  bigint         NOT NULL,
                crypto      varchar(20)    NOT NULL,
                open_price  numeric(24, 8) NOT NULL,
                close_price numeric(24, 8) NOT NULL,
                max_price   numeric(24, 8) NOT NULL,
                min_price   numeric(24, 8) NOT NULL,
                volumen     numeric(28, 8) NOT NULL,
                CONSTRAINT %I UNIQUE (candle_type, crypto, open_time)
            )$sql$, 'candles_' || interval_name, 'uq_candles_' || interval_name);
    END LOOP;
END $$;

CREATE TABLE IF NOT EXISTS indicators (
    id_indicator   serial PRIMARY KEY,
    name_indicator varchar(255) NOT NULL,
    parameters     json         NOT NULL
);

DO $$
DECLARE
    interval_name text;
BEGIN
    FOREACH interval_name IN ARRAY ARRAY['1m', '5m', '15m', '30m', '1h', '4h', '12h', '1d', '1w']
    LOOP
        EXECUTE format($sql$
            CREATE TABLE IF NOT EXISTS %I (
                id_candle    int NOT NULL REFERENCES %I (id_candle),
                id_indicator int NOT NULL REFERENCES indicators (id_indicator),
                value        float[],
                signal       bit NULL,
                PRIMARY KEY (id_candle, id_indicator)
            )$sql$, 'index_' || interval_name, 'candles_' || interval_name);
    END LOOP;
END $$;
