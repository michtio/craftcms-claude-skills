# Email System

How to send email from Craft CMS 5: system messages, custom messages, programmatic sending, email templates, and events. For mailer transport configuration (SMTP, SES, Mailgun, etc.), see `config-app.md`. For `testToEmailAddress` and other general config settings, see `config-general.md`.

## Documentation

- Email settings: https://craftcms.com/docs/5.x/system/mail.html

## Common Pitfalls

- Sending email synchronously in a web request — use a queue job for non-trivial email sending. The SMTP handshake alone can take several seconds.
- Not testing with Mailpit — DDEV includes Mailpit at `https://yoursite.ddev.site:8026`. Zero config, captures all outbound mail.
- Hardcoding `fromEmail` — use `Craft::$app->getProjectConfig()->get('email.fromEmail')` or let the Mailer component handle defaults.
- Forgetting that system message bodies are rendered as Markdown — HTML tags work, but the body goes through Twig then Markdown (GFM) then the HTML wrapper template.
- Assuming `SentMessage::getMessage()->toString()` reflects the current message — it's a clone frozen at construction, so post-construction mutations are invisible. Custom transports must serialize after any mutating event, and never reuse an earlier serialization. See [Custom transports](#custom-transports-sentmessage-freezes-the-message-at-construction).
- Not accounting for per-site email overrides (since 5.6.0) — multi-site installs can have different `fromEmail`, `fromName`, `replyToEmail`, and HTML templates per site.

## Contents

- [System Messages](#system-messages)
- [Built-in System Messages](#built-in-system-messages)
- [Registering Custom System Messages](#registering-custom-system-messages)
- [Sending Email Programmatically](#sending-email-programmatically)
- [Email Templates](#email-templates)
- [Testing Email](#testing-email)
- [Events](#events)

## System Messages

System messages are admin-customizable email templates managed at **Utilities > System Messages** (Craft Pro only). Each message has:

| Property | Purpose |
|----------|---------|
| `key` | Unique identifier (e.g., `account_activation`) |
| `heading` | Display name in the CP utility |
| `subject` | Email subject line (rendered as Twig) |
| `body` | Email body (rendered as Twig, then parsed as Markdown GFM) |

Multi-site installs can customize messages per language. System messages are stored in project config under `email.messages`.

### Variables available in all system messages

| Variable | Type | Description |
|----------|------|-------------|
| `user` | `User` | The recipient user element |
| `link` | `string` | Tokenized URL (activation, verification, reset) |
| `emailKey` | `string` | The system message key |
| `fromEmail` | `string` | Sender email address |
| `replyToEmail` | `string` | Reply-to address |
| `fromName` | `string` | Sender name |
| `language` | `string` | Message language |

Standard Twig context is also available: `siteUrl()`, `siteName`, `now`, `craft.app`, etc.

## Built-in System Messages

| Key | Purpose | Key Variables |
|-----|---------|--------------|
| `account_activation` | New user account needs activation | `user`, `link` |
| `verify_new_email` | Existing user changed their email | `user`, `link` |
| `forgot_password` | User requested password reset | `user`, `link` |
| `test_email` | Sent from Settings > Email test button | `user` |

## Registering Custom System Messages

```php
use craft\events\RegisterEmailMessagesEvent;
use craft\services\SystemMessages;
use yii\base\Event;

Event::on(
    SystemMessages::class,
    SystemMessages::EVENT_REGISTER_MESSAGES,
    function(RegisterEmailMessagesEvent $event) {
        $event->messages[] = [
            'key' => 'my_plugin_order_confirmation',
            'heading' => Craft::t('my-plugin', 'Order Confirmation'),
            'subject' => Craft::t('my-plugin', 'Your order #{{ order.reference }}'),
            'body' => Craft::t('my-plugin', implode("\n\n", [
                'Hey {{ user.friendlyName }},',
                'Your order **{{ order.reference }}** has been confirmed.',
                '[View your order]({{ order.url }})',
            ])),
        ];
    }
);
```

Registered messages appear in **Utilities > System Messages** where admins can customize the subject and body per language.

## Sending Email Programmatically

### From a system message key

```php
$mailer = Craft::$app->getMailer();

$message = $mailer->composeFromKey('my_plugin_order_confirmation', [
    'user' => $user,
    'order' => $order,
]);

$message->setTo($user);
$success = $mailer->send($message);

if (!$success) {
    Craft::error(
        "Failed to send order confirmation to {$user->email}: {$message->error}",
        __METHOD__
    );
}
```

`composeFromKey()` loads the system message, renders subject/body as Twig with the provided variables, and returns a `craft\mail\Message` instance.

### Freeform composition

```php
$message = Craft::$app->getMailer()->compose()
    ->setTo($user)              // User element, email string, or array
    ->setSubject('Hello')
    ->setHtmlBody('<p>Content</p>')
    ->setTextBody('Content');

Craft::$app->getMailer()->send($message);
```

### Sending via queue job

For non-trivial email (marketing, bulk, transactional), wrap in a queue job to avoid blocking the web request:

```php
use craft\queue\BaseJob;

class SendNotification extends BaseJob
{
    public int $userId;
    public string $messageKey;
    public array $variables = [];

    /**
     * @inheritdoc
     */
    public function execute($queue): void
    {
        $user = Craft::$app->getUsers()->getUserById($this->userId);
        if (!$user) {
            return;
        }

        $mailer = Craft::$app->getMailer();
        $message = $mailer->composeFromKey($this->messageKey, array_merge(
            $this->variables,
            ['user' => $user]
        ));
        $message->setTo($user);

        if (!$mailer->send($message)) {
            throw new \RuntimeException("Email send failed: {$message->error}");
        }
    }

    /**
     * @inheritdoc
     */
    protected function defaultDescription(): ?string
    {
        return Craft::t('my-plugin', 'Sending notification email');
    }
}
```

### Message class

`craft\mail\Message` extends `yii\symfonymailer\Message`. Key methods:

| Method | Accepts | Notes |
|--------|---------|-------|
| `setTo()` | `User`, `string`, `array` | Normalizes via `MailerHelper::normalizeEmails()` |
| `setFrom()` | `User`, `string`, `array` | Defaults to mailer config `fromEmail`/`fromName` |
| `setReplyTo()` | `User`, `string`, `array` | |
| `setCc()` / `setBcc()` | `User`, `string`, `array` | |
| `setSubject()` | `string` | |
| `setHtmlBody()` | `string` | |
| `setTextBody()` | `string` | Auto-generated from HTML if omitted |

### Per-site email overrides (since 5.6.0)

`Mailer::$siteOverrides` allows different `fromEmail`, `fromName`, `replyToEmail`, and HTML template per site. Overrides are keyed by site UID:

```php
// Craft handles this via Settings > Email > Site Overrides
// Plugins sending email can specify a site:
$message = $mailer->composeFromKey('my_plugin_notification', [
    'user' => $user,
]);
$message->siteId = $site->id; // Override applies automatically
$message->setTo($user);
$mailer->send($message);
```

When `$message->siteId` is set, Craft looks up the site's overrides and applies them before sending. This is relevant for multi-site installs where different sites have different brands, from addresses, or email templates.

## Email Templates

### Rendering pipeline

For system messages (`composeFromKey`):

1. Load system message by key (admin-customized or default)
2. Render subject as sandboxed Twig
3. Render body as Twig, then parse as Markdown (GFM)
4. Wrap in the HTML email template

### HTML email template

Default template: `_special/email.twig` — minimal wrapper that renders `{{ body }}` inside styled HTML with `<html lang="{{ language }}">`.

Custom template: Set at **Settings > Email > HTML Email Template** (path relative to `templates/`). The template receives:

| Variable | Type | Description |
|----------|------|-------------|
| `body` | `string` | Already-rendered Markdown HTML |
| `user` | `User` | Recipient |
| `language` | `string` | Message language |

Per-site template overrides are available since Craft 5.6.

### Twig sandbox

When `enableTwigSandbox` is enabled in general config, system messages render in a restricted Twig environment. Customizable via `config/twig-sandbox.php`.

## Testing Email

| Method | How |
|--------|-----|
| **DDEV Mailpit** | Built-in at `https://yoursite.ddev.site:8026`. Captures all mail. Zero config. |
| **CP test button** | Settings > Email > Test. Sends `test_email` system message. |
| **`testToEmailAddress`** | General config setting. Redirects all outbound mail to a single address. Accepts string, array, or env var. |
| **Debug toolbar** | Mail panel shows emails sent during a request. |

## Events

| Event | Class | Constant | When |
|-------|-------|----------|------|
| Before prep | `craft\mail\Mailer` | `EVENT_BEFORE_PREP` | Before message body is rendered (subject/body not yet compiled). Cancelable. |
| Before send | `yii\mail\BaseMailer` | `EVENT_BEFORE_SEND` | After prep, before transport dispatch. `$event->message` available. Set `$event->isValid = false` to cancel. |
| After send | `yii\mail\BaseMailer` | `EVENT_AFTER_SEND` | After transport dispatch. `$event->isSuccessful` indicates delivery result. |
| Register messages | `craft\services\SystemMessages` | `EVENT_REGISTER_MESSAGES` | When system messages are collected. Add custom messages here. |
| Register transports | `craft\helpers\MailerHelper` | `EVENT_REGISTER_MAILER_TRANSPORTS` | When transport adapters are collected. Add custom transport adapters here. |

### Custom transports: `SentMessage` freezes the message at construction

If you're writing a transport adapter (or anything that serializes a message to hand to an API), know what `Symfony\Component\Mailer\SentMessage` actually holds. Its constructor takes a **clone** and serializes it immediately:

```php
// Symfony\Component\Mailer\SentMessage::__construct() — symfony/mailer 7.4
$this->original = $message;

if ($message instanceof Message) {
    $message = clone $message;
    $headers = $message->getHeaders();
    // ...
    $this->raw = new RawMessage($message->toIterable());
}
```

So there are two different views of the message:

| Accessor | Returns | Reflects later mutations? |
|----------|---------|--------------------------|
| `getMessage()` | `$this->raw` — the frozen clone | **No** |
| `getOriginalMessage()` | `$this->original` — the live object | Yes |

`getMessage()->toString()` is therefore a snapshot taken at construction time. Any listener that mutates the message *after* `SentMessage` was built — adding headers, rewriting recipients, injecting tracking, applying a footer — is invisible to it. The email sends without those changes, and nothing errors.

Symfony's own `AbstractTransport::send()` gets the ordering right: it dispatches `MessageEvent`, reads `$event->getMessage()` back, and *then* constructs `SentMessage`. Custom transports go wrong when they deviate:

- **Serializing before the mutating event.** Build the payload after every before-send hook has run, not while assembling.
- **Reusing an earlier serialization.** A common shape is serializing once to check the size against an API limit, then reusing that string as the payload. If anything mutated the message in between, you ship the stale version. Re-serialize, or size-check the final serialization.

```php
// Right — serialize once, after mutations, and use that exact string
protected function doSend(SentMessage $message): void
{
    // getMessage() is the post-event frozen clone; that's what should go on the
    // wire. Don't rebuild from getOriginalMessage() unless you know a later
    // mutation must be picked up — the two can disagree.
    $mime = $message->getMessage()->toString();

    if (strlen($mime) > self::MAX_PAYLOAD_BYTES) {
        throw new TransportException('Message exceeds the provider payload limit.');
    }

    $this->_client->send($mime);   // same string that was size-checked
}
```

Craft's layer sits above this: `craft\mail\Mailer` extends `yii\symfonymailer\Mailer`, and Yii's `BaseMailer::send()` fires `EVENT_BEFORE_SEND` before handing off to the transport. A listener on that event mutates the message *before* `SentMessage` exists, so it is picked up normally — the trap is specific to transports that serialize early or cache a serialization.

### Logging sent emails

```php
use yii\mail\BaseMailer;
use yii\mail\MailEvent;
use yii\base\Event;

Event::on(
    BaseMailer::class,
    BaseMailer::EVENT_AFTER_SEND,
    function(MailEvent $event) {
        $to = implode(', ', array_keys($event->message->getTo() ?? []));
        $subject = $event->message->getSubject();
        $status = $event->isSuccessful ? 'sent' : 'failed';

        Craft::info(
            "Email {$status}: \"{$subject}\" to {$to}",
            'my-plugin'
        );
    }
);
```
