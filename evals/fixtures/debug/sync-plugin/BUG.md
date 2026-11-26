# Bug report

Since 1.2.0, the nightly `SyncJob` exports 0 products for the French site (`fr`, siteId 2). The English site (`en`, siteId 1, primary) exports all 42 products. Nothing else changed on the server.

1.2.0 changed `src/jobs/SyncJob.php`: it now exports only live products (`->status('live')`) and filters rows per site.

The editor says the French products are enabled. A content export the editor ran this morning (`ddev craft` query, pasted by them):

```
elements_sites for section products, siteId 2: 42 rows, enabled = 1 on all 42
entries.postDate: all in 2025 or earlier; expiryDate: null on all 42
```

The queue log from last night's run is in `storage/logs/queue.log`.
