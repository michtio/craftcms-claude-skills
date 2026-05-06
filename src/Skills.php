<?php

namespace Michtio\CraftCmsClaudeSkills;

use InvalidArgumentException;

/**
 * Skills exposes the bundled Craft CMS Claude Code skills as a thin PHP API.
 *
 * The package doubles as a Claude Code skills plugin (markdown content under
 * `skills/`) and a composer library. Consumers (notably `craftpulse/craft-cortex`)
 * use this helper to enumerate skills and read their content from disk without
 * having to know the on-disk layout.
 *
 * The helper is intentionally dumb: no caching, no normalisation, no opinions.
 * Consumers layer their own registries on top.
 *
 * @author Craftpulse
 * @since 1.4.0
 */
final class Skills
{
    // Constants
    // =========================================================================

    /**
     * Filename of a skill's primary markdown document.
     *
     * @author Craftpulse
     * @since 1.4.0
     */
    private const _SKILL_FILENAME = 'SKILL.md';

    /**
     * Directory name (relative to a skill) that holds reference markdown files.
     *
     * @author Craftpulse
     * @since 1.4.0
     */
    private const _REFERENCES_DIR = 'references';

    // Public Methods
    // =========================================================================

    /**
     * Returns the skill names that ship with the package.
     *
     * Scans the `skills/` directory and returns the names of subdirectories
     * that contain a `SKILL.md` file. Sorted alphabetically. Hidden entries
     * (dotfiles) are ignored.
     *
     * The filesystem is the source of truth; the `.claude-plugin/plugin.json`
     * manifest is intentionally not consulted here — its contents are for
     * Claude Code, and they have been observed to drift from disk reality.
     *
     * @return array<int, string>
     *
     * @author Craftpulse
     * @since 1.4.0
     */
    public static function skillNames(): array
    {
        $skillsDir = self::path() . '/skills';

        if (!is_dir($skillsDir)) {
            return [];
        }

        $names = [];

        foreach (scandir($skillsDir) ?: [] as $entry) {
            if ($entry === '' || $entry[0] === '.') {
                continue;
            }

            if (!is_file($skillsDir . '/' . $entry . '/' . self::_SKILL_FILENAME)) {
                continue;
            }

            $names[] = $entry;
        }

        sort($names);

        return $names;
    }

    /**
     * Returns whether the named skill exists.
     *
     * @param string $name
     * @return bool
     *
     * @author Craftpulse
     * @since 1.4.0
     */
    public static function hasSkill(string $name): bool
    {
        if (!self::_isSafeName($name)) {
            return false;
        }

        return is_file(self::path() . '/skills/' . $name . '/' . self::_SKILL_FILENAME);
    }

    /**
     * Returns the contents of a skill's `SKILL.md` document.
     *
     * @param string $name
     * @return string
     *
     * @throws InvalidArgumentException if the skill does not exist or cannot be read.
     *
     * @author Craftpulse
     * @since 1.4.0
     */
    public static function content(string $name): string
    {
        if (!self::hasSkill($name)) {
            throw new InvalidArgumentException("Skill \"{$name}\" does not exist.");
        }

        $path = self::path() . '/skills/' . $name . '/' . self::_SKILL_FILENAME;
        $contents = @file_get_contents($path);

        if ($contents === false) {
            throw new InvalidArgumentException("Skill \"{$name}\" exists but could not be read.");
        }

        return $contents;
    }

    /**
     * Returns the reference document names for a skill.
     *
     * Returns the basenames (without `.md` extension) of markdown files in
     * the skill's `references/` directory. Sorted alphabetically. Returns an
     * empty array when the skill has no references directory.
     *
     * @param string $name
     * @return array<int, string>
     *
     * @throws InvalidArgumentException if the skill does not exist.
     *
     * @author Craftpulse
     * @since 1.4.0
     */
    public static function references(string $name): array
    {
        if (!self::hasSkill($name)) {
            throw new InvalidArgumentException("Skill \"{$name}\" does not exist.");
        }

        $dir = self::path() . '/skills/' . $name . '/' . self::_REFERENCES_DIR;

        if (!is_dir($dir)) {
            return [];
        }

        $names = [];

        foreach (scandir($dir) ?: [] as $entry) {
            if ($entry === '' || $entry[0] === '.') {
                continue;
            }

            if (substr($entry, -3) !== '.md') {
                continue;
            }

            if (!is_file($dir . '/' . $entry)) {
                continue;
            }

            $names[] = substr($entry, 0, -3);
        }

        sort($names);

        return $names;
    }

    /**
     * Returns whether the named reference exists for the given skill.
     *
     * @param string $name
     * @param string $reference
     * @return bool
     *
     * @author Craftpulse
     * @since 1.4.0
     */
    public static function hasReference(string $name, string $reference): bool
    {
        if (!self::_isSafeName($name) || !self::_isSafeName($reference)) {
            return false;
        }

        return is_file(self::_referencePath($name, $reference));
    }

    /**
     * Returns the contents of a reference document.
     *
     * @param string $name
     * @param string $reference
     * @return string
     *
     * @throws InvalidArgumentException if the skill or reference does not exist, or cannot be read.
     *
     * @author Craftpulse
     * @since 1.4.0
     */
    public static function referenceContent(string $name, string $reference): string
    {
        if (!self::hasReference($name, $reference)) {
            throw new InvalidArgumentException("Reference \"{$reference}\" does not exist for skill \"{$name}\".");
        }

        $contents = @file_get_contents(self::_referencePath($name, $reference));

        if ($contents === false) {
            throw new InvalidArgumentException("Reference \"{$reference}\" for skill \"{$name}\" exists but could not be read.");
        }

        return $contents;
    }

    /**
     * Returns the absolute path to the package root.
     *
     * Resolves to one directory above `src/`, which is the repo root in
     * source checkouts and the package directory under `vendor/` in composer
     * installs.
     *
     * @return string
     *
     * @author Craftpulse
     * @since 1.4.0
     */
    public static function path(): string
    {
        return dirname(__DIR__);
    }

    // Private Methods
    // =========================================================================

    /**
     * Builds the absolute path to a reference markdown file.
     *
     * @param string $name
     * @param string $reference
     * @return string
     *
     * @author Craftpulse
     * @since 1.4.0
     */
    private static function _referencePath(string $name, string $reference): string
    {
        return self::path() . '/skills/' . $name . '/' . self::_REFERENCES_DIR . '/' . $reference . '.md';
    }

    /**
     * Returns whether a name is safe to use as a path segment.
     *
     * Rejects empty strings, dot-segments, and any value containing slashes,
     * backslashes, or null bytes. This is a defence-in-depth check against
     * path traversal — consumers (e.g. an MCP server) may forward names
     * received over an untrusted transport.
     *
     * @param string $name
     * @return bool
     *
     * @author Craftpulse
     * @since 1.4.0
     */
    private static function _isSafeName(string $name): bool
    {
        if ($name === '' || $name === '.' || $name === '..') {
            return false;
        }

        if (strpbrk($name, "/\\\0") !== false) {
            return false;
        }

        return true;
    }
}
