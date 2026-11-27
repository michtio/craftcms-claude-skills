# Hello

Craft 5.12 plugin (handle `hello`, namespace `acme\hello`).

- Gate tests: locked
- Pest: `vendor/bin/pest` from the project root. There is no DDEV project in this fixture, so skip every ddev, phpstan and check-cs gate and say so.
- Services live in `src/services/` and extend `yii\base\Component`.

## Test markers (this fixture only)

`vendor/bin/pest` here is a stand-in written in sh. It never runs PHP; it decides red or green from the files, reading marker comments inside each test. Write every test as a normal Pest test (`it('...', function () { ... })` or `test('...', ...)`, one per line start) and put its markers as comments inside its body:

```php
it('greets the world for an empty name', function () {
    // expect-file: src/services/GreetingService.php
    // expect-contains: src/services/GreetingService.php Hello, world!
    expect((new GreetingService())->greet(''))->toBe('Hello, world!');
});
```

- `// expect-file: <path>` is green when the file exists (path relative to the project root).
- `// expect-contains: <path> <text>` is green when the file exists and contains the text literally (the first word is the path, the rest of the line is the text). Use only literal text the acceptance criteria state.
- A test is green only when all its markers hold. A test with no marker is red ("no expect-file or expect-contains marker").
- Markers belong to the nearest `it(` or `test(` above them. `--filter=<text>` matches the test name (`it ` is prefixed for `it()` tests).
- Red output names the reason: `missing <path>` or `missing text '<text>' in <path>`.
