#!/usr/bin/env bash
#
# Validate every skills/*/SKILL.md frontmatter against the Agent Skills spec
# (https://agentskills.io/specification) and Claude Code's listing cap
# (https://code.claude.com/docs/en/skills).
#
#   bash bin/validate-skills.sh
#
# Checks, per skill:
#   - frontmatter parses as strict YAML (an invalid escape such as \u inside a
#     double-quoted string fails here, as it does in PhpStorm and other
#     spec-strict clients)
#   - only known keys: the spec's fields plus Claude Code's `when_to_use`
#   - name: 1-64 chars, lowercase letters/digits/hyphens, matches the directory
#   - description: 1-1024 chars (spec limit)
#   - description + " - " + when_to_use: <= 1536 chars (Claude Code truncates
#     the combined text in the skill listing beyond this)
#
# Exits non-zero on any failure. Called by bin/release.sh and CI.
#
# Requires: ruby (macOS system ruby and every GitHub ubuntu runner have it).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ruby -ryaml - "$REPO_ROOT"/skills/*/SKILL.md <<'RUBY'
ALLOWED = %w[name description license compatibility metadata allowed-tools when_to_use]
DESC_MAX = 1024
LISTING_MAX = 1536
SEPARATOR = " - "

failures = 0
ARGV.each do |path|
  skill = File.basename(File.dirname(path))
  errors = []
  parts = File.read(path).split(/^---\s*$/, 3)

  if parts.length < 3 || !parts[0].strip.empty?
    errors << "missing --- frontmatter block"
  else
    begin
      fm = YAML.safe_load(parts[1])
    rescue Psych::Exception => e
      fm = nil
      errors << "invalid YAML: #{e.message.lines.first.strip}"
    end

    if fm.is_a?(Hash)
      extra = fm.keys - ALLOWED
      errors << "unknown keys: #{extra.join(', ')}" unless extra.empty?

      name = fm["name"].to_s
      errors << "name '#{name}' does not match directory '#{skill}'" unless name == skill
      errors << "name must be 1-64 lowercase letters, digits, hyphens" unless name.match?(/\A[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?\z/)

      desc = fm["description"].to_s
      wtu = fm["when_to_use"].to_s
      errors << "description is empty" if desc.strip.empty?
      errors << "description is #{desc.length} chars (max #{DESC_MAX})" if desc.length > DESC_MAX

      listing = wtu.empty? ? desc.length : desc.length + SEPARATOR.length + wtu.length
      errors << "description + when_to_use is #{listing} chars (max #{LISTING_MAX})" if listing > LISTING_MAX
    elsif fm
      errors << "frontmatter is not a mapping"
    end
  end

  if errors.empty?
    puts "ok    #{skill}"
  else
    failures += 1
    errors.each { |e| puts "FAIL  #{skill}: #{e}" }
  end
end

exit(failures.zero? ? 0 : 1)
RUBY
