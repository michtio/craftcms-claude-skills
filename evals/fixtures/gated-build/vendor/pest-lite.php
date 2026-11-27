<?php
// A very small Pest stand-in for the gated-build eval fixture. It implements
// test(), it(), uses(), beforeEach(), expect() and the common expectations, and
// autoloads acme\hello\ from src/. A missing class, a wrong value or an
// unimplemented expectation is a red test; everything green exits 0.

namespace yii\base {
    class Component
    {
    }
}

namespace {
    $root = dirname(__DIR__);

    spl_autoload_register(function (string $class) use ($root): void {
        $prefix = 'acme\\hello\\';
        if (strncmp($class, $prefix, strlen($prefix)) === 0) {
            $file = $root . '/src/' . str_replace('\\', '/', substr($class, strlen($prefix))) . '.php';
            if (is_file($file)) {
                require $file;
            }
        }
    });

    $GLOBALS['__tests'] = [];
    $GLOBALS['__before'] = [];

    class PestLiteChain
    {
        public function __call(string $name, array $args): self
        {
            return $this;
        }
    }

    class PestLiteExpectation
    {
        private bool $negate = false;

        public function __construct(public mixed $value)
        {
        }

        public function __get(string $name): self
        {
            if ($name === 'not') {
                $this->negate = !$this->negate;
                return $this;
            }
            throw new Exception("pest-lite: unsupported property $name");
        }

        private function check(bool $ok, string $message): self
        {
            if ($ok === $this->negate) {
                throw new Exception(($this->negate ? 'not: ' : '') . $message);
            }
            return $this;
        }

        public function __call(string $name, array $a): self
        {
            $v = $this->value;
            $show = fn($x) => var_export($x, true);
            switch ($name) {
                case 'toBe': return $this->check($v === $a[0], 'expected ' . $show($a[0]) . ', got ' . $show($v));
                case 'toEqual': return $this->check($v == $a[0], 'expected ' . $show($a[0]) . ', got ' . $show($v));
                case 'toBeTrue': return $this->check($v === true, 'expected true, got ' . $show($v));
                case 'toBeFalse': return $this->check($v === false, 'expected false, got ' . $show($v));
                case 'toBeNull': return $this->check($v === null, 'expected null, got ' . $show($v));
                case 'toBeEmpty': return $this->check(empty($v), 'expected empty, got ' . $show($v));
                case 'toBeString': return $this->check(is_string($v), 'expected a string');
                case 'toBeInt': return $this->check(is_int($v), 'expected an int');
                case 'toBeArray': return $this->check(is_array($v), 'expected an array');
                case 'toBeInstanceOf': return $this->check($v instanceof $a[0], 'expected an instance of ' . $a[0]);
                case 'toContain': return $this->check(is_string($v) ? str_contains($v, (string) $a[0]) : in_array($a[0], (array) $v, true), 'expected to contain ' . $show($a[0]));
                case 'toHaveCount': return $this->check(count($v) === $a[0], 'expected count ' . $a[0] . ', got ' . count($v));
                case 'toHaveKey': return $this->check(is_array($v) && array_key_exists($a[0], $v), 'expected key ' . $show($a[0]));
                case 'toMatch': return $this->check(preg_match($a[0], (string) $v) === 1, 'expected a match for ' . $a[0]);
                case 'toBeGreaterThan': return $this->check($v > $a[0], 'expected greater than ' . $show($a[0]));
                case 'toBeLessThan': return $this->check($v < $a[0], 'expected less than ' . $show($a[0]));
                case 'toThrow':
                    $thrown = null;
                    try {
                        ($v)();
                    } catch (Throwable $e) {
                        $thrown = $e;
                    }
                    $ok = $thrown !== null && (!isset($a[0]) || (class_exists($a[0]) ? $thrown instanceof $a[0] : str_contains($thrown->getMessage(), $a[0])));
                    return $this->check($ok, 'expected a throw');
            }
            throw new Exception("pest-lite: unsupported expectation $name");
        }
    }

    function uses(mixed ...$args): PestLiteChain
    {
        return new PestLiteChain();
    }

    function expect(mixed $value): PestLiteExpectation
    {
        return new PestLiteExpectation($value);
    }

    function beforeEach(callable $fn): void
    {
        $GLOBALS['__before'][] = $fn;
    }

    function test(string $name, ?callable $fn = null): PestLiteChain
    {
        $GLOBALS['__tests'][] = [$name, $fn];
        return new PestLiteChain();
    }

    function it(string $name, ?callable $fn = null): PestLiteChain
    {
        return test('it ' . $name, $fn);
    }

    $filter = null;
    $files = [];
    $argv = array_slice($_SERVER['argv'], 1);
    for ($i = 0; $i < count($argv); $i++) {
        if (str_starts_with($argv[$i], '--filter=')) {
            $filter = substr($argv[$i], 9);
        } elseif ($argv[$i] === '--filter') {
            $filter = $argv[++$i] ?? null;
        } elseif (!str_starts_with($argv[$i], '-')) {
            $files[] = $argv[$i];
        }
    }

    if (is_file($root . '/tests/Pest.php')) {
        require $root . '/tests/Pest.php';
    }
    if (!$files) {
        $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root . '/tests', FilesystemIterator::SKIP_DOTS));
        foreach ($it as $f) {
            if (str_ends_with($f->getFilename(), 'Test.php')) {
                $files[] = $f->getPathname();
            }
        }
        sort($files);
    }
    foreach ($files as $file) {
        try {
            require $file;
        } catch (Throwable $e) {
            echo "  ERROR  $file: " . $e->getMessage() . "\n";
            exit(2);
        }
    }

    $pass = 0;
    $fail = 0;
    foreach ($GLOBALS['__tests'] as [$name, $fn]) {
        if ($filter !== null && !(@preg_match('/' . str_replace('/', '\/', $filter) . '/i', $name) ?: stripos($name, $filter) !== false)) {
            continue;
        }
        try {
            foreach ($GLOBALS['__before'] as $before) {
                $before();
            }
            if ($fn === null) {
                throw new Exception('test has no body');
            }
            $fn();
            $pass++;
            echo "  PASS  $name\n";
        } catch (Throwable $e) {
            $fail++;
            echo "  FAIL  $name\n        " . get_class($e) . ': ' . $e->getMessage() . "\n";
        }
    }
    if ($pass + $fail === 0) {
        echo "  No tests found.\n";
        exit(1);
    }
    echo "\n  Tests: " . ($fail ? "$fail failed, " : '') . "$pass passed\n";
    exit($fail ? 1 : 0);
}
