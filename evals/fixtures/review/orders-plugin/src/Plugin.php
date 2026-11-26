<?php

namespace acme\orders;

use Craft;
use craft\base\Plugin as BasePlugin;
use craft\events\RegisterUserPermissionsEvent;
use craft\services\UserPermissions;
use yii\base\Event;

/**
 * Orders plugin.
 *
 * @author Acme
 * @since 1.0.0
 */
class Plugin extends BasePlugin
{
    // Constants
    // =========================================================================

    public const PERMISSION_MANAGE_NOTES = 'orders-manage-notes';

    // Public Methods
    // =========================================================================

    /**
     * @inheritdoc
     * @author Acme
     */
    public function init(): void
    {
        parent::init();

        $this->setComponents([
            'orders' => services\OrdersService::class,
        ]);

        Event::on(
            UserPermissions::class,
            UserPermissions::EVENT_REGISTER_PERMISSIONS,
            function(RegisterUserPermissionsEvent $event) {
                $event->permissions[] = [
                    'heading' => Craft::t('orders', 'Orders'),
                    'permissions' => [
                        self::PERMISSION_MANAGE_NOTES => ['label' => Craft::t('orders', 'Manage order notes')],
                    ],
                ];
            }
        );
    }
}
