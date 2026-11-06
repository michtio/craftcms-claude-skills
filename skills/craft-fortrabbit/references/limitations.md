# Limitations, Jobs and Detection Signals

What fortrabbit constrains for a Craft site, how the jobs component runs the Craft queue and crons, and the repo signals that identify a fortrabbit project.

## Documentation

- Limits: https://docs.fortrabbit.com/platform/concepts/limits
- Jobs component: https://docs.fortrabbit.com/platform/components/jobs
- Workers: https://docs.fortrabbit.com/platform/jobs/workers
- Crons: https://docs.fortrabbit.com/platform/jobs/crons
- Craft queue jobs: https://docs.fortrabbit.com/guides/craft-cms/queueing
- Craft image transforms: https://docs.fortrabbit.com/guides/craft-cms/image-transforms
- Craft caching: https://docs.fortrabbit.com/guides/craft-cms/caching
- Craft plugins: https://docs.fortrabbit.com/guides/craft-cms/plugins
- Logs: https://docs.fortrabbit.com/platform/settings/logs

## Runtime constraints

- **No root shell.** SSH works for deployment and everyday tasks. Nothing can be installed at runtime: no mail server, no global npm package, no extra PHP extension outside the PHP settings.
- **Node.js only in the build.** It runs in the build commands, not on the environment.
- **Heavy binaries in jobs only.** ffmpeg, Ghostscript, Chromium, cwebp and the image optimizers `jpegoptim`, `optipng`, `pngquant`, `gifsicle` are installed for jobs, not for web requests or SSH. Image-optimizer plugins that shell out to them must run in a worker job.
- **No `sendmail`.** PHP `mail()` fails. Configure Craft's mail transport as SMTP or a transactional mail provider adapter; SMTP ports 25, 465 and 587 are open outbound.
- **No wkhtmltopdf.** Use dompdf or a PDF service.
- **Executable bit.** Call PHP scripts through the interpreter: `php craft`, not `./craft`.
- **PHP does not autoscale.** The PHP plan sets memory and the number of PHP processes. When all processes are busy, the site answers 503; a request over the time limit answers 504.
- **SSH rate limit.** More than about 20 new SSH connections a minute from one IP gets throttled. Batch commands: `ssh … 'php craft migrate/all && php craft clear-caches/all'`.
- **Logs.** The template sets `CRAFT_STREAM_LOG=true`, so Craft logs to stderr. Read them in the dashboard's Logs tab, not in `storage/logs/`.

## The jobs component

Jobs is an optional component per environment. Jobs run in their own container with the same file system, database, ENV vars and settings as the environment, so heavy work doesn't slow web requests. Each successful deployment restarts all jobs, so they run the latest code. All jobs share the memory of the jobs plan.

### The Craft queue in a worker

By default Craft runs the queue through web requests, which block PHP processes meant for visitors. Move it to a worker:

1. Book the jobs component for the environment.
2. Add a worker job in the dashboard with the command `php craft queue/listen --verbose`.
3. Turn off web-triggered queue processing on that environment. Craft reads any general config setting from a `CRAFT_`-prefixed ENV var, so no config file change is needed:

```sh
# ENV vars of the fortrabbit environment that has the worker
CRAFT_RUN_QUEUE_AUTOMATICALLY=false
```

Without a worker, `runQueueAutomatically` set to `false` means the queue never runs. Keep it `true` locally and on environments without the jobs component.

### Image transforms

Transforms are behind many 504 errors and memory kills on Craft sites. Each transform loads the full source image into memory. When a transform doesn't exist yet, Craft queues a job and renders a temporary URL; whichever comes first, the queue job or the first browser request to the URL, creates the file.

- Run the queue in a worker, as above, so transforms happen there.
- Keep `generateTransformsBeforePageLoad` at its default `false`.
- Scale source images down before upload: about twice the largest display size. Memory grows with the pixel count.
- Define fewer transform sizes and formats.

### Crons

Cron jobs are jobs of the same component, set up in the dashboard with a five-field schedule in UTC. Output goes to the jobs logs. Use them for console commands on a schedule, e.g. a nightly `php craft resave/entries --section=news` or a plugin's sync command. Crons that start at the same time share the plan's memory.

## Caching notes

- A `{% cache %}` tag without a specific key creates many cache items with the same data, a poor hit rate and disk I/O.
- A full-page cache flushed every hour re-warms every hour, requesting every page again.
- Static CSS and JS in `templates/` are served through PHP. Put them in `web/`.

See the `craft-site` skill for `{% cache %}` usage and `craft-plugins` for Blitz.

## Detection signals

A Craft project is hosted on fortrabbit when any of these holds:

- A deploy file `.fortrabbit/deploy.yml`, `.fortrabbit/deploy.yaml` or `.fortrabbit/deploy.json` in the repo. A plain `.fortrabbit` file (not a folder) is a leftover from an older fortrabbit generation; ignore it.
- `FORTRABBIT_*` variables referenced in config files or documentation, e.g. `${FORTRABBIT_DB_HOST}`.
- Hostnames `*.frbit.app` or `*.frbit.cloud`, or `ssh.<region>.frbit.app` in scripts, README or `.ddev/` config.
- Environment IDs of the form `en-xxxxxx`, app IDs `ap-xxxxxx`.

There is no fortrabbit Composer package to detect: the platform needs nothing installed in the project.

## Common Pitfalls

1. **Queue running in web requests** — the site slows or 504s while editors work or after bulk saves. Worker job plus `CRAFT_RUN_QUEUE_AUTOMATICALLY=false` on that environment.
2. **`CRAFT_RUN_QUEUE_AUTOMATICALLY=false` without a worker** — jobs pile up, transforms stay temporary URLs. Book the jobs component or turn it back on.
3. **Image optimizer plugins on web requests** — the binaries aren't there. Run optimization in a worker job.
4. **`mail()` or Sendmail transport** — mail silently fails. Set an SMTP or provider transport in the email settings, with credentials in ENV vars.
5. **Many SSH calls in a loop** — the rate limit throttles the IP. Batch commands in one call.
6. **Looking for log files** — with `CRAFT_STREAM_LOG=true` Craft writes to stderr; read the dashboard logs.
