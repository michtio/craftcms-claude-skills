# Authorization Parity Across Surfaces

A plugin that exposes the same capability through more than one surface — CP controller, console command, GraphQL resolver, queue job acting on a user's behalf — has to enforce the same rules on each of them. Craft gives you no help here: each surface is a separate entry point with its own base class and its own conventions, and nothing warns you when one of them lets an action through that another blocks.

The pattern below is one shared gate plus per-surface tests. The reason it's worth the indirection is that the alternative — the same check written four times — drifts, and the drift is invisible until someone finds the surface that doesn't check.

## Contents

- One gate, every surface
- Console is not exempt
- GraphQL schema scope is not your permission matrix
- Self-referential guards don't exist unless you write them
- Parity means the same *plugin* gates, not the same *core* calls
- Proving parity with tests

## One gate, every surface

Put every authorization decision in one service, and have each surface call it. The gate answers plugin questions; it doesn't render, redirect, or throw HTTP exceptions — the surface translates the answer into its own idiom.

```php
namespace acme\myplugin\services;

use Craft;
use craft\elements\User;
use yii\base\Component;

/**
 * Single authorization gate for every surface: CP controllers, console
 * commands, GraphQL resolvers, and queue jobs acting for a user.
 *
 * Surfaces translate the boolean into their own failure mode. Keeping the
 * decision here is what makes parity testable — there is one place to change
 * and one place to assert against.
 *
 * @author  Acme
 * @since   1.0.0
 */
class Scope extends Component
{
    // =========================================================================
    // Public Methods
    // =========================================================================

    /**
     * Returns whether the user may approve the given submission.
     *
     * @param Submission $submission
     * @param User|null $user
     * @return bool
     */
    public function canApprove(Submission $submission, ?User $user): bool
    {
        if ($user === null) {
            return false;
        }

        if (!$user->can(Permissions::APPROVE)) {
            return false;
        }

        // Orthogonal to role: an author may hold the permission and still not
        // be allowed to approve their own work. See "Self-referential guards".
        if ($this->_isSelf($submission, $user) && !$user->can(Permissions::APPROVE_OWN)) {
            return false;
        }

        return true;
    }
}
```

Each surface calls the same method:

```php
// CP controller — HTTP idiom
if (!MyPlugin::getInstance()->getScope()->canApprove($submission, static::currentUser())) {
    throw new ForbiddenHttpException('You do not have permission to approve this submission.');
}

// Console controller — exit code idiom
if (!MyPlugin::getInstance()->getScope()->canApprove($submission, $actor)) {
    $this->stderr("Not permitted to approve submission {$submission->id}." . PHP_EOL, Console::FG_RED);

    return ExitCode::NOPERM;
}

// GraphQL resolver — resolver idiom
if (!MyPlugin::getInstance()->getScope()->canApprove($submission, $resolveInfo->context['user'] ?? null)) {
    throw new \GraphQL\Error\UserError('Not permitted.');
}

// Queue job acting for a user — re-check at execution time; permissions may
// have changed between enqueue and run.
if (!MyPlugin::getInstance()->getScope()->canApprove($submission, $actor)) {
    Craft::warning("Skipping approval for {$submission->id}: actor lost permission.", __METHOD__);

    return;
}
```

## Console is not exempt

The most common hole is a console command with no authorization at all, on the reasoning that "you need shell access to run it." That reasoning fails as soon as the command is the documented cron path, wired into a scheduler, or invocable through a hosting platform's command runner — at which point it's an unauthenticated capability with the plugin's full privileges.

Console commands that act **on behalf of a user** must resolve that user and run the same gate:

```php
/**
 * @param int $submissionId
 * @param string $actor Username or email of the user the action is performed as.
 * @return int
 */
public function actionApprove(int $submissionId, string $actor): int
{
    $user = Craft::$app->getUsers()->getUserByUsernameOrEmail($actor);

    if ($user === null) {
        $this->stderr("Unknown actor: {$actor}" . PHP_EOL, Console::FG_RED);

        return ExitCode::NOUSER;
    }

    // Same gate the CP controller calls.
    if (!MyPlugin::getInstance()->getScope()->canApprove($submission, $user)) {
        return ExitCode::NOPERM;
    }

    // ...
}
```

Commands that are genuinely system-level (maintenance, reindexing, GC) don't need a user — but make that explicit in the docblock rather than leaving the absence of a check ambiguous. "No gate because there's no actor" and "no gate because nobody wrote one" look identical in code.

## GraphQL schema scope is not your permission matrix

Craft's GraphQL schema scopes (`sections.{uid}:read`, `usergroups.{uid}:read`, …) control which **Craft** components a token can reach. They know nothing about your plugin's permissions, and a token with a broad schema does not imply the caller holds any of your handles.

So a resolver that checks only the schema scope — or nothing, on the reasoning that "the token was already validated" — bypasses the plugin's entire authorization model. Resolvers enforce plugin permissions themselves:

```php
public static function resolve($source, array $arguments, $context, ResolveInfo $resolveInfo): mixed
{
    // Schema scope got the caller to this field. It says nothing about whether
    // they hold the plugin's permission.
    $user = $context['user'] ?? null;

    if (!MyPlugin::getInstance()->getScope()->canViewSubmissions($user)) {
        throw new UserError('Not permitted.');
    }

    // ...
}
```

Note the identity question too: a GraphQL request authenticated by token may have **no** user. Decide deliberately whether a token-only caller is permitted, and encode that in the gate rather than letting `$user === null` fall through to a permissive branch.

## Self-referential guards don't exist unless you write them

Craft has no concept of "you may not approve your own submission," "you may not review your own change," or "you may not grant yourself this role." Peer permissions (`savePeerEntries`) are about *other people's* content, not about excluding your own — they're the opposite axis.

So every self-referential rule is yours to implement. Three properties make them behave:

1. **Live in the shared gate**, not in the controller — otherwise the console path skips them, which is exactly the hole that separation of duties is meant to close.
2. **Orthogonal to role checks.** A user can hold `APPROVE` and still be blocked on their own item. Don't fold the two into one permission; the resulting matrix can't express "approver who may self-approve in a break-glass case."
3. **An explicit bypass permission** (`my-plugin:approve-own`), so the exception is grantable, auditable, and visible in the CP permissions UI rather than implemented as a hardcoded admin escape hatch.

```php
/**
 * @param Submission $submission
 * @param User $user
 * @return bool
 */
private function _isSelf(Submission $submission, User $user): bool
{
    return $submission->authorId === $user->id;
}
```

Bear in mind admins hold every permission implicitly (`can()` returns `true` before any lookup), so an admin always self-approves. If the rule must bind admins too — a genuine compliance requirement — the gate needs an explicit `$user->admin` branch, and that decision should be documented as deliberate.

## Parity means the same *plugin* gates, not the same *core* calls

This is the nuance that makes naive parity refactors fail. Two surfaces should reach the same **decision**, which is not the same as executing the same **code**.

A web-path check often carries implicit context the web supplies. The classic case: a CP controller operating on a **draft** the current user owns can reasonably call `Craft::$app->getElements()->canSave($draft, $user)`, because draft ownership grants the user save rights on their own draft. Copy that line into a console command that resolves the **canonical** element, and `canSave()` now asks whether the user may save the canonical entry — a native Craft permission (`saveEntries:{uid}`) that a governed workflow deliberately withholds from the very users the plugin is supposed to let act.

The console path then fails for users who are, by the plugin's model, entitled. The fix isn't to grant them the native permission (that hands them unmediated access, defeating the plugin) — it's to call the **plugin's** gate on both surfaces and let the gate decide what core calls, if any, are appropriate for each context:

```php
// WRONG on a console path resolving the canonical element: demands a native
// permission the plugin's model intentionally withholds.
if (!Craft::$app->getElements()->canSave($entry, $user)) { /* ... */ }

// Right: the plugin's own decision, identical on both surfaces.
if (!MyPlugin::getInstance()->getScope()->canSubmitForApproval($entry, $user)) { /* ... */ }
```

When the gate genuinely needs different core checks per context, take the context as a parameter rather than duplicating the method — one decision, explicit about what varies.

## Proving parity with tests

Parity is a claim about multiple surfaces, so it needs a test per surface. A single service-level test proves the gate works, not that every surface calls it.

Write the matrix once and run it across surfaces:

```php
// Web
it('forbids approval without the permission (HTTP)', function () {
    $this->actingAs(userWithout(Permissions::APPROVE))
        ->post(UrlHelper::actionUrl('my-plugin/submissions/approve'), ['id' => $submission->id])
        ->assertForbidden();
});

// Console
it('forbids approval without the permission (console)', function () {
    $this->consoleCommand('my-plugin/submissions/approve', [(string) $submission->id, 'editor'])
        ->exitCode(ExitCode::NOPERM)
        ->run();
});

// GraphQL
it('forbids approval without the permission (graphql)', function () {
    expect(executeGraphql($mutation, user: userWithout(Permissions::APPROVE)))
        ->toHaveKey('errors');
});

// The self-referential rule, on every surface that can act
it('forbids self-approval without the bypass permission', function () {
    $own = submissionAuthoredBy($approver);

    expect(MyPlugin::getInstance()->getScope()->canApprove($own, $approver))->toBeFalse();
});
```

A checklist that catches the common holes when auditing an existing plugin:

- [ ] Every capability has exactly one gate method; no surface re-implements the logic.
- [ ] Every console command that acts for a user resolves that user and calls the gate.
- [ ] System-level commands document *why* there's no actor.
- [ ] Every GraphQL resolver calls the gate; none rely on schema scope alone.
- [ ] Queue jobs re-check at execution time, not only at enqueue time.
- [ ] Self-referential rules live in the gate with an explicit bypass permission.
- [ ] No surface copies a core `can*()` call whose implicit context it doesn't share.
- [ ] One authorization test per surface, not one per capability.

For the permission-handle mechanics (registration, constants, nested handles, and the silent orphan-drop in `saveGroupPermissions()`), see the `craftcms` skill's `permissions.md`.
