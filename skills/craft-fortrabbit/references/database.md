# Database — MySQL over SSH

Each fortrabbit environment can book one MySQL database. It is reachable only from inside the environment or through SSH. Craft connects through the `CRAFT_DB_*` ENV vars of the software template (see `deploy-and-environments.md`).

## Documentation

- Craft database: https://docs.fortrabbit.com/guides/craft-cms/database
- MySQL access: https://docs.fortrabbit.com/platform/mysql/access/intro
- SSH: https://docs.fortrabbit.com/platform/code-access/ssh
- Backups: https://docs.fortrabbit.com/platform/components/backups
- Craft troubleshooting: https://docs.fortrabbit.com/guides/craft-cms/troubleshooting

## Facts

- MySQL 8 is the only database fortrabbit offers. No Postgres, no MariaDB.
- One database per environment. Database name and user are the environment ID (`en-xxxxxx`).
- The password is in the dashboard (environment → MySQL → Access) and in `FORTRABBIT_DB_PASSWORD` on the environment. Don't commit it or paste it into a chat.
- After the first deployment the database is empty. Import the local database to bring content and structure up.
- The number of MySQL connections follows the PHP plan: one per PHP process, plus some for jobs and clients.

## Dump over SSH (down)

The dump runs on the environment, where the credentials are set, so no password crosses the network:

```sh
ssh <env>@ssh.<region>.frbit.app \
  'mysqldump --single-transaction --set-gtid-purged=OFF --no-tablespaces "$FORTRABBIT_DB_NAME"' \
  | gzip > /tmp/<env>.sql.gz
```

The single quotes make `$FORTRABBIT_DB_NAME` expand on the environment, not locally. Check the file isn't tiny before importing: a failed connection leaves an empty dump.

Import into DDEV:

```sh
ddev import-db --file=/tmp/<env>.sql.gz
ddev craft clear-caches/all
```

## Import (up)

Replaces every table that is in the dump. On production, back up first (the dump above, or a manual backup in the dashboard).

```sh
ddev export-db --file=/tmp/local.sql.gz
ssh <env>@ssh.<region>.frbit.app 'cat > /data/home/import.sql.gz' < /tmp/local.sql.gz
ssh <env>@ssh.<region>.frbit.app \
  'gzip -dc /data/home/import.sql.gz | mysql "$FORTRABBIT_DB_NAME"; rm -f /data/home/import.sql.gz'
```

The `mysql` and `mysqldump` clients on the environment are preconfigured with the credentials. The upload goes to `/data/home`, outside the web root `/data/www`.

Then match what differs between local and remote:

- **Security key**: the template generates a random `CRAFT_SECURITY_KEY`. Data encrypted locally (plugin API keys, some field values) can't be read with it. Copy the local `CRAFT_SECURITY_KEY` into the environment's ENV vars when you import a local database.
- **Table prefix**: a local `CRAFT_DB_TABLE_PREFIX` needs the same value on the environment.

## SSH tunnel for clients

For TablePlus, Sequel Ace or a local `mysql` client. Keep the tunnel open in one terminal:

```sh
ssh -N -L 13306:mysql:3306 <env>@ssh.<region>.frbit.app
```

Client settings over SSH: SSH host `ssh.<region>.frbit.app`, SSH user `<env>`, MySQL host `mysql`, port `3306`, user and database `<env>`, password from the dashboard. Through the tunnel above: host `127.0.0.1`, port `13306`.

## Backups

Every environment has backups: one full backup every 24 hours (file archive plus a `mysqldump`), stored off-site in the app's region, retention set by the backup plan. Manual backups, downloads and restores are in the dashboard. No point-in-time recovery.

`php craft db/backup` over SSH works too, but the dump slows the site while it runs, and the file lands on the storage, which counts toward its size.

## Common Pitfalls

1. **Importing a local database without the local security key** — errors when Craft decrypts stored values. Copy the local `CRAFT_SECURITY_KEY` to the environment.
2. **Different table prefix** — Craft finds no tables. Set `CRAFT_DB_TABLE_PREFIX` on both sides.
3. **Expanding `$FORTRABBIT_DB_NAME` locally** — double quotes around the remote command send an empty name. Use single quotes.
4. **Leaving dumps in the repository or on the storage** — dumps hold customer data and fill the storage. Keep them outside the repo, delete them when done.
5. **Expecting a public MySQL port** — there is none. Use SSH or the tunnel.
6. **Running out of connections** — many jobs plus a busy site can use up the connections of a small PHP plan. Scale PHP and MySQL together.
