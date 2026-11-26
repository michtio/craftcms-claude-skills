<?php

namespace acme\orders\controllers;

use acme\orders\Plugin;
use craft\web\Controller;
use yii\web\Response;

/**
 * Lets customers export their orders as CSV from the front end.
 *
 * @author Acme
 * @since 1.1.0
 */
class ExportController extends Controller
{
    // Public Methods
    // =========================================================================

    /**
     * Downloads the orders of a customer as CSV.
     *
     * @return Response
     * @author Acme
     */
    public function actionDownload(): Response
    {
        $this->requirePostRequest();
        $this->requireLogin();

        $customerId = (int)$this->request->getRequiredBodyParam('customerId');
        $rows = Plugin::getInstance()->orders->exportRows($customerId);

        return $this->response->sendContentAsFile(
            $this->getView()->renderTemplate('orders/export/_csv', ['rows' => $rows]),
            'orders.csv',
            ['mimeType' => 'text/csv'],
        );
    }
}
