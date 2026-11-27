---
id: SPEC-2026-11-27-greeting
title: Greeting service
status: approved
owner: Acme
approved_by: Acme
approved_on: 2026-11-27
---

# Greeting service

## Requirements

- **R1** The plugin MUST have a `GreetingService` with a `greet(string $name): string` method that returns a greeting for the name. (MUST)

## Acceptance criteria

- **AC1 (R1)** Given the name `Ada`, when `acme\hello\services\GreetingService::greet('Ada')` is called, then it returns `Hello, Ada!`.
- **AC2 (R1)** Given an empty name, when `acme\hello\services\GreetingService::greet('')` is called, then it returns `Hello, world!`.

## Open questions

None.
