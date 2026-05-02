# Testing

- Write tests alongside each layer, not after. Service tests with the service, controller tests with the controller.
- Pest over PHPUnit. Use `ddev exec vendor/bin/pest` to run, never `vendor/bin/pest` on the host.
- `--filter=ClassName` for targeted runs during development. Full suite before committing.
- `->site('*')` and `->status(null)` in test queries to avoid false negatives from site/status scoping.
- `actingAs($user)->post()` for controller tests. Assert both HTTP status and DB state.
- Test edge cases: empty results, missing entities, expired elements, permission denials.
- Factories for element setup. Never rely on database seeding or fixture ordering.
- Multi-site: test propagation behavior when the plugin touches elements across sites.
- Queue jobs: dispatch and assert the job processed correctly, not just that it was pushed.
- `Craft::$app->getProjectConfig()->muteEvents = true` when tests modify project config directly.
